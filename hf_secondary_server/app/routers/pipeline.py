from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl
import os
import uuid

from app.config import WORKDIR
from app.services.video import (
    ensure_workdir, get_meta, extract_last_frame,
    normalize_video_url, preflight_video_url, download_video,
    cleanup_workdir,
)
from app.services.s3_uploader import upload_file
from app.services.higgsfield import submit_minimax_i2v, poll_job_set

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class ContinueReq(BaseModel):
    previous_video_url: HttpUrl = Field(..., description="URL предыдущего видео")
    previous_prompt: str = Field(..., description="Промпт предыдущего видео (для контекста)")
    next_prompt: str = Field(..., description="Промпт, по которому создаётся новое видео")


class ContinueResp(BaseModel):
    new_video_url: HttpUrl
    used_prompt: str
    job_set_id: str
    frame_image_url: HttpUrl
    meta: dict


@router.post(
    "/continue",
    response_model=ContinueResp,
    summary="Продолжить видео одним вызовом",
    description=(
        "1) Скачивает предыдущее видео\n"
        "2) Берёт последний кадр и заливает его в Spaces (CDN)\n"
        "3) Отправляет image2video/minimax с составным промптом "
        "(previous→next)\n"
        "4) Ждёт завершения и возвращает URL нового видео + только next_prompt"
    ),
)
def continue_video(req: ContinueReq):
    ensure_workdir()

    raw_url = str(req.previous_video_url)
    safe_url = normalize_video_url(raw_url)
    pf = preflight_video_url(safe_url)
    print("preflight previous_video_url →", pf)
    if not pf.get("ok"):
        raise HTTPException(400, detail={
            "msg": "previous_video_url не выглядит как доступное видео",
            "checked_url": safe_url,
            "check": pf
        })

    vid_id = str(uuid.uuid4())
    local_video = os.path.join(WORKDIR, f"{vid_id}.mp4")
    download_video(safe_url, local_video)

    w, h, dur, fps = get_meta(local_video)
    frame_path = os.path.join(WORKDIR, f"{vid_id}_last.jpg")
    t = extract_last_frame(local_video, frame_path)

    try:
        frame_image_url = upload_file(frame_path, prefix="frames")
    except Exception as e:
        raise HTTPException(502, detail=f"upload to Spaces failed: {e}")


    prompt_text = (
        f"In first part of video was {req.previous_prompt}, "
        f"generate new part with {req.next_prompt}"
    )

    params = {
        "duration": 10,
        "resolution": "768",
        "enhance_prompt": True,
        "input_image": {"type": "image_url", "image_url": frame_image_url},
        "prompt": prompt_text,
    }

    try:
        submit = submit_minimax_i2v(params)
    except Exception as e:
        raise HTTPException(502, detail=f"submit to Higgsfield failed: {e}")

    job_set_id = submit.get("id")
    if not job_set_id:
        raise HTTPException(500, detail="No job_set_id in submit response")

    try:
        js = poll_job_set(job_set_id)
    except Exception as e:
        raise HTTPException(502, detail=f"poll job failed: {e}")

    jobs = js.get("jobs") or []
    status = jobs[0].get("status") if jobs else "unknown"
    if status != "completed":
        raise HTTPException(500, detail=f"Job did not complete (status={status})")

    try:
        new_video_url = jobs[0]["results"]["raw"]["url"]
    except Exception as e:
        raise HTTPException(500, detail=f"parse results failed: {e}")
        

    resp = ContinueResp(
        new_video_url=new_video_url,
        used_prompt=req.next_prompt, 
        job_set_id=job_set_id,
        frame_image_url=frame_image_url,
        meta={
            "previous_video_url": safe_url,
            "previous_prompt": req.previous_prompt,
            "video_meta": {"width": w, "height": h, "duration": dur, "fps": fps},
            "last_frame_time": round(t, 3),
            "higgsfield_params": params,
        },
    )

    try:
        cleanup_workdir()
    except Exception as e:
        print(f"[workdir] cleanup after /pipeline/continue warn: {e}")

    return resp

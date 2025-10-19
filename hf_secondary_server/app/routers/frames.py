from fastapi import APIRouter, HTTPException
import os
import uuid

from app.schemas import FromVideoReq, FromVideoResp
from app.config import WORKDIR
from app.services.video import ensure_workdir, curl_download, get_meta, extract_last_frame
from app.services.s3_uploader import upload_file

router = APIRouter(prefix="/frames", tags=["frames"])

@router.post(
    "/from-video",
    response_model=FromVideoResp,
    summary="Сделать image_url из последнего кадра видео",
    description="Скачивает видео по URL, берёт последний кадр, грузит его в S3 (Spaces), возвращает публичный image_url."
)
def frame_from_video(req: FromVideoReq):
    ensure_workdir()
    vid_id = str(uuid.uuid4())
    local_video = os.path.join(WORKDIR, f"{vid_id}.mp4")
    frame_path = os.path.join(WORKDIR, f"{vid_id}_last.jpg")
    t = None

    try:
        curl_download(req.video_url, local_video)

        w, h, dur, fps = get_meta(local_video)
        t = extract_last_frame(local_video, frame_path)

        image_url = upload_file(frame_path, prefix="frames")

        return FromVideoResp(
            video_url=req.video_url,
            local_video_path=local_video,
            width=w, height=h, duration=dur, fps=fps,
            frame_time_sec=round(t or 0, 3),
            local_frame_path=frame_path,
            image_url=image_url
        )

    finally:
        try:
            if os.path.exists(local_video):
                os.remove(local_video)
        except Exception as e:
            print(f"[cleanup] video remove warn: {e}")

        try:
            if os.path.exists(frame_path):
                os.remove(frame_path)
        except Exception as e:
            print(f"[cleanup] frame remove warn: {e}")

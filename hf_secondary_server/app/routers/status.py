from fastapi import APIRouter, HTTPException, Path
from app.schemas import StatusResp
from app.services.higgsfield import poll_job_set

router = APIRouter(prefix="/status", tags=["status"])

@router.get("/{job_set_id}", response_model=StatusResp,
            summary="Проверить статус job-set",
            description="Опрашивает Higgsfield до завершения, при completed возвращает ссылку на видео.")
def check_status(job_set_id: str = Path(..., description="ID из submit-ответа"), wait: bool = True):
    try:
        js = poll_job_set(job_set_id) if wait else {"jobs": [{"status": "unknown"}]}
    except Exception as e:
        raise HTTPException(502, detail=f"poll failed: {e}")

    jobs = js.get("jobs") or []
    status = jobs[0].get("status") if jobs else "unknown"
    video_url = None
    if status == "completed":
        try:
            video_url = jobs[0]["results"]["raw"]["url"]
        except Exception:
            pass
    return StatusResp(job_set_id=job_set_id, status=status, video_url=video_url, raw=js)

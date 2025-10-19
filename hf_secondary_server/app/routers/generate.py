from fastapi import APIRouter, HTTPException
from app.schemas import GenerateReq, GenerateResp
from app.services.higgsfield import submit_minimax_i2v

router = APIRouter(prefix="/generate", tags=["generate"])

@router.post(
    "/minimax-i2v",
    response_model=GenerateResp,
    summary="Запустить Higgsfield image2video/minimax",
    description="Принимает image_url и prompt, отправляет POST на Higgsfield, возвращает job_set_id. Логи и debug-дампы включены."
)
def generate_minimax_i2v(req: GenerateReq):
    params = {
        "duration": req.duration,
        "resolution": req.resolution,
        "enhance_prompt": bool(req.enhance_prompt),
        "input_image": {"type": "image_url", "image_url": str(req.image_url)},
        "prompt": req.prompt,
    }
    try:
        submit = submit_minimax_i2v(params)
    except Exception as e:
        raise HTTPException(502, detail=f"submit failed: {e}")

    job_set_id = submit.get("id")
    if not job_set_id:
        raise HTTPException(500, "No job_set_id in submit response")
    return GenerateResp(job_set_id=job_set_id, request_params=params)

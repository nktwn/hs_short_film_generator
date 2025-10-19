from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import GenerateRequest, GenerateResponse, StatusResponse
from config import settings
from providers.higgsfield import HiggsfieldProvider

app = FastAPI(title="Video Gen Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOW_ORIGINS] if settings.CORS_ALLOW_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

provider = HiggsfieldProvider(
    base_url=settings.HIGGSFIELD_BASE_URL,
    api_key=settings.HIGGSFIELD_API_KEY,
    api_secret=settings.HIGGSFIELD_API_SECRET,
    timeout=settings.REQUEST_TIMEOUT
)

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    text = (req.user_prompt or "").strip()
    if len(text) < 3:
        raise HTTPException(400, "user_prompt is too short")
 
    try:
        job_id = await provider.submit(
            prompt=text,
            duration_s=settings.DEFAULT_DURATION_S,
            aspect_ratio=settings.DEFAULT_ASPECT_RATIO,
            seed=None,
            model=settings.DEFAULT_MODEL,
            enhance_prompt=True,
            resolution=settings.DEFAULT_RESOLUTION,
            webhook=None,
        )
    except Exception as e:
        raise HTTPException(502, f"Provider submit failed: {e}")

    last_status, last_url, meta = "queued", None, None

    return GenerateResponse(
        job_id=job_id,
        status=last_status,
        provider=provider.name,
        video_url=(f"/result/{job_id}.mp4"),
        prompt_used=text if last_status in ("failed","succeeded") else None,
        meta=meta
    )

@app.get("/status/{job_id}", response_model=StatusResponse)
async def status(job_id: str):
    try:
        status, url, meta = await provider.status(job_id)
    except Exception as e:
        raise HTTPException(502, f"Provider status failed: {e}")

    return StatusResponse(
        job_id=job_id,
        status=status,
        video_url=(f"/result/{job_id}.mp4" if url else None),
        meta=meta
    )
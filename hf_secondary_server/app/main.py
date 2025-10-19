from fastapi import FastAPI
from app.routers.frames import router as frames_router
from app.routers.generate import router as generate_router
from app.routers.status import router as status_router
from app.routers.pipeline import router as pipeline_router  # <— вот это

app = FastAPI(
    title="Higgsfield Multimodal Orchestrator",
    version="0.2.0",
    description="Единый пайплайн + низкоуровневые ручки (frames/generate/status).",
)

app.include_router(frames_router)
app.include_router(generate_router)
app.include_router(status_router)
app.include_router(pipeline_router)  # <— и это

@app.get("/health", tags=["meta"])
def health():
    return {"ok": True}

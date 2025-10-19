from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict

class GenerateRequest(BaseModel):
    user_prompt: str = Field(..., example="A black Mustang races across the desert at golden hour")

class GenerateResponse(BaseModel):
    job_id: str
    status: Literal["queued","processing","succeeded","failed"]
    provider: str
    video_url: Optional[str] = None
    prompt_used: Optional[str] = None
    meta: Optional[Dict] = None

class StatusResponse(BaseModel):
    job_id: str
    status: Literal["queued","processing","succeeded","failed"]
    video_url: Optional[str] = None
    meta: Optional[Dict] = None

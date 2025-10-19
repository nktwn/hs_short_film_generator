from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl

class FromVideoReq(BaseModel):
    video_url: HttpUrl = Field(..., description="Публичный URL исходного видео")

class FromVideoResp(BaseModel):
    video_url: HttpUrl
    local_video_path: str
    width: int
    height: int
    duration: float
    fps: int
    frame_time_sec: float
    local_frame_path: str
    image_url: HttpUrl

class GenerateReq(BaseModel):
    image_url: HttpUrl
    prompt: str = Field(default="A running robot, dynamic camera, cinematic lighting")
    duration: int = Field(default=10, ge=1, le=30)
    resolution: str = Field(default="768")
    enhance_prompt: bool = True

class GenerateResp(BaseModel):
    job_set_id: str
    request_params: Dict[str, Any]

class StatusResp(BaseModel):
    job_set_id: str
    status: str
    video_url: Optional[str] = None
    raw: Dict[str, Any]

from typing import Optional, Dict, Tuple, Protocol

class T2VProvider(Protocol):
    name: str
    async def submit(self, prompt: str, duration_s: int, aspect_ratio: str, seed: Optional[int]) -> str:
        """Отправить задачу. Возвращает job_id."""
    async def status(self, job_id: str) -> Tuple[str, Optional[str], Dict]:
        """Вернёт (status, video_url, meta). status: queued|processing|succeeded|failed"""
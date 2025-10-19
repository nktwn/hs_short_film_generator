import httpx, asyncio
from typing import Optional, Tuple, Dict, Any, List

class HiggsfieldProvider:
    name = "higgsfield"

    def __init__(self, base_url: str, api_key: str, api_secret: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self._headers = {
            "Content-Type": "application/json",
            "hf-api-key": self.api_key,
            "hf-secret": self.api_secret,
        }

    async def submit(
        self,
        prompt: str,
        duration_s: int,
        aspect_ratio: str,
        seed: Optional[int],
        model: str = "minimax-t2v",
        enhance_prompt: bool = True,
        webhook: Optional[dict] = None,
        resolution: Optional[str] = "768",
        **kwargs: Any,
    ) -> str:
        # точный маршрут из Playground: /generate/<model>
        url = f"{self.base_url}/generate/{model}"
        params: Dict[str, Any] = {
            "prompt": prompt,
            "duration": duration_s,
            "resolution": str(resolution or "768"),
            # поддержим оба написания на всякий случай
            "enable_prompt_optimizier": bool(enhance_prompt),
            "enable_prompt_optimizer": bool(enhance_prompt),
        }
        if seed is not None:
            params["seed"] = seed
        if aspect_ratio:
            params["aspect_ratio"] = aspect_ratio

        payload: Dict[str, Any] = {"params": params}
        if webhook:
            payload["webhook"] = webhook

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload, headers=self._headers)
            r.raise_for_status()
            data = r.json()
            job_set_id = data.get("id") or data.get("job_set_id")
            if not job_set_id:
                raise ValueError(f"Submit OK but no job_set id in response: {data}")
            return job_set_id

    async def status(self, job_id: str) -> Tuple[str, Optional[str], Dict]:
        # пробуем несколько путей и ретраим 5xx (502 и т.п.)
        candidate_paths = [
            f"/v1/job-sets/{job_id}",
            f"/job-sets/{job_id}",
        ]
        last_exc: Exception | None = None
        for attempt in range(3):
            for path in candidate_paths:
                url = f"{self.base_url}{path}"
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        r = await client.get(url, headers=self._headers)
                        if r.status_code == 404:
                            continue
                        r.raise_for_status()
                        data = r.json()

                    jobs = data.get("jobs", []) or []
                    statuses = [j.get("status","queued") for j in jobs]
                    if any(s == "failed" for s in statuses):
                        overall = "failed"
                    elif jobs and all(s == "succeeded" for s in statuses):
                        overall = "succeeded"
                    elif any(s in ("processing","running","queued") for s in statuses):
                        overall = "processing"
                    else:
                        overall = "queued"

                    video_url = None
                    for j in jobs:
                        res = j.get("results") or {}
                        raw = (res.get("raw") or {}).get("url")
                        mn  = (res.get("min") or {}).get("url")
                        video_url = raw or mn
                        if video_url: break

                    return overall, video_url, data

                except httpx.HTTPStatusError as e:
                    last_exc = e
                    if 500 <= e.response.status_code < 600:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                except Exception as e:
                    last_exc = e
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
        raise httpx.HTTPError(f"All status paths failed for job_id={job_id}: {last_exc}")

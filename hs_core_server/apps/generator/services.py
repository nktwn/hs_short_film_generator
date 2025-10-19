# apps/generator/services.py
import requests
from django.conf import settings

PIPELINE_BASE_URL = getattr(
    settings, "GENERATOR_PIPELINE_BASE_URL", "http://139.59.143.107:8001"
)

# Новый: раздельные таймауты
# connect — короткий (быстро упасть, если хост недоступен),
# read — None (ждать бесконечно, пока сервер не вернёт ответ).
PIPELINE_CONNECT_TIMEOUT = getattr(
    settings, "GENERATOR_PIPELINE_CONNECT_TIMEOUT", 5
)  # seconds
PIPELINE_READ_TIMEOUT = getattr(
    settings, "GENERATOR_PIPELINE_READ_TIMEOUT", None
)  # None = бесконечно


class PipelineError(RuntimeError):
    pass


def _post_json(url: str, payload: dict) -> dict:
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=(PIPELINE_CONNECT_TIMEOUT, PIPELINE_READ_TIMEOUT),  # <--- ключевое
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        try:
            detail = resp.json()
        except Exception:
            detail = getattr(resp, "text", "")
        raise PipelineError(f"HTTP error: {e} - {detail}") from e
    except requests.Timeout as e:
        # сюда больше попадать не будем из-за read_timeout=None, но оставим на всякий
        raise PipelineError(f"Timeout: {e}") from e
    except requests.RequestException as e:
        raise PipelineError(f"Request error: {e}") from e

    try:
        return resp.json()
    except ValueError as e:
        raise PipelineError("Invalid JSON in pipeline response") from e


def continue_pipeline(
    previous_video_url: str, previous_prompt: str, next_prompt: str
) -> dict:
    url = f"{PIPELINE_BASE_URL}/pipeline/continue"
    payload = {
        "previous_video_url": previous_video_url,
        "previous_prompt": previous_prompt,
        "next_prompt": next_prompt,
    }
    return _post_json(url, payload)

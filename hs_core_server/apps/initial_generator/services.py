import requests
from django.conf import settings

GENERATOR_BASE_URL = getattr(settings, "GENERATOR_BASE_URL", "http://192.168.0.17:8001")


def start_generation(prompt: str) -> dict:
    """Отправляет запрос на генерацию видео и возвращает job_id и статус."""
    url = f"{GENERATOR_BASE_URL}/generate"
    resp = requests.post(url, json={"user_prompt": prompt}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def get_generation_status(job_id: str) -> dict:
    """Проверяет статус и возвращает результат из внешнего API."""
    url = f"{GENERATOR_BASE_URL}/status/{job_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

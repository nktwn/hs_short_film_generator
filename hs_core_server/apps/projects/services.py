# apps/projects/services/deepseek_client.py
import json
import re
from typing import List

from django.conf import settings
from openai import APIConnectionError, APIStatusError, OpenAI

DEEPSEEK_MODEL = getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")


class DeepSeekError(RuntimeError):
    pass


def _client() -> OpenAI:
    if not settings.DEEPSEEK_API_KEY:
        raise DeepSeekError("DeepSeek API key is not configured")
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_API_BASE,  # например, "https://api.deepseek.com/v1"
    )


def _cleanup_and_shorten(items: List[str], limit: int = 20) -> List[str]:
    cleaned, seen = [], set()
    for v in items:
        first = (v or "").strip().split("\n")[0]
        first = re.split(r"[.!?\n]", first, maxsplit=1)[0].strip(" \"'—-")
        first = first[:limit].strip()
        if first and first not in seen:
            cleaned.append(first)
            seen.add(first)
    return cleaned


def _try_extract_json_array(text: str) -> List[str]:
    """
    Пытаемся достать JSON-массив строк из content.
    1) Прямой json.loads
    2) Регексп по первому [...] и потом json.loads
    3) Если совсем не JSON — попробуем по строкам (маркеры -, *, •, новые строки)
       (это всё равно обработка ответа модели, не наш фолбэк-контент)
    """
    text = (text or "").strip()

    # 1) прямой parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass

    # 2) вырезать первый JSON-массив
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass

    # 3) fallback-парсинг по строкам из ОТВЕТА МОДЕЛИ (не выдумываем свои)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\*\u2022]\s*", "", line)  # убираем буллеты -,*,•
        if line:
            lines.append(line)
    return lines


def suggest_short_continuations(
    prompt: str, count: int = 3, limit: int = 20
) -> List[str]:
    """
    Один вызов к DeepSeek (n=1). Просим РОВНО count вариантов
    в формате JSON-массива строк. Возвращаем только то, что пришло от модели,
    после чистки/обрезки. Никаких «своих» вариантов.
    """
    system = (
        "You are a concise screenwriter assistant. "
        "Output MUST be a pure JSON array (no markdown, no prefix/suffix). "
        f"Return exactly {count} short ON-TOPIC continuations in English. "
        f"Each string must be <= {limit} characters. "
        "No numbering, no quotes, no trailing punctuation, no explanations."
    )
    user = (
        "Story:\n"
        f"{prompt}\n\n"
        f"Respond with a JSON array of exactly {count} strings. "
        'Example: ["First option", "Second option", "Third option"]'
    )

    try:
        client = _client()
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # ВАЖНО: DeepSeek сейчас поддерживает только n=1
            n=1,
            max_tokens=128,  # чуть больше, т.к. это массив
            temperature=0.8,
        )
    except (APIConnectionError, APIStatusError) as e:
        raise DeepSeekError(f"HTTP error: {e}") from e
    except Exception as e:
        raise DeepSeekError(str(e)) from e

    choices = getattr(resp, "choices", None) or []
    if not isinstance(choices, list) or len(choices) == 0:
        raise DeepSeekError("DeepSeek returned no choices")

    content = ""
    msg = getattr(choices[0], "message", None) or {}
    content = getattr(msg, "content", None) or msg.get("content") or ""

    # Пытаемся извлечь массив строк из ответа модели
    raw_items = _try_extract_json_array(content)
    cleaned = _cleanup_and_shorten(raw_items, limit=limit)

    # Возвращаем то, что реально получилось достать от модели
    return cleaned[:count]

import os
import shlex
import subprocess
import tempfile
import uuid
from typing import List, Tuple

import requests
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

CONNECT_TIMEOUT = getattr(settings, "GENERATOR_PIPELINE_CONNECT_TIMEOUT", 5)
READ_TIMEOUT = getattr(settings, "GENERATOR_PIPELINE_READ_TIMEOUT", None)


def _download_file(url: str, dst_path: str) -> None:
    # Качаем без read-таймаута
    with requests.get(url, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)) as r:
        r.raise_for_status()
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _ffmpeg_concat_demuxer(input_paths: List[str], out_path: str) -> Tuple[int, str]:
    """
    Склейка без перекодирования (если все файлы совместимы) через concat demuxer.
    Если контейнеры разные — можно заменить на фильтр concat с перекодированием.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listfile:
        for p in input_paths:
            # безопасно экранируем путь
            listfile.write(f"file {shlex.quote(p)}\n")
        list_path = listfile.name

    # Попытка без перекодирования
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-c",
        "copy",
        out_path,
    ]
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    return proc.returncode, proc.stdout


def _ffmpeg_concat_filter(input_paths: List[str], out_path: str) -> Tuple[int, str]:
    """
    Альтернатива: склейка с перекодированием через фильтр concat.
    Универсально, но дольше.
    """
    # Пример на N входов
    args = ["ffmpeg", "-y"]
    for p in input_paths:
        args += ["-i", p]
    n = len(input_paths)
    filter_complex = (
        "".join([f"[{i}:v:0][{i}:a:0]" for i in range(n)])
        + f"concat=n={n}:v=1:a=1[outv][outa]"
    )
    args += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        out_path,
    ]
    proc = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    return proc.returncode, proc.stdout


def assemble_videos_to_media(project_id: str, video_urls: List[str]) -> str:
    """
    Склеивает список видео по порядку в один mp4, кладёт в MEDIA_ROOT/assemblies/.
    Возвращает web-URL (MEDIA_URL + path).
    """
    if not video_urls:
        raise ValueError("No videos to assemble")

    assemblies_subdir = getattr(settings, "ASSEMBLIES_SUBDIR", "assemblies")
    # имя файла: {project}-{ts}-{uuid}.mp4
    ts = timezone.now().strftime("%Y%m%dT%H%M%S")
    file_name = f"{project_id}-{ts}-{uuid.uuid4().hex[:8]}.mp4"
    rel_path = os.path.join(assemblies_subdir, file_name)

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, assemblies_subdir), exist_ok=True)

    # Рабочая директория со скачанными файлами
    with tempfile.TemporaryDirectory() as tmpdir:
        local_inputs = []
        # Скачиваем по очереди
        for i, url in enumerate(video_urls):
            loc = os.path.join(tmpdir, f"in_{i:03d}.mp4")
            _download_file(url, loc)
            local_inputs.append(loc)

        # Путь назначения во временную папку, потом переложим в storage
        out_local = os.path.join(tmpdir, "out.mp4")

        # Шаг 1: попытка склеить без перекодирования
        code, log = _ffmpeg_concat_demuxer(local_inputs, out_local)

        # Если не получилось — пробуем со сжатием через фильтр
        if (
            code != 0
            or not os.path.exists(out_local)
            or os.path.getsize(out_local) == 0
        ):
            code2, log2 = _ffmpeg_concat_filter(local_inputs, out_local)
            if (
                code2 != 0
                or not os.path.exists(out_local)
                or os.path.getsize(out_local) == 0
            ):
                raise RuntimeError(f"ffmpeg concat failed:\n{log}\n---\n{log2}")

        # Кладём в media storage
        with open(out_local, "rb") as f:
            # убедимся, что каталог есть
            storage_path = default_storage.save(rel_path, f)

    # Вернём абсолютный URL
    return settings.MEDIA_URL.rstrip("/") + "/" + storage_path.replace("\\", "/")

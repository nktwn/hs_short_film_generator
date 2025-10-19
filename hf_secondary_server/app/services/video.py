# app/services/video.py
import os
import shlex
import httpx
import subprocess
import shutil

from app.config import WORKDIR


def sh(cmd: str):
    print(f"$ {cmd}")
    subprocess.check_call(shlex.split(cmd))


def _ffprobe(path: str, field: str) -> str:
    return subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", field, "-of", "default=nw=1:nk=1", path]
    ).decode().strip()

def cleanup_workdir():
    if os.path.isdir(WORKDIR):
        try:
            shutil.rmtree(WORKDIR)
        except Exception as e:
            print(f"[workdir] cleanup warn: {e}")
    try:
        os.makedirs(WORKDIR, exist_ok=True)
    except Exception as e:
        print(f"[workdir] recreate warn: {e}")

def get_meta(path: str):
    width = int(_ffprobe(path, "stream=width"))
    height = int(_ffprobe(path, "stream=height"))
    duration = float(_ffprobe(path, "format=duration"))
    fps_str = _ffprobe(path, "stream=r_frame_rate")
    if "/" in fps_str:
        num, den = map(int, fps_str.split("/"))
        fps = round(num / den) if den else num
    else:
        fps = int(float(fps_str))
    return width, height, duration, fps


def extract_last_frame(video_path: str, out_path: str) -> float:
    _, _, duration, _ = get_meta(video_path)
    ts = max(0.0, duration - 0.1 if duration > 0.1 else duration - 0.05)
    sh(f'ffmpeg -ss {ts:.3f} -i "{video_path}" -frames:v 1 -update 1 -y "{out_path}"')
    return ts


def ensure_workdir():
    os.makedirs(WORKDIR, exist_ok=True)



def normalize_video_url(url: str) -> str:
    return url[:-1] if url.endswith("/") else url


def preflight_video_url(url: str) -> dict:

    with httpx.Client(timeout=30, follow_redirects=True) as c:
        r = c.head(url)
        if r.status_code >= 400:
            r = c.get(url, headers={"Range": "bytes=0-0"})
        ct = r.headers.get("Content-Type", "").lower()
        cl = r.headers.get("Content-Length", "")
        ok_type = ("video/" in ct) or url.lower().endswith(".mp4")
        ok_size = (cl.isdigit() and int(cl) > 1024) or r.status_code == 206
        return {
            "ok": (r.status_code < 400) and ok_type and ok_size,
            "status_code": r.status_code,
            "content_type": ct,
            "content_length": cl,
        }


def download_video(url: str, out_path: str):

    with httpx.Client(timeout=None, follow_redirects=True) as c:
        with c.stream("GET", url) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
    _ = _ffprobe(out_path, "stream=width")


def curl_download(url: str, out_path: str):
    sh(f'curl -L "{url}" -o "{out_path}"')

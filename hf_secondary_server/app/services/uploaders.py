import os
import httpx

def upload_catbox(file_path: str) -> str:

    with httpx.Client(timeout=60) as c:
        with open(file_path, "rb") as f:
            r = c.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(file_path), f, "image/jpeg")},
            )
        r.raise_for_status()
        url = r.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"Catbox bad response: {r.text[:200]}")
        return url

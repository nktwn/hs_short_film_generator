import os
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_SECRET  = os.getenv("HF_SECRET", "")
WORKDIR    = os.path.abspath(os.getenv("WORKDIR", "./work"))

BASE_API   = "https://platform.higgsfield.ai"

HEADERS_JSON = {
    "Content-Type": "application/json",
    "hf-api-key": HF_API_KEY,
    "hf-secret": HF_SECRET,
}

SPACES_ENDPOINT   = os.getenv("SPACES_ENDPOINT", "https://fra1.digitaloceanspaces.com")
SPACES_CDN_BASE   = os.getenv("SPACES_CDN_BASE", "")
SPACES_REGION     = os.getenv("SPACES_REGION", "fra1")
SPACES_BUCKET     = os.getenv("SPACES_BUCKET", "hacknu")
SPACES_ACCESS_KEY = os.getenv("SPACES_ACCESS_KEY", "")
SPACES_SECRET_KEY = os.getenv("SPACES_SECRET_KEY", "")

os.makedirs(WORKDIR, exist_ok=True)

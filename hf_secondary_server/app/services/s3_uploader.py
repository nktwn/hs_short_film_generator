import os
import asyncio
import json
from datetime import datetime
from miniopy_async import Minio
from miniopy_async.error import S3Error
from app.config import (
    SPACES_ENDPOINT, SPACES_REGION, SPACES_BUCKET,
    SPACES_ACCESS_KEY, SPACES_SECRET_KEY, SPACES_CDN_BASE
)

def _endpoint_host(endpoint: str) -> str:
    return endpoint.replace("https://", "").replace("http://", "")

async def _ensure_bucket(client: Minio):
    try:
        exists = await client.bucket_exists(SPACES_BUCKET)
        if not exists:
            print(f"[spaces] bucket '{SPACES_BUCKET}' not found → creating…")
            await client.make_bucket(SPACES_BUCKET, location=SPACES_REGION)
        else:
            print(f"[spaces] bucket '{SPACES_BUCKET}' exists")
    except S3Error as e:
        print(f"[spaces] ensure_bucket warn: {e}")

async def _ensure_public_policy(client: Minio):
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowPublicRead",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{SPACES_BUCKET}/*"]
        }]
    }
    policy_json = json.dumps(policy)
    try:
        await client.set_bucket_policy(SPACES_BUCKET, policy_json)
        print("[spaces] public-read policy applied on bucket")
    except S3Error as e:
        print(f"[spaces] set_bucket_policy warn: {e}")

def _key_for_local_file(local_path: str, prefix: str = "frames") -> str:
    base = os.path.basename(local_path)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}/{ts}_{base}"

async def upload_file_async(local_path: str, prefix: str = "frames") -> str:

    client = Minio(
        endpoint=_endpoint_host(SPACES_ENDPOINT),
        access_key=SPACES_ACCESS_KEY,
        secret_key=SPACES_SECRET_KEY,
        secure=SPACES_ENDPOINT.startswith("https://"),
        region=SPACES_REGION,
    )

    await _ensure_bucket(client)
    await _ensure_public_policy(client)

    key = _key_for_local_file(local_path, prefix=prefix)
    size = os.path.getsize(local_path)

    lp = local_path.lower()
    if lp.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif lp.endswith(".png"):
        content_type = "image/png"
    elif lp.endswith(".mp4"):
        content_type = "video/mp4"
    else:
        content_type = "application/octet-stream"

    print(f"[spaces] upload start bucket={SPACES_BUCKET} key={key} size={size} ct={content_type}")
    with open(local_path, "rb") as data:
        await client.put_object(
            SPACES_BUCKET,
            key,
            data,
            size,
            content_type=content_type,
        )
    print(f"[spaces] upload done: {key}")

    cdn = SPACES_CDN_BASE.rstrip("/")
    return f"{cdn}/{key}"

def upload_file(local_path: str, prefix: str = "frames") -> str:
    return asyncio.run(upload_file_async(local_path, prefix=prefix))

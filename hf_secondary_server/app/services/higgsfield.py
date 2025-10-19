import os
import time
import json
import httpx
from datetime import datetime
from app.config import BASE_API, HEADERS_JSON, WORKDIR

def _dump(name: str, data: dict | str):
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(WORKDIR, f"debug_{name}_{ts}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[debug] wrote {path}")
    except Exception as e:
        print(f"[debug] failed to write {path}: {e}")

def submit_minimax_i2v(params: dict) -> dict:

    payload = {"params": params}
    _dump("submit_payload", payload)
    print(f"[submit] url={BASE_API}/v1/image2video/minimax")
    print(f"[submit] headers={{'hf-api-key': '***', 'hf-secret': '***', 'Content-Type':'application/json'}}")
    print(f"[submit] params.image_url={params.get('input_image',{}).get('image_url')} duration={params.get('duration')} res={params.get('resolution')} enhance={params.get('enhance_prompt')}")

    with httpx.Client(timeout=120) as c:
        last = None
        for attempt in range(3):
            try:
                r = c.post(f"{BASE_API}/v1/image2video/minimax",
                           headers=HEADERS_JSON,
                           content=json.dumps(payload))
                print(f"[submit] status={r.status_code}")
                if r.status_code < 400:
                    body = r.json()
                    _dump("submit_ok", body)
                    return body
                txt = r.text
                _dump("submit_err", {"status": r.status_code, "text": txt[:2048]})
                print(f"[submit] error {r.status_code}: {txt[:512]}")
                last = r
                if 500 <= r.status_code < 600 and attempt < 2:
                    sleep_s = 3 * (attempt + 1)
                    print(f"[submit] retrying in {sleep_s}s …")
                    time.sleep(sleep_s)
                    continue
                break
            except Exception as e:
                _dump("submit_exc", {"exc": str(e)})
                print(f"[submit] exception: {e}")
                last = e
                time.sleep(2)
        if isinstance(last, httpx.Response):
            last_body = last.text
            raise httpx.HTTPStatusError(
                f"Submit failed {last.status_code}: {last_body[:512]}",
                request=last.request, response=last
            )
        raise RuntimeError(f"Submit failed: {last}")

def poll_job_set(job_set_id: str, interval_sec: int = 30) -> dict:
    with httpx.Client(timeout=120) as c:
        while True:
            time.sleep(interval_sec)
            s = c.get(f"{BASE_API}/v1/job-sets/{job_set_id}", headers=HEADERS_JSON)
            print(f"[poll] {job_set_id} status={s.status_code}")
            s.raise_for_status()
            js = s.json()
            _dump("poll_tick", {"job_set_id": job_set_id, "data": js})
            jobs = js.get("jobs") or []
            status = jobs[0].get("status") if jobs else None
            print(f"[poll] status={status}")
            if status in ("completed", "failed"):
                return js

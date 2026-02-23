import os, sys
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

HYP3_API_URL = os.getenv("HYP3_API_URL", "https://hyp3-api.asf.alaska.edu").strip().rstrip("/")
EDL_TOKEN = os.getenv("EDL_TOKEN", "").strip()

POLL_LIMIT = int(os.getenv("POLL_LIMIT", "20"))

def supabase_headers():
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def hyp3_headers():
    return {
        "Authorization": f"Bearer {EDL_TOKEN}",
        "Accept": "application/json",
    }

def sb_get(path, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    r = requests.get(url, headers=supabase_headers(), params=params or {}, timeout=60)
    r.raise_for_status()
    return r.json()

def sb_patch(table, where_qs, payload):
    url = f"{SUPABASE_URL}/rest/v1/{table}{where_qs}"
    r = requests.patch(url, headers=supabase_headers(), json=payload, timeout=60)
    if r.status_code not in (200, 204):
        print("Supabase PATCH status:", r.status_code, "body:", r.text[:800])
        r.raise_for_status()

def hyp3_get_job(job_id: str):
    candidates = [
        (f"{HYP3_API_URL}/jobs", {"job_id": job_id}),
        (f"{HYP3_API_URL}/api/jobs", {"job_id": job_id}),
    ]
    last = None
    for url, params in candidates:
        r = requests.get(url, headers=hyp3_headers(), params=params, timeout=90)
        if r.status_code == 404:
            last = (r.status_code, r.text)
            continue
        r.raise_for_status()
        data = r.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return jobs[0] if jobs else None
    raise RuntimeError(f"HyP3 GET failed. Last: {last}")

def normalize_status(status_code: str) -> str:
    s = (status_code or "").upper()
    if s == "SUCCEEDED":
        return "succeeded"
    if s in ("FAILED", "CANCELED"):
        return "failed"
    return "running"

def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
    if not EDL_TOKEN:
        raise RuntimeError("Missing EDL_TOKEN")

    # כל מה שלא succeeded/failed נחשב עדיין פעיל
    jobs = sb_get(
        "hyp3_jobs",
        params={
            "select": "job_id,pair_key,status",
            "status": "neq.succeeded",
            "order": "submitted_at.asc",
            "limit": str(POLL_LIMIT),
        },
    )
    jobs = [j for j in jobs if j.get("status") != "failed"]
    print("Jobs to poll:", len(jobs))
    if not jobs:
        return

    now = datetime.now(timezone.utc).isoformat()

    for j in jobs:
        job_id = j["job_id"]
        pair_key = j["pair_key"]
        info = hyp3_get_job(job_id)
        if not info:
            print("Job not found in HyP3 yet:", job_id)
            continue

        status_code = info.get("status_code") or ""
        status_norm = normalize_status(status_code)

        sb_patch("hyp3_jobs", f"?job_id=eq.{job_id}", {
            "status": status_norm,
            "updated_at": now,
            "result_meta": info,
        })

        if status_norm == "succeeded":
            sb_patch("pairs", f"?pair_key=eq.{pair_key}", {"status": "done"})
        elif status_norm == "failed":
            sb_patch("pairs", f"?pair_key=eq.{pair_key}", {"status": "failed"})

        print("Updated", job_id, "->", status_norm)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

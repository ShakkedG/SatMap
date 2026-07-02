import os
import sys
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

HYP3_API_URL = os.getenv("HYP3_API_URL", "https://hyp3-api.asf.alaska.edu").strip().rstrip("/")
EDL_TOKEN = os.getenv("EDL_TOKEN", "").strip()

POLL_LIMIT = int(os.getenv("POLL_LIMIT", "20"))

_HYP3_ROOT = None


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


def hyp3_pick_root(base: str) -> str:
    base = base.rstrip("/")
    for root in (base, base + "/api"):
        openapi = f"{root}/openapi.json"
        try:
            r = requests.get(openapi, timeout=30)
            print(f"[HyP3] probe {openapi} -> {r.status_code}")
            if r.status_code == 200:
                return root
        except Exception as e:
            print(f"[HyP3] probe failed {openapi}: {e}")
    return base


def hyp3_root() -> str:
    global _HYP3_ROOT
    if _HYP3_ROOT is None:
        _HYP3_ROOT = hyp3_pick_root(HYP3_API_URL)
    return _HYP3_ROOT


def hyp3_get_job(job_id: str):
    root = hyp3_root()

    # 1) /jobs/<id>
    url1 = f"{root}/jobs/{job_id}"
    r1 = requests.get(url1, headers=hyp3_headers(), timeout=90)
    if r1.status_code == 200:
        data = r1.json()
        # לפעמים מחזיר {"job": {...}} או {...}
        if isinstance(data, dict) and "job" in data and isinstance(data["job"], dict):
            return data["job"]
        return data if isinstance(data, dict) else None

    # 2) fallback: /jobs?job_id=<id>
    url2 = f"{root}/jobs"
    r2 = requests.get(url2, headers=hyp3_headers(), params={"job_id": job_id}, timeout=90)
    if r2.status_code == 200:
        data = r2.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        return jobs[0] if jobs else None

    # אם שניהם נכשלו
    last = (r1.status_code, r1.text[:300], r2.status_code, r2.text[:300])
    raise RuntimeError(f"HyP3 GET failed. Last: {last}")


def normalize_status(status_code: str) -> str:
    s = (status_code or "").upper().strip()
    if s == "SUCCEEDED":
        return "succeeded"
    if s in ("FAILED", "CANCELED", "CANCELLED"):
        return "failed"
    if s in ("PENDING", "QUEUED"):
        return "queued"
    return "running"


def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
    if not EDL_TOKEN:
        raise RuntimeError("Missing EDL_TOKEN")

    # פעילים = לא succeeded וגם לא failed
    jobs = sb_get(
        "hyp3_jobs",
        params={
            "select": "job_id,pair_key,status",
            "status": "neq.succeeded",
            "order": "submitted_at.asc",
            "limit": str(POLL_LIMIT),
        },
    )
    jobs = [j for j in jobs if (j.get("status") or "").lower() != "failed"]

    print("Jobs to poll:", len(jobs))
    if not jobs:
        return

    for j in jobs:
        job_id = j["job_id"]
        pair_key = j["pair_key"]
        current_status = (j.get("status") or "").lower()

        info = hyp3_get_job(job_id)
        if not info:
            print("Job not found in HyP3 yet:", job_id)
            continue

        status_code = info.get("status_code") or info.get("status") or ""
        status_norm = normalize_status(status_code)

        # אם אין שינוי בסטטוס - לא מעדכנים DB (מוריד רעש)
        if status_norm == current_status:
            print("No change", job_id, "still", status_norm)
            continue

        now = datetime.now(timezone.utc).isoformat()

        sb_patch(
            "hyp3_jobs",
            f"?job_id=eq.{job_id}",
            {
                "status": status_norm,
                "updated_at": now,
                "result_meta": info,
            },
        )

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

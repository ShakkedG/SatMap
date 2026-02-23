import os, sys, json, hashlib
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

HYP3_API_URL = os.getenv("HYP3_API_URL", "https://hyp3-api.asf.alaska.edu").strip().rstrip("/")
EDL_TOKEN = os.getenv("EDL_TOKEN", "").strip()

SUBMIT_LIMIT = int(os.getenv("SUBMIT_LIMIT", "3"))
LOOKS = os.getenv("HYP3_LOOKS", "10x2").strip()
INCLUDE_LOS = os.getenv("INCLUDE_LOS", "true").strip().lower() == "true"

def supabase_headers():
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

def hyp3_headers():
    return {
        "Authorization": f"Bearer {EDL_TOKEN}",
        "Content-Type": "application/json",
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

def sb_upsert(table, rows, on_conflict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    r = requests.post(url, headers=supabase_headers(), json=rows, timeout=120)
    if r.status_code not in (200, 201, 204):
        print("Supabase UPSERT status:", r.status_code, "body:", r.text[:800])
        r.raise_for_status()

def hyp3_post_jobs(payload):
    # HyP3 שרתים לפעמים חשופים גם ב-/api וגם ב-/
    candidates = [f"{HYP3_API_URL}/jobs", f"{HYP3_API_URL}/api/jobs"]
    last = None
    for u in candidates:
        try:
            r = requests.post(u, headers=hyp3_headers(), json=payload, timeout=120)
            if r.status_code in (404,):
                last = (r.status_code, r.text)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"HyP3 POST failed. Last error: {last}")

def short_name(pair_key: str) -> str:
    h = hashlib.sha1(pair_key.encode("utf-8")).hexdigest()[:10]
    return f"satmap-insar-{h}"

def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
    if not EDL_TOKEN:
        raise RuntimeError("Missing EDL_TOKEN (Earthdata bearer token)")

    # 1) קח N זוגות new
    pairs = sb_get(
        "pairs",
        params={
            "select": "pair_key,ref_granule_id,sec_granule_id,status,created_at",
            "status": "eq.new",
            "order": "created_at.asc",
            "limit": str(SUBMIT_LIMIT),
        },
    )
    print("Pairs fetched:", len(pairs))
    if not pairs:
        print("No pairs with status=new")
        return

    # 2) בנה jobs list (INSAR_GAMMA עם ESA granule IDs) :contentReference[oaicite:2]{index=2}
    jobs = []
    for p in pairs:
        pair_key = p["pair_key"]
        ref_g = p["ref_granule_id"]
        sec_g = p["sec_granule_id"]

        job_def = {
            "name": short_name(pair_key),
            "job_type": "INSAR_GAMMA",
            "job_parameters": {
                "granules": [ref_g, sec_g],
                "looks": LOOKS,
                "include_los_displacement": INCLUDE_LOS,
            },
        }
        jobs.append(job_def)

    payload = {"jobs": jobs}
    print("Submitting HyP3 jobs:", len(jobs), "api:", HYP3_API_URL)

    # 3) שליחה ל-HyP3
    resp = hyp3_post_jobs(payload)
    hyp3_jobs = resp.get("jobs", []) if isinstance(resp, dict) else []
    print("HyP3 returned jobs:", len(hyp3_jobs))

    # 4) שמירה ב-Supabase + עדכון סטטוס בזוגות
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for idx, p in enumerate(pairs):
        pair_key = p["pair_key"]
        j = hyp3_jobs[idx] if idx < len(hyp3_jobs) else {}
        job_id = j.get("job_id") or j.get("id")
        status_code = j.get("status_code") or "RUNNING"

        # map לסטטוסים שלנו
        status_norm = "running"
        if str(status_code).upper() == "SUCCEEDED":
            status_norm = "succeeded"
        elif str(status_code).upper() in ("FAILED", "CANCELED"):
            status_norm = "failed"

        if not job_id:
            raise RuntimeError(f"Missing job_id in HyP3 response for pair {pair_key}")

        rows.append({
            "job_id": job_id,
            "pair_key": pair_key,
            "product_type": "INSAR_GAMMA",
            "status": status_norm,
            "submitted_at": now,
            "updated_at": now,
            "result_meta": j,
        })

        # update pairs.status
        sb_patch("pairs", f"?pair_key=eq.{pair_key}", {"status": "submitted"})

    sb_upsert("hyp3_jobs", rows, on_conflict="job_id")
    print("Saved hyp3_jobs:", len(rows), "and marked pairs=submitted")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

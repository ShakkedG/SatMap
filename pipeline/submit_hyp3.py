import os
import sys
import json
import hashlib
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

HYP3_API_URL = os.getenv("HYP3_API_URL", "https://hyp3-api.asf.alaska.edu").strip().rstrip("/")
EDL_TOKEN = os.getenv("EDL_TOKEN", "").strip()

SUBMIT_LIMIT = int(os.getenv("SUBMIT_LIMIT", "3"))

# INSAR_GAMMA params (לפי הדוקס)
LOOKS = os.getenv("HYP3_LOOKS", "10x2").strip()  # למשל 10x2 / 5x1
INCLUDE_LOOK_VECTORS = os.getenv("INCLUDE_LOOK_VECTORS", "true").strip().lower() == "true"
INCLUDE_LOS_DISPLACEMENT = os.getenv("INCLUDE_LOS_DISPLACEMENT", "true").strip().lower() == "true"


def sb_headers():
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def hyp3_headers():
    if not EDL_TOKEN:
        raise RuntimeError("Missing EDL_TOKEN")
    return {
        "Authorization": f"Bearer {EDL_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def sb_get(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.get(url, headers=sb_headers(), params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def sb_patch(table, where_qs, payload):
    url = f"{SUPABASE_URL}/rest/v1/{table}{where_qs}"
    r = requests.patch(url, headers=sb_headers(), json=payload, timeout=60)
    if r.status_code not in (200, 204):
        print("Supabase PATCH status:", r.status_code)
        print(r.text[:800])
        r.raise_for_status()


def sb_upsert(table, rows, on_conflict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    r = requests.post(url, headers=sb_headers(), json=rows, timeout=120)
    if r.status_code not in (200, 201, 204):
        print("Supabase UPSERT status:", r.status_code)
        print(r.text[:800])
        r.raise_for_status()


def hyp3_pick_root(base: str) -> str:
    base = base.rstrip("/")
    candidates = [base, base + "/api"]
    for root in candidates:
        openapi = f"{root}/openapi.json"
        try:
            r = requests.get(openapi, timeout=30)
            print(f"[HyP3] probe {openapi} -> {r.status_code}")
            if r.status_code == 200:
                return root
        except Exception as e:
            print(f"[HyP3] probe failed {openapi}: {e}")
    return base


def clean_granule_id(g: str) -> str:
    """
    HyP3 API מצפה ל-ESA granule IDs (ללא '-SLC').
    אם מגיע מה-ASF עם '-SLC' בסוף – נוריד.
    """
    g = (g or "").strip()
    if g.endswith("-SLC"):
        g = g[:-4]
    return g


def hyp3_post_jobs(payload: dict) -> dict:
    root = hyp3_pick_root(HYP3_API_URL)
    url = f"{root}/jobs"

    print(f"[HyP3] POST {url}")
    print(f"[HyP3] jobs count: {len(payload.get('jobs', []))}")
    if payload.get("jobs"):
        print("[HyP3] sample job (sanitized):")
        print(json.dumps(payload["jobs"][0], indent=2)[:1200])

    r = requests.post(url, headers=hyp3_headers(), json=payload, timeout=180)
    print(f"[HyP3] status: {r.status_code}")
    if r.status_code >= 400:
        print("[HyP3] body (first 2000):")
        print(r.text[:2000])
        r.raise_for_status()

    return r.json()


def short_name(pair_key: str) -> str:
    h = hashlib.sha1(pair_key.encode("utf-8")).hexdigest()[:10]
    return f"satmap-insar-{h}"


def normalize_status(status_code: str) -> str:
    s = (status_code or "").upper()
    if s == "SUCCEEDED":
        return "succeeded"
    if s in ("FAILED", "CANCELED"):
        return "failed"
    return "running"

def hyp3_get_user() -> dict:
    root = hyp3_pick_root(HYP3_API_URL)
    url = f"{root}/user"
    r = requests.get(url, headers=hyp3_headers(), timeout=60)
    if r.status_code >= 400:
        print("[HyP3] /user failed:", r.status_code, r.text[:800])
        r.raise_for_status()
    return r.json()

def hyp3_get_costs() -> dict:
    root = hyp3_pick_root(HYP3_API_URL)
    url = f"{root}/costs"
    r = requests.get(url, headers=hyp3_headers(), timeout=60)
    if r.status_code >= 400:
        print("[HyP3] /costs failed:", r.status_code, r.text[:800])
        r.raise_for_status()
    return r.json()

def extract_job_cost(costs_resp: dict, job_type: str) -> float | int | None:
    # תומך בכמה פורמטים אפשריים
    if costs_resp is None:
        return None
    if job_type in costs_resp and isinstance(costs_resp[job_type], (int, float)):
        return costs_resp[job_type]
    if "costs" in costs_resp:
        c = costs_resp["costs"]
        if isinstance(c, dict) and job_type in c and isinstance(c[job_type], (int, float)):
            return c[job_type]
    if "jobs" in costs_resp and isinstance(costs_resp["jobs"], list):
        for row in costs_resp["jobs"]:
            if (row.get("job_type") == job_type) and isinstance(row.get("credit_cost"), (int, float)):
                return row["credit_cost"]
    return None
def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")

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

    jobs = []
    for p in pairs:
        pair_key = p["pair_key"]
        ref_g = clean_granule_id(p["ref_granule_id"])
        sec_g = clean_granule_id(p["sec_granule_id"])

        job_parameters = {
            "granules": [ref_g, sec_g],
            "looks": LOOKS,
            "include_look_vectors": INCLUDE_LOOK_VECTORS,
            "include_los_displacement": INCLUDE_LOS_DISPLACEMENT,
        }

        jobs.append({
            "name": short_name(pair_key),
            "job_type": "INSAR_GAMMA",
            "job_parameters": job_parameters,
        })

    payload = {"jobs": jobs}
    resp = hyp3_post_jobs(payload)

    hyp3_jobs = resp.get("jobs", []) if isinstance(resp, dict) else []
    print("HyP3 returned jobs:", len(hyp3_jobs))

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for idx, p in enumerate(pairs):
        pair_key = p["pair_key"]
        j = hyp3_jobs[idx] if idx < len(hyp3_jobs) else {}
        job_id = j.get("job_id") or j.get("id")
        status_code = j.get("status_code") or "RUNNING"

        if not job_id:
            raise RuntimeError(f"Missing job_id for pair {pair_key}. Job: {json.dumps(j)[:800]}")

        rows.append({
            "job_id": job_id,
            "pair_key": pair_key,
            "product_type": "INSAR_GAMMA",
            "status": normalize_status(status_code),
            "submitted_at": now,
            "updated_at": now,
            "result_meta": j,
        })

        sb_patch("pairs", f"?pair_key=eq.{pair_key}", {"status": "submitted"})

    sb_upsert("hyp3_jobs", rows, on_conflict="job_id")
    print("Saved hyp3_jobs:", len(rows), "and marked pairs=submitted")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

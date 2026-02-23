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
LOOKS = os.getenv("HYP3_LOOKS", "10x2").strip()
INCLUDE_LOS = os.getenv("INCLUDE_LOS", "true").strip().lower() == "true"


def sb_headers():
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def hyp3_headers():
    if not EDL_TOKEN:
        raise RuntimeError("Missing EDL_TOKEN (GitHub Actions secret)")
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
        print("Supabase body (first 800):", r.text[:800])
        r.raise_for_status()


def sb_upsert(table, rows, on_conflict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    r = requests.post(url, headers=sb_headers(), json=rows, timeout=120)
    if r.status_code not in (200, 201, 204):
        print("Supabase UPSERT status:", r.status_code)
        print("Supabase body (first 800):", r.text[:800])
        r.raise_for_status()


def hyp3_pick_root(base: str) -> str:
    """
    HyP3 מציג ב-OpenAPI servers: '/' וגם '/api'.
    נבדוק openapi.json על base ואז base/api, ונבחר מה שמחזיר 200.
    """
    candidates = [base.rstrip("/"), base.rstrip("/") + "/api"]
    for root in candidates:
        openapi = f"{root}/openapi.json"
        try:
            r = requests.get(openapi, timeout=30)
            print(f"[HyP3] probe {openapi} -> {r.status_code}")
            if r.status_code == 200:
                return root
        except Exception as e:
            print(f"[HyP3] probe failed {openapi}: {e}")

    # fallback: אם אין openapi, ננסה /user עם auth (200/401/403 אומר קיים)
    for root in candidates:
        user = f"{root}/user"
        try:
            r = requests.get(user, headers=hyp3_headers(), timeout=30)
            print(f"[HyP3] probe {user} -> {r.status_code}")
            if r.status_code != 404:
                return root
        except Exception as e:
            print(f"[HyP3] probe failed {user}: {e}")

    return base.rstrip("/")


def hyp3_post_jobs(payload: dict) -> dict:
    root = hyp3_pick_root(HYP3_API_URL)
    url = f"{root}/jobs"
    print(f"[HyP3] base: {HYP3_API_URL}")
    print(f"[HyP3] root: {root}")
    print(f"[HyP3] POST: {url}")
    print(f"[HyP3] jobs: {len(payload.get('jobs', []))}")

    r = requests.post(url, headers=hyp3_headers(), json=payload, timeout=120)
    print(f"[HyP3] status: {r.status_code}")
    if r.status_code >= 400:
        print("[HyP3] body (first 1000):")
        print(r.text[:1000])
        r.raise_for_status()

    return r.json()


def short_name(pair_key: str) -> str:
    h = hashlib.sha1(pair_key.encode("utf-8")).hexdigest()[:10]
    return f"satmap-insar-{h}"


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
        ref_g = p["ref_granule_id"]
        sec_g = p["sec_granule_id"]

        jobs.append({
            "name": short_name(pair_key),
            "job_type": "INSAR_GAMMA",
            "job_parameters": {
                "granules": [ref_g, sec_g],
                "looks": LOOKS,
                "include_los_displacement": INCLUDE_LOS,
            },
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
        status_code = (j.get("status_code") or "RUNNING").upper()

        if not job_id:
            raise RuntimeError(f"Missing job_id for pair {pair_key}. Full job: {json.dumps(j)[:800]}")

        if status_code == "SUCCEEDED":
            status_norm = "succeeded"
        elif status_code in ("FAILED", "CANCELED"):
            status_norm = "failed"
        else:
            status_norm = "running"

        rows.append({
            "job_id": job_id,
            "pair_key": pair_key,
            "product_type": "INSAR_GAMMA",
            "status": status_norm,
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

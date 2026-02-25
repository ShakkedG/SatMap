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

# INSAR_GAMMA params
LOOKS = os.getenv("HYP3_LOOKS", "10x2").strip()
INCLUDE_LOOK_VECTORS = os.getenv("INCLUDE_LOOK_VECTORS", "true").strip().lower() == "true"
INCLUDE_LOS_DISPLACEMENT = os.getenv("INCLUDE_LOS_DISPLACEMENT", "true").strip().lower() == "true"

_HYP3_ROOT = None


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


def hyp3_root() -> str:
    global _HYP3_ROOT
    if _HYP3_ROOT is None:
        _HYP3_ROOT = hyp3_pick_root(HYP3_API_URL)
    return _HYP3_ROOT


def clean_granule_id(g: str) -> str:
    g = (g or "").strip()
    if g.endswith("-SLC"):
        g = g[:-4]
    return g


def hyp3_post_jobs(payload: dict) -> dict:
    url = f"{hyp3_root()}/jobs"

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


def hyp3_get_user() -> dict:
    url = f"{hyp3_root()}/user"
    r = requests.get(url, headers=hyp3_headers(), timeout=60)
    print(f"[HyP3] GET {url} -> {r.status_code}")
    if r.status_code >= 400:
        print("[HyP3] /user failed:", r.status_code, r.text[:800])
        r.raise_for_status()
    return r.json()


def hyp3_get_costs() -> dict:
    url = f"{hyp3_root()}/costs"
    r = requests.get(url, headers=hyp3_headers(), timeout=60)
    print(f"[HyP3] GET {url} -> {r.status_code}")
    if r.status_code >= 400:
        print("[HyP3] /costs failed:", r.status_code, r.text[:800])
        r.raise_for_status()
    return r.json()


def extract_job_cost(costs_resp: dict, job_type: str) -> float | int | None:
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


def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")

    # ---------- credit guard ----------
    submit_limit = SUBMIT_LIMIT

    remaining = None
    job_cost = None
    try:
        user = hyp3_get_user()
        remaining = user.get("remaining_credits", None)

        costs = hyp3_get_costs()
        job_cost = extract_job_cost(costs, "INSAR_GAMMA")

        print("[HyP3] remaining_credits:", remaining, "job_cost:", job_cost)

        if isinstance(remaining, (int, float)) and remaining <= 0:
            print("No credits — skipping submit.")
            return

        if isinstance(remaining, (int, float)) and isinstance(job_cost, (int, float)) and job_cost > 0:
            max_jobs = int(remaining // job_cost)
            if max_jobs <= 0:
                print("Not enough credits for even 1 job — skipping submit.")
                return
            submit_limit = min(submit_limit, max_jobs)
            print("Adjusted submit_limit =", submit_limit)

    except Exception as e:
        # לא מפילים את כל הריצה אם /user או /costs בעייתיים—רק מזהירים וממשיכים עם submit_limit רגיל
        print("[HyP3] WARNING: credit guard failed:", type(e).__name__, str(e))

    # ---------- fetch pairs ----------
    pairs = sb_get(
        "pairs",
        params={
            "select": "pair_key,ref_granule_id,sec_granule_id,status,created_at",
            "status": "eq.new",
            "order": "created_at.asc",
            "limit": str(submit_limit),
        },
    )

    print("Pairs fetched:", len(pairs))
    if not pairs:
        print("No pairs with status=new")
        return

    # ---------- build jobs ----------
    jobs = []
    pair_name_map = {}  # name -> pair_key
    for p in pairs:
        pair_key = p["pair_key"]
        ref_g = clean_granule_id(p["ref_granule_id"])
        sec_g = clean_granule_id(p["sec_granule_id"])

        name = short_name(pair_key)
        pair_name_map[name] = pair_key

        job_parameters = {
            "granules": [ref_g, sec_g],
            "looks": LOOKS,
            "include_look_vectors": INCLUDE_LOOK_VECTORS,
            "include_los_displacement": INCLUDE_LOS_DISPLACEMENT,
        }

        jobs.append(
            {
                "name": name,
                "job_type": "INSAR_GAMMA",
                "job_parameters": job_parameters,
            }
        )

    payload = {"jobs": jobs}
    resp = hyp3_post_jobs(payload)

    hyp3_jobs = resp.get("jobs", []) if isinstance(resp, dict) else []
    print("HyP3 returned jobs:", len(hyp3_jobs))

    # map response by name (יותר יציב מאינדקס)
    jobs_by_name = {}
    for j in hyp3_jobs:
        n = j.get("name")
        if n:
            jobs_by_name[n] = j

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    pair_keys_to_mark = []

    for job_req in jobs:
        name = job_req["name"]
        pair_key = pair_name_map[name]

        j = jobs_by_name.get(name)
        if j is None:
            # fallback לאינדקס אם API לא מחזיר name משום מה
            idx = list(pair_name_map.keys()).index(name)
            j = hyp3_jobs[idx] if idx < len(hyp3_jobs) else {}

        job_id = j.get("job_id") or j.get("id")
        status_code = j.get("status_code") or "RUNNING"

        if not job_id:
            raise RuntimeError(f"Missing job_id for pair {pair_key}. Job: {json.dumps(j)[:800]}")

        rows.append(
            {
                "job_id": job_id,
                "pair_key": pair_key,
                "product_type": "INSAR_GAMMA",
                "status": normalize_status(status_code),
                "submitted_at": now,
                "updated_at": now,
                "result_meta": j,
            }
        )
        pair_keys_to_mark.append(pair_key)

    # קודם שומרים jobs, ורק אחרי זה מסמנים pairs
    sb_upsert("hyp3_jobs", rows, on_conflict="job_id")
    for pair_key in pair_keys_to_mark:
        sb_patch("pairs", f"?pair_key=eq.{pair_key}", {"status": "submitted"})

    print("Saved hyp3_jobs:", len(rows), "and marked pairs=submitted")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

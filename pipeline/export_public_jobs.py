import os, json, requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
OUT_PATH = os.getenv("OUT_PATH", "client/public/hyp3_jobs.json").strip()

def headers():
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
    }

def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")

    url = f"{SUPABASE_URL}/rest/v1/hyp3_jobs"
    params = {
        "select": "job_id,pair_key,product_type,status,submitted_at,updated_at",
        "order": "submitted_at.desc",
        "limit": "200",
    }
    r = requests.get(url, headers=headers(), params=params, timeout=60)
    r.raise_for_status()
    jobs = r.json()

    counts = {}
    for j in jobs:
        s = (j.get("status") or "unknown").lower()
        counts[s] = counts.get(s, 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "jobs": jobs,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Wrote", OUT_PATH, "jobs:", len(jobs))

if __name__ == "__main__":
    main()

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

def pick_links(result_meta: dict):
    """Best-effort extract common HyP3 file links."""
    if not isinstance(result_meta, dict):
        return {"zip": None, "browse": None, "files": []}

    files = []
    # HyP3 sometimes returns "files": [{"url": "...", "filename": "...", ...}, ...]
    if isinstance(result_meta.get("files"), list):
        for f in result_meta["files"]:
            if isinstance(f, dict):
                url = f.get("url") or f.get("href")
                name = f.get("filename") or f.get("name") or f.get("file_name")
                if url:
                    files.append({"name": name or "", "url": url})

    # heuristics for zip + browse
    zip_url = None
    browse_url = None
    for f in files:
        u = (f.get("url") or "").lower()
        n = (f.get("name") or "").lower()
        if zip_url is None and (u.endswith(".zip") or n.endswith(".zip")):
            zip_url = f["url"]
        if browse_url is None and ("browse" in n or "browse" in u) and (u.endswith(".png") or u.endswith(".jpg") or u.endswith(".jpeg")):
            browse_url = f["url"]

    # Some APIs expose a single "browse_url" or "download_url"
    if browse_url is None:
        browse_url = result_meta.get("browse_url") or result_meta.get("browse")
    if zip_url is None:
        zip_url = result_meta.get("download_url") or result_meta.get("download")

    return {"zip": zip_url, "browse": browse_url, "files": files}

def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")

    url = f"{SUPABASE_URL}/rest/v1/hyp3_jobs"
    params = {
        "select": "job_id,pair_key,product_type,status,submitted_at,updated_at,result_meta",
        "order": "submitted_at.desc",
        "limit": "200",
    }
    r = requests.get(url, headers=headers(), params=params, timeout=60)
    r.raise_for_status()
    rows = r.json()

    counts = {}
    jobs = []
    for j in rows:
        s = (j.get("status") or "unknown").lower()
        counts[s] = counts.get(s, 0) + 1

        links = pick_links(j.get("result_meta"))
        jobs.append({
            "job_id": j.get("job_id"),
            "pair_key": j.get("pair_key"),
            "product_type": j.get("product_type"),
            "status": s,
            "submitted_at": j.get("submitted_at"),
            "updated_at": j.get("updated_at"),
            "download_zip": links["zip"],
            "browse": links["browse"],
            "files": links["files"][:50],  # לא להעמיס
        })

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

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
AOI_WKT = os.getenv("AOI_WKT", "").strip()

DAYS_BACK = int(os.getenv("DAYS_BACK", "14"))
AFTER = os.getenv("AFTER", "").strip()
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "2000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))

ASF_URL = "https://api.daac.asf.alaska.edu/services/search/param"

def compute_start_date() -> str:
    if AFTER:
        return AFTER
    dt = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    return dt.date().isoformat()

def asf_search(aoi_wkt: str, start_date: str):
    params = {
        "platform": "Sentinel-1",
        "processingLevel": "SLC",
        "intersectsWith": aoi_wkt,
        "start": start_date,
        "output": "geojson",
        "maxResults": MAX_RESULTS,
    }

    print("ASF URL:", ASF_URL)
    print("ASF params:", json.dumps({k: params[k] for k in params if k != "intersectsWith"}, ensure_ascii=False))
    print("AOI_WKT length:", len(aoi_wkt))

    r = requests.get(ASF_URL, params=params, timeout=90)
    if r.status_code != 200:
        print("ASF status:", r.status_code)
        print("ASF response (first 400 chars):", r.text[:400])
    r.raise_for_status()
    return r.json()

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def build_rows(features):
    rows = []
    for f in features:
        p = f.get("properties", {}) or {}
        granule_id = p.get("fileID") or p.get("sceneName") or p.get("granuleID") or p.get("productName")
        if not granule_id:
            continue

        rows.append({
            "granule_id": granule_id,
            "start_time": p.get("startTime") or p.get("start"),
            "stop_time": p.get("stopTime") or p.get("stop"),
            "direction": p.get("flightDirection") or p.get("orbitDirection"),
            "relative_orbit": p.get("relativeOrbit") or p.get("pathNumber"),
            "platform": p.get("platform") or p.get("platformName") or "Sentinel-1",
            "aoi_tag": "pilot",
            "status": "new",
            "meta": p,
        })
    return rows

def supabase_upsert_scenes(rows):
    url = f"{SUPABASE_URL}/rest/v1/scenes?on_conflict=granule_id"
    headers = {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    for batch in chunks(rows, BATCH_SIZE):
        r = requests.post(url, headers=headers, json=batch, timeout=120)
        if r.status_code not in (200, 201, 204):
            print("Supabase status:", r.status_code)
            print("Supabase response (first 800 chars):", r.text[:800])
            r.raise_for_status()

def main():
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is empty. Add GitHub secret SUPABASE_URL.")
    if not SERVICE_ROLE:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is empty. Add GitHub secret SUPABASE_SERVICE_ROLE_KEY.")
    if not AOI_WKT:
        raise RuntimeError("AOI_WKT is empty. Add GitHub secret AOI_WKT.")

    start_date = compute_start_date()
    data = asf_search(AOI_WKT, start_date)
    features = data.get("features", []) or []
    print("ASF returned features:", len(features))

    rows = build_rows(features)
    print("Rows to upsert:", len(rows))

    supabase_upsert_scenes(rows)
    print("Upsert done at", datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

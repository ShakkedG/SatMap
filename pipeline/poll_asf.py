import os
import sys
import json
import requests
import psycopg
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()
AOI_WKT = os.getenv("AOI_WKT", "").strip()

DAYS_BACK = int(os.getenv("DAYS_BACK", "7"))
AFTER = os.getenv("AFTER", "").strip()          # אופציונלי: YYYY-MM-DD
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "2000"))

ASF_URL = "https://api.daac.asf.alaska.edu/services/search/param"

def safe_print_db_parts():
    if not SUPABASE_DB_URL:
        print("DB: SUPABASE_DB_URL is EMPTY")
        return
    p = urlparse(SUPABASE_DB_URL)
    print("DB scheme:", p.scheme)
    print("DB host:", p.hostname)
    print("DB port:", p.port)
    print("DB user:", p.username)
    print("DB name:", (p.path or "").lstrip("/"))
    print("DB has sslmode:", "sslmode=" in (p.query or ""))

def compute_after_date() -> str:
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

def upsert_scenes(features):
    # חיבור DB
  with psycopg.connect(SUPABASE_DB_URL, prepare_threshold=0) as con:
        inserted = 0
        for f in features:
            p = f.get("properties", {}) or {}
            granule_id = p.get("fileID") or p.get("sceneName") or p.get("granuleID") or p.get("productName")
            if not granule_id:
                continue

            start_time = p.get("startTime") or p.get("start")
            stop_time = p.get("stopTime") or p.get("stop")
            direction = p.get("flightDirection") or p.get("orbitDirection")
            relative_orbit = p.get("relativeOrbit") or p.get("pathNumber")
            platform = p.get("platform") or p.get("platformName") or "Sentinel-1"

            con.execute(
                """
                insert into scenes(granule_id, start_time, stop_time, direction, relative_orbit, platform, aoi_tag, status, meta)
                values (%s,%s,%s,%s,%s,%s,'pilot','new',%s)
                on conflict (granule_id) do update set
                  start_time=excluded.start_time,
                  stop_time=excluded.stop_time,
                  direction=excluded.direction,
                  relative_orbit=excluded.relative_orbit,
                  platform=excluded.platform,
                  meta=excluded.meta
                """,
                (granule_id, start_time, stop_time, direction, relative_orbit, platform, p),
            )
            inserted += 1

        con.commit()
        return inserted

def main():
    if not AOI_WKT:
        raise RuntimeError("AOI_WKT is empty. Add GitHub Actions secret AOI_WKT (WKT polygon).")

    if not SUPABASE_DB_URL:
        raise RuntimeError("SUPABASE_DB_URL is empty. Add GitHub Actions secret SUPABASE_DB_URL.")

    # דיבאג בטוח ל-DB (בלי סיסמה)
    safe_print_db_parts()

    start_date = compute_after_date()
    data = asf_search(AOI_WKT, start_date)
    features = data.get("features", []) or []
    print("ASF returned features:", len(features))

    inserted = upsert_scenes(features)
    print("Upserted scenes:", inserted)
    print("Done:", datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

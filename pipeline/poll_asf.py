import os
import sys
import json
import requests
import psycopg
from datetime import datetime, timezone, timedelta

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

AOI_WKT = os.environ.get("AOI_WKT", "").strip()

# ברירת מחדל: למשוך רק שבוע אחורה כדי לא לחטוף יותר מדי תוצאות
DAYS_BACK = int(os.environ.get("DAYS_BACK", "7"))
AFTER = os.environ.get("AFTER", "").strip()  # ISO date like 2026-02-01 (optional)
OUTPUT = os.environ.get("ASF_OUTPUT", "geojson")
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "2000"))

def compute_after_date() -> str:
    if AFTER:
        return AFTER
    dt = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    return dt.date().isoformat()

def asf_search(aoi_wkt: str, after_date: str):
    url = "https://api.daac.asf.alaska.edu/services/search/param"
    params = {
        "platform": "Sentinel-1",
        "processingLevel": "SLC",
        "intersectsWith": aoi_wkt,
        "output": OUTPUT,
        "maxResults": MAX_RESULTS,
        # ASF param API accepts "start" (YYYY-MM-DD). We'll use after_date.
        "start": after_date,
    }

    print("ASF URL:", url)
    print("ASF params:", json.dumps({k: params[k] for k in params if k != "intersectsWith"}, ensure_ascii=False))
    print("AOI_WKT length:", len(aoi_wkt))

    r = requests.get(url, params=params, timeout=90)
    if r.status_code != 200:
        print("ASF status:", r.status_code)
        print("ASF response (first 400 chars):", r.text[:400])
    r.raise_for_status()
    return r.json()

def upsert_scenes(features):
    inserted = 0
    with psycopg.connect(SUPABASE_DB_URL) as con:
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
    # אם אין AOI ב-Actions—זה ייפול בצורה ברורה במקום לשלוח intersectsWith ריק
    if not AOI_WKT:
        raise RuntimeError("AOI_WKT is empty. Add GitHub Actions secret AOI_WKT (WKT polygon).")

    after_date = compute_after_date()
    data = asf_search(AOI_WKT, after_date)
    features = data.get("features", []) or []
    print("ASF returned features:", len(features))

    inserted = upsert_scenes(features)
    print("Upserted scenes:", inserted)
    print("Done at", datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

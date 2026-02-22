import os
import requests
import psycopg
from datetime import datetime, timezone

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

AOI_WKT = os.environ.get(
    "AOI_WKT",
    "POLYGON((35.35 31.55, 35.35 31.05, 35.75 31.05, 35.75 31.55, 35.35 31.55))"
)

DATE_START = os.environ.get("DATE_START", "2025-01-01")
DATE_END = os.environ.get("DATE_END")

def asf_search():
    url = "https://api.daac.asf.alaska.edu/services/search/param"
    params = {
        "platform": "Sentinel-1",
        "processingLevel": "SLC",
        "intersectsWith": AOI_WKT,
        "start": DATE_START,
        "output": "geojson",
        "maxResults": 2000,
    }
    if DATE_END:
        params["end"] = DATE_END

    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def upsert_scenes(features):
    with psycopg.connect(SUPABASE_DB_URL) as con:
        for f in features:
            p = f.get("properties", {})
            granule_id = p.get("fileID") or p.get("sceneName") or p.get("granuleID")
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
        con.commit()

def main():
    data = asf_search()
    features = data.get("features", [])
    print("ASF returned:", len(features))
    upsert_scenes(features)
    print("Done:", datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    main()

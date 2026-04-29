import os
import sys
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

AOI_TAG = os.getenv("AOI_TAG", "pilot").strip()
ALLOWED_DELTAS_DAYS = os.getenv("ALLOWED_DELTAS_DAYS", "6,12,24").strip()
MAX_BACKLINKS = int(os.getenv("MAX_BACKLINKS", "3"))  # כמה זוגות אחורה לכל סצנה

def parse_iso(dt_str: str) -> datetime:
    # Supabase מחזיר timestamptz; זה בד"כ ISO עם +00:00
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(timezone.utc)

def get_scenes():
    # מושך את כל הסצנות של aoi_tag=pilot (אפשר לשנות)
    url = f"{SUPABASE_URL}/rest/v1/scenes"
    params = {
        "select": "granule_id,start_time,direction,relative_orbit,platform,aoi_tag",
        "aoi_tag": f"eq.{AOI_TAG}",
        "order": "start_time.asc",
    }
    headers = {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
    }
    r = requests.get(url, headers=headers, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def upsert_pairs(rows):
    url = f"{SUPABASE_URL}/rest/v1/pairs?on_conflict=pair_key"
    headers = {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    # batches קטנים כדי לא לחטוף timeout
    BATCH = 500
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        r = requests.post(url, headers=headers, json=batch, timeout=120)
        if r.status_code not in (200, 201, 204):
            print("Supabase status:", r.status_code)
            print(r.text[:800])
            r.raise_for_status()

def main():
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL missing")
    if not SERVICE_ROLE:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing")

    allowed = sorted({int(x.strip()) for x in ALLOWED_DELTAS_DAYS.split(",") if x.strip()})
    scenes = get_scenes()
    print("Scenes fetched:", len(scenes), "allowed deltas:", allowed)

    # group by (direction, relative_orbit, platform) כדי לא לערבב מסלולים/כיוונים/לווינים
    groups = {}
    for s in scenes:
        if not s.get("start_time") or not s.get("granule_id"):
            continue
        key = (s.get("direction"), s.get("relative_orbit"), s.get("platform"))
        groups.setdefault(key, []).append(s)

    to_upsert = []
    for key, arr in groups.items():
        arr.sort(key=lambda x: x["start_time"])
        # לבנות זוגות “אחורה” לכל סצנה
        for i in range(len(arr)):
            sec = arr[i]
            sec_t = parse_iso(sec["start_time"])

            links = 0
            j = i - 1
            while j >= 0 and links < MAX_BACKLINKS:
                ref = arr[j]
                ref_t = parse_iso(ref["start_time"])
                dd = (sec_t - ref_t).days
                if dd in allowed:
                    ref_id = ref["granule_id"]
                    sec_id = sec["granule_id"]
                    pair_key = f"{ref_id}__{sec_id}"  # ייחודי
                    to_upsert.append({
                        "pair_key": pair_key,
                        "ref_granule_id": ref_id,
                        "sec_granule_id": sec_id,
                        "status": "new",
                        # created_at יש לך default now()
                    })
                    links += 1
                j -= 1

    print("Pairs to upsert:", len(to_upsert))
    if to_upsert:
        upsert_pairs(to_upsert)
    print("Done.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

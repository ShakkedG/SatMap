import os, sys, re, json, csv, zipfile, tempfile
import requests
import rasterio
from datetime import datetime, timezone
from shapely import wkt as shwkt
from pyproj import Transformer

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

OUT_CSV = os.getenv("OUT_CSV", "client/public/insar_buildings.csv").strip()

AOI_WKT = os.getenv("AOI_WKT", "").strip()  # אותו WKT שאתה כבר משתמש בו ל-ASF
GOVMAP_QUERY_URL = os.getenv("GOVMAP_QUERY_URL", "").strip()
GOVMAP_TOKEN = os.getenv("GOVMAP_TOKEN", "").strip()

# הגבלות כדי לא להעמיס
PAGE_SIZE = int(os.getenv("GOVMAP_PAGE_SIZE", "2000"))
MAX_BUILDINGS = int(os.getenv("MAX_BUILDINGS", "50000"))  # תתחיל קטן ותעלה


def sb_headers():
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
    }


def sb_get(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.get(url, headers=sb_headers(), params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def pick_zip_from_result_meta(result_meta: dict) -> str | None:
    if not isinstance(result_meta, dict):
        return None
    files = result_meta.get("files")
    if isinstance(files, list):
        for f in files:
            if isinstance(f, dict):
                u = f.get("url") or f.get("href")
                name = (f.get("filename") or f.get("name") or "").lower()
                if u and (u.lower().endswith(".zip") or name.endswith(".zip")):
                    return u
    u = result_meta.get("download_url") or result_meta.get("download")
    if isinstance(u, str) and u.lower().endswith(".zip"):
        return u
    return None


def extract_pair_dates(pair_key: str):
    dates = re.findall(r"_(\d{8})T", pair_key or "")
    if len(dates) >= 2:
        return dates[0], dates[1]
    return None, None


def days_between(d1: str, d2: str) -> int | None:
    try:
        from datetime import datetime
        a = datetime.strptime(d1, "%Y%m%d")
        b = datetime.strptime(d2, "%Y%m%d")
        return abs((b - a).days)
    except Exception:
        return None


def choose_tif(extracted_dir: str) -> str:
    tifs = []
    for root, _, files in os.walk(extracted_dir):
        for fn in files:
            if fn.lower().endswith((".tif", ".tiff")):
                tifs.append(os.path.join(root, fn))
    if not tifs:
        raise RuntimeError("No GeoTIFF found in HyP3 zip")

    def score(p):
        n = os.path.basename(p).lower()
        # תעדוף displacement/los, לא coherence
        if "los" in n and "dis" in n: return 0
        if "displacement" in n: return 1
        if "unwrap" in n: return 3
        if "coh" in n or "coherence" in n: return 9
        return 5

    tifs.sort(key=score)
    return tifs[0]


def aoi_bounds_4326():
    if not AOI_WKT:
        raise RuntimeError("Missing AOI_WKT env")
    geom = shwkt.loads(AOI_WKT)
    minx, miny, maxx, maxy = geom.bounds
    return minx, miny, maxx, maxy


def govmap_query_buildings_centroids():
    if not GOVMAP_QUERY_URL:
        raise RuntimeError("Missing GOVMAP_QUERY_URL env")

    minx, miny, maxx, maxy = aoi_bounds_4326()
    geometry = f"{minx},{miny},{maxx},{maxy}"

    features = []
    offset = 0

    while True:
        params = {
            "f": "json",
            "where": "1=1",
            "geometry": geometry,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "OBJECTID",
            "returnGeometry": "false",
            "returnCentroid": "true",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
        }
        if GOVMAP_TOKEN:
            params["token"] = GOVMAP_TOKEN

        r = requests.get(GOVMAP_QUERY_URL, params=params, timeout=120)
        r.raise_for_status()
        data = r.json()

        batch = data.get("features") or []
        if not batch:
            break

        for ft in batch:
            attrs = ft.get("attributes") or {}
            oid = attrs.get("OBJECTID") or attrs.get("objectid")
            cent = ft.get("centroid") or {}
            x = cent.get("x")
            y = cent.get("y")
            if oid is None or x is None or y is None:
                continue
            features.append((str(oid), float(x), float(y)))  # lon/lat
            if len(features) >= MAX_BUILDINGS:
                return features

        offset += len(batch)
        if len(batch) < PAGE_SIZE:
            break

    return features


def main():
    if not SUPABASE_URL or not SERVICE_ROLE:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")

    # 1) latest succeeded job
    rows = sb_get("hyp3_jobs", {
        "select": "job_id,pair_key,status,result_meta,updated_at",
        "status": "eq.succeeded",
        "order": "updated_at.desc",
        "limit": "1",
    })
    if not rows:
        print("No succeeded jobs yet.")
        return

    job = rows[0]
    job_id = job.get("job_id")
    pair_key = job.get("pair_key") or ""
    zip_url = pick_zip_from_result_meta(job.get("result_meta"))
    if not zip_url:
        raise RuntimeError("Could not find download zip url in result_meta for job " + str(job_id))

    d1, d2 = extract_pair_dates(pair_key)
    dd = days_between(d1, d2) if d1 and d2 else None
    if not dd or dd <= 0:
        raise RuntimeError("Could not parse pair delta days from pair_key")
    delta_years = dd / 365.25

    print("Using job:", job_id, "delta_days:", dd, "delta_years:", delta_years)
    print("Downloading:", zip_url)

    # 2) fetch building centroids directly from GovMap layer
    buildings = govmap_query_buildings_centroids()
    print("Buildings fetched from GovMap:", len(buildings))
    if not buildings:
        raise RuntimeError("No buildings returned from GovMap query (check AOI_WKT / layer URL)")

    # 3) download + extract zip
    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, "hyp3.zip")
        with requests.get(zip_url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        extract_dir = os.path.join(td, "unzipped")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        tif_path = choose_tif(extract_dir)
        print("Chosen GeoTIFF:", tif_path)

        # 4) sample raster at centroid -> rate
        out_rows = []
        with rasterio.open(tif_path) as src:
            if src.crs is None:
                raise RuntimeError("Raster has no CRS")

            tf = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)

            for oid, lon, lat in buildings:
                x, y = tf.transform(lon, lat)
                val = next(src.sample([(x, y)]))[0]
                try:
                    v = float(val)
                except Exception:
                    continue
                if not (v == v):  # NaN
                    continue

                # הנחה: displacement במטרים -> mm
                disp_mm = v * 1000.0
                rate_mm_yr = disp_mm / delta_years
                out_rows.append((oid, rate_mm_yr))

        # 5) write CSV (בדיוק מה שהאתר שלך מצפה)
        os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["objectid", "rate"])
            w.writerows(out_rows)

        print("Wrote:", OUT_CSV, "rows:", len(out_rows))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        sys.exit(1)

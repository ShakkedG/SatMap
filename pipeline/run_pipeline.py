import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats

ROOT = Path(__file__).resolve().parents[1]

def load_json(path: str) -> dict:
    p = (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def isfinite(v):
    return v is not None and isinstance(v, (int, float)) and np.isfinite(v)

def clamp01(x):
    if not isfinite(x):
        return None
    return float(max(0.0, min(1.0, x)))

def step_mbtiles_to_pmtiles(cfg: dict):
    """
    אופציונלי: אם יש לך MBTiles מ-QGIS ורוצה רק להמיר ל-PMTiles.
    לא שומר שום דבר בגיט, רק מייצר קובץ ב-exports.
    """
    pmtiles_cli = cfg.get("tools", {}).get("pmtiles_cli", "pmtiles")

    mb = cfg.get("mbtiles", {}).get("path")
    out = cfg.get("mbtiles", {}).get("out_pmtiles")
    if not mb or not out:
        print("דילוג: לא הוגדר mbtiles.path / mbtiles.out_pmtiles בקונפיג.")
        return

    mb_path = (ROOT / mb).resolve()
    out_path = (ROOT / out).resolve()
    ensure_dir(out_path.parent)

    if not mb_path.exists():
        raise FileNotFoundError(f"לא נמצא MBTiles: {mb_path}")

    print("ממיר MBTiles → PMTiles...")
    subprocess.check_call([pmtiles_cli, "convert", str(mb_path), str(out_path)])
    print("OK:", out_path)

def step_building_stats(cfg: dict):
    buildings_path = (ROOT / cfg["buildings"]["path"]).resolve()
    buildings_layer = cfg["buildings"]["layer"]
    id_field = cfg["buildings"]["id_field"]

    vel_path = (ROOT / cfg["insar"]["velocity_tif"]).resolve()
    coh_path = (ROOT / cfg["insar"]["coherence_tif"]).resolve()

    out_gpkg = (ROOT / cfg["outputs"]["joined_gpkg"]).resolve()
    out_layer = cfg["outputs"]["joined_layer"]

    thrVel = float(cfg["params"]["thrVel"])
    thrCoh = float(cfg["params"]["thrCoh"])
    minPts = int(cfg["params"]["minPts"])
    suspectBand = float(cfg["params"].get("suspectBand", 0.5))

    ensure_dir(out_gpkg.parent)

    if not buildings_path.exists():
        raise FileNotFoundError(f"לא נמצא buildings.gpkg: {buildings_path}")
    if not vel_path.exists() or not coh_path.exists():
        raise FileNotFoundError(
            "חסרים רסטרים של InSAR. צריך שיהיו:\n"
            f"- {vel_path}\n- {coh_path}\n"
            "ברגע שתשים אותם שם, השלב הזה ירוץ."
        )

    print("טוען בניינים...")
    gdf = gpd.read_file(buildings_path, layer=buildings_layer)
    if gdf.crs is None:
        raise ValueError("לשכבת הבניינים אין CRS. תקבע ב-QGIS ותשמור מחדש.")
    if id_field not in gdf.columns:
        raise ValueError(f"חסר שדה מזהה '{id_field}' בבניינים")

    print("פותח רסטר velocity כדי ליישר CRS...")
    with rasterio.open(vel_path) as vel_src:
        vel_crs = vel_src.crs
        vel_nodata = vel_src.nodata

    if gdf.crs != vel_crs:
        gdf = gdf.to_crs(vel_crs)

    geoms = gdf.geometry

    print("Zonal stats: velocity (mean,count)...")
    vel_stats = zonal_stats(
        geoms, str(vel_path),
        stats=["mean", "count"],
        nodata=vel_nodata,
        all_touched=True
    )

    print("Zonal stats: coherence (mean)...")
    with rasterio.open(coh_path) as coh_src:
        coh_nodata = coh_src.nodata

    coh_stats = zonal_stats(
        geoms, str(coh_path),
        stats=["mean"],
        nodata=coh_nodata,
        all_touched=True
    )

    vel_mean = []
    vel_count = []
    coh_mean = []

    for vs, cs in zip(vel_stats, coh_stats):
        vm = vs.get("mean", None)
        vc = vs.get("count", 0) or 0
        cm = cs.get("mean", None)

        vm = float(vm) if isfinite(vm) else None
        cm = float(cm) if isfinite(cm) else None

        vel_mean.append(vm)
        vel_count.append(int(vc))
        coh_mean.append(cm)

    gdf["Vel_mean"] = vel_mean
    gdf["Vel_count"] = vel_count
    gdf["coer_mean"] = coh_mean

    # שדות קלים לטיילס (מומלץ)
    gdf["vel_mm10"] = gdf["Vel_mean"].apply(lambda v: int(round(v * 10)) if v is not None else None)
    gdf["coh_100"] = gdf["coer_mean"].apply(lambda c: int(round(clamp01(c) * 100)) if c is not None else None)
    gdf["n"] = gdf["Vel_count"].astype(int)

    # status_code: 0 subsiding, 1 suspect, 2 stable, 3 low_quality, 4 no_data
    def status_code(row):
        v = row["Vel_mean"]
        c = row["coer_mean"]
        n = row["Vel_count"]

        if v is None or n <= 0:
            return 4  # no_data

        coh_ok = True if c is None else (c >= thrCoh)
        cnt_ok = (n >= minPts)

        if (not coh_ok) or (not cnt_ok):
            return 3  # low_quality

        if v < thrVel:
            return 0  # subsiding

        if abs(v - thrVel) <= suspectBand:
            return 1  # suspect

        return 2  # stable

    gdf["status"] = gdf.apply(status_code, axis=1)

    if out_gpkg.exists():
        out_gpkg.unlink()  # overwrite פשוט

    print("שומר פלט...")
    gdf.to_file(out_gpkg, layer=out_layer, driver="GPKG")
    print("OK:", out_gpkg, "layer:", out_layer)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to config json (in repo)")
    ap.add_argument("--step", default="stats", choices=["stats", "mbtiles2pmtiles", "all"])
    args = ap.parse_args()

    cfg = load_json(args.config)

    if args.step in ("mbtiles2pmtiles", "all"):
        step_mbtiles_to_pmtiles(cfg)
    if args.step in ("stats", "all"):
        step_building_stats(cfg)

if __name__ == "__main__":
    main()

# SatMap Pipeline (V1)

מטרה: לבנות תהליך אוטומטי שמייצר לבניינים שדות:
- Vel_mean (mm/yr)
- coer_mean (0–1)
- Vel_count (כמות דגימות/פיקסלים)
- status_code (לצביעה מהירה בפרונט)

> חשוב: אי אפשר לחשב Vel/Coherence מהבניינים לבד.
> הפייפליין מניח שבשלב כלשהו נכנסים שני רסטרים:
> data/insar/velocity.tif + data/insar/coherence.tif

## מבנה תיקיות
pipeline/
  config/
    config.example.json
  data/                (לא נכנס לגיט)
    buildings.gpkg
    insar/
      velocity.tif
      coherence.tif
  exports/             (לא נכנס לגיט)
    buildings_joined.gpkg
  run_pipeline.py
  requirements.txt

## איך משתמשים (כשתריץ מקומית/בשרת)
1) שים את שכבת הבניינים כאן:
   pipeline/data/buildings.gpkg (Layer: buildings)
2) שים רסטרים כאן:
   pipeline/data/insar/velocity.tif
   pipeline/data/insar/coherence.tif
3) התקן תלויות:
   pip install -r pipeline/requirements.txt
4) הרץ:
   python pipeline/run_pipeline.py --config pipeline/config/config.example.json --step stats

## שלבים
- step=mbtiles2pmtiles  : המרה מ-MBTiles (של QGIS) ל-PMTiles (אם יש לך mbtiles)
- step=stats            : חישוב סטטיסטיקות לבניינים מתוך velocity/coherence rasters
- step=all              : מריץ הכל לפי מה שקיים

## למה לא מעלים PMTiles לגיט?
כי זה קובץ ענק (GBים), וגיטהאב לא בנוי לזה. מעלים אותו לאחסון חיצוני (R2/S3 וכו') ומפנים אליו מהאתר.

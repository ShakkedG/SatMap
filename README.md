# SatMap

## GOVMAP (GitHub Pages)

הפרויקט משתמש ב־GOVMAP API כדי להציג שכבת משתמש (בניינים) מתוך GOVMAP.

### 1) הוספת טוקן בצורה בטוחה
ב־GitHub:
1. Settings → Secrets and variables → Actions → **New repository secret**
2. שם הסוד: `VITE_GOVMAP_TOKEN`
3. ערך הסוד: הטוקן שקיבלת מ־GOVMAP

ה־workflow כבר מזריק את המשתנה `VITE_GOVMAP_TOKEN` בזמן הבילד.

### 2) שכבת הבניינים
ברירת המחדל היא `225287` בתוך `client/src/App.vue` (משתנה `govmapLayerId`).

### 3) פריסה
ה־GitHub Action תחת `.github/workflows/pages.yml` בונה את Vite ומפרסם ל־GitHub Pages.

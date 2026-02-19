<template>
  <div class="app" dir="rtl">
    <!-- Top bar (CrimesMap-like) -->
    <header class="topbar">
      <div class="brand">
        <div class="title">SatMap</div>
        <div class="subtitle">GovMap בניינים + JOIN ל-CSV + הדגשת תנועה חריגה</div>
      </div>

      <div class="top-actions">
        <button class="btn ghost" @click="fitToLayer" :disabled="!govReady">התמקד בשכבה</button>
        <button class="btn" @click="reloadAll" :disabled="loadingCsv || loadingQuery">טען מחדש</button>
      </div>
    </header>

    <div class="layout">
      <!-- Side panel -->
      <aside class="panel" :class="{ open: panelOpen }">
        <div class="panelHead">
          <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">☰</button>

          <div class="tabs">
            <button class="tab" :class="{ on: tab==='join' }" @click="tab='join'">JOIN</button>
            <button class="tab" :class="{ on: tab==='csv' }" @click="tab='csv'">CSV</button>
            <button class="tab" :class="{ on: tab==='about' }" @click="tab='about'">הסבר</button>
          </div>
        </div>

        <!-- JOIN TAB -->
        <section v-if="tab==='join'" class="box">
          <div class="boxTitle">הדגשה + JOIN</div>

          <div class="grid2">
            <div>
              <label class="lbl">סף חריגה |rate|</label>
              <input class="inp" type="number" step="0.5" v-model.number="rateThreshold" />
              <div class="hint">ה-CSV שלך נראה כמו: <span class="monoInline">id,val2,rate</span> (ללא כותרות)</div>
            </div>

            <div>
              <label class="lbl">הצג גם לא-חריגים</label>
              <div class="rowInline">
                <label class="switch">
                  <input type="checkbox" v-model="showNormals" />
                  <span></span>
                </label>
                <span class="muted">כחול = לא-חריג</span>
              </div>
            </div>
          </div>

          <div class="grid2">
            <div>
              <label class="lbl">שכבת בניינים (GovMap)</label>
              <input class="inp" v-model.trim="BUILDINGS_LAYER" />
              <div class="hint">אצלך זה: <b>225287</b></div>
            </div>

            <div>
              <label class="lbl">שדה מזהה (אם קיים)</label>
              <input class="inp" v-model.trim="BUILDING_ID_FIELD" />
              <div class="hint">אם לא בטוח – תשאיר <b>ID</b> (הקוד גם מנסה ObjectID)</div>
            </div>
          </div>

          <div class="grid2">
            <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady || !csvReady">
              בחר אזור (מלבן) → JOIN
            </button>
            <button class="btn ghost" @click="joinFromExtent" :disabled="!govReady || !csvReady">
              JOIN לפי היקף המפה
            </button>
          </div>

          <div class="grid2">
            <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">נקה הדגשות</button>
            <button class="btn ghost" @click="toggleGovLayer" :disabled="!govReady">
              {{ govLayerVisible ? 'הסתר שכבה' : 'הצג שכבה' }}
            </button>
          </div>

          <div class="sep"></div>

          <div class="stats">
            <div class="stat">
              <div class="k">סטטוס</div>
              <div class="v">
                <span v-if="!govReady">טוען GovMap…</span>
                <span v-else>GovMap מוכן</span>
                <span v-if="loadingCsv"> · CSV…</span>
                <span v-if="loadingQuery"> · בניינים…</span>
              </div>
            </div>

            <div class="stat">
              <div class="k">CSV rows</div>
              <div class="v">{{ csvRowCount }}</div>
            </div>

            <div class="stat">
              <div class="k">בניינים שנשלפו</div>
              <div class="v">{{ buildings.length }}</div>
            </div>

            <div class="stat">
              <div class="k">JOIN hits</div>
              <div class="v">{{ joinedCount }}</div>
            </div>

            <div class="stat">
              <div class="k">חריגים</div>
              <div class="v">{{ anomalies.length }}</div>
            </div>
          </div>

          <div v-if="errorMsg" class="err">{{ errorMsg }}</div>
          <div v-if="warnMsg" class="warn">{{ warnMsg }}</div>
        </section>

        <!-- CSV TAB -->
        <section v-if="tab==='csv'" class="box">
          <div class="boxTitle">טעינת CSV (פתרון 404)</div>

          <div class="muted small">
            הקובץ חייב להיות ב-<b>client/public/data/tablecsv.csv</b><br />
            הקוד מנסה אוטומטית כמה כתובות עד שמוצא (כולל <span class="monoInline">/SatMap/data/...</span>).
          </div>

          <div class="sep"></div>

          <div class="row">
            <div class="lbl">נתיב קובץ</div>
            <div class="mono">{{ CSV_RELATIVE_PATH }}</div>
          </div>

          <div class="row">
            <div class="lbl">נמצא ב-URL</div>
            <div class="mono">{{ csvResolvedUrl || '—' }}</div>
          </div>

          <div class="grid2">
            <button class="btn" @click="loadCsv" :disabled="loadingCsv">טען / רענן CSV</button>
            <button class="btn ghost" @click="showUrlDebug = !showUrlDebug">{{ showUrlDebug ? 'הסתר' : 'הצג' }} ניסיונות URL</button>
          </div>

          <div v-if="showUrlDebug" class="debug">
            <div class="muted small">כתובות שנבדקו:</div>
            <ul class="urlList">
              <li v-for="u in csvTriedUrls" :key="u">{{ u }}</li>
            </ul>
          </div>

          <div class="sep"></div>

          <div class="muted small">תצוגה מקדימה (10 שורות)</div>
          <div class="tableWrap" v-if="csvPreview.length">
            <table class="miniTable">
              <thead>
                <tr><th>id</th><th>val2</th><th>rate</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r,i) in csvPreview" :key="i">
                  <td>{{ r.id }}</td>
                  <td>{{ r.val2 }}</td>
                  <td>{{ r.rate }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- ABOUT TAB -->
        <section v-if="tab==='about'" class="box">
          <div class="boxTitle">איך זה עובד</div>
          <div class="muted small" style="line-height:1.6">
            1) נטען CSV גדול (ללא כותרות) מה-public.<br />
            2) נבנה אינדקס לפי מזהה: גם <b>id</b> וגם וריאנט מספרי.<br />
            3) כשאתה בוחר אזור/extent – אנחנו שולפים בניינים מהשכבה של GovMap (עם WKT).<br />
            4) JOIN נעשה קודם לפי <b>BUILDING_ID_FIELD</b>, ואם אין התאמה – לפי <b>ObjectID</b>.<br />
            5) מציירים Overlay: אדום=חריג, כחול=לא-חריג (אם מופעל).
          </div>
        </section>

        <!-- Anomalies list (always visible bottom) -->
        <section class="box">
          <div class="boxTitle">רשימת חריגים</div>

          <div class="row">
            <label class="lbl">חיפוש</label>
            <input class="inp" v-model.trim="search" placeholder="ID / ObjectID" />
          </div>

          <div v-if="filteredAnomalies.length === 0" class="muted">אין חריגים להצגה.</div>

          <div v-else class="list">
            <button
              v-for="b in filteredAnomalies"
              :key="b.key"
              class="listItem"
              :class="{ on: selected?.key === b.key }"
              @click="selectBuilding(b)"
            >
              <div class="liTop">
                <div class="liId">ID: {{ b.bestJoinId }}</div>
                <div class="liRate">{{ formatRate(b.movement?.rate_mm_yr) }}</div>
              </div>
              <div class="liSub">
                <span>layerId: {{ b.joinKey || '—' }}</span>
                <span class="dot">•</span>
                <span>objectId: {{ b.objectId || '—' }}</span>
              </div>
            </button>
          </div>
        </section>
      </aside>

      <!-- Map -->
      <main class="mapWrap">
        <div id="map" class="map"></div>

        <div class="legend">
          <div class="legItem"><span class="swatch red"></span> חריג</div>
          <div class="legItem"><span class="swatch blue"></span> לא-חריג</div>
          <div class="legItem"><span class="swatch gold"></span> נבחר</div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

/* =========================
 * CONFIG (שלך)
 * ========================= */
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";

// שכבה ושדה מזהה
const BUILDINGS_LAYER = ref("225287");
const BUILDING_ID_FIELD = ref("ID");

// CSV: חייב להיות ב client/public/data/tablecsv.csv
const CSV_RELATIVE_PATH = "data/tablecsv.csv";

/**
 * CSV אצלך: בלי כותרות, 3 עמודות:
 * col0 = id
 * col1 = val2 (לא חובה)
 * col2 = rate (תנועה)
 */
const CSV_COL_ID = 0;
const CSV_COL_VAL2 = 1;
const CSV_COL_RATE = 2;

/* =========================
 * UI / STATE
 * ========================= */
const panelOpen = ref(true);
const tab = ref("join");

const govReady = ref(false);
const govLayerVisible = ref(true);

const rateThreshold = ref(2.0);
const showNormals = ref(false);

const loadingCsv = ref(false);
const loadingQuery = ref(false);

const errorMsg = ref("");
const warnMsg = ref("");

const search = ref("");
const selected = ref(null);

const buildings = ref([]); // {key, objectId, joinKey, wkt, movement, isAnomaly, bestJoinId}
const lastQueryWkt = ref("");

/* =========================
 * CSV data
 * ========================= */
const csvReady = ref(false);
const csvRows = ref([]); // {id,val2,rate}
const csvPreview = ref([]);
const csvResolvedUrl = ref("");
const csvTriedUrls = ref([]);
const showUrlDebug = ref(false);

// JOIN index
const movementIndex = ref(new Map()); // key -> {rate_mm_yr, raw}

/* =========================
 * DERIVED
 * ========================= */
const csvRowCount = computed(() => csvRows.value.length);
const joinedCount = computed(() => buildings.value.filter(b => !!b.movement).length);

const anomalies = computed(() =>
  buildings.value
    .filter(b => b.isAnomaly)
    .sort((a,b) => Math.abs(b.movement?.rate_mm_yr ?? 0) - Math.abs(a.movement?.rate_mm_yr ?? 0))
);

const filteredAnomalies = computed(() => {
  const q = search.value.trim();
  if (!q) return anomalies.value;
  return anomalies.value.filter(b => String(b.bestJoinId || "").includes(q));
});

/* =========================
 * GOVMAP LOADER + INIT
 * ========================= */
function loadGovMapScript() {
  return new Promise((resolve, reject) => {
    if (window.govmap) return resolve();
    const id = "govmap-api-js";
    if (document.getElementById(id)) {
      const t = setInterval(() => {
        if (window.govmap) { clearInterval(t); resolve(); }
      }, 50);
      setTimeout(() => { clearInterval(t); reject(new Error("GovMap loaded but window.govmap missing")); }, 8000);
      return;
    }
    const s = document.createElement("script");
    s.id = id;
    s.src = "https://www.govmap.gov.il/govmap/api/govmap.api.js";
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load govmap.api.js"));
    document.head.appendChild(s);
  });
}

async function initGovMap() {
  errorMsg.value = "";
  await loadGovMapScript();
  if (!GOVMAP_TOKEN) throw new Error("חסר GOVMAP_TOKEN.");

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN,
    background: 3,
    layers: govLayerVisible.value ? [BUILDINGS_LAYER.value] : [],
    layersMode: 1,
    showXY: false,
    identifyOnClick: false,
    zoomButtons: true,
    onLoad: () => {
      govReady.value = true;
      // נסיון להדליק שכבה (API משתנה בין גרסאות)
      try {
        if (govLayerVisible.value) {
          window.govmap.setVisibleLayers?.([BUILDINGS_LAYER.value]);
          window.govmap.addLayers?.([BUILDINGS_LAYER.value]);
        }
      } catch (_) {}
    },
    onError: (e) => {
      errorMsg.value = "שגיאת GovMap: " + (e?.message || JSON.stringify(e));
    },
  });
}

function toggleGovLayer() {
  govLayerVisible.value = !govLayerVisible.value;
  if (!govReady.value) return;
  try {
    if (govLayerVisible.value) {
      window.govmap.setVisibleLayers?.([BUILDINGS_LAYER.value]);
      window.govmap.addLayers?.([BUILDINGS_LAYER.value]);
    } else {
      window.govmap.setVisibleLayers?.([]);
    }
  } catch (_) {}
}

function fitToLayer() {
  // אין תמיד API עקבי ל-zoomToLayer; זה best-effort
  try {
    window.govmap.zoomToLayer?.({ layerName: BUILDINGS_LAYER.value });
  } catch (_) {
    // fallback: אל תקרוס
  }
}

onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
  } catch (_) {}
});

/* =========================
 * CSV: FIX 404 (GitHub Pages)
 * ========================= */

/**
 * יוצר רשימת URL-ים אפשריים ומנסה עד שמוצא:
 * - עובד גם ב: https://USER.github.io/REPO/   (כמו SatMap)
 * - וגם ב: https://domain/   (שורש)
 */
function buildCsvCandidateUrls() {
  const origin = window.location.origin;
  const host = window.location.hostname;
  const path = window.location.pathname; // /SatMap/ or /SatMap/index.html ...

  // 1) URL יחסי לעמוד (הכי חסין):
  const relToPage = new URL(`./${CSV_RELATIVE_PATH}`, window.location.href).href;

  // 2) Root:
  const root = new URL(`/${CSV_RELATIVE_PATH}`, origin).href;

  // 3) אם זה github.io – ננסה להוסיף את שם הריפו כסגמנט ראשון
  let repoGuess = "";
  if (host.endsWith("github.io")) {
    const seg = path.split("/").filter(Boolean)[0]; // "SatMap"
    if (seg) repoGuess = new URL(`/${seg}/${CSV_RELATIVE_PATH}`, origin).href;
  }

  // 4) אם יש <base href> (לפעמים ב-Vite):
  const baseHref = document.querySelector("base")?.href;
  const baseTry = baseHref ? new URL(CSV_RELATIVE_PATH, baseHref).href : "";

  const list = [baseTry, repoGuess, relToPage, root].filter(Boolean);

  // remove duplicates
  return [...new Set(list)];
}

async function loadCsv() {
  loadingCsv.value = true;
  errorMsg.value = "";
  warnMsg.value = "";
  csvResolvedUrl.value = "";
  csvTriedUrls.value = [];

  try {
    const candidates = buildCsvCandidateUrls();
    csvTriedUrls.value = candidates;

    let okUrl = "";
    let text = "";

    for (const u of candidates) {
      try {
        const res = await fetch(u, { cache: "no-store" });
        if (!res.ok) continue;
        const t = await res.text();
        if (t && t.length > 10) { // קצת sanity
          okUrl = u;
          text = t;
          break;
        }
      } catch (_) {}
    }

    if (!okUrl) {
      throw new Error(
        `לא נמצא CSV. בדוק שהוא קיים ב client/public/${CSV_RELATIVE_PATH} ושהוא עלה לפרודקשן. (404)`
      );
    }

    csvResolvedUrl.value = okUrl;

    const { rows, preview } = parseHeaderlessCsv3cols(text);
    csvRows.value = rows;
    csvPreview.value = preview;

    buildMovementIndexFromCsv();

    csvReady.value = true;

    if (rows.length < 10) {
      warnMsg.value = "ה-CSV נטען אבל יש מעט שורות. בדוק שהקובץ בפורמט הנכון.";
    }
  } catch (err) {
    csvReady.value = false;
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingCsv.value = false;
  }
}

function parseHeaderlessCsv3cols(csvText) {
  const lines = csvText.split(/\r?\n/).filter(l => l.trim().length);
  const rows = [];
  const preview = [];

  for (let i = 0; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i], ",");
    if (cells.length < 3) continue;

    const r = {
      id: String(cells[CSV_COL_ID] ?? "").trim(),
      val2: String(cells[CSV_COL_VAL2] ?? "").trim(),
      rate: String(cells[CSV_COL_RATE] ?? "").trim(),
    };

    rows.push(r);
    if (preview.length < 10) preview.push(r);
  }

  return { rows, preview };
}

function parseCsvLine(line, delimiter = ",") {
  const out = [];
  let cur = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { cur += '"'; i++; }
      else inQuotes = !inQuotes;
      continue;
    }
    if (!inQuotes && ch === delimiter) { out.push(cur); cur = ""; continue; }
    cur += ch;
  }
  out.push(cur);
  return out;
}

function normalizeId(v) {
  return String(v ?? "").trim();
}
function normalizeIdNumeric(v) {
  const s = String(v ?? "").trim();
  if (!s) return "";
  if (!/^-?\d+(\.\d+)?$/.test(s)) return "";
  const n = Number(s);
  return Number.isFinite(n) ? String(n) : "";
}
function toNumberSafe(v) {
  const s = String(v ?? "").trim().replace(",", ".");
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function buildMovementIndexFromCsv() {
  const idx = new Map();

  for (const r of csvRows.value) {
    const id = normalizeId(r.id);
    const rate = toNumberSafe(r.rate);
    if (!id || rate === null) continue;

    const movement = { rate_mm_yr: rate, source: "CSV", raw: r };

    const variants = new Set();
    variants.add(id);
    const asNum = normalizeIdNumeric(id);
    if (asNum) variants.add(asNum);

    for (const k of variants) idx.set(k, movement);
  }

  movementIndex.value = idx;
}

/* =========================
 * GovMap query + JOIN
 * ========================= */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  if (!csvReady.value) { warnMsg.value = "קודם טען CSV."; tab.value = "csv"; return; }

  errorMsg.value = "";
  warnMsg.value = "";
  selected.value = null;

  try {
    const res = await window.govmap.draw(window.govmap.drawType.Rectangle);
    const wkt = res?.wkt;
    if (!wkt) throw new Error("לא התקבל WKT מהשרטוט");
    lastQueryWkt.value = wkt;

    await loadBuildingsByWkt(wkt);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    try { window.govmap.setDefaultTool?.(); } catch (_) {}
  }
}

async function joinFromExtent() {
  if (!govReady.value) return;
  if (!csvReady.value) { warnMsg.value = "קודם טען CSV."; tab.value = "csv"; return; }

  errorMsg.value = "";
  warnMsg.value = "";
  selected.value = null;

  try {
    const ext = await window.govmap.getExtent?.();
    const wkt = extentToWkt(ext);
    if (!wkt) throw new Error("לא הצלחתי לקרוא extent מהמפה");
    lastQueryWkt.value = wkt;
    await loadBuildingsByWkt(wkt);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
}

async function loadBuildingsByWkt(wkt) {
  loadingQuery.value = true;

  try {
    const resp = await window.govmap.intersectFeatures({
      layerName: BUILDINGS_LAYER.value,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD.value, "ID", "BLDG_ID"],
      getShapes: true,
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    const parsed = [];

    for (const it of items) {
      const objectId = String(it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.id ?? "").trim();
      const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];

      const joinKey = String(extractFieldValue(values, BUILDING_ID_FIELD.value) ?? "").trim();
      const shape =
        it?.Shape ??
        it?.shape ??
        it?.WKT ??
        it?.wkt ??
        it?.Geometry ??
        it?.geometry ??
        extractFieldValue(values, "SHAPE");

      const geomWkt = typeof shape === "string" ? shape : "";

      const base = {
        key: `${(joinKey || objectId || "X")}__${objectId || Math.random().toString(16).slice(2)}`,
        objectId,
        joinKey,
        wkt: geomWkt,
        movement: null,
        isAnomaly: false,
        bestJoinId: "",
      };

      parsed.push(applyJoinAndAnomaly(base));
    }

    buildings.value = parsed;

    await redrawOverlays();

    if (parsed.length && joinedCount.value === 0 && movementIndex.value.size) {
      warnMsg.value =
        "נשלפו בניינים אבל JOIN hits=0. זה אומר שה-ID ב-CSV לא תואם לשדה בשכבה. הקוד כבר מנסה גם ObjectID.";
    }
  } finally {
    loadingQuery.value = false;
  }
}

function extractFieldValue(values, fieldName) {
  if (!values) return null;

  if (Array.isArray(values)) {
    const hit = values.find((x) => {
      const n = x?.FieldName ?? x?.fieldName ?? x?.name ?? x?.Field ?? x?.field ?? "";
      return String(n).toLowerCase() === String(fieldName).toLowerCase();
    });
    if (hit) return hit?.Value ?? hit?.value ?? hit?.val ?? null;
  } else if (typeof values === "object") {
    const keys = Object.keys(values);
    const k = keys.find((k0) => k0.toLowerCase() === String(fieldName).toLowerCase());
    return k ? values[k] : null;
  }

  return null;
}

function applyJoinAndAnomaly(b) {
  const keys = [];

  if (b.joinKey) {
    keys.push(normalizeId(b.joinKey));
    keys.push(normalizeIdNumeric(b.joinKey));
  }
  if (b.objectId) {
    keys.push(normalizeId(b.objectId));
    keys.push(normalizeIdNumeric(b.objectId));
  }

  const candidates = keys.filter(Boolean);

  let movement = null;
  let best = "";

  for (const k of candidates) {
    const hit = movementIndex.value.get(k);
    if (hit) { movement = hit; best = k; break; }
  }

  const rate = movement?.rate_mm_yr;
  const isAnom = typeof rate === "number" && Number.isFinite(rate)
    ? Math.abs(rate) >= Number(rateThreshold.value)
    : false;

  return {
    ...b,
    movement,
    isAnomaly: !!movement && isAnom,
    bestJoinId: best || (b.joinKey || b.objectId || ""),
  };
}

function extentToWkt(ext) {
  if (!ext) return "";
  const xmin = ext?.xmin ?? ext?.XMin ?? ext?.XMIN;
  const ymin = ext?.ymin ?? ext?.YMin ?? ext?.YMIN;
  const xmax = ext?.xmax ?? ext?.XMax ?? ext?.XMAX;
  const ymax = ext?.ymax ?? ext?.YMax ?? ext?.YMAX;
  if (![xmin, ymin, xmax, ymax].every(v => typeof v === "number")) return "";
  return `POLYGON((${xmin} ${ymin}, ${xmax} ${ymin}, ${xmax} ${ymax}, ${xmin} ${ymax}, ${xmin} ${ymin}))`;
}

/* =========================
 * Drawing overlays
 * ========================= */
const MAX_DRAW_ANOM = 900;
const MAX_DRAW_NORM = 900;

function isPolygonWkt(wkt) {
  const s = String(wkt || "").trim().toUpperCase();
  return s.startsWith("POLYGON") || s.startsWith("MULTIPOLYGON");
}

async function clearOverlays() {
  if (!govReady.value) return;
  try {
    window.govmap.clearGeometriesByName(["anom_poly", "norm_poly", "sel_poly"]);
  } catch (_) {}
}

async function redrawOverlays() {
  if (!govReady.value) return;
  await clearOverlays();

  const anom = [];
  const norm = [];

  for (const b of buildings.value) {
    if (!b.wkt || !isPolygonWkt(b.wkt)) continue;
    if (b.isAnomaly) anom.push(b);
    else if (showNormals.value) norm.push(b);
  }

  if (showNormals.value && norm.length) {
    const list = norm.slice(0, MAX_DRAW_NORM);
    await window.govmap.displayGeometries({
      wkts: list.map(b => b.wkt),
      names: list.map(() => "norm_poly"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [0, 80, 255, 0.85], outlineWidth: 1, fillColor: [0, 80, 255, 0.12] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (anom.length) {
    const list = anom.slice(0, MAX_DRAW_ANOM);
    await window.govmap.displayGeometries({
      wkts: list.map(b => b.wkt),
      names: list.map(() => "anom_poly"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [255, 0, 0, 1], outlineWidth: 2, fillColor: [255, 0, 0, 0.33] },
      clearExisting: false,
      showBubble: false,
    });
  }
}

async function drawSelectedOverlay(b) {
  if (!govReady.value || !b?.wkt || !isPolygonWkt(b.wkt)) return;
  try { window.govmap.clearGeometriesByName(["sel_poly"]); } catch (_) {}
  await window.govmap.displayGeometries({
    wkts: [b.wkt],
    names: ["sel_poly"],
    geometryType: window.govmap.geometryType.POLYGON,
    defaultSymbol: { outlineColor: [255, 215, 0, 1], outlineWidth: 3, fillColor: [255, 215, 0, 0.14] },
    clearExisting: false,
    showBubble: false,
  });
}

async function selectBuilding(b) {
  selected.value = b;
  await drawSelectedOverlay(b);
}

/* =========================
 * Actions
 * ========================= */
async function reloadAll() {
  await loadCsv();
  if (lastQueryWkt.value && govReady.value && csvReady.value) {
    await loadBuildingsByWkt(lastQueryWkt.value);
  }
}

/* =========================
 * Formatting
 * ========================= */
function formatRate(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2)} mm/yr`;
}

/* =========================
 * Lifecycle + watchers
 * ========================= */
onMounted(async () => {
  try {
    await initGovMap();
    await loadCsv();
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
});

watch([rateThreshold, showNormals], async () => {
  buildings.value = buildings.value.map(applyJoinAndAnomaly);
  await redrawOverlays();
});

watch(BUILDINGS_LAYER, () => {
  // אם משנים שכבה, נסה להראות אותה
  if (govReady.value && govLayerVisible.value) {
    try {
      window.govmap.setVisibleLayers?.([BUILDINGS_LAYER.value]);
      window.govmap.addLayers?.([BUILDINGS_LAYER.value]);
    } catch (_) {}
  }
});
</script>

<style scoped>
/* CrimesMap-ish look */
.app{height:100vh;width:100%;background:#f3f5f8;overflow:hidden;display:flex;flex-direction:column}
.topbar{
  height:64px;display:flex;align-items:center;justify-content:space-between;
  padding:0 14px;background:#fff;border-bottom:1px solid #e6e9ef
}
.brand .title{font-weight:900;font-size:18px;letter-spacing:.2px}
.brand .subtitle{font-size:12px;color:#616b7a;margin-top:2px}
.top-actions{display:flex;gap:10px}

.layout{flex:1;display:grid;grid-template-columns:420px 1fr;min-height:0}
.panel{background:#fff;border-left:1px solid #e6e9ef;overflow:auto;padding:12px;min-height:0}
.panelHead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}
.iconBtn{border:1px solid #dfe4ee;background:#fff;border-radius:12px;width:40px;height:40px;cursor:pointer;font-weight:900}
.tabs{display:flex;gap:8px}
.tab{border:1px solid #dfe4ee;background:#fff;border-radius:999px;padding:8px 12px;cursor:pointer;font-weight:900;font-size:12px;color:#2a3240}
.tab.on{background:#1d5cff;border-color:#1d5cff;color:#fff}

.box{border:1px solid #eef1f6;border-radius:16px;padding:12px;background:#fbfcff;margin-bottom:12px}
.boxTitle{font-weight:900;margin-bottom:10px}
.lbl{font-size:12px;color:#2a3240;font-weight:800}
.inp{width:100%;padding:10px;border:1px solid #dfe4ee;border-radius:12px;outline:none;background:#fff;margin-top:6px}
.hint{margin-top:6px;font-size:12px;color:#687285}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.row{display:grid;grid-template-columns:120px 1fr;gap:10px;align-items:center;margin-top:10px}
.rowInline{display:flex;align-items:center;gap:10px;margin-top:8px}

.btn{padding:10px 12px;border-radius:12px;border:1px solid #1d5cff;background:#1d5cff;color:#fff;cursor:pointer;font-weight:900}
.btn.ghost{background:#fff;color:#1d5cff}
.btn:disabled{opacity:.6;cursor:not-allowed}

.sep{height:1px;background:#eef1f6;margin:12px 0}

.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.stat{border:1px solid #eef1f6;border-radius:14px;padding:10px;background:#fff}
.stat .k{font-size:12px;color:#6a7282}
.stat .v{font-size:14px;font-weight:900;margin-top:2px}

.err{margin-top:10px;padding:10px;border-radius:14px;background:#fff1f1;border:1px solid #ffd0d0;color:#b3261e;font-size:13px}
.warn{margin-top:10px;padding:10px;border-radius:14px;background:#fff7e6;border:1px solid #ffe2a8;color:#7a4b00;font-size:13px}

.muted{color:#6a7282}
.muted.small{font-size:12px;line-height:1.5}

.mono{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  background:#f3f5fb;border:1px solid #e9ecf7;border-radius:12px;padding:8px 10px;direction:ltr;text-align:left;overflow:auto}
.monoInline{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  background:#f3f5fb;border:1px solid #e9ecf7;border-radius:10px;padding:2px 6px}

.debug{margin-top:10px}
.urlList{margin:8px 0 0;padding:0 18px;color:#2a3240}
.urlList li{direction:ltr;text-align:left;font-size:12px;margin:4px 0}

.tableWrap{margin-top:10px;border:1px solid #eef1f6;border-radius:14px;background:#fff;overflow:auto;max-height:220px}
.miniTable{width:100%;border-collapse:collapse;font-size:12px}
.miniTable th,.miniTable td{border-bottom:1px solid #eef1f6;padding:8px 10px;white-space:nowrap}
.miniTable th{position:sticky;top:0;background:#fbfcff;z-index:1;font-weight:900}

.list{display:grid;gap:8px;margin-top:10px}
.listItem{text-align:right;padding:10px;border-radius:14px;border:1px solid #eef1f6;background:#fff;cursor:pointer}
.listItem.on{border-color:#1d5cff;box-shadow:0 0 0 3px rgba(29,92,255,.12)}
.liTop{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.liId{font-weight:900}
.liRate{font-weight:900;color:#b3261e}
.liSub{margin-top:6px;font-size:12px;color:#6a7282;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.dot{opacity:.6}

.mapWrap{position:relative;min-height:0}
.map{height:100%;width:100%;background:#dfe6f6}

.legend{
  position:absolute;left:12px;bottom:12px;background:rgba(255,255,255,.92);
  border:1px solid #e6e9ef;border-radius:16px;padding:10px 12px;
  display:grid;gap:8px;box-shadow:0 8px 30px rgba(0,0,0,.08)
}
.legItem{display:flex;align-items:center;gap:8px;font-size:12px;color:#2a3240;font-weight:900}
.swatch{width:14px;height:14px;border-radius:5px;border:1px solid rgba(0,0,0,.15)}
.swatch.red{background:rgba(255,0,0,.35)}
.swatch.blue{background:rgba(0,80,255,.18)}
.swatch.gold{background:rgba(255,215,0,.18)}

/* toggle switch */
.switch{position:relative;width:46px;height:26px;display:inline-block}
.switch input{display:none}
.switch span{position:absolute;inset:0;background:#d7dbea;border-radius:999px;transition:.2s}
.switch span::after{
  content:"";position:absolute;top:3px;right:3px;width:20px;height:20px;background:#fff;border-radius:999px;transition:.2s;
  box-shadow:0 2px 8px rgba(0,0,0,.08)
}
.switch input:checked + span{background:#1d5cff}
.switch input:checked + span::after{transform:translateX(-20px)}

@media (max-width:980px){
  .layout{grid-template-columns:1fr;grid-template-rows:auto 1fr}
  .panel{position:sticky;top:64px;z-index:2}
}
</style>

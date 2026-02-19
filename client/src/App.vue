<template>
  <div class="app" dir="rtl">
    <!-- LEFT PANEL -->
    <aside class="panel" :class="{ open: panelOpen }">
      <header class="panelHeader">
        <div class="brand">
          <div class="title">SatMap</div>
          <div class="subtitle">Buildings (GovMap) + CSV Join + חריגות תנועה</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">☰</button>
      </header>

      <nav class="tabs">
        <button class="tab" :class="{ on: tab === 'search' }" @click="tab = 'search'">חיפוש</button>
        <button class="tab" :class="{ on: tab === 'anoms' }" @click="tab = 'anoms'">חריגים</button>
        <button class="tab" :class="{ on: tab === 'selected' }" @click="tab = 'selected'">נבחר</button>
        <button class="tab" :class="{ on: tab === 'settings' }" @click="tab = 'settings'">הגדרות</button>
      </nav>

      <!-- STATUS BAR -->
      <section class="statusBar">
        <div class="pill" :class="{ ok: govReady }">
          <span class="dot"></span>
          <span>{{ govReady ? "GovMap מוכן" : "טוען GovMap..." }}</span>
        </div>
        <div class="pill" :class="{ ok: csvReady }" :title="csvReady ? `שורות: ${csvRowCount.toLocaleString()}` : csvError || ''">
          <span class="dot"></span>
          <span>{{ csvReady ? "CSV נטען" : "טוען CSV..." }}</span>
        </div>
      </section>

      <div v-if="topError" class="errTop">
        {{ topError }}
      </div>

      <!-- SEARCH TAB -->
      <section v-show="tab === 'search'" class="box">
        <div class="boxTitle">חיפוש בסגנון CrimesMap</div>

        <div class="row">
          <label class="lbl">כתובת (GovMap geocode)</label>
          <input class="inp" v-model.trim="addressQuery" placeholder="לדוגמה: הרוקמים 26 חולון" />
        </div>
        <div class="row2">
          <button class="btn" :disabled="!govReady || !addressQuery" @click="locateAddress">אתר</button>
          <button class="btn ghost" :disabled="!govReady" @click="toggleClickPick">
            {{ clickPickOn ? "כיבוי לחיצה להצגת נתונים" : "הדלק לחיצה להצגת נתונים" }}
          </button>
        </div>

        <div class="sep"></div>

        <div class="row">
          <label class="lbl">חיפוש לפי מזהה בניין (Join Key)</label>
          <input class="inp" v-model.trim="idQuery" placeholder="הדבק ID של בניין" @keydown.enter="highlightIdOnMap" />
        </div>
        <div class="row2">
          <button class="btn" :disabled="!govReady || !idQuery" @click="highlightIdOnMap">הדגש במפה</button>
          <button class="btn ghost" :disabled="!idQuery" @click="openCsvOnlyById">הצג נתוני CSV</button>
        </div>

        <div class="hint">
          טיפ: אחרי “הדגש במפה” פשוט לחץ על הבניין כדי לראות את הנתונים שלו מה־CSV.
        </div>
      </section>

      <!-- ANOMALIES TAB -->
      <section v-show="tab === 'anoms'" class="box">
        <div class="boxTitle">חריגים (לפי |rate|)</div>

        <div class="row">
          <label class="lbl">סף חריגה |rate| (mm/yr)</label>
          <input class="inp" type="number" v-model.number="rateThreshold" step="0.5" />
        </div>

        <div class="row">
          <label class="lbl">הצג גם לא־חריגים</label>
          <label class="switch">
            <input type="checkbox" v-model="showNormals" />
            <span></span>
          </label>
        </div>

        <div class="row2">
          <button class="btn" :disabled="!govReady" @click="drawRectangleAndLoad">בחר אזור (מלבן) וטעינה</button>
          <button class="btn ghost" :disabled="!govReady || !lastQueryWkt" @click="refreshFromLastQuery">טען שוב</button>
        </div>

        <div class="row2">
          <button class="btn ghost" :disabled="!govReady" @click="clearOverlays">נקה הדגשות</button>
          <button class="btn ghost" :disabled="loadingQuery" @click="toggleAutoRefresh">
            {{ autoRefresh ? "כבה עדכון אוטומטי" : "הדלק עדכון אוטומטי" }}
          </button>
        </div>

        <div class="sep"></div>

        <div class="stats">
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
          <div class="stat">
            <div class="k">מצב</div>
            <div class="v">{{ loadingQuery ? "טוען…" : "מוכן" }}</div>
          </div>
        </div>

        <div class="sep"></div>

        <div v-if="anomalies.length === 0" class="muted">
          אין חריגים כרגע. בחר אזור/הורד סף.
        </div>

        <div v-else class="list">
          <button
            v-for="b in anomalies"
            :key="b.key"
            class="listItem"
            :class="{ on: selected?.key === b.key }"
            @click="selectBuilding(b)"
          >
            <div class="liTop">
              <div class="liId">ID: {{ b.joinKey }}</div>
              <div class="liRate">{{ formatRate(b.csv?.rate) }}</div>
            </div>
            <div class="liSub">
              <span>objectId: {{ b.objectId }}</span>
              <span class="dotSep">•</span>
              <span v-if="b.csv?.rowsCount">שורות CSV: {{ b.csv.rowsCount }}</span>
              <span v-else>אין CSV</span>
            </div>
          </button>
        </div>
      </section>

      <!-- SELECTED TAB -->
      <section v-show="tab === 'selected'" class="box">
        <div class="boxTitle">בניין נבחר</div>

        <div v-if="!selected" class="muted">
          לחץ על בניין במפה (כשהמצב “לחיצה להצגת נתונים” דולק) או בחר מהרשימה.
        </div>

        <div v-else>
          <div class="kv">
            <div class="k">Join Key</div>
            <div class="v">{{ selected.joinKey }}</div>

            <div class="k">Rate (CSV)</div>
            <div class="v">{{ formatRate(selected.csv?.rate) }}</div>

            <div class="k">חריג?</div>
            <div class="v">{{ selected.isAnomaly ? "כן" : "לא" }}</div>

            <div class="k">שורות CSV</div>
            <div class="v">{{ selected.csv?.rowsCount ?? 0 }}</div>
          </div>

          <div class="sep"></div>

          <div class="boxTitle small">שורות מה־CSV (ראשונות)</div>
          <div v-if="!selected.csv?.rows?.length" class="muted">לא נמצאו נתוני CSV ל־ID הזה.</div>

          <div v-else class="csvTable">
            <div class="csvRow csvHead">
              <div v-for="(h, i) in selected.csv.headers" :key="i" class="cell">{{ h }}</div>
            </div>
            <div v-for="(r, ri) in selected.csv.rows" :key="ri" class="csvRow">
              <div v-for="(c, ci) in r" :key="ci" class="cell">{{ c }}</div>
            </div>
          </div>

          <div class="row2 mt12">
            <button class="btn ghost" :disabled="!govReady" @click="zoomToSelected">התמקד לבניין</button>
            <button class="btn ghost" :disabled="!govReady" @click="clearSelection">נקה בחירה</button>
          </div>
        </div>
      </section>

      <!-- SETTINGS TAB -->
      <section v-show="tab === 'settings'" class="box">
        <div class="boxTitle">הגדרות / דיבוג</div>

        <div class="muted small">
          <div><b>שכבת בניינים:</b> {{ BUILDINGS_LAYER }}</div>
          <div><b>שדה מזהה בשכבה:</b> {{ BUILDING_ID_FIELD }}</div>
          <div><b>CSV:</b> {{ CSV_URL }}</div>
          <div class="mt8">
            אם “לחיצה לא עושה כלום” — ודא שהמצב “לחיצה להצגת נתונים” דולק, ושאתה לוחץ בתוך המפה (לא על הפאנל).
          </div>
        </div>

        <div class="sep"></div>

        <div class="row2">
          <button class="btn ghost" :disabled="!csvReady" @click="reloadCsv">טען CSV מחדש</button>
          <button class="btn ghost" :disabled="!govReady" @click="rebindMapClick">רענן מאזין לחיצה</button>
        </div>

        <div v-if="csvError" class="err mt12">{{ csvError }}</div>
      </section>
    </aside>

    <!-- MAP -->
    <main class="mapWrap">
      <div id="map" class="map"></div>

      <div v-if="toast" class="toast" @click="toast = ''">{{ toast }}</div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

/* =========================
   CONFIG – תתאים אליך
========================= */
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";

// שכבת הבניינים (כמו אצלך)
const BUILDINGS_LAYER = "225287";

// השדה שמייצג מזהה בניין בשכבה (אם לא נכון – לא יהיה JOIN!)
const BUILDING_ID_FIELD = "ID";

// CSV נמצא כאן: client/public/data/tablecsv.csv
// חשוב: BASE_URL זה path (למשל "/SatMap/") ולכן מצרפים מחרוזות ולא משתמשים ב-new URL(..., BASE_URL)
const CSV_URL = `${import.meta.env.BASE_URL}data/tablecsv.csv`;

// אם אין כותרת ב-CSV (נראה שאין) – נשאר false
const CSV_HAS_HEADER = false;

// עמודת ID + עמודת rate (ב-CSV בלי כותרת)
const CSV_ID_COL = 0;
const CSV_RATE_COL = 2;

// כמה שורות להציג בפרטי בניין (לא להעמיס UI)
const MAX_CSV_ROWS_PREVIEW = 20;

// ביצועים בציור
const MAX_DRAW_ANOMALIES = 800;
const MAX_DRAW_NORMALS = 800;

/* =========================
   STATE
========================= */
const panelOpen = ref(true);
const tab = ref("search"); // search | anoms | selected | settings

const govReady = ref(false);
const csvReady = ref(false);
const loadingQuery = ref(false);

const topError = ref("");
const csvError = ref("");

const toast = ref("");

const addressQuery = ref("");
const idQuery = ref("");

const rateThreshold = ref(2.0);
const showNormals = ref(false);
const autoRefresh = ref(false);
const clickPickOn = ref(true);

const lastQueryWkt = ref("");
const buildings = ref([]);
const selected = ref(null);

// CSV index: id -> { rows: string[][], rate: number|null, headers: string[], rowsCount: number }
const csvIndex = ref(new Map());
const csvRowCount = ref(0);
const csvHeaders = ref([]);

// debounce / anti-double click
let lastClickTs = 0;

/* =========================
   DERIVED
========================= */
const joinedCount = computed(() => buildings.value.filter((b) => !!b.csv).length);

const anomalies = computed(() =>
  [...buildings.value]
    .filter((b) => b.isAnomaly)
    .sort((a, b) => Math.abs((b.csv?.rate ?? 0) - 0) - Math.abs((a.csv?.rate ?? 0) - 0))
);

/* =========================
   GOVMAP loader + init
========================= */
function gm() {
  return window.govmap;
}

function loadGovMapScript() {
  return new Promise((resolve, reject) => {
    if (window.govmap) return resolve();
    const id = "govmap-api-js";
    if (document.getElementById(id)) {
      const t = setInterval(() => {
        if (window.govmap) {
          clearInterval(t);
          resolve();
        }
      }, 50);
      setTimeout(() => {
        clearInterval(t);
        reject(new Error("GovMap script loaded but window.govmap not found"));
      }, 12000);
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
  topError.value = "";
  await loadGovMapScript();

  if (!GOVMAP_TOKEN) throw new Error("חסר GOVMAP_TOKEN");

  gm().createMap("map", {
    token: GOVMAP_TOKEN,
    background: 3,
    layers: [BUILDINGS_LAYER],       // מנסה גם להציג את שכבת הבניינים עצמה
    visibleLayers: [BUILDINGS_LAYER],
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    layersMode: 1,
    zoomButtons: true,

    // הכי חשוב: onClick שמתרגם ללחיצה ובודק בניין
    onClick: async (e) => {
      if (!clickPickOn.value) return;
      await handleMapClick(e);
    },

    onLoad: () => {
      govReady.value = true;
      // גיבוי: גם אירוע CLICK (בחלק מהדפדפנים זה יציב יותר)
      rebindMapClick();
      toastMsg("המפה מוכנה. לחץ על בניין כדי לראות נתוני CSV.");
    },
    onError: (e) => {
      topError.value = "שגיאת GovMap: " + (e?.message || JSON.stringify(e));
    },
  });

  // עדכון לפי תצוגה (אם הופעל)
  gm().onEvent(gm().events.EXTENT_CHANGE).progress(async (e) => {
    if (!autoRefresh.value) return;
    const extent = e?.extent;
    const wkt = extentToWkt(extent);
    if (wkt) await loadBuildingsByWkt(wkt);
  });
}

function rebindMapClick() {
  try {
    gm().unbindEvent?.(gm().events.CLICK);
  } catch (_) {}

  try {
    gm().onEvent(gm().events.CLICK).progress(async (e) => {
      if (!clickPickOn.value) return;
      await handleMapClick(e);
    });
  } catch (_) {
    // לא קריטי: onClick של createMap עדיין עובד
  }
}

onBeforeUnmount(() => {
  try {
    gm()?.unbindEvent?.(gm().events.EXTENT_CHANGE);
    gm()?.unbindEvent?.(gm().events.CLICK);
  } catch (_) {}
});

/* =========================
   MAP CLICK -> SELECT BUILDING
========================= */
async function handleMapClick(e) {
  const now = Date.now();
  if (now - lastClickTs < 250) return; // למנוע דאבל-טריגר (onClick + onEvent)
  lastClickTs = now;

  if (!govReady.value) return;

  const p = extractMapPoint(e);
  if (!p) return;

  await inspectBuildingAtPoint(p.x, p.y);
}

function extractMapPoint(e) {
  const mp = e?.mapPoint || e?.MapPoint || e?.point || e?.Point;
  if (mp && typeof mp.x === "number" && typeof mp.y === "number") return { x: mp.x, y: mp.y };

  const x = e?.x ?? e?.X;
  const y = e?.y ?? e?.Y;
  if (typeof x === "number" && typeof y === "number") return { x, y };

  return null;
}

async function inspectBuildingAtPoint(x, y) {
  loadingQuery.value = true;
  topError.value = "";
  try {
    const wkt = `POINT(${x} ${y})`;

    const resp = await gm().intersectFeatures({
      geometry: wkt,
      layerName: BUILDINGS_LAYER,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    if (!items.length) {
      toastMsg("לא נמצא בניין בנקודה הזו.");
      return;
    }

    const it = items[0];
    const objectId = it?.objectid ?? it?.ObjectID ?? it?.OBJECTID ?? it?.id ?? "";

    const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];
    const joinKey = String(extractFieldValue(values, BUILDING_ID_FIELD) ?? "").trim();

    const shape =
      it?.Shape ??
      it?.shape ??
      it?.WKT ??
      it?.wkt ??
      it?.Geometry ??
      it?.geometry ??
      extractFieldValue(values, "SHAPE");

    const geomWkt = typeof shape === "string" ? shape : "";

    if (!joinKey) {
      toastMsg(`נמצא בניין אבל לא נמצא שדה ${BUILDING_ID_FIELD}. עדכן BUILDING_ID_FIELD.`);
      return;
    }

    const b = buildBuildingRecord({
      objectId,
      joinKey,
      wkt: geomWkt,
    });

    selected.value = b;
    tab.value = "selected";

    await drawSelectedOverlay(b);
    await updateMarkerToBuilding(b);

    // הודעה קטנה
    toastMsg(b.csv ? `נבחר בניין ${b.joinKey} (rate: ${formatRate(b.csv.rate)})` : `נבחר בניין ${b.joinKey} (אין נתוני CSV)`);

  } catch (err) {
    topError.value = err?.message || String(err);
  } finally {
    loadingQuery.value = false;
  }
}

function buildBuildingRecord({ objectId, joinKey, wkt }) {
  const csv = lookupCsv(joinKey);
  const rate = csv?.rate;
  const isAnom = typeof rate === "number" && Number.isFinite(rate) ? Math.abs(rate) >= Number(rateThreshold.value) : false;

  return {
    key: `${joinKey}__${objectId || Math.random().toString(16).slice(2)}`,
    objectId,
    joinKey,
    wkt,
    csv,
    isAnomaly: !!csv && isAnom,
  };
}

/* =========================
   CSV LOADING (REAL CSV)
========================= */
async function loadCsv() {
  csvReady.value = false;
  csvError.value = "";
  csvRowCount.value = 0;
  csvIndex.value = new Map();
  csvHeaders.value = [];

  try {
    const res = await fetch(CSV_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`CSV לא נטען (${res.status}) — בדוק שהקובץ נמצא ב-public/data/tablecsv.csv`);

    // Streaming parse (כדי לא לתקוע על 13.6MB)
    const reader = res.body?.getReader?.();
    if (!reader) {
      const text = await res.text();
      parseCsvText(text);
    } else {
      await parseCsvStream(reader);
    }

    csvReady.value = true;
    toastMsg(`CSV נטען בהצלחה (${csvRowCount.value.toLocaleString()} שורות).`);
  } catch (err) {
    csvError.value = err?.message || String(err);
  }
}

async function parseCsvStream(reader) {
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let lineNo = 0;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || "";

    for (const line of lines) {
      lineNo++;
      processCsvLine(line, lineNo);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    lineNo++;
    processCsvLine(buffer, lineNo);
  }
}

function parseCsvText(text) {
  const lines = text.split(/\r?\n/);
  let lineNo = 0;
  for (const line of lines) {
    lineNo++;
    processCsvLine(line, lineNo);
  }
}

function processCsvLine(line, lineNo) {
  const s = line.trim();
  if (!s) return;

  const cols = splitCsvSimple(s);
  if (!cols.length) return;

  // header detection (אם CSV_HAS_HEADER)
  if (lineNo === 1 && CSV_HAS_HEADER) {
    csvHeaders.value = cols.map((c, i) => c || `col${i}`);
    return;
  }

  // no header:
  if (lineNo === 1 && !CSV_HAS_HEADER && !csvHeaders.value.length) {
    // ניצור כותרות גנריות לפי מספר עמודות
    csvHeaders.value = cols.map((_, i) => (i === CSV_ID_COL ? "id" : i === CSV_RATE_COL ? "rate" : `col${i}`));
  }

  const id = normalizeId(cols[CSV_ID_COL]);
  if (!id) return;

  const rate = toNumberSafe(cols[CSV_RATE_COL]);

  const map = csvIndex.value;
  let rec = map.get(id);
  if (!rec) {
    rec = {
      headers: csvHeaders.value,
      rows: [],
      rowsCount: 0,
      rate: null,
    };
    map.set(id, rec);
  }

  rec.rowsCount++;

  // נשמור כמה שורות ראשונות להצגה (לא את כולן)
  if (rec.rows.length < MAX_CSV_ROWS_PREVIEW) {
    rec.rows.push(cols);
  }

  // rate: אם יש כמה שורות לאותו ID – נשמור את האחרון (אפשר להחליף ל-average אם תרצה)
  if (typeof rate === "number" && Number.isFinite(rate)) {
    rec.rate = rate;
  }

  csvRowCount.value++;
}

function splitCsvSimple(line) {
  // parser קל: תומך בקבצי CSV “פשוטים” (כמו אצלך – מספרים מופרדים בפסיק, בלי גרשיים מורכבים)
  // אם בעתיד יהיו גרשיים/פסיקים בתוך טקסט – נחליף ל-parser מלא.
  return line.split(",").map((x) => x.trim());
}

function normalizeId(v) {
  const s = String(v ?? "").trim();
  if (!s) return "";
  // ננסה גם “מספרי” (למקרה שב-GovMap זה number וב-CSV זה string)
  const n = Number(s);
  if (Number.isFinite(n) && String(n) !== "NaN") return String(n);
  return s;
}

function lookupCsv(joinKey) {
  if (!csvReady.value) return null;
  const key1 = normalizeId(joinKey);
  const map = csvIndex.value;

  return map.get(key1) || null;
}

function toNumberSafe(v) {
  const n = Number(String(v).trim());
  return Number.isFinite(n) ? n : null;
}

/* =========================
   LOAD BUILDINGS BY RECT (JOIN + ANOMS)
========================= */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  topError.value = "";
  try {
    const res = await gm().draw(gm().drawType.Rectangle);
    const wkt = res?.wkt;
    if (!wkt) throw new Error("לא התקבל WKT מהשרטוט");
    lastQueryWkt.value = wkt;

    try {
      gm().zoomToDrawing?.();
    } catch (_) {}

    await loadBuildingsByWkt(wkt);
    tab.value = "anoms";
  } catch (err) {
    topError.value = err?.message || String(err);
  } finally {
    try {
      gm().setDefaultTool?.();
    } catch (_) {}
  }
}

async function refreshFromLastQuery() {
  if (!lastQueryWkt.value) return;
  await loadBuildingsByWkt(lastQueryWkt.value);
}

async function loadBuildingsByWkt(wkt) {
  if (!govReady.value) return;
  if (!wkt) return;

  loadingQuery.value = true;
  topError.value = "";

  try {
    const zoom = await gm().getZoomLevel?.();
    if (typeof zoom === "number" && zoom < 7) {
      throw new Error("הזום נמוך מדי לשאילתת בניינים. תתקרב ואז תנסה שוב.");
    }

    const resp = await gm().intersectFeatures({
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    const parsed = [];

    for (const it of items) {
      const objectId = it?.objectid ?? it?.ObjectID ?? it?.OBJECTID ?? it?.id ?? "";
      const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];
      const joinKey = String(extractFieldValue(values, BUILDING_ID_FIELD) ?? "").trim();
      if (!joinKey) continue;

      const shape =
        it?.Shape ??
        it?.shape ??
        it?.WKT ??
        it?.wkt ??
        it?.Geometry ??
        it?.geometry ??
        extractFieldValue(values, "SHAPE");

      const geomWkt = typeof shape === "string" ? shape : "";

      parsed.push(buildBuildingRecord({ objectId, joinKey, wkt: geomWkt }));
    }

    buildings.value = parsed;
    await redrawOverlays();
  } catch (err) {
    topError.value = err?.message || String(err);
  } finally {
    loadingQuery.value = false;
  }
}

/* =========================
   DRAW OVERLAYS
========================= */
async function clearOverlays() {
  if (!govReady.value) return;
  try {
    gm().clearGeometriesByName(["anom", "norm", "sel"]);
  } catch (_) {}
}

async function redrawOverlays() {
  if (!govReady.value) return;

  await clearOverlays();

  const anom = [];
  const norm = [];

  for (const b of buildings.value) {
    if (!b.wkt || !b.wkt.toUpperCase().includes("POLYGON")) continue;
    if (b.isAnomaly) anom.push(b);
    else if (showNormals.value) norm.push(b);
  }

  const anomToDraw = anom.slice(0, MAX_DRAW_ANOMALIES);
  const normToDraw = norm.slice(0, MAX_DRAW_NORMALS);

  if (normToDraw.length) {
    await gm().displayGeometries({
      wkts: normToDraw.map((b) => b.wkt),
      names: normToDraw.map(() => "norm"),
      geometryType: gm().geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [0, 90, 255, 0.65],
        outlineWidth: 1,
        fillColor: [0, 90, 255, 0.10],
      },
      clearExistings: false,
      clearExisting: false,
      showBubble: false,
      data: { tooltips: normToDraw.map((b) => `בניין ${b.joinKey}`) },
    });
  }

  if (anomToDraw.length) {
    await gm().displayGeometries({
      wkts: anomToDraw.map((b) => b.wkt),
      names: anomToDraw.map(() => "anom"),
      geometryType: gm().geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [255, 0, 0, 1],
        outlineWidth: 2,
        fillColor: [255, 0, 0, 0.32],
      },
      clearExistings: false,
      clearExisting: false,
      showBubble: false,
      data: {
        tooltips: anomToDraw.map((b) => `חריג • ${b.joinKey} • ${formatRate(b.csv?.rate)}`),
      },
    });
  }

  // אם יש נבחר – נצייר אותו שוב מעל
  if (selected.value?.wkt) {
    await drawSelectedOverlay(selected.value);
  }
}

async function drawSelectedOverlay(b) {
  if (!govReady.value || !b?.wkt) return;
  try {
    gm().clearGeometriesByName(["sel"]);
  } catch (_) {}

  if (!b.wkt.toUpperCase().includes("POLYGON")) return;

  await gm().displayGeometries({
    wkts: [b.wkt],
    names: ["sel"],
    geometryType: gm().geometryType.POLYGON,
    defaultSymbol: {
      outlineColor: [255, 215, 0, 1],
      outlineWidth: 3,
      fillColor: [255, 215, 0, 0.14],
    },
    clearExistings: false,
    clearExisting: false,
    showBubble: false,
    data: { tooltips: [`נבחר: ${b.joinKey}`] },
  });
}

/* =========================
   UI ACTIONS
========================= */
async function locateAddress() {
  if (!govReady.value || !addressQuery.value) return;
  topError.value = "";
  try {
    const resp = await gm().geocode({
      keyword: addressQuery.value,
      type: gm().geocodeType.AccuracyOnly,
    });

    const x = resp?.X ?? resp?.x ?? resp?.data?.X ?? resp?.data?.x;
    const y = resp?.Y ?? resp?.y ?? resp?.data?.Y ?? resp?.data?.y;

    if (typeof x !== "number" || typeof y !== "number") {
      throw new Error("לא נמצאה תוצאה מדויקת. נסה לנסח כתובת אחרת/להוסיף מספר בית.");
    }

    gm().zoomToXY({ x, y, level: 9 });
    gm().setMapMarker?.({ x, y });
  } catch (err) {
    topError.value = err?.message || String(err);
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value;
  toastMsg(autoRefresh.value ? "עדכון אוטומטי הופעל (Extent Change)" : "עדכון אוטומטי כובה");
}

function toggleClickPick() {
  clickPickOn.value = !clickPickOn.value;
  toastMsg(clickPickOn.value ? "לחיצה להצגת נתונים הופעלה" : "לחיצה להצגת נתונים כובתה");
}

async function highlightIdOnMap() {
  if (!govReady.value || !idQuery.value) return;
  topError.value = "";
  try {
    // מדגיש במפה (לא מחזיר WKT) – אחרי זה המשתמש לוחץ על הבניין כדי לשלוף WKT + CSV
    gm().searchInLayer({
      layerName: BUILDINGS_LAYER,
      fieldName: BUILDING_ID_FIELD,
      fieldValues: [idQuery.value],
      highlight: true,
      showBubble: false,
      outLineColor: [255, 215, 0, 1],
      fillColor: [255, 215, 0, 0.18],
    });

    toastMsg("הודגש במפה. עכשיו לחץ על הבניין כדי לראות נתוני CSV.");
  } catch (err) {
    topError.value = err?.message || String(err);
  }
}

function openCsvOnlyById() {
  const rec = lookupCsv(idQuery.value);
  if (!rec) {
    toastMsg("לא נמצאו נתוני CSV ל־ID הזה.");
    return;
  }
  selected.value = {
    key: `csvonly__${normalizeId(idQuery.value)}`,
    objectId: "",
    joinKey: normalizeId(idQuery.value),
    wkt: "",
    csv: rec,
    isAnomaly: typeof rec.rate === "number" ? Math.abs(rec.rate) >= Number(rateThreshold.value) : false,
  };
  tab.value = "selected";
}

async function selectBuilding(b) {
  selected.value = b;
  tab.value = "selected";
  await drawSelectedOverlay(b);
  await updateMarkerToBuilding(b);
}

async function zoomToSelected() {
  if (!selected.value?.wkt) return;
  const c = centroidFromPolygonWkt(selected.value.wkt);
  if (!c) return;
  gm().zoomToXY({ x: c.x, y: c.y, level: 10 });
  gm().setMapMarker?.({ x: c.x, y: c.y });
}

function clearSelection() {
  selected.value = null;
  try {
    gm().clearGeometriesByName(["sel"]);
  } catch (_) {}
}

async function updateMarkerToBuilding(b) {
  const c = centroidFromPolygonWkt(b.wkt);
  if (!c) return;
  try {
    gm().setMapMarker?.({ x: c.x, y: c.y });
  } catch (_) {}
}

async function reloadCsv() {
  await loadCsv();
}

/* =========================
   HELPERS
========================= */
function toastMsg(msg) {
  toast.value = msg;
  setTimeout(() => {
    if (toast.value === msg) toast.value = "";
  }, 3500);
}

function formatRate(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2)} mm/yr`;
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

function extentToWkt(ext) {
  const xmin = ext?.xmin ?? ext?.XMin ?? ext?.XMIN;
  const ymin = ext?.ymin ?? ext?.YMin ?? ext?.YMIN;
  const xmax = ext?.xmax ?? ext?.XMax ?? ext?.XMAX;
  const ymax = ext?.ymax ?? ext?.YMax ?? ext?.YMAX;
  if (![xmin, ymin, xmax, ymax].every((v) => typeof v === "number")) return "";
  return `POLYGON((${xmin} ${ymin}, ${xmax} ${ymin}, ${xmax} ${ymax}, ${xmin} ${ymax}, ${xmin} ${ymin}))`;
}

function centroidFromPolygonWkt(wkt) {
  if (!wkt || typeof wkt !== "string") return null;
  const m = wkt.match(/POLYGON\s*\(\(\s*([^)]+?)\s*\)\)/i);
  if (!m) return null;

  const coords = m[1]
    .split(",")
    .map((p) => p.trim().split(/\s+/).map(Number))
    .filter((xy) => xy.length >= 2 && Number.isFinite(xy[0]) && Number.isFinite(xy[1]))
    .map(([x, y]) => ({ x, y }));

  if (coords.length < 3) return null;

  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const p = coords[i];
    const q = coords[i + 1];
    const cross = p.x * q.y - q.x * p.y;
    a += cross;
    cx += (p.x + q.x) * cross;
    cy += (p.y + q.y) * cross;
  }
  a *= 0.5;
  if (Math.abs(a) < 1e-9) {
    const sx = coords.reduce((s, p) => s + p.x, 0);
    const sy = coords.reduce((s, p) => s + p.y, 0);
    return { x: sx / coords.length, y: sy / coords.length };
  }
  cx /= 6 * a;
  cy /= 6 * a;
  return { x: cx, y: cy };
}

/* =========================
   LIFECYCLE
========================= */
onMounted(async () => {
  try {
    await initGovMap();
  } catch (e) {
    topError.value = e?.message || String(e);
  }
  await loadCsv();
});

/* =========================
   WATCHERS
========================= */
watch([rateThreshold, showNormals], async () => {
  // עדכון חריגות/תצוגה
  buildings.value = buildings.value.map((b) => buildBuildingRecord({ objectId: b.objectId, joinKey: b.joinKey, wkt: b.wkt }));
  await redrawOverlays();
});
</script>

<style scoped>
/* Layout */
.app {
  height: 100vh;
  width: 100%;
  display: grid;
  grid-template-columns: 390px 1fr;
  background: #f3f5fa;
  overflow: hidden;
}

.panel {
  height: 100%;
  overflow: auto;
  background: #ffffff;
  border-left: 1px solid #e8ebf5;
  padding: 12px 12px 16px;
}

/* Header */
.panelHeader {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 6px 12px;
}

.brand .title {
  font-weight: 900;
  font-size: 18px;
  letter-spacing: 0.2px;
}
.brand .subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #5e667a;
  line-height: 1.25;
}

.iconBtn {
  border: 1px solid #e0e5f3;
  background: #fff;
  border-radius: 12px;
  width: 38px;
  height: 38px;
  cursor: pointer;
}

/* Tabs */
.tabs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 0 4px 10px;
}
.tab {
  border: 1px solid #e7ebf7;
  background: #fbfcff;
  border-radius: 12px;
  padding: 9px 10px;
  font-weight: 800;
  font-size: 13px;
  cursor: pointer;
  color: #2d3342;
}
.tab.on {
  border-color: #2a62ff;
  box-shadow: 0 0 0 3px rgba(42, 98, 255, 0.10);
}

/* Status */
.statusBar {
  display: flex;
  gap: 8px;
  padding: 0 4px 10px;
  flex-wrap: wrap;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid #e7ebf7;
  background: #fbfcff;
  font-size: 12px;
  font-weight: 800;
  color: #5b647a;
}
.pill .dot {
  width: 9px;
  height: 9px;
  border-radius: 99px;
  background: #c8cfdf;
}
.pill.ok {
  color: #1c6b3a;
  border-color: #d9f0e3;
  background: #f2fbf6;
}
.pill.ok .dot {
  background: #22c55e;
}

/* Boxes */
.box {
  border: 1px solid #eef1fb;
  border-radius: 16px;
  padding: 12px;
  margin: 10px 4px;
  background: #fbfcff;
}
.boxTitle {
  font-weight: 900;
  margin-bottom: 10px;
  color: #1f2430;
}
.boxTitle.small {
  font-size: 13px;
  margin-bottom: 8px;
}

.row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
  margin: 10px 0;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.lbl {
  font-size: 13px;
  font-weight: 800;
  color: #2c3342;
}
.inp {
  width: 100%;
  padding: 10px 11px;
  border: 1px solid #e0e5f3;
  border-radius: 12px;
  outline: none;
  background: #fff;
  font-size: 14px;
}

.btn {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid #2a62ff;
  background: #2a62ff;
  color: #fff;
  cursor: pointer;
  font-weight: 900;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn.ghost {
  background: #fff;
  color: #2a62ff;
}

.sep {
  height: 1px;
  background: #eef1fb;
  margin: 12px 0;
}

.hint {
  margin-top: 10px;
  font-size: 12px;
  color: #6a7287;
  line-height: 1.5;
}

/* Stats */
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.stat {
  border: 1px solid #eef1fb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
}
.stat .k {
  font-size: 12px;
  color: #6a7287;
  font-weight: 800;
}
.stat .v {
  font-size: 15px;
  font-weight: 900;
  margin-top: 2px;
  color: #1f2430;
}

/* List */
.list {
  display: grid;
  gap: 8px;
}
.listItem {
  text-align: right;
  padding: 10px;
  border-radius: 14px;
  border: 1px solid #eef1fb;
  background: #fff;
  cursor: pointer;
}
.listItem.on {
  border-color: #2a62ff;
  box-shadow: 0 0 0 3px rgba(42, 98, 255, 0.10);
}
.liTop {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
}
.liId {
  font-weight: 900;
}
.liRate {
  font-weight: 900;
  color: #b3261e;
}
.liSub {
  margin-top: 6px;
  font-size: 12px;
  color: #6a7287;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.dotSep {
  opacity: 0.55;
}

/* Selected KV */
.kv {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px 10px;
}
.kv .k {
  font-size: 12px;
  color: #6a7287;
  font-weight: 800;
}
.kv .v {
  font-size: 13px;
  font-weight: 900;
  color: #1f2430;
}

/* CSV preview */
.csvTable {
  border: 1px solid #eef1fb;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
}
.csvRow {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
}
.csvRow + .csvRow {
  border-top: 1px solid #eef1fb;
}
.csvHead {
  background: #f6f8ff;
  font-weight: 900;
}
.cell {
  padding: 8px 10px;
  font-size: 12px;
  border-left: 1px solid #eef1fb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.csvRow .cell:first-child {
  border-left: none;
}

/* Errors */
.errTop {
  margin: 6px 4px 0;
  padding: 10px;
  border-radius: 14px;
  background: #fff1f1;
  border: 1px solid #ffd0d0;
  color: #b3261e;
  font-size: 13px;
  font-weight: 800;
}
.err {
  padding: 10px;
  border-radius: 14px;
  background: #fff1f1;
  border: 1px solid #ffd0d0;
  color: #b3261e;
  font-size: 13px;
  font-weight: 800;
}
.muted {
  color: #6a7287;
  font-size: 13px;
}
.muted.small {
  font-size: 12px;
  line-height: 1.5;
}
.mt8 { margin-top: 8px; }
.mt12 { margin-top: 12px; }

/* Map */
.mapWrap {
  position: relative;
  height: 100%;
  width: 100%;
}
.map {
  height: 100%;
  width: 100%;
  background: #dfe6f6;
}

/* Toast */
.toast {
  position: absolute;
  left: 14px;
  bottom: 14px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(30, 34, 45, 0.92);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  max-width: min(520px, calc(100% - 28px));
}

/* Toggle */
.switch {
  position: relative;
  width: 46px;
  height: 26px;
  display: inline-block;
}
.switch input { display: none; }
.switch span {
  position: absolute;
  inset: 0;
  background: #d7dbea;
  border-radius: 999px;
  transition: 0.2s;
}
.switch span::after {
  content: "";
  position: absolute;
  top: 3px;
  right: 3px;
  width: 20px;
  height: 20px;
  background: #fff;
  border-radius: 999px;
  transition: 0.2s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.switch input:checked + span { background: #2a62ff; }
.switch input:checked + span::after { transform: translateX(-20px); }

@media (max-width: 980px) {
  .app {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  .panel {
    position: sticky;
    top: 0;
    z-index: 2;
  }
}
</style>

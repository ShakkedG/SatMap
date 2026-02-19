<template>
  <div class="app" dir="rtl">
    <!-- PANEL (CrimesMap-style) -->
    <aside class="panel" :class="{ closed: !panelOpen }">
      <header class="panelHeader">
        <div class="brand">
          <div class="title">SatMap</div>
          <div class="subtitle">Buildings + CSV Join (GovMap)</div>
        </div>

        <div class="headerBtns">
          <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">☰</button>
        </div>
      </header>

      <!-- Search -->
      <section class="card">
        <div class="cardTitle">חיפוש</div>

        <div class="searchRow">
          <input
            class="input"
            v-model.trim="searchId"
            placeholder="חפש לפי Building ID (מהשכבה/CSV)…"
            @keydown.enter.prevent="searchById()"
          />
          <button class="btn" @click="searchById" :disabled="!govReady || !searchId">חפש</button>
        </div>

        <div class="searchRow">
          <input
            class="input"
            v-model.trim="addressQuery"
            placeholder="חיפוש כתובת (GovMap geocode)…"
            @keydown.enter.prevent="locateAddress()"
          />
          <button class="btn ghost" @click="locateAddress" :disabled="!govReady || !addressQuery">אתר</button>
        </div>

        <div class="hint">
          טיפ: אפשר גם פשוט <b>ללחוץ על בניין במפה</b> ותקבל את נתוני ה-CSV שלו.
        </div>
      </section>

      <!-- Controls -->
      <section class="card">
        <div class="cardTitle">סינון ותצוגה</div>

        <div class="grid2">
          <div class="field">
            <label>סף חריגה |rate|</label>
            <input class="input" type="number" v-model.number="rateThreshold" step="0.5" />
            <div class="micro">מעל הסף → מסומן כחריג</div>
          </div>

          <div class="field">
            <label>מצב טעינה</label>
            <div class="pillRow">
              <span class="pill" :class="{ ok: govReady }">GovMap: {{ govReady ? "מוכן" : "טוען…" }}</span>
              <span class="pill" :class="{ ok: csvReady }">CSV: {{ csvReady ? "נטען" : "טוען…" }}</span>
            </div>
            <div class="micro" v-if="csvMeta">
              {{ csvMeta.rows.toLocaleString() }} שורות • ID col: {{ csvMeta.idColName }} • rate col: {{ csvMeta.rateColName }}
            </div>
          </div>
        </div>

        <div class="toggles">
          <label class="toggle">
            <input type="checkbox" v-model="showNormals" />
            <span>הצג גם לא-חריגים</span>
          </label>

          <label class="toggle">
            <input type="checkbox" v-model="autoRefresh" />
            <span>רענון אוטומטי בזום/הזזה</span>
          </label>
        </div>

        <div class="btnRow">
          <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady">בחר אזור (מלבן) וטען</button>
          <button class="btn ghost" @click="refreshFromLastQuery" :disabled="!govReady || !lastQueryWkt">טען שוב</button>
        </div>

        <div class="btnRow">
          <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">נקה הדגשות</button>
          <button class="btn ghost" @click="reloadCsv" :disabled="loadingCsv">רענן CSV</button>
        </div>

        <div class="stats">
          <div class="stat">
            <div class="k">בניינים שהתקבלו</div>
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
            <div class="k">נבחר</div>
            <div class="v">{{ selected ? selected.joinKey : "—" }}</div>
          </div>
        </div>

        <div v-if="errorMsg" class="errorBox">{{ errorMsg }}</div>
      </section>

      <!-- Anomalies list -->
      <section class="card">
        <div class="cardTitle">
          חריגים
          <span class="chip">{{ anomalies.length }}</span>
        </div>

        <div class="listFilter">
          <input class="input" v-model.trim="listQuery" placeholder="סנן ברשימה (ID)…" />
        </div>

        <div v-if="filteredAnomalies.length === 0" class="empty">
          אין חריגים להצגה כרגע.
        </div>

        <div v-else class="list">
          <button
            v-for="b in filteredAnomalies"
            :key="b.key"
            class="rowItem"
            :class="{ active: selected?.key === b.key }"
            @click="selectBuilding(b)"
          >
            <div class="rowMain">
              <div class="id">ID: {{ b.joinKey }}</div>
              <div class="badge danger">{{ formatRate(b.csv?.rate) }}</div>
            </div>
            <div class="rowSub">
              <span>objectId: {{ b.objectId }}</span>
              <span class="dot">•</span>
              <span v-if="b.csv?.rawLineIndex !== undefined">CSV line: {{ b.csv.rawLineIndex }}</span>
              <span v-else>אין שורה ב-CSV</span>
            </div>
          </button>
        </div>
      </section>

      <!-- Selected building details -->
      <section class="card" v-if="selected">
        <div class="cardTitle">פרטי בניין</div>

        <div class="detailTop">
          <div class="bigId">{{ selected.joinKey }}</div>
          <div class="badge" :class="selected.isAnomaly ? 'danger' : 'ok'">
            {{ selected.isAnomaly ? "חריג" : "תקין" }}
          </div>
        </div>

        <div class="kv">
          <div class="k">Rate (מה-CSV)</div>
          <div class="v">{{ formatRate(selected.csv?.rate) }}</div>

          <div class="k">שורה ב-CSV</div>
          <div class="v">{{ selected.csv?.rawLineIndex ?? "—" }}</div>

          <div class="k">objectId</div>
          <div class="v">{{ selected.objectId }}</div>
        </div>

        <div class="subTitle">כל עמודות ה-CSV לבניין</div>
        <div v-if="selected.csv?.cols?.length" class="csvTable">
          <div v-for="(c, i) in selected.csv.cols" :key="i" class="csvRow">
            <div class="csvK">{{ csvMeta?.headers?.[i] ?? `col_${i}` }}</div>
            <div class="csvV">{{ c }}</div>
          </div>
        </div>
        <div v-else class="empty small">
          לא נמצאה רשומה תואמת ב-CSV ל-ID הזה.
        </div>
      </section>

      <!-- About / config -->
      <section class="card">
        <div class="cardTitle">הגדרות (אם צריך לשנות)</div>
        <div class="microBlock">
          <div><b>BUILDINGS_LAYER</b>: {{ BUILDINGS_LAYER }}</div>
          <div><b>BUILDING_ID_FIELD</b>: {{ BUILDING_ID_FIELD }}</div>
          <div><b>CSV_PATH</b>: {{ CSV_PATH }}</div>
        </div>
        <div class="hint">
          אם ה-CSV לא נמצא: ודא שהוא נמצא בנתיב
          <b>client/public/data/tablecsv.csv</b>
          (ואז הוא יוגש כ-<b>/data/tablecsv.csv</b> בתוך האתר).
        </div>
      </section>
    </aside>

    <!-- MAP -->
    <main class="mapWrap">
      <div id="map" class="map"></div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

/* =========================
 * CONFIG
 * ========================= */
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";

// שכבת הבניינים (כמו ב-URL עם lay=225287)
const BUILDINGS_LAYER = "225287";

// השדה שמייצג מזהה בניין בשכבה (תתאים אם צריך)
const BUILDING_ID_FIELD = "ID";

// CSV בתוך public
const CSV_PATH = "data/tablecsv.csv";

// ציור
const MAX_DRAW_ANOMALIES = 800;
const MAX_DRAW_NORMALS = 800;

/* =========================
 * STATE
 * ========================= */
const panelOpen = ref(true);
const govReady = ref(false);

const loadingQuery = ref(false);
const loadingCsv = ref(false);

const errorMsg = ref("");

const rateThreshold = ref(2.0);
const showNormals = ref(false);
const autoRefresh = ref(false);

const addressQuery = ref("");
const searchId = ref("");
const listQuery = ref("");

const lastQueryWkt = ref("");

const buildings = ref([]);   // results after JOIN (from queried area)
const selected = ref(null);

const csvReady = ref(false);
const csvIndex = ref(new Map()); // id -> { cols[], rate, rawLineIndex }
const csvMeta = ref(null);       // { rows, headers, idCol, rateCol, idColName, rateColName }

/* Guards */
const isDrawing = ref(false);
const clickHandlerBound = ref(false);

/* =========================
 * DERIVED
 * ========================= */
const joinedCount = computed(() => buildings.value.filter((b) => !!b.csv).length);

const anomalies = computed(() =>
  buildings.value
    .filter((b) => b.isAnomaly)
    .sort((a, b) => Math.abs((b.csv?.rate ?? 0)) - Math.abs((a.csv?.rate ?? 0)))
);

const filteredAnomalies = computed(() => {
  const q = (listQuery.value || "").trim();
  if (!q) return anomalies.value;
  return anomalies.value.filter((b) => String(b.joinKey).includes(q));
});

/* =========================
 * GOVMAP loader
 * ========================= */
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
        reject(new Error("GovMap script loaded but govmap object not found"));
      }, 8000);
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

  if (!GOVMAP_TOKEN) throw new Error("חסר GOVMAP_TOKEN");

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN,
    background: "3",
    // מדליק את שכבת הבניינים עצמה במפה:
    layers: [BUILDINGS_LAYER],
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    layersMode: 1,
    zoomButtons: true,
    onLoad: () => {
      govReady.value = true;
      bindGovMapEvents();
    },
    onError: (e) => {
      errorMsg.value = "שגיאת GovMap: " + (e?.message || JSON.stringify(e));
    },
  });
}

function bindGovMapEvents() {
  if (clickHandlerBound.value) return;
  clickHandlerBound.value = true;

  // CLICK event – מתועד רשמית ומחזיר mapPoint (x,y). :contentReference[oaicite:2]{index=2}
  window.govmap.onEvent(window.govmap.events.CLICK).progress(async (e) => {
    if (isDrawing.value) return;          // לא להפריע בזמן שרטוט
    if (!govReady.value) return;

    const p = e?.mapPoint;
    if (!p || typeof p.x !== "number" || typeof p.y !== "number") return;

    await inspectBuildingAtPoint(p.x, p.y, true);
  });

  // auto refresh on extent change
  window.govmap.onEvent(window.govmap.events.EXTENT_CHANGE).progress(async (e) => {
    if (!autoRefresh.value) return;
    const extent = e?.extent;
    const wkt = extentToWkt(extent);
    if (wkt) await loadBuildingsByWkt(wkt);
  });
}

/* =========================
 * CSV loading (real CSV)
 * ========================= */
function buildCsvUrlCandidates() {
  // הכי יציב ל-GH Pages: BASE_URL + "data/tablecsv.csv"
  const base = (import.meta?.env?.BASE_URL ?? "/").toString(); // לדוגמה "/SatMap/"
  const c1 = `${base}${CSV_PATH}`;     // "/SatMap/data/tablecsv.csv"
  const c2 = `./${CSV_PATH}`;          // יחסי לעמוד הנוכחי
  const c3 = `/${CSV_PATH}`;           // root (לפעמים עובד אם האתר ב-root)
  return [c1, c2, c3];
}

async function fetchFirstOk(urls) {
  let lastErr = null;
  for (const u of urls) {
    try {
      const res = await fetch(u, { cache: "no-store" });
      if (res.ok) return { url: u, res };
      lastErr = new Error(`${u} → ${res.status}`);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("CSV fetch failed");
}

function isProbablyHeaderLine(line) {
  // אם יש אותיות – כנראה כותרת
  return /[A-Za-z\u0590-\u05FF]/.test(line);
}

// CSV parser מהיר (ללא ספריות) – מספיק טוב ל-13MB
function parseCsvToIndex(csvText) {
  const text = csvText.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  let i = 0;
  let lineStart = 0;

  // לקרוא שורה ראשונה
  const firstNL = text.indexOf("\n");
  const firstLine = (firstNL === -1 ? text : text.slice(0, firstNL)).trim();

  let headers = null;
  let idCol = 0;
  let rateCol = null; // נזהה אוטומטית, ואם אין אז "אחרון"
  let lineIndex = 0;

  if (firstLine && isProbablyHeaderLine(firstLine)) {
    headers = splitCsvLine(firstLine);
    lineIndex = 1;
    lineStart = firstNL + 1;

    idCol = detectIdColumn(headers);
    rateCol = detectRateColumn(headers);
    if (rateCol == null) rateCol = headers.length - 1;
  } else {
    // אין כותרת: id=col0, rate=colLast
    headers = null;
    idCol = 0;
    // נזהה לפי מספר עמודות של השורה הראשונה
    const cols = splitCsvLine(firstLine);
    rateCol = Math.max(0, cols.length - 1);
    lineIndex = 0;
    lineStart = 0;
  }

  const idx = new Map();
  let rows = 0;

  // iterate lines without creating huge array
  i = lineStart;
  while (i <= text.length) {
    const nl = text.indexOf("\n", i);
    const end = nl === -1 ? text.length : nl;
    const line = text.slice(i, end).trim();
    i = end + 1;

    if (!line) continue;

    const cols = splitCsvLine(line);
    if (!cols.length) continue;

    const id = (cols[idCol] ?? "").toString().trim();
    if (!id) continue;

    const rateRaw = cols[rateCol];
    const rate = toNumberSafe(rateRaw);

    idx.set(id, {
      cols,
      rate,
      rawLineIndex: lineIndex,
    });

    lineIndex++;
    rows++;
  }

  const idColName = headers ? headers[idCol] : `col_${idCol}`;
  const rateColName = headers ? headers[rateCol] : `col_${rateCol}`;

  return {
    idx,
    meta: {
      rows,
      headers,
      idCol,
      rateCol,
      idColName,
      rateColName,
    },
  };
}

function splitCsvLine(line) {
  // CSV פשוט (תואם למבנה שלך: ערכים מופרדים בפסיקים, בלי quoted commas מורכבים)
  // אם בעתיד יהיו גרשיים/פסיקים בתוך שדה – נחליף ל-parser מלא.
  return line.split(",").map((s) => s.trim());
}

function detectIdColumn(headers) {
  const lowered = headers.map((h) => String(h).toLowerCase());
  const candidates = ["id", "bldg_id", "building_id", "objectid", "oid", "gid"];
  for (const c of candidates) {
    const hit = lowered.findIndex((h) => h === c || h.includes(c));
    if (hit !== -1) return hit;
  }
  return 0;
}

function detectRateColumn(headers) {
  const lowered = headers.map((h) => String(h).toLowerCase());
  const candidates = ["rate", "rate_mm_yr", "mm/yr", "mm_yr", "velocity", "vel", "v", "delta", "drate"];
  for (const c of candidates) {
    const hit = lowered.findIndex((h) => h === c || h.includes(c));
    if (hit !== -1) return hit;
  }
  return null;
}

async function reloadCsv() {
  loadingCsv.value = true;
  errorMsg.value = "";
  csvReady.value = false;

  try {
    const { res } = await fetchFirstOk(buildCsvUrlCandidates());
    const txt = await res.text();

    const { idx, meta } = parseCsvToIndex(txt);
    csvIndex.value = idx;
    csvMeta.value = meta;
    csvReady.value = true;

    // refresh current buildings anomalies
    if (buildings.value.length) {
      buildings.value = buildings.value.map((b) => applyJoinAndAnomaly(b));
      await redrawOverlays();
    }
  } catch (e) {
    errorMsg.value =
      "לא הצלחתי לטעון_toggle_את ה-CSV. בדוק שהקובץ נמצא ב client/public/data/tablecsv.csv וש-GH Pages מגיש אותו.\n" +
      (e?.message || String(e));
  } finally {
    loadingCsv.value = false;
  }
}

/* =========================
 * JOIN + anomaly logic
 * ========================= */
function applyJoinAndAnomaly(b) {
  const csv = csvIndex.value.get(String(b.joinKey));
  const rate = csv?.rate;

  const isAnom =
    typeof rate === "number" && Number.isFinite(rate)
      ? Math.abs(rate) >= Number(rateThreshold.value)
      : false;

  return {
    ...b,
    csv: csv || null,
    isAnomaly: !!csv && isAnom,
  };
}

/* =========================
 * GovMap query (by WKT / by click)
 * ========================= */
async function loadBuildingsByWkt(wkt) {
  if (!govReady.value) return;
  if (!wkt) return;

  loadingQuery.value = true;
  errorMsg.value = "";
  lastQueryWkt.value = wkt;
  selected.value = null;

  try {
    const zoom = await window.govmap.getZoomLevel?.();
    if (typeof zoom === "number" && zoom < 7) {
      throw new Error("הזום נמוך מדי לשאילתת בניינים. תתקרב ואז תנסה שוב.");
    }

    // intersectFeatures מתועד רשמית. :contentReference[oaicite:3]{index=3}
    const params = {
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);
    const items = normalizeGovItems(resp);

    const parsed = [];
    for (const it of items) {
      const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? null;
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

      parsed.push(
        applyJoinAndAnomaly({
          key: `${joinKey}__${objectId ?? Math.random().toString(16).slice(2)}`,
          objectId: objectId ?? "",
          joinKey,
          wkt: geomWkt,
          csv: null,
          isAnomaly: false,
        })
      );
    }

    buildings.value = parsed;
    await redrawOverlays();
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    loadingQuery.value = false;
  }
}

async function inspectBuildingAtPoint(x, y, keepExistingList = false) {
  if (!govReady.value) return;
  loadingQuery.value = true;
  errorMsg.value = "";

  try {
    const wkt = `POINT(${x} ${y})`;

    const params = {
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);
    const items = normalizeGovItems(resp);

    if (!items.length) return;

    const it = items[0];
    const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? "";
    const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];

    const joinKey = String(extractFieldValue(values, BUILDING_ID_FIELD) ?? "").trim();
    if (!joinKey) return;

    const shape =
      it?.Shape ??
      it?.shape ??
      it?.WKT ??
      it?.wkt ??
      it?.Geometry ??
      it?.geometry ??
      extractFieldValue(values, "SHAPE");

    const geomWkt = typeof shape === "string" ? shape : "";

    const b = applyJoinAndAnomaly({
      key: `${joinKey}__${objectId || "pt"}`,
      objectId,
      joinKey,
      wkt: geomWkt,
      csv: null,
      isAnomaly: false,
    });

    selected.value = b;
    panelOpen.value = true;

    // לא מוחקים את הרשימה אם זה click רגיל (כדי שעדיין יהיה “CrimesMap feel”)
    if (!keepExistingList) buildings.value = [b];

    await redrawOverlays();
    await drawSelectedOverlay(b);
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    loadingQuery.value = false;
  }
}

function normalizeGovItems(resp) {
  return Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
}

/* =========================
 * Drawing overlays
 * ========================= */
async function clearOverlays() {
  if (!govReady.value) return;
  try {
    window.govmap.clearGeometriesByName(["anom", "norm", "sel"]);
  } catch (_) {}
}

async function redrawOverlays() {
  if (!govReady.value) return;
  await clearOverlays();

  const anom = [];
  const norm = [];

  for (const b of buildings.value) {
    if (!b.wkt || !String(b.wkt).toUpperCase().includes("POLYGON")) continue;
    if (b.isAnomaly) anom.push(b);
    else if (showNormals.value) norm.push(b);
  }

  const anomToDraw = anom.slice(0, MAX_DRAW_ANOMALIES);
  const normToDraw = norm.slice(0, MAX_DRAW_NORMALS);

  if (showNormals.value && normToDraw.length) {
    await window.govmap.displayGeometries({
      wkts: normToDraw.map((b) => b.wkt),
      names: normToDraw.map(() => "norm"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [0, 90, 255, 0.75],
        outlineWidth: 1,
        fillColor: [0, 90, 255, 0.12],
      },
      clearExisting: false,
      clearExistings: false,
      showBubble: false,
      data: { tooltips: normToDraw.map((b) => `ID ${b.joinKey}`) },
    });
  }

  if (anomToDraw.length) {
    await window.govmap.displayGeometries({
      wkts: anomToDraw.map((b) => b.wkt),
      names: anomToDraw.map(() => "anom"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [255, 0, 0, 1],
        outlineWidth: 2,
        fillColor: [255, 0, 0, 0.32],
      },
      clearExisting: false,
      clearExistings: false,
      showBubble: false,
      data: {
        tooltips: anomToDraw.map((b) => `חריג • ${b.joinKey} • ${formatRate(b.csv?.rate)}`),
      },
    });
  }

  // selected overlay on top
  if (selected.value?.wkt) await drawSelectedOverlay(selected.value);
}

async function drawSelectedOverlay(b) {
  if (!govReady.value || !b?.wkt) return;
  try {
    window.govmap.clearGeometriesByName(["sel"]);
  } catch (_) {}

  await window.govmap.displayGeometries({
    wkts: [b.wkt],
    names: ["sel"],
    geometryType: window.govmap.geometryType.POLYGON,
    defaultSymbol: {
      outlineColor: [255, 215, 0, 1],
      outlineWidth: 3,
      fillColor: [255, 215, 0, 0.15],
    },
    clearExisting: false,
    clearExistings: false,
    showBubble: false,
    data: { tooltips: [`נבחר: ${b.joinKey}`] },
  });
}

/* =========================
 * UI actions
 * ========================= */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  errorMsg.value = "";
  isDrawing.value = true;

  try {
    const res = await window.govmap.draw(window.govmap.drawType.Rectangle);
    const wkt = res?.wkt;
    if (!wkt) throw new Error("לא התקבל WKT מהשרטוט");

    try {
      window.govmap.zoomToDrawing?.();
    } catch (_) {}

    await loadBuildingsByWkt(wkt);
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    isDrawing.value = false;
    try {
      window.govmap.setDefaultTool?.();
    } catch (_) {}
  }
}

async function refreshFromLastQuery() {
  if (!lastQueryWkt.value) return;
  await loadBuildingsByWkt(lastQueryWkt.value);
}

async function searchById() {
  const id = String(searchId.value || "").trim();
  if (!id) return;

  // קודם: אם כבר נטענו בניינים באזור, נחפש בתוך הרשימה
  const inList = buildings.value.find((b) => String(b.joinKey) === id);
  if (inList) {
    await selectBuilding(inList);
    return;
  }

  // אם לא נמצא — נבצע חיפוש בשכבה לפי שדה+ערך (אופציונלי),
  // אבל כדי לא להסתבך בין env של השכבה, נלך על קליק-לוגיקה:
  // נציג הודעה אם אין.
  errorMsg.value = "ID לא נמצא ברשימה שנטענה. טען אזור (מלבן) ואז חפש/בחר.";
}

async function selectBuilding(b) {
  selected.value = b;
  panelOpen.value = true;

  // zoom to centroid
  const c = centroidFromPolygonWkt(b.wkt);
  if (c) {
    window.govmap.zoomToXY({ x: c.x, y: c.y, level: 9 });
    window.govmap.setMapMarker?.({ x: c.x, y: c.y });
  }

  await redrawOverlays();
}

async function locateAddress() {
  if (!govReady.value || !addressQuery.value) return;
  errorMsg.value = "";
  try {
    const resp = await window.govmap.geocode({
      keyword: addressQuery.value,
      type: window.govmap.geocodeType.AccuracyOnly,
    });

    const x = resp?.X ?? resp?.x ?? resp?.data?.X ?? resp?.data?.x;
    const y = resp?.Y ?? resp?.y ?? resp?.data?.Y ?? resp?.data?.y;

    if (typeof x !== "number" || typeof y !== "number") {
      throw new Error("לא נמצאה תוצאה מדויקת. נסה לנסח כתובת אחרת/להוסיף מספר בית.");
    }

    window.govmap.zoomToXY({ x, y, level: 9 });
    window.govmap.setMapMarker?.({ x, y });
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  }
}

/* =========================
 * Helpers
 * ========================= */
function toNumberSafe(v) {
  if (v === null || v === undefined) return null;
  const n = Number(String(v).replace(/\s+/g, ""));
  return Number.isFinite(n) ? n : null;
}

function formatRate(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2)}`;
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
    const p = coords[i], q = coords[i + 1];
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
 * Lifecycle
 * ========================= */
onMounted(async () => {
  try {
    await initGovMap();
    await reloadCsv();
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  }
});

onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) {
      window.govmap.unbindEvent(window.govmap.events.CLICK);         // מתועד :contentReference[oaicite:4]{index=4}
      window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE); // מתועד :contentReference[oaicite:5]{index=5}
    }
  } catch (_) {}
});

/* =========================
 * Watchers
 * ========================= */
watch([rateThreshold, showNormals], async () => {
  buildings.value = buildings.value.map((b) => applyJoinAndAnomaly(b));
  await redrawOverlays();
});
</script>

<style scoped>
/* CrimesMap-ish layout */
.app {
  height: 100vh;
  width: 100%;
  display: grid;
  grid-template-columns: 420px 1fr;
  background: #f3f5fb;
  overflow: hidden;
}

.panel {
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #e7e9f2;
  overflow: auto;
  padding: 14px;
}

.panel.closed {
  width: 60px;
  padding: 10px 8px;
}

.panelHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 4px 12px;
  border-bottom: 1px solid #eef0f7;
  margin-bottom: 12px;
}

.brand .title {
  font-weight: 900;
  font-size: 18px;
  letter-spacing: 0.2px;
}
.brand .subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #66708a;
}

.iconBtn {
  border: 1px solid #e2e5f0;
  background: #fff;
  border-radius: 12px;
  width: 40px;
  height: 40px;
  cursor: pointer;
}

.card {
  border: 1px solid #eef0f7;
  border-radius: 16px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fbfcff;
  box-shadow: 0 1px 0 rgba(0,0,0,0.02);
}

.cardTitle {
  font-weight: 900;
  font-size: 13px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chip {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #e2e5f0;
  background: #fff;
  color: #334;
}

.searchRow {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin-bottom: 10px;
}

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e5f0;
  border-radius: 12px;
  outline: none;
  background: #fff;
}

.btn {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #2a62ff;
  background: #2a62ff;
  color: #fff;
  cursor: pointer;
  font-weight: 800;
}

.btn.ghost {
  background: #fff;
  color: #2a62ff;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  font-size: 12px;
  color: #6a7187;
  line-height: 1.5;
}

.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.field label {
  display: block;
  font-size: 12px;
  color: #434a5e;
  font-weight: 800;
  margin-bottom: 6px;
}

.micro {
  margin-top: 6px;
  font-size: 11px;
  color: #7a8299;
}

.microBlock {
  font-size: 12px;
  color: #4a5164;
  line-height: 1.6;
}

.pillRow {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pill {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #e2e5f0;
  background: #fff;
  color: #5b6073;
}
.pill.ok {
  border-color: rgba(25, 135, 84, 0.35);
  color: #0f5132;
  background: rgba(25, 135, 84, 0.08);
}

.toggles {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #2b2f3a;
}

.btnRow {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.stats {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat {
  border: 1px solid #eef0f7;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
}
.stat .k {
  font-size: 12px;
  color: #6a7187;
}
.stat .v {
  font-size: 16px;
  font-weight: 900;
  margin-top: 2px;
}

.errorBox {
  margin-top: 12px;
  padding: 10px;
  border-radius: 14px;
  background: #fff1f1;
  border: 1px solid #ffd0d0;
  color: #b3261e;
  white-space: pre-wrap;
  font-size: 13px;
}

.listFilter {
  margin-bottom: 10px;
}

.list {
  display: grid;
  gap: 8px;
}

.rowItem {
  text-align: right;
  border: 1px solid #eef0f7;
  background: #fff;
  border-radius: 14px;
  padding: 10px;
  cursor: pointer;
  transition: 0.15s;
}
.rowItem:hover {
  border-color: rgba(42, 98, 255, 0.35);
}
.rowItem.active {
  border-color: #2a62ff;
  box-shadow: 0 0 0 3px rgba(42, 98, 255, 0.12);
}

.rowMain {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.id {
  font-weight: 900;
  font-size: 13px;
  color: #1f2330;
}
.rowSub {
  margin-top: 6px;
  font-size: 12px;
  color: #6a7187;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.dot {
  opacity: 0.6;
}

.badge {
  font-size: 12px;
  font-weight: 900;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #e2e5f0;
  background: #fff;
  color: #334;
}
.badge.ok {
  border-color: rgba(25, 135, 84, 0.35);
  background: rgba(25, 135, 84, 0.08);
  color: #0f5132;
}
.badge.danger {
  border-color: rgba(220, 53, 69, 0.35);
  background: rgba(220, 53, 69, 0.08);
  color: #842029;
}

.detailTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.bigId {
  font-size: 18px;
  font-weight: 950;
}

.kv {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px 10px;
}
.kv .k {
  font-size: 12px;
  color: #6a7187;
  font-weight: 800;
}
.kv .v {
  font-size: 13px;
  font-weight: 900;
  color: #1f2330;
}

.subTitle {
  margin-top: 12px;
  font-weight: 900;
  font-size: 12px;
  color: #3c4254;
}

.csvTable {
  margin-top: 8px;
  border: 1px solid #eef0f7;
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
}
.csvRow {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 10px;
  padding: 8px 10px;
  border-bottom: 1px solid #f1f3fa;
}
.csvRow:last-child {
  border-bottom: none;
}
.csvK {
  font-size: 12px;
  color: #6a7187;
  font-weight: 800;
}
.csvV {
  font-size: 12px;
  color: #1f2330;
  font-weight: 800;
  word-break: break-word;
}

.empty {
  padding: 12px;
  color: #6a7187;
  font-size: 13px;
}
.empty.small {
  padding: 8px 0 0;
  font-size: 12px;
}

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

@media (max-width: 980px) {
  .app {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
  .panel {
    position: sticky;
    top: 0;
    z-index: 5;
  }
}
</style>

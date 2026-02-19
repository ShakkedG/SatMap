<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div class="titles">
          <div class="appTitle">SatMap – Buildings + CSV Join</div>
          <div class="appSub">
            GovMap שכבת בניינים + JOIN ל-CSV (tablecsv.csv) + הדגשת תנועה חריגה
          </div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">☰</button>
      </div>

      <!-- ============ CONTROLS ============ -->
      <section class="box">
        <div class="boxTitle">הגדרות</div>

        <div class="row">
          <label class="lbl">סף “חריגה” |rate| (mm/yr)</label>
          <input class="inp" type="number" v-model.number="rateThreshold" step="0.5" />
        </div>

        <div class="row">
          <label class="lbl">הצג גם לא-חריגים (כחול)</label>
          <label class="switch">
            <input type="checkbox" v-model="showNormals" />
            <span></span>
          </label>
        </div>

        <div class="row">
          <label class="lbl">הצג את שכבת GovMap עצמה</label>
          <label class="switch">
            <input type="checkbox" v-model="showGovLayer" @change="applyGovLayerVisibility" />
            <span></span>
          </label>
        </div>

        <div class="row">
          <label class="lbl">עדכון אוטומטי בזמן זום/הזזה</label>
          <label class="switch">
            <input type="checkbox" v-model="autoRefresh" />
            <span></span>
          </label>
        </div>

        <div class="row">
          <label class="lbl">שדה מזהה בשכבה (JOIN key)</label>
          <input class="inp" v-model.trim="buildingIdField" placeholder="לדוגמה: ID / OBJECTID / BLDG_ID" />
        </div>

        <div class="row2">
          <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady">בחר אזור (מלבן) וטעינה</button>
          <button class="btn ghost" @click="loadFromCurrentExtent" :disabled="!govReady">טען לפי המפה</button>
        </div>

        <div class="row2">
          <button class="btn ghost" @click="refreshFromLastQuery" :disabled="!govReady || !lastQueryWkt">טען שוב</button>
          <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">נקה הדגשות</button>
        </div>

        <div class="sep"></div>

        <div class="row">
          <label class="lbl">חיפוש כתובת (GovMap geocode)</label>
          <input class="inp" v-model.trim="addressQuery" placeholder="לדוגמה: הרוקמים 26 חולון" />
        </div>

        <div class="row2">
          <button class="btn" @click="locateAddress" :disabled="!govReady || !addressQuery">אתר</button>
          <button class="btn ghost" @click="pickPointAndInspect" :disabled="!govReady">בחר נקודה → בדוק</button>
        </div>

        <div class="sep"></div>

        <div class="stats">
          <div class="stat">
            <div class="k">סטטוס</div>
            <div class="v">
              <span v-if="!govReady">טוען GovMap…</span>
              <span v-else>מוכן</span>
              <span v-if="loadingQuery"> · שואב ישויות…</span>
              <span v-if="loadingCsv"> · טוען CSV…</span>
              <span v-if="loadingJoin"> · בונה JOIN…</span>
            </div>
          </div>
          <div class="stat"><div class="k">ישויות שנשלפו</div><div class="v">{{ buildings.length }}</div></div>
          <div class="stat"><div class="k">JOIN hits</div><div class="v">{{ joinedCount }}</div></div>
          <div class="stat"><div class="k">חריגים</div><div class="v">{{ anomalies.length }}</div></div>
        </div>

        <div v-if="errorMsg" class="err">{{ errorMsg }}</div>
        <div v-if="warnMsg" class="warn">{{ warnMsg }}</div>
      </section>

      <!-- ============ CSV ============ -->
      <section class="box">
        <div class="boxTitle">נתוני תנועה (CSV)</div>

        <div class="muted small">
          הקובץ צריך להיות כאן: <b>client/public/data/tablecsv.csv</b><br />
          ה-URL בפועל שהאתר טוען ממנו:
          <div class="mono">{{ csvUrl }}</div>
        </div>

        <div class="row2" style="margin-top: 10px">
          <button class="btn" @click="loadCsv" :disabled="loadingCsv">טען / רענן CSV</button>
          <button class="btn ghost" @click="rebuildJoinIndex" :disabled="!csvHeaders.length || loadingJoin">
            בנה JOIN מחדש
          </button>
        </div>

        <div v-if="csvHeaders.length" class="grid3" style="margin-top: 10px">
          <div>
            <label class="lbl">עמודת ID ב-CSV</label>
            <select class="inp" v-model="csvIdCol">
              <option v-for="h in csvHeaders" :key="h" :value="h">{{ h }}</option>
            </select>
          </div>

          <div>
            <label class="lbl">עמודת rate (mm/yr)</label>
            <select class="inp" v-model="csvRateCol">
              <option v-for="h in csvHeaders" :key="h" :value="h">{{ h }}</option>
            </select>
          </div>

          <div>
            <label class="lbl">עמודת תאריך (אופציונלי)</label>
            <select class="inp" v-model="csvDateCol">
              <option value="">—</option>
              <option v-for="h in csvHeaders" :key="h" :value="h">{{ h }}</option>
            </select>
          </div>
        </div>

        <div v-if="csvPreview.length" class="previewWrap">
          <div class="muted small">תצוגה מקדימה ({{ csvPreview.length }} שורות ראשונות)</div>
          <div class="tableWrap">
            <table class="miniTable">
              <thead>
                <tr>
                  <th v-for="h in previewCols" :key="h">{{ h }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in csvPreview" :key="i">
                  <td v-for="h in previewCols" :key="h">{{ r[h] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="sep"></div>

        <div class="muted small">
          טיפ: אם JOIN hits נשאר 0 — כמעט תמיד זה אומר שה-<b>buildingIdField</b> לא נכון (ב־GovMap),
          או שהעמודת ID ב-CSV לא תואמת בדיוק (רווחים/אפסים מובילים/שמות שונים).
        </div>
      </section>

      <!-- ============ ANOM LIST ============ -->
      <section class="box">
        <div class="boxTitle">חריגים (לפי |rate|)</div>

        <div class="row">
          <label class="lbl">חיפוש לפי ID</label>
          <input class="inp" v-model.trim="idSearch" placeholder="לדוגמה: 12345" />
        </div>

        <div v-if="filteredAnomalies.length === 0" class="muted">
          אין חריגים להצגה כרגע (או הפילטר ריק).
        </div>

        <div v-else class="list">
          <button
            v-for="b in filteredAnomalies"
            :key="b.key"
            class="listItem"
            :class="{ on: selected?.key === b.key }"
            @click="selectBuilding(b)"
          >
            <div class="liTop">
              <div class="liId">ID: {{ b.joinKey }}</div>
              <div class="liRate">{{ formatRate(b.movement?.rate_mm_yr) }}</div>
            </div>
            <div class="liSub">
              <span v-if="b.movement?.last_date">עדכון: {{ b.movement.last_date }}</span>
              <span v-else>אין תאריך</span>
              <span class="dot">•</span>
              <span>objectId: {{ b.objectId }}</span>
            </div>
          </button>
        </div>
      </section>

      <!-- ============ SELECTED ============ -->
      <section v-if="selected" class="box">
        <div class="boxTitle">פרטי ישות נבחרת</div>

        <div class="kv">
          <div class="k">Join Key</div>
          <div class="v">{{ selected.joinKey }}</div>

          <div class="k">Rate (mm/yr)</div>
          <div class="v">{{ formatRate(selected.movement?.rate_mm_yr) }}</div>

          <div class="k">חריג?</div>
          <div class="v">{{ selected.isAnomaly ? "כן" : "לא" }}</div>

          <div class="k">מקור</div>
          <div class="v">{{ selected.movement?.source || "—" }}</div>
        </div>
      </section>
    </aside>

    <main class="mapWrap">
      <div id="map" class="map"></div>

      <!-- Legend -->
      <div class="legend">
        <div class="legItem"><span class="swatch red"></span> חריג</div>
        <div class="legItem"><span class="swatch blue"></span> לא-חריג</div>
        <div class="legItem"><span class="swatch gold"></span> נבחר</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

/* =========================
 *  CONFIG
 * ========================= */
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";
const BUILDINGS_LAYER = "225287";

/* =========================
 *  URL builder (GitHub Pages safe)
 *  builds absolute base first, then uses new URL safely
 * ========================= */
function getAppBaseHref() {
  // If you have <base href="/SatMap/"> this will be perfect
  const baseTagHref = document.querySelector("base")?.href;
  if (baseTagHref) return baseTagHref;

  // Vite BASE_URL is usually "/SatMap/" on GH Pages
  const base = import.meta?.env?.BASE_URL || "/";
  return new URL(base, window.location.origin).href;
}

const appBaseHref = getAppBaseHref();
const csvUrl = new URL("data/tablecsv.csv", appBaseHref).href;

/* =========================
 *  STATE
 * ========================= */
const panelOpen = ref(true);
const govReady = ref(false);

const loadingQuery = ref(false);
const loadingCsv = ref(false);
const loadingJoin = ref(false);

const errorMsg = ref("");
const warnMsg = ref("");

const rateThreshold = ref(2.0);
const showNormals = ref(false);
const autoRefresh = ref(false);
const showGovLayer = ref(true);

const buildingIdField = ref("ID");
const addressQuery = ref("");
const lastQueryWkt = ref("");

const buildings = ref([]);
const selected = ref(null);
const idSearch = ref("");

/* CSV meta + data */
const csvHeaders = ref([]);
const csvPreview = ref([]);
const csvRowsRaw = ref([]); // array of objects (full) – used to build index

const csvIdCol = ref("");
const csvRateCol = ref("");
const csvDateCol = ref("");

/* JOIN index: id -> movement */
const movementIndex = ref(new Map());

/* =========================
 *  DERIVED
 * ========================= */
const joinedCount = computed(() => buildings.value.filter((b) => !!b.movement).length);

const anomalies = computed(() =>
  [...buildings.value]
    .filter((b) => b.isAnomaly)
    .sort((a, b) => Math.abs(b.movement?.rate_mm_yr ?? 0) - Math.abs(a.movement?.rate_mm_yr ?? 0))
);

const filteredAnomalies = computed(() => {
  const q = idSearch.value.trim();
  if (!q) return anomalies.value;
  return anomalies.value.filter((b) => String(b.joinKey).includes(q));
});

const previewCols = computed(() => {
  // show a small set of relevant columns
  const cols = [];
  if (csvIdCol.value) cols.push(csvIdCol.value);
  if (csvRateCol.value && csvRateCol.value !== csvIdCol.value) cols.push(csvRateCol.value);
  if (csvDateCol.value && !cols.includes(csvDateCol.value)) cols.push(csvDateCol.value);

  // fallback: first 5 headers
  if (!cols.length) return csvHeaders.value.slice(0, 5);
  return cols.slice(0, 5);
});

/* =========================
 *  GovMap loader
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
  warnMsg.value = "";

  await loadGovMapScript();
  if (!GOVMAP_TOKEN) throw new Error("חסר GOVMAP_TOKEN.");

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN,
    background: 3,

    // חשוב: זה מדליק את שכבת GovMap עצמה
    layers: showGovLayer.value ? [BUILDINGS_LAYER] : [],

    showXY: false,
    identifyOnClick: false,
    layersMode: 1,
    zoomButtons: true,

    onLoad: () => {
      govReady.value = true;
      applyGovLayerVisibility();

      // auto refresh on extent change
      window.govmap.onEvent(window.govmap.events.EXTENT_CHANGE).progress(async (e) => {
        if (!autoRefresh.value) return;
        const extent = e?.extent;
        const wkt = extentToWkt(extent);
        if (wkt) await loadBuildingsByWkt(wkt);
      });
    },

    onError: (e) => {
      errorMsg.value = "שגיאת GovMap: " + (e?.message || JSON.stringify(e));
    },
  });
}

function applyGovLayerVisibility() {
  if (!govReady.value) return;
  try {
    if (showGovLayer.value) window.govmap.setVisibleLayers([BUILDINGS_LAYER]);
    else window.govmap.setVisibleLayers([]);
  } catch (_) {
    // לא קריטי — המפה עדיין עובדת
  }
}

onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
  } catch (_) {}
});

/* =========================
 *  CSV load + parse
 * ========================= */
async function loadCsv() {
  loadingCsv.value = true;
  errorMsg.value = "";
  warnMsg.value = "";

  try {
    const res = await fetch(csvUrl, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(
        `CSV לא נמצא (${res.status}). בדוק שהקובץ באמת ב: client/public/data/tablecsv.csv`
      );
    }

    const text = await res.text();

    // parse (full) + preview
    const parsed = parseCsvToObjects(text, { maxPreviewRows: 30 });

    csvHeaders.value = parsed.headers;
    csvPreview.value = parsed.preview;
    csvRowsRaw.value = parsed.rows;

    // auto detect columns (best effort)
    const h = parsed.headers.map((x) => x.toLowerCase());

    csvIdCol.value =
      pickHeader(parsed.headers, ["id", "ID", "bldg_id", "building_id", "objectid"]) || parsed.headers[0] || "";
    csvRateCol.value =
      pickHeader(parsed.headers, ["rate_mm_yr", "rate", "v", "velocity", "vel_mm_yr", "mm_yr"]) ||
      parsed.headers[1] ||
      "";
    csvDateCol.value = pickHeader(parsed.headers, ["last_date", "date", "obs_date", "lastdate"]) || "";

    await rebuildJoinIndex();
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingCsv.value = false;
  }
}

async function rebuildJoinIndex() {
  if (!csvHeaders.value.length || !csvRowsRaw.value.length) {
    warnMsg.value = "אין CSV טעון עדיין.";
    return;
  }
  if (!csvIdCol.value || !csvRateCol.value) {
    warnMsg.value = "בחר עמודות ID ו-rate.";
    return;
  }

  loadingJoin.value = true;
  warnMsg.value = "";
  errorMsg.value = "";

  try {
    const idx = new Map();

    for (const r of csvRowsRaw.value) {
      const id = String(r?.[csvIdCol.value] ?? "").trim();
      if (!id) continue;

      const rate = toNumberSafe(r?.[csvRateCol.value]);
      if (rate === null) continue;

      const lastDate = csvDateCol.value ? String(r?.[csvDateCol.value] ?? "").trim() : "";

      idx.set(id, {
        rate_mm_yr: rate,
        last_date: lastDate,
        source: "CSV",
        raw: r,
      });
    }

    movementIndex.value = idx;

    // apply join to current buildings
    if (buildings.value.length) {
      buildings.value = buildings.value.map(applyJoinAndAnomaly);
      await redrawOverlays();
    }

    // quick warning if index is tiny
    if (idx.size < 10) {
      warnMsg.value =
        "ה-CSV נטען, אבל נבנה אינדקס קטן מאוד. כנראה שהעמודות שנבחרו לא נכונות או שה-rate לא מספרי.";
    }
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingJoin.value = false;
  }
}

/**
 * CSV parser:
 * - supports quotes
 * - returns full rows + preview
 * - NOTE: for huge CSV it’s still OK (13–20MB) in modern browsers
 */
function parseCsvToObjects(csvText, { delimiter = ",", maxPreviewRows = 30 } = {}) {
  const lines = csvText.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return { headers: [], rows: [], preview: [] };

  const headers = parseCsvLine(lines[0], delimiter).map((h) => String(h ?? "").trim());
  const rows = [];
  const preview = [];

  for (let i = 1; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i], delimiter);
    const obj = {};
    for (let j = 0; j < headers.length; j++) obj[headers[j]] = (cells[j] ?? "").trim();
    rows.push(obj);
    if (preview.length < maxPreviewRows) preview.push(obj);
  }

  return { headers, rows, preview };
}

function parseCsvLine(line, delimiter = ",") {
  const out = [];
  let cur = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];

    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (!inQuotes && ch === delimiter) {
      out.push(cur);
      cur = "";
      continue;
    }

    cur += ch;
  }

  out.push(cur);
  return out;
}

function pickHeader(headers, candidates) {
  const map = new Map(headers.map((h) => [String(h).toLowerCase(), h]));
  for (const c of candidates) {
    const hit = map.get(String(c).toLowerCase());
    if (hit) return hit;
  }
  return "";
}

/* =========================
 *  GovMap querying
 * ========================= */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  errorMsg.value = "";
  warnMsg.value = "";

  try {
    const res = await window.govmap.draw(window.govmap.drawType.Rectangle);
    const wkt = res?.wkt;
    if (!wkt) throw new Error("לא התקבל WKT מהשרטוט");
    try {
      window.govmap.zoomToDrawing?.();
    } catch (_) {}
    await loadBuildingsByWkt(wkt);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    try {
      window.govmap.setDefaultTool?.();
    } catch (_) {}
  }
}

async function loadFromCurrentExtent() {
  if (!govReady.value) return;
  try {
    const ext = await window.govmap.getExtent?.();
    const wkt = extentToWkt(ext);
    if (!wkt) throw new Error("לא הצלחתי לקרוא extent מהמפה.");
    await loadBuildingsByWkt(wkt);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
}

async function refreshFromLastQuery() {
  if (!lastQueryWkt.value) return;
  await loadBuildingsByWkt(lastQueryWkt.value);
}

async function loadBuildingsByWkt(wkt) {
  if (!govReady.value || !wkt) return;

  loadingQuery.value = true;
  errorMsg.value = "";
  warnMsg.value = "";
  lastQueryWkt.value = wkt;
  selected.value = null;

  try {
    // intersectFeatures
    const params = {
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [buildingIdField.value],
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    if (!items.length) {
      warnMsg.value = "לא התקבלו ישויות באזור. נסה אזור אחר/זום קרוב יותר.";
    }

    const parsed = [];
    for (const it of items) {
      const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? "";
      const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];
      const joinKey = String(extractFieldValue(values, buildingIdField.value) ?? "").trim();

      const shape =
        it?.Shape ??
        it?.shape ??
        it?.WKT ??
        it?.wkt ??
        it?.Geometry ??
        it?.geometry ??
        extractFieldValue(values, "SHAPE");

      const geomWkt = typeof shape === "string" ? shape : "";

      if (!joinKey) continue;

      parsed.push(
        applyJoinAndAnomaly({
          key: `${joinKey}__${objectId || Math.random().toString(16).slice(2)}`,
          objectId,
          joinKey,
          wkt: geomWkt,
          movement: null,
          isAnomaly: false,
        })
      );
    }

    buildings.value = parsed;
    await redrawOverlays();

    // If join is 0, give a hint
    if (parsed.length && joinedCount.value === 0 && movementIndex.value.size) {
      warnMsg.value =
        "נשלפו ישויות אבל JOIN hits = 0. בדוק ש-buildingIdField נכון ושעמודת ה-ID ב-CSV תואמת בדיוק.";
    }
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingQuery.value = false;
  }
}

function applyJoinAndAnomaly(b) {
  const m = movementIndex.value.get(String(b.joinKey));
  const rate = m?.rate_mm_yr;

  const isAnom =
    typeof rate === "number" && Number.isFinite(rate) ? Math.abs(rate) >= Number(rateThreshold.value) : false;

  return {
    ...b,
    movement: m || null,
    isAnomaly: !!m && isAnom,
  };
}

/* =========================
 *  Drawing overlays
 * ========================= */
const MAX_DRAW_ANOMALIES = 800;
const MAX_DRAW_NORMALS = 800;

async function clearOverlays() {
  if (!govReady.value) return;
  try {
    window.govmap.clearGeometriesByName(["anom_poly", "anom_pt", "norm_poly", "norm_pt", "sel_poly", "sel_pt"]);
  } catch (_) {}
}

function wktKind(wkt) {
  const s = String(wkt || "").trim().toUpperCase();
  if (s.startsWith("POLYGON") || s.startsWith("MULTIPOLYGON")) return "poly";
  if (s.startsWith("POINT") || s.startsWith("MULTIPOINT")) return "pt";
  return "other";
}

async function redrawOverlays() {
  if (!govReady.value) return;
  await clearOverlays();

  const anomPoly = [];
  const anomPt = [];
  const normPoly = [];
  const normPt = [];

  for (const b of buildings.value) {
    if (!b.wkt) continue;
    const k = wktKind(b.wkt);

    if (b.isAnomaly) {
      if (k === "poly") anomPoly.push(b);
      else if (k === "pt") anomPt.push(b);
    } else if (showNormals.value) {
      if (k === "poly") normPoly.push(b);
      else if (k === "pt") normPt.push(b);
    }
  }

  if (normPoly.length) {
    await window.govmap.displayGeometries({
      wkts: normPoly.slice(0, MAX_DRAW_NORMALS).map((b) => b.wkt),
      names: normPoly.slice(0, MAX_DRAW_NORMALS).map(() => "norm_poly"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [0, 80, 255, 0.8], outlineWidth: 1, fillColor: [0, 80, 255, 0.12] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (normPt.length) {
    await window.govmap.displayGeometries({
      wkts: normPt.slice(0, MAX_DRAW_NORMALS).map((b) => b.wkt),
      names: normPt.slice(0, MAX_DRAW_NORMALS).map(() => "norm_pt"),
      geometryType: window.govmap.geometryType.POINT,
      defaultSymbol: { size: 6, color: [0, 80, 255, 0.85] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (anomPoly.length) {
    await window.govmap.displayGeometries({
      wkts: anomPoly.slice(0, MAX_DRAW_ANOMALIES).map((b) => b.wkt),
      names: anomPoly.slice(0, MAX_DRAW_ANOMALIES).map(() => "anom_poly"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [255, 0, 0, 1], outlineWidth: 2, fillColor: [255, 0, 0, 0.33] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (anomPt.length) {
    await window.govmap.displayGeometries({
      wkts: anomPt.slice(0, MAX_DRAW_ANOMALIES).map((b) => b.wkt),
      names: anomPt.slice(0, MAX_DRAW_ANOMALIES).map(() => "anom_pt"),
      geometryType: window.govmap.geometryType.POINT,
      defaultSymbol: { size: 10, color: [255, 0, 0, 0.95] },
      clearExisting: false,
      showBubble: false,
    });
  }
}

async function drawSelectedOverlay(b) {
  if (!govReady.value || !b?.wkt) return;

  try {
    window.govmap.clearGeometriesByName(["sel_poly", "sel_pt"]);
  } catch (_) {}

  const k = wktKind(b.wkt);
  if (k === "poly") {
    await window.govmap.displayGeometries({
      wkts: [b.wkt],
      names: ["sel_poly"],
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [255, 215, 0, 1], outlineWidth: 3, fillColor: [255, 215, 0, 0.12] },
      clearExisting: false,
      showBubble: false,
    });
  } else if (k === "pt") {
    await window.govmap.displayGeometries({
      wkts: [b.wkt],
      names: ["sel_pt"],
      geometryType: window.govmap.geometryType.POINT,
      defaultSymbol: { size: 12, color: [255, 215, 0, 0.95] },
      clearExisting: false,
      showBubble: false,
    });
  }
}

/* =========================
 *  UI actions (geocode / point)
 * ========================= */
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
      throw new Error("לא נמצאה תוצאה מדויקת. נסה לנסח כתובת אחרת.");
    }

    window.govmap.zoomToXY({ x, y, level: 9 });
    window.govmap.setMapMarker?.({ x, y });
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
}

async function pickPointAndInspect() {
  if (!govReady.value) return;
  errorMsg.value = "";

  try {
    const xy = await window.govmap.getXY();
    const p = xy?.mapPoint;
    if (!p) throw new Error("לא התקבלו קואורדינטות");
    await inspectAtPoint(p.x, p.y);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    try {
      window.govmap.setDefaultTool?.();
    } catch (_) {}
  }
}

async function inspectAtPoint(x, y) {
  loadingQuery.value = true;
  errorMsg.value = "";
  warnMsg.value = "";
  selected.value = null;

  try {
    const wkt = `POINT(${x} ${y})`;
    const resp = await window.govmap.intersectFeatures({
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [buildingIdField.value],
      getShapes: true,
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    if (!items.length) throw new Error("לא נמצאה ישות בנקודה הזו.");

    const it = items[0];
    const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? "";
    const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];
    const joinKey = String(extractFieldValue(values, buildingIdField.value) ?? "").trim();

    const shape =
      it?.Shape ??
      it?.shape ??
      it?.WKT ??
      it?.wkt ??
      it?.Geometry ??
      it?.geometry ??
      extractFieldValue(values, "SHAPE");

    const geomWkt = typeof shape === "string" ? shape : wkt;

    const b = applyJoinAndAnomaly({
      key: `${joinKey || "NO_ID"}__${objectId || "pt"}`,
      objectId,
      joinKey: joinKey || "",
      wkt: geomWkt,
      movement: null,
      isAnomaly: false,
    });

    buildings.value = [b];
    selected.value = b;

    await redrawOverlays();
    await drawSelectedOverlay(b);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingQuery.value = false;
  }
}

async function selectBuilding(b) {
  selected.value = b;
  await drawSelectedOverlay(b);

  // zoom to centroid if polygon
  const c = centroidFromPolygonWkt(b.wkt);
  if (c) {
    try {
      window.govmap.zoomToXY({ x: c.x, y: c.y, level: 9 });
      window.govmap.setMapMarker?.({ x: c.x, y: c.y });
    } catch (_) {}
  }
}

/* =========================
 *  Helpers
 * ========================= */
function toNumberSafe(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim().replace(",", ".");
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
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
  if (!ext) return "";
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

  let a = 0;
  let cx = 0;
  let cy = 0;

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
 *  LIFECYCLE
 * ========================= */
onMounted(async () => {
  try {
    await initGovMap();
    await loadCsv(); // load CSV immediately
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
});

/* =========================
 *  WATCHERS
 * ========================= */
watch([rateThreshold, showNormals], async () => {
  buildings.value = buildings.value.map(applyJoinAndAnomaly);
  await redrawOverlays();
});

watch([csvIdCol, csvRateCol, csvDateCol], async () => {
  // if user changes mapping, rebuild index and rejoin
  if (!csvHeaders.value.length) return;
  await rebuildJoinIndex();
});
</script>

<style scoped>
.app {
  height: 100vh;
  width: 100%;
  display: grid;
  grid-template-columns: 390px 1fr;
  background: #f6f7fb;
  overflow: hidden;
}

.panel {
  height: 100%;
  overflow: auto;
  background: #fff;
  border-left: 1px solid #e7e9f2;
  padding: 14px;
}

.panelTop {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.titles .appTitle {
  font-weight: 900;
  font-size: 16px;
}

.titles .appSub {
  margin-top: 4px;
  font-size: 12px;
  color: #5b6073;
  line-height: 1.35;
}

.iconBtn {
  border: 1px solid #e2e5f0;
  background: #fff;
  border-radius: 10px;
  width: 36px;
  height: 36px;
  cursor: pointer;
}

.box {
  border: 1px solid #eef0f7;
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fbfbfe;
}

.boxTitle {
  font-weight: 900;
  margin-bottom: 10px;
}

.row {
  display: grid;
  grid-template-columns: 1fr 130px;
  gap: 10px;
  align-items: center;
  margin: 8px 0;
}

.grid3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.lbl {
  font-size: 13px;
  color: #2b2f3a;
}

.inp {
  width: 100%;
  padding: 9px 10px;
  border: 1px solid #e2e5f0;
  border-radius: 10px;
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
  background: #eef0f7;
  margin: 12px 0;
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat {
  border: 1px solid #eef0f7;
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.stat .k {
  font-size: 12px;
  color: #6a7187;
}

.stat .v {
  font-size: 14px;
  font-weight: 900;
  margin-top: 2px;
}

.err {
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  background: #fff1f1;
  border: 1px solid #ffd0d0;
  color: #b3261e;
  font-size: 13px;
}

.warn {
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  background: #fff7e6;
  border: 1px solid #ffe2a8;
  color: #7a4b00;
  font-size: 13px;
}

.muted {
  color: #6a7187;
  font-size: 13px;
}
.muted.small {
  font-size: 12px;
  line-height: 1.5;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  background: #f3f5fb;
  border: 1px solid #e9ecf7;
  border-radius: 10px;
  padding: 8px 10px;
  margin-top: 6px;
  direction: ltr;
  text-align: left;
  overflow: auto;
}

.previewWrap {
  margin-top: 10px;
}

.tableWrap {
  margin-top: 6px;
  border: 1px solid #eef0f7;
  border-radius: 12px;
  background: #fff;
  overflow: auto;
  max-height: 220px;
}

.miniTable {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.miniTable th,
.miniTable td {
  border-bottom: 1px solid #eef0f7;
  padding: 8px 10px;
  white-space: nowrap;
}
.miniTable th {
  position: sticky;
  top: 0;
  background: #fbfbfe;
  z-index: 1;
  font-weight: 900;
}

.list {
  display: grid;
  gap: 8px;
}

.listItem {
  text-align: right;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #eef0f7;
  background: #fff;
  cursor: pointer;
}

.listItem.on {
  border-color: #2a62ff;
  box-shadow: 0 0 0 3px rgba(42, 98, 255, 0.12);
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
  color: #6a7187;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.dot {
  opacity: 0.6;
}

.kv {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px 10px;
}

.kv .k {
  font-size: 12px;
  color: #6a7187;
}

.kv .v {
  font-size: 13px;
  font-weight: 900;
  color: #232633;
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

/* legend */
.legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #e7e9f2;
  border-radius: 14px;
  padding: 10px 12px;
  display: grid;
  gap: 8px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}
.legItem {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #2b2f3a;
  font-weight: 800;
}
.swatch {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.15);
}
.swatch.red { background: rgba(255, 0, 0, 0.35); }
.swatch.blue { background: rgba(0, 80, 255, 0.18); }
.swatch.gold { background: rgba(255, 215, 0, 0.18); }

/* toggle switch */
.switch {
  position: relative;
  width: 46px;
  height: 26px;
  display: inline-block;
}
.switch input {
  display: none;
}
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.switch input:checked + span {
  background: #2a62ff;
}
.switch input:checked + span::after {
  transform: translateX(-20px);
}

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
  .grid3 {
    grid-template-columns: 1fr;
  }
}
</style>

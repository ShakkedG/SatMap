<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div class="titles">
          <div class="appTitle">SatMap – Buildings + Join</div>
          <div class="appSub">GovMap שכבה + JOIN ל־CSV/JSON + סימון תנועה חריגה</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">☰</button>
      </div>

      <section class="box">
        <div class="row">
          <label class="lbl">סף “חריגה” |rate| (mm/yr)</label>
          <input class="inp" type="number" v-model.number="rateThreshold" step="0.5" />
        </div>

        <div class="row">
          <label class="lbl">הצג גם לא־חריגים</label>
          <label class="switch">
            <input type="checkbox" v-model="showNormals" />
            <span></span>
          </label>
        </div>

        <div class="row">
          <label class="lbl">עדכון אוטומטי בזמן הזזה/זום</label>
          <label class="switch">
            <input type="checkbox" v-model="autoRefresh" />
            <span></span>
          </label>
        </div>

        <div class="row2">
          <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady">בחר אזור (מלבן) וטעינה</button>
          <button class="btn ghost" @click="refreshFromLastQuery" :disabled="!govReady || !lastQueryWkt">טען שוב</button>
        </div>

        <div class="row2">
          <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">נקה הדגשות</button>
          <button class="btn ghost" @click="reloadBuildingData" :disabled="loadingData">רענן נתוני CSV</button>
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
              <span v-if="loadingQuery"> · שואב שכבה…</span>
              <span v-if="loadingData"> · טוען CSV…</span>
            </div>
          </div>
          <div class="stat"><div class="k">ישויות שהתקבלו</div><div class="v">{{ buildings.length }}</div></div>
          <div class="stat"><div class="k">חריגים</div><div class="v">{{ anomalies.length }}</div></div>
          <div class="stat"><div class="k">JOIN hits</div><div class="v">{{ joinedCount }}</div></div>
        </div>

        <div v-if="errorMsg" class="err">{{ errorMsg }}</div>
      </section>

      <section class="box">
        <div class="boxTitle">רשימת חריגים (לפי |rate|)</div>
        <div v-if="anomalies.length === 0" class="muted">אין חריגים כרגע.</div>

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

      <section v-if="selected" class="box">
        <div class="boxTitle">פרטי ישות נבחרת</div>
        <div class="kv">
          <div class="k">Join Key</div><div class="v">{{ selected.joinKey }}</div>
          <div class="k">Rate (mm/yr)</div><div class="v">{{ formatRate(selected.movement?.rate_mm_yr) }}</div>
          <div class="k">האם חריג</div><div class="v">{{ selected.isAnomaly ? "כן" : "לא" }}</div>
          <div class="k">מקור</div><div class="v">{{ selected.movement?.source || "—" }}</div>
        </div>
      </section>

      <section class="box">
        <div class="boxTitle">מה חובה להתאים אצלך</div>
        <div class="muted small">
          1) <b>BUILDINGS_LAYER</b> = מספר השכבה שלך (אצלך 225287).<br />
          2) <b>BUILDING_ID_FIELD</b> = שם השדה בשכבה שמזהה ישות (ID/OBJECTID/...).<br />
          3) ב־CSV: חייבת להיות עמודה לאותו ID כדי שה־JOIN יעבוד.
        </div>
      </section>
    </aside>

    <main class="mapWrap">
      <div id="map" class="map"></div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

/* ========= CONFIG ========= */
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";
const BUILDINGS_LAYER = "225287";

/**
 * השדה בשכבה שממנו אתה לוקח מזהה ל־JOIN
 * אם אצלך בשכבה זה OBJECTID למשל – תחליף כאן ל-"OBJECTID"
 */
const BUILDING_ID_FIELD = "ID";

/**
 * CSV נמצא אצלך: client/public/data/tablecsv.csv
 * כדי שלא ניפול על /data במקום /SatMap/data – נבנה URL יחסי לכתובת הנוכחית (מוחלט).
 */
const BUILDING_DATA_URL = new URL("./data/tablecsv.csv", window.location.href).toString();

/**
 * התאמת שמות עמודות ב־CSV (ננסה למצוא לפי מועמדים).
 * אם אתה יודע בדיוק שם עמודה – שים אותה ראשונה.
 */
const CSV_ID_COL_CANDIDATES = ["ID", "id", "BLDG_ID", "building_id", "OBJECTID", "objectid"];
const CSV_RATE_COL_CANDIDATES = ["rate_mm_yr", "rate", "v", "velocity", "vel_mm_yr", "mm_yr"];
const CSV_DATE_COL_CANDIDATES = ["last_date", "date", "obs_date", "lastDate", "LastDate"];

const MAX_FEATURES = 3000;
const MAX_DRAW_ANOMALIES = 800;
const MAX_DRAW_NORMALS = 800;

/* ========= STATE ========= */
const panelOpen = ref(true);
const govReady = ref(false);
const loadingQuery = ref(false);
const loadingData = ref(false);
const errorMsg = ref("");

const rateThreshold = ref(2.0);
const showNormals = ref(false);
const autoRefresh = ref(false);

const addressQuery = ref("");
const lastQueryWkt = ref("");

const buildings = ref([]);
const selected = ref(null);
const movementIndex = ref(new Map());

/* ========= DERIVED ========= */
const anomalies = computed(() =>
  [...buildings.value]
    .filter((b) => b.isAnomaly)
    .sort((a, b) => Math.abs(b.movement?.rate_mm_yr ?? 0) - Math.abs(a.movement?.rate_mm_yr ?? 0))
);

const joinedCount = computed(() => buildings.value.filter((b) => !!b.movement).length);

/* ========= GOVMAP loader ========= */
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

  if (!GOVMAP_TOKEN) throw new Error("חסר GOVMAP_TOKEN.");

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN,
    background: 3,

    // 🔥 זה מה שיגרום לשכבה עצמה להופיע במפה
    layers: [BUILDINGS_LAYER], // :contentReference[oaicite:1]{index=1}

    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    layersMode: 1,
    zoomButtons: true,
    onLoad: () => {
      govReady.value = true;

      // לפעמים צריך הדלקה מפורשת כדי לוודא שהיא ON
      try {
        window.govmap.setVisibleLayers([BUILDINGS_LAYER]); // :contentReference[oaicite:2]{index=2}
      } catch (_) {}
    },
    onError: (e) => {
      errorMsg.value = "שגיאת GovMap: " + (e?.message || JSON.stringify(e));
    },
  });

  window.govmap.onEvent(window.govmap.events.EXTENT_CHANGE).progress(async (e) => {
    if (!autoRefresh.value) return;
    const extent = e?.extent;
    if (!extent) return;
    const wkt = extentToWkt(extent);
    await loadBuildingsByWkt(wkt);
  });
}

onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
  } catch (_) {}
});

/* ========= LOAD CSV ========= */
async function reloadBuildingData() {
  loadingData.value = true;
  errorMsg.value = "";

  try {
    const res = await fetch(BUILDING_DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`CSV לא נטען: ${res.status}. בדוק שהקובץ קיים תחת public/data`);

    const text = await res.text();
    const idx = buildIndexFromCsv(text);

    movementIndex.value = idx;

    // Re-join existing results
    if (buildings.value.length) {
      buildings.value = buildings.value.map(applyJoinAndAnomaly);
      await redrawOverlays();
    }
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingData.value = false;
  }
}

function buildIndexFromCsv(csvText) {
  const lines = csvText.split(/\r?\n/).filter((l) => l.trim().length);
  if (lines.length < 2) throw new Error("CSV ריק/לא תקין");

  const headers = parseCsvLine(lines[0]).map((h) => String(h || "").trim());
  const idIdx = pickHeaderIndex(headers, CSV_ID_COL_CANDIDATES);
  const rateIdx = pickHeaderIndex(headers, CSV_RATE_COL_CANDIDATES);
  const dateIdx = pickHeaderIndex(headers, CSV_DATE_COL_CANDIDATES, true);

  if (idIdx < 0) throw new Error(`לא מצאתי עמודת ID ב־CSV. כותרות: ${headers.join(", ")}`);
  if (rateIdx < 0) throw new Error(`לא מצאתי עמודת rate ב־CSV. כותרות: ${headers.join(", ")}`);

  const idx = new Map();

  for (let i = 1; i < lines.length; i++) {
    const fields = parseCsvLine(lines[i]);
    const id = String(fields[idIdx] ?? "").trim();
    if (!id) continue;

    const rate = toNumberSafe(fields[rateIdx]);
    const lastDate = dateIdx >= 0 ? String(fields[dateIdx] ?? "").trim() : "";

    idx.set(id, {
      rate_mm_yr: rate,
      last_date: lastDate,
      source: "CSV",
    });
  }

  return idx;
}

function pickHeaderIndex(headers, candidates, optional = false) {
  const norm = (s) => String(s || "").trim().toLowerCase();
  const hs = headers.map(norm);
  for (const c of candidates) {
    const j = hs.indexOf(norm(c));
    if (j >= 0) return j;
  }
  return optional ? -1 : -1;
}

// CSV parser (תומך גם בגרשיים ו-"" בתוך גרשיים)
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

/* ========= GovMap query ========= */
async function loadBuildingsByWkt(wkt) {
  if (!govReady.value || !wkt) return;

  loadingQuery.value = true;
  errorMsg.value = "";
  lastQueryWkt.value = wkt;
  selected.value = null;

  try {
    const resp = await window.govmap.intersectFeatures({
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true, // :contentReference[oaicite:3]{index=3}
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    const parsed = [];

    for (const it of items.slice(0, MAX_FEATURES)) {
      const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? "";
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
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingQuery.value = false;
  }
}

function applyJoinAndAnomaly(b) {
  const m = movementIndex.value.get(String(b.joinKey));
  const rate = m?.rate_mm_yr;
  const isAnom = typeof rate === "number" && Number.isFinite(rate) && Math.abs(rate) >= Number(rateThreshold.value);

  return { ...b, movement: m || null, isAnomaly: !!m && isAnom };
}

/* ========= Draw overlays ========= */
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
  if (s.startsWith("LINESTRING") || s.startsWith("MULTILINESTRING")) return "line";
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
      defaultSymbol: { outlineColor: [0, 80, 255, 0.7], outlineWidth: 1, fillColor: [0, 80, 255, 0.12] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (normPt.length) {
    await window.govmap.displayGeometries({
      wkts: normPt.slice(0, MAX_DRAW_NORMALS).map((b) => b.wkt),
      names: normPt.slice(0, MAX_DRAW_NORMALS).map(() => "norm_pt"),
      geometryType: window.govmap.geometryType.POINT,
      defaultSymbol: { size: 6, color: [0, 80, 255, 0.7] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (anomPoly.length) {
    await window.govmap.displayGeometries({
      wkts: anomPoly.slice(0, MAX_DRAW_ANOMALIES).map((b) => b.wkt),
      names: anomPoly.slice(0, MAX_DRAW_ANOMALIES).map(() => "anom_poly"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [255, 0, 0, 1], outlineWidth: 2, fillColor: [255, 0, 0, 0.35] },
      clearExisting: false,
      showBubble: false,
    });
  }

  if (anomPt.length) {
    await window.govmap.displayGeometries({
      wkts: anomPt.slice(0, MAX_DRAW_ANOMALIES).map((b) => b.wkt),
      names: anomPt.slice(0, MAX_DRAW_ANOMALIES).map(() => "anom_pt"),
      geometryType: window.govmap.geometryType.POINT,
      defaultSymbol: { size: 9, color: [255, 0, 0, 0.9] },
      clearExisting: false,
      showBubble: false,
    });
  }
}

async function drawSelectedOverlay(b) {
  if (!govReady.value || !b?.wkt) return;

  const k = wktKind(b.wkt);
  try {
    window.govmap.clearGeometriesByName(["sel_poly", "sel_pt"]);
  } catch (_) {}

  if (k === "poly") {
    await window.govmap.displayGeometries({
      wkts: [b.wkt],
      names: ["sel_poly"],
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: { outlineColor: [255, 215, 0, 1], outlineWidth: 3, fillColor: [255, 215, 0, 0.15] },
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

/* ========= UI actions ========= */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  errorMsg.value = "";

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

async function refreshFromLastQuery() {
  if (!lastQueryWkt.value) return;
  await loadBuildingsByWkt(lastQueryWkt.value);
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
      throw new Error("לא נמצאה תוצאה מדויקת.");
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
  selected.value = null;

  try {
    const wkt = `POINT(${x} ${y})`;
    const resp = await window.govmap.intersectFeatures({
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    if (!items.length) throw new Error("לא נמצאה ישות בנקודה הזו.");

    const it = items[0];
    const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? "";
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
}

/* ========= Helpers ========= */
function toNumberSafe(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim().replace(",", ".");
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
  const xmin = ext?.xmin ?? ext?.XMin ?? ext?.XMIN;
  const ymin = ext?.ymin ?? ext?.YMin ?? ext?.YMIN;
  const xmax = ext?.xmax ?? ext?.XMax ?? ext?.XMAX;
  const ymax = ext?.ymax ?? ext?.YMax ?? ext?.YMAX;
  if (![xmin, ymin, xmax, ymax].every((v) => typeof v === "number")) return "";
  return `POLYGON((${xmin} ${ymin}, ${xmax} ${ymin}, ${xmax} ${ymax}, ${xmin} ${ymax}, ${xmin} ${ymin}))`;
}

/* ========= lifecycle ========= */
onMounted(async () => {
  try {
    await initGovMap();
    await reloadBuildingData();
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
});

watch([rateThreshold, showNormals], async () => {
  buildings.value = buildings.value.map(applyJoinAndAnomaly);
  await redrawOverlays();
});
</script>

<style scoped>
/* (אותו CSS שהיה לך – השארתי כמו שהוא) */
.app{height:100vh;width:100%;display:grid;grid-template-columns:380px 1fr;background:#f6f7fb;overflow:hidden}
.panel{height:100%;overflow:auto;background:#fff;border-left:1px solid #e7e9f2;padding:14px}
.panelTop{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:12px}
.titles .appTitle{font-weight:800;font-size:16px}
.titles .appSub{margin-top:4px;font-size:12px;color:#5b6073;line-height:1.35}
.iconBtn{border:1px solid #e2e5f0;background:#fff;border-radius:10px;width:36px;height:36px;cursor:pointer}
.box{border:1px solid #eef0f7;border-radius:14px;padding:12px;margin-bottom:12px;background:#fbfbfe}
.boxTitle{font-weight:800;margin-bottom:10px}
.row{display:grid;grid-template-columns:1fr 120px;gap:10px;align-items:center;margin:8px 0}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.lbl{font-size:13px;color:#2b2f3a}
.inp{width:100%;padding:9px 10px;border:1px solid #e2e5f0;border-radius:10px;outline:none;background:#fff}
.btn{padding:10px 12px;border-radius:12px;border:1px solid #2a62ff;background:#2a62ff;color:#fff;cursor:pointer;font-weight:700}
.btn:disabled{opacity:.6;cursor:not-allowed}
.btn.ghost{background:#fff;color:#2a62ff}
.sep{height:1px;background:#eef0f7;margin:12px 0}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.stat{border:1px solid #eef0f7;border-radius:12px;padding:10px;background:#fff}
.stat .k{font-size:12px;color:#6a7187}
.stat .v{font-size:14px;font-weight:800;margin-top:2px}
.err{margin-top:10px;padding:10px;border-radius:12px;background:#fff1f1;border:1px solid #ffd0d0;color:#b3261e;font-size:13px}
.muted{color:#6a7187;font-size:13px}
.muted.small{font-size:12px;line-height:1.5}
.list{display:grid;gap:8px}
.listItem{text-align:right;padding:10px;border-radius:12px;border:1px solid #eef0f7;background:#fff;cursor:pointer}
.listItem.on{border-color:#2a62ff;box-shadow:0 0 0 3px rgba(42,98,255,.12)}
.liTop{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.liId{font-weight:900}
.liRate{font-weight:900;color:#b3261e}
.liSub{margin-top:6px;font-size:12px;color:#6a7187;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.dot{opacity:.6}
.kv{display:grid;grid-template-columns:120px 1fr;gap:8px 10px}
.kv .k{font-size:12px;color:#6a7187}
.kv .v{font-size:13px;font-weight:800;color:#232633}
.mapWrap{position:relative;height:100%;width:100%}
.map{height:100%;width:100%;background:#dfe6f6}
.switch{position:relative;width:46px;height:26px;display:inline-block}
.switch input{display:none}
.switch span{position:absolute;inset:0;background:#d7dbea;border-radius:999px;transition:.2s}
.switch span::after{content:"";position:absolute;top:3px;right:3px;width:20px;height:20px;background:#fff;border-radius:999px;transition:.2s;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.switch input:checked + span{background:#2a62ff}
.switch input:checked + span::after{transform:translateX(-20px)}
@media (max-width:980px){.app{grid-template-columns:1fr;grid-template-rows:auto 1fr}.panel{position:sticky;top:0;z-index:2}}
</style>

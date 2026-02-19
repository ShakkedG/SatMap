<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div class="titles">
          <div class="appTitle">SatMap – Buildings + Join</div>
          <div class="appSub">
            GovMap בניינים + JOIN לנתוני בניינים (CSV/JSON/API) + סימון תנועה חריגה
          </div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">
          ☰
        </button>
      </div>

      <section class="box">
        <div class="row">
          <label class="lbl">סף “חריגה” |Δrate| (mm/yr)</label>
          <input class="inp" type="number" v-model.number="rateThreshold" step="0.5" />
        </div>

        <div class="row">
          <label class="lbl">הצג גם בניינים לא־חריגים</label>
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
          <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady">
            בחר אזור (מלבן) וטעינה
          </button>
          <button class="btn ghost" @click="refreshFromLastQuery" :disabled="!govReady || !lastQueryWkt">
            טען שוב
          </button>
        </div>

        <div class="row2">
          <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">
            נקה הדגשות
          </button>
          <button class="btn ghost" @click="reloadBuildingData" :disabled="loadingData">
            רענן נתוני בניינים
          </button>
        </div>

        <div class="sep"></div>

        <div class="row">
          <label class="lbl">חיפוש כתובת (GovMap geocode)</label>
          <input class="inp" v-model.trim="addressQuery" placeholder="לדוגמה: הרוקמים 26 חולון" />
        </div>

        <div class="row2">
          <button class="btn" @click="locateAddress" :disabled="!govReady || !addressQuery">
            אתר
          </button>
          <button class="btn ghost" @click="pickPointAndInspect" :disabled="!govReady">
            בחר נקודה → בדוק בניין
          </button>
        </div>

        <div class="sep"></div>

        <div class="stats">
          <div class="stat">
            <div class="k">סטטוס</div>
            <div class="v">
              <span v-if="!govReady">טוען GovMap…</span>
              <span v-else>מוכן</span>
              <span v-if="loadingQuery"> · שואב בניינים…</span>
              <span v-if="loadingData"> · טוען נתוני בניינים…</span>
            </div>
          </div>
          <div class="stat">
            <div class="k">בניינים שהתקבלו</div>
            <div class="v">{{ buildings.length }}</div>
          </div>
          <div class="stat">
            <div class="k">חריגים</div>
            <div class="v">{{ anomalies.length }}</div>
          </div>
          <div class="stat">
            <div class="k">JOIN hits</div>
            <div class="v">{{ joinedCount }}</div>
          </div>
        </div>

        <div v-if="errorMsg" class="err">{{ errorMsg }}</div>
      </section>

      <section class="box">
        <div class="boxTitle">רשימת חריגים (לפי |rate|)</div>

        <div v-if="anomalies.length === 0" class="muted">
          אין חריגים כרגע. (נסה להגדיל אזור, או להוריד סף חריגה)
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
        <div class="boxTitle">פרטי בניין נבחר</div>

        <div class="kv">
          <div class="k">Join Key</div>
          <div class="v">{{ selected.joinKey }}</div>

          <div class="k">Rate (mm/yr)</div>
          <div class="v">{{ formatRate(selected.movement?.rate_mm_yr) }}</div>

          <div class="k">האם חריג</div>
          <div class="v">{{ selected.isAnomaly ? "כן" : "לא" }}</div>

          <div class="k">מקור נתונים</div>
          <div class="v">{{ selected.movement?.source || "—" }}</div>
        </div>
      </section>

      <section class="box">
        <div class="boxTitle">הגדרות JOIN (מה לשנות אצלך)</div>
        <div class="muted small">
          1) שנה למעלה את <b>BUILDINGS_LAYER</b> לשם/מספר השכבה שלך ב־GovMap.<br />
          2) שנה את <b>BUILDING_ID_FIELD</b> לשם השדה שמזהה בניין בשכבה (למשל ID / BLDG_ID / OBJECTID).<br />
          3) הנתונים שלך כרגע מגיעים מ־CSV: <b>public/data/tablecsv.csv</b> (לא building_data.json).
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

/**
 * =========================
 *  CONFIG
 * =========================
 */

// טוקן GovMap
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";

// שכבת הבניינים שלך ב־GovMap
const BUILDINGS_LAYER = "225287";

// שם השדה בשכבת הבניינים שמייצג מזהה לבניין (ה־JOIN key)
const BUILDING_ID_FIELD = "ID";

/**
 * הנתונים שלך נמצאים כאן:
 * client/public/data/tablecsv.csv
 * לכן ב-build זה יהיה: <BASE_URL>/data/tablecsv.csv
 */
const BASE_URL = (import.meta?.env?.BASE_URL || "/").replace(/\/?$/, "/");
const BUILDING_DATA_URL = `${BASE_URL}data/tablecsv.csv`;

/**
 * אם אתה יודע בוודאות את שמות העמודות ב-CSV — תוכל לשים כאן.
 * אם תשאיר ריק, הקוד ינסה לזהות אוטומטית.
 */
const CSV_ID_COL_HINT = ""; // לדוגמה: "ID" / "building_id"
const CSV_RATE_COL_HINT = ""; // לדוגמה: "rate_mm_yr" / "v"
const CSV_DATE_COL_HINT = ""; // לדוגמה: "last_date"

/**
 * ביצועים: לא לצייר אלפי פוליגונים בבת אחת
 */
const MAX_DRAW_ANOMALIES = 600;
const MAX_DRAW_NORMALS = 600;

/* =========================
 *  STATE
 * ========================= */
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

const buildings = ref([]); // בניינים מה-GovMap אחרי JOIN
const selected = ref(null);

/* Index: joinKey -> movement */
const movementIndex = ref(new Map());

/* =========================
 *  DERIVED
 * ========================= */
const anomalies = computed(() =>
  [...buildings.value]
    .filter((b) => b.isAnomaly)
    .sort((a, b) => Math.abs(b.movement?.rate_mm_yr ?? 0) - Math.abs(a.movement?.rate_mm_yr ?? 0))
);

const joinedCount = computed(() => buildings.value.filter((b) => !!b.movement).length);

/* =========================
 *  GOVMAP script loader
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

/* =========================
 *  INIT
 * ========================= */
async function initGovMap() {
  errorMsg.value = "";
  await loadGovMapScript();

  if (!GOVMAP_TOKEN) {
    throw new Error("חסר GOVMAP_TOKEN.");
  }

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN,
    background: 3,
    layers: [],
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    layersMode: 1,
    zoomButtons: true,
    onLoad: () => {
      govReady.value = true;
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

/* =========================
 *  CLEANUP
 * ========================= */
onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) {
      window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
    }
  } catch (_) {}
});

/* =========================
 *  DATA LOADER (CSV)
 * ========================= */
async function reloadBuildingData() {
  loadingData.value = true;
  errorMsg.value = "";

  try {
    const res = await fetch(BUILDING_DATA_URL, { cache: "no-store" });

    // אם אין קובץ (בזמן פיתוח/דיפלוי) — לא להפיל
    if (res.status === 404) {
      movementIndex.value = new Map();
      return;
    }
    if (!res.ok) throw new Error(`BUILDING_DATA_URL נכשל (${res.status})`);

    // Streaming parse כדי להתמודד עם קובץ גדול
    const reader = res.body?.getReader?.();
    if (!reader) {
      // fallback: טקסט מלא
      const text = await res.text();
      movementIndex.value = parseCsvToIndex(text);
      if (buildings.value.length) {
        buildings.value = buildings.value.map((b) => applyJoinAndAnomaly(b));
        await redrawOverlays();
      }
      return;
    }

    const decoder = new TextDecoder("utf-8");
    let buf = "";
    let headers = null;
    let delim = ",";
    let idIdx = -1;
    let rateIdx = -1;
    let dateIdx = -1;

    const idx = new Map();

    const pickAndSetIndices = (hdrs) => {
      headers = hdrs;

      const idCandidates = [
        "id",
        "building_id",
        "bldg_id",
        "bldgid",
        "blgd_id",
        "objectid",
        "OBJECTID",
        "ID",
      ];
      const rateCandidates = [
        "rate_mm_yr",
        "rate",
        "velocity",
        "vel",
        "v",
        "mm_yr",
        "mm/yr",
        "subsidence",
        "sink_rate",
      ];
      const dateCandidates = ["last_date", "date", "last", "timestamp", "time"];

      const idCol = CSV_ID_COL_HINT ? pickHeaderFuzzy(headers, [CSV_ID_COL_HINT]) : pickHeaderFuzzy(headers, idCandidates);
      const rateCol = CSV_RATE_COL_HINT
        ? pickHeaderFuzzy(headers, [CSV_RATE_COL_HINT])
        : pickHeaderFuzzy(headers, rateCandidates);
      const dateCol = CSV_DATE_COL_HINT
        ? pickHeaderFuzzy(headers, [CSV_DATE_COL_HINT])
        : pickHeaderFuzzy(headers, dateCandidates);

      if (!idCol || !rateCol) {
        const sample = headers.slice(0, 60).join(", ");
        throw new Error(
          `לא הצלחתי לזהות עמודות ב-CSV (צריך לפחות ID + RATE).\n` +
            `כותרות (חלקי): ${sample}\n` +
            `אם אתה יודע את השמות: תגדיר CSV_ID_COL_HINT ו-CSV_RATE_COL_HINT.`
        );
      }

      idIdx = headers.findIndex((h) => sameHeader(h, idCol));
      rateIdx = headers.findIndex((h) => sameHeader(h, rateCol));
      dateIdx = dateCol ? headers.findIndex((h) => sameHeader(h, dateCol)) : -1;
    };

    const processLine = (line) => {
      if (!line) return;

      if (!headers) {
        const commaCount = (line.match(/,/g) || []).length;
        const semiCount = (line.match(/;/g) || []).length;
        delim = semiCount > commaCount ? ";" : ",";
        const hdrs = parseCsvLine(line, delim).map((h) => h.trim()).filter(Boolean);
        pickAndSetIndices(hdrs);
        return;
      }

      const row = parseCsvLine(line, delim);
      if (!row || row.length <= Math.max(idIdx, rateIdx)) return;

      const id = String(row[idIdx] ?? "").trim();
      if (!id) return;

      const rate = toNumberSafe(row[rateIdx]);
      if (rate === null) return;

      const lastDate = dateIdx >= 0 ? String(row[dateIdx] ?? "").trim() : "";

      idx.set(id, {
        rate_mm_yr: rate,
        last_date: lastDate,
        source: "tablecsv.csv",
      });
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });

      let lines = buf.split(/\r?\n/);
      buf = lines.pop() ?? "";

      for (const ln of lines) processLine(ln);
    }

    buf += decoder.decode();
    if (buf) processLine(buf);

    movementIndex.value = idx;

    if (buildings.value.length) {
      buildings.value = buildings.value.map((b) => applyJoinAndAnomaly(b));
      await redrawOverlays();
    }
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingData.value = false;
  }
}

function parseCsvToIndex(text) {
  const lines = text.split(/\r?\n/);
  if (lines.length < 2) return new Map();

  const headerLine = lines[0] || "";
  const commaCount = (headerLine.match(/,/g) || []).length;
  const semiCount = (headerLine.match(/;/g) || []).length;
  const delim = semiCount > commaCount ? ";" : ",";

  const headers = parseCsvLine(headerLine, delim).map((h) => h.trim()).filter(Boolean);

  const idCandidates = ["id", "building_id", "bldg_id", "objectid", "ID"];
  const rateCandidates = ["rate_mm_yr", "rate", "velocity", "vel", "v", "mm/yr", "mm_yr", "subsidence"];
  const dateCandidates = ["last_date", "date", "timestamp", "time"];

  const idCol = CSV_ID_COL_HINT ? pickHeaderFuzzy(headers, [CSV_ID_COL_HINT]) : pickHeaderFuzzy(headers, idCandidates);
  const rateCol = CSV_RATE_COL_HINT
    ? pickHeaderFuzzy(headers, [CSV_RATE_COL_HINT])
    : pickHeaderFuzzy(headers, rateCandidates);
  const dateCol = CSV_DATE_COL_HINT
    ? pickHeaderFuzzy(headers, [CSV_DATE_COL_HINT])
    : pickHeaderFuzzy(headers, dateCandidates);

  if (!idCol || !rateCol) {
    const sample = headers.slice(0, 60).join(", ");
    throw new Error(
      `לא הצלחתי לזהות עמודות ב-CSV (צריך לפחות ID + RATE).\n` +
        `כותרות (חלקי): ${sample}\n` +
        `אם אתה יודע את השמות: תגדיר CSV_ID_COL_HINT ו-CSV_RATE_COL_HINT.`
    );
  }

  const idIdx = headers.findIndex((h) => sameHeader(h, idCol));
  const rateIdx = headers.findIndex((h) => sameHeader(h, rateCol));
  const dateIdx = dateCol ? headers.findIndex((h) => sameHeader(h, dateCol)) : -1;

  const idx = new Map();

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;
    const row = parseCsvLine(line, delim);
    if (!row || row.length <= Math.max(idIdx, rateIdx)) continue;

    const id = String(row[idIdx] ?? "").trim();
    if (!id) continue;

    const rate = toNumberSafe(row[rateIdx]);
    if (rate === null) continue;

    const lastDate = dateIdx >= 0 ? String(row[dateIdx] ?? "").trim() : "";

    idx.set(id, { rate_mm_yr: rate, last_date: lastDate, source: "tablecsv.csv" });
  }

  return idx;
}

/* =========================
 *  GovMap query: buildings by WKT
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
      throw new Error("הזום נמוך מדי לשאילתת בניינים. תתקרב (zoom) ואז תנסה שוב.");
    }

    const params = {
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    const parsed = [];

    for (const it of items) {
      const objectId = it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.objectid ?? it?.id ?? null;

      const values = it?.Values ?? it?.values ?? it?.Fields ?? it?.fields ?? [];
      const fieldVal = extractFieldValue(values, BUILDING_ID_FIELD);

      const joinKey = String(fieldVal ?? "").trim();
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
  const isAnom = typeof rate === "number" && Number.isFinite(rate) ? Math.abs(rate) >= Number(rateThreshold.value) : false;

  return {
    ...b,
    movement: m || null,
    isAnomaly: !!m && isAnom,
  };
}

/* =========================
 *  Draw overlays
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
    if (!b.wkt || !b.wkt.toUpperCase().includes("POLYGON")) continue;
    if (b.isAnomaly) anom.push(b);
    else if (showNormals.value) norm.push(b);
  }

  const anomToDraw = anom.slice(0, MAX_DRAW_ANOMALIES);
  const normToDraw = norm.slice(0, MAX_DRAW_NORMALS);

  if (normToDraw.length) {
    await window.govmap.displayGeometries({
      wkts: normToDraw.map((b) => b.wkt),
      names: normToDraw.map(() => "norm"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [0, 80, 255, 0.7],
        outlineWidth: 1,
        fillColor: [0, 80, 255, 0.12],
      },
      symbols: [],
      clearExistings: false,
      clearExisting: false,
      showBubble: false,
      data: { tooltips: normToDraw.map((b) => `בניין ${b.joinKey}`) },
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
        fillColor: [255, 0, 0, 0.35],
      },
      symbols: [],
      clearExistings: false,
      clearExisting: false,
      showBubble: false,
      data: {
        tooltips: anomToDraw.map((b) => `חריג • ${b.joinKey} • ${formatRate(b.movement?.rate_mm_yr)}`),
      },
    });
  }
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
    clearExistings: false,
    clearExisting: false,
    showBubble: false,
    data: { tooltips: [`נבחר: ${b.joinKey}`] },
  });
}

/* =========================
 *  UI actions
 * ========================= */
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
      throw new Error("לא נמצאה תוצאה מדויקת. נסה לנסח כתובת אחרת/להוסיף מספר בית.");
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
    await inspectBuildingAtPoint(p.x, p.y);
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    try {
      window.govmap.setDefaultTool?.();
    } catch (_) {}
  }
}

async function inspectBuildingAtPoint(x, y) {
  loadingQuery.value = true;
  errorMsg.value = "";
  selected.value = null;

  try {
    const wkt = `POINT(${x} ${y})`;

    const params = {
      layerName: BUILDINGS_LAYER,
      geometry: wkt,
      fields: [BUILDING_ID_FIELD],
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);
    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];

    if (!items.length) throw new Error("לא נמצא בניין בנקודה הזו.");

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

    const geomWkt = typeof shape === "string" ? shape : "";

    const b = applyJoinAndAnomaly({
      key: `${joinKey}__${objectId || "pt"}`,
      objectId,
      joinKey,
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

  const c = centroidFromPolygonWkt(b.wkt);
  if (c) {
    window.govmap.zoomToXY({ x: c.x, y: c.y, level: 9 });
    window.govmap.setMapMarker?.({ x: c.x, y: c.y });
  }
}

/* =========================
 *  Helpers
 * ========================= */
function toNumberSafe(v) {
  const n = Number(String(v).replace(",", "."));
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

/** CSV helpers **/
function normalizeHeader(s) {
  return String(s ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\u200F\u200E]/g, "")
    .replace(/[^a-z0-9א-ת]+/g, "");
}

function sameHeader(a, b) {
  return normalizeHeader(a) === normalizeHeader(b);
}

// קודם מנסה התאמה מדויקת, ואם לא – "מכיל" (fuzzy)
function pickHeaderFuzzy(headers, candidates) {
  const nHeaders = headers.map((h) => normalizeHeader(h));

  // exact
  for (const c of candidates) {
    const nc = normalizeHeader(c);
    const idx = nHeaders.indexOf(nc);
    if (idx >= 0) return headers[idx];
  }

  // contains
  for (const c of candidates) {
    const nc = normalizeHeader(c);
    const idx = nHeaders.findIndex((h) => h.includes(nc) || nc.includes(h));
    if (idx >= 0) return headers[idx];
  }

  return null;
}

// parser קטן עם תמיכה בגרשיים ו-"" בתוך גרשיים
function parseCsvLine(line, delim = ",") {
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

    if (!inQuotes && ch === delim) {
      out.push(cur);
      cur = "";
      continue;
    }

    cur += ch;
  }
  out.push(cur);
  return out;
}

/* =========================
 *  LIFECYCLE
 * ========================= */
onMounted(async () => {
  try {
    await initGovMap();
    await reloadBuildingData();
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  }
});

watch([rateThreshold, showNormals], async () => {
  buildings.value = buildings.value.map((b) => applyJoinAndAnomaly(b));
  await redrawOverlays();
});
</script>

<style scoped>
/* --- נשאר כמו אצלך --- */
.app {
  height: 100vh;
  width: 100%;
  display: grid;
  grid-template-columns: 380px 1fr;
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
  font-weight: 800;
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
  font-weight: 800;
  margin-bottom: 10px;
}

.row {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 10px;
  align-items: center;
  margin: 8px 0;
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
  font-weight: 700;
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
  font-weight: 800;
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
  white-space: pre-wrap;
}

.muted {
  color: #6a7187;
  font-size: 13px;
}

.muted.small {
  font-size: 12px;
  line-height: 1.5;
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
  font-weight: 800;
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
}
</style>

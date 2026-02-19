<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div class="titles">
          <div class="appTitle">SatMap – GovMap Buildings + CSV Join</div>
          <div class="appSub">טעינת שכבת בניינים מ-GovMap + JOIN ל-CSV (ללא כותרות) + הדגשת חריגים</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור' : 'פתח'">☰</button>
      </div>

      <!-- SETTINGS -->
      <section class="box">
        <div class="boxTitle">הגדרות</div>

        <div class="row">
          <label class="lbl">מספר שכבת בניינים (GovMap)</label>
          <input class="inp" v-model.trim="buildingsLayer" />
        </div>

        <div class="row">
          <label class="lbl">שם שדה מזהה בשכבה (אם קיים)</label>
          <input class="inp" v-model.trim="buildingIdField" placeholder="לרוב: ID / BLDG_ID … (אם לא בטוח – תשאיר ID)" />
        </div>

        <div class="row">
          <label class="lbl">הצג שכבת בניינים של GovMap</label>
          <label class="switch">
            <input type="checkbox" v-model="showGovLayer" @change="applyGovLayerVisibility" />
            <span></span>
          </label>
        </div>

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
          <label class="lbl">עדכון אוטומטי בזמן זום/הזזה</label>
          <label class="switch">
            <input type="checkbox" v-model="autoRefresh" />
            <span></span>
          </label>
        </div>

        <div class="row2">
          <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady">בחר אזור (מלבן) ו-JOIN</button>
          <button class="btn ghost" @click="loadFromCurrentExtent" :disabled="!govReady">JOIN לפי היקף המפה</button>
        </div>

        <div class="row2">
          <button class="btn ghost" @click="refreshFromLastQuery" :disabled="!govReady || !lastQueryWkt">טען שוב</button>
          <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">נקה הדגשות</button>
        </div>

        <div class="sep"></div>

        <div class="stats">
          <div class="stat">
            <div class="k">סטטוס</div>
            <div class="v">
              <span v-if="!govReady">טוען GovMap…</span>
              <span v-else>מוכן</span>
              <span v-if="loadingCsv"> · טוען CSV…</span>
              <span v-if="loadingQuery"> · שואב ישויות…</span>
              <span v-if="loadingJoin"> · JOIN…</span>
            </div>
          </div>
          <div class="stat"><div class="k">CSV rows</div><div class="v">{{ csvRowCount }}</div></div>
          <div class="stat"><div class="k">ישויות שנשלפו</div><div class="v">{{ buildings.length }}</div></div>
          <div class="stat"><div class="k">JOIN hits</div><div class="v">{{ joinedCount }}</div></div>
        </div>

        <div v-if="errorMsg" class="err">{{ errorMsg }}</div>
        <div v-if="warnMsg" class="warn">{{ warnMsg }}</div>
      </section>

      <!-- CSV -->
      <section class="box">
        <div class="boxTitle">CSV (ללא כותרות)</div>

        <div class="muted small">
          קובץ: <b>client/public/data/tablecsv.csv</b><br />
          URL שטוענים בפועל:
          <div class="mono">{{ csvUrl }}</div>
          פורמט צפוי: <span class="monoInline">id,val2,rate</span> (לדוגמה: <span class="monoInline">710791,53743,-34</span>)
        </div>

        <div class="row2" style="margin-top:10px">
          <button class="btn" @click="loadCsv" :disabled="loadingCsv">טען / רענן CSV</button>
          <button class="btn ghost" @click="rebuildJoinIndex" :disabled="!csvRowCount || loadingJoin">בנה אינדקס JOIN</button>
        </div>

        <div v-if="csvPreview.length" class="previewWrap">
          <div class="muted small">תצוגה מקדימה (10 שורות)</div>
          <div class="tableWrap">
            <table class="miniTable">
              <thead>
                <tr>
                  <th>id</th><th>val2</th><th>rate</th>
                </tr>
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
        </div>

        <div class="sep"></div>

        <div class="muted small">
          אם JOIN hits נשאר 0: זה כמעט תמיד אומר שה-CSV משתמש ב-<b>OBJECTID</b> של השכבה ולא ב-ID אחר.
          הקוד פה מנסה JOIN גם לפי <b>joinKey</b> וגם לפי <b>objectId</b> אוטומטית.
        </div>
      </section>

      <!-- ANOMALIES -->
      <section class="box">
        <div class="boxTitle">חריגים</div>

        <div class="row">
          <label class="lbl">חיפוש ID</label>
          <input class="inp" v-model.trim="idSearch" placeholder="חפש לפי מזהה" />
        </div>

        <div v-if="filteredAnomalies.length === 0" class="muted">אין חריגים להצגה כרגע.</div>

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
              <span>layerId: {{ b.joinKey }}</span>
              <span class="dot">•</span>
              <span>objectId: {{ b.objectId }}</span>
            </div>
          </button>
        </div>
      </section>

      <!-- SELECTED -->
      <section v-if="selected" class="box">
        <div class="boxTitle">נבחר</div>
        <div class="kv">
          <div class="k">ID (ל-JOIN)</div>
          <div class="v">{{ selected.bestJoinId }}</div>

          <div class="k">Rate</div>
          <div class="v">{{ formatRate(selected.movement?.rate_mm_yr) }}</div>

          <div class="k">חריג?</div>
          <div class="v">{{ selected.isAnomaly ? "כן" : "לא" }}</div>
        </div>
      </section>
    </aside>

    <main class="mapWrap">
      <div id="map" class="map"></div>

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

/* ===== GovMap config ===== */
const GOVMAP_TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";

/* ===== URL (GitHub Pages safe) ===== */
function getAppBaseHref() {
  const baseTagHref = document.querySelector("base")?.href;
  if (baseTagHref) return baseTagHref;
  const base = import.meta?.env?.BASE_URL || "/";
  return new URL(base, window.location.origin).href;
}
const appBaseHref = getAppBaseHref();
const csvUrl = new URL("data/tablecsv.csv", appBaseHref).href;

/* ===== STATE ===== */
const panelOpen = ref(true);
const govReady = ref(false);

const errorMsg = ref("");
const warnMsg = ref("");

const loadingCsv = ref(false);
const loadingQuery = ref(false);
const loadingJoin = ref(false);

const rateThreshold = ref(2.0);
const showNormals = ref(false);
const autoRefresh = ref(false);

const showGovLayer = ref(true);
const buildingsLayer = ref("225287");   // שכבת הבניינים שלך
const buildingIdField = ref("ID");      // אם אין/לא בטוח – עדיין יש ObjectID שנקבל תמיד

const lastQueryWkt = ref("");

const buildings = ref([]);
const selected = ref(null);
const idSearch = ref("");

/* CSV parsed: headerless => {id,val2,rate} */
const csvRows = ref([]);
const csvPreview = ref([]);
const csvRowCount = computed(() => csvRows.value.length);

/* JOIN index: multiple normalized keys -> movement */
const movementIndex = ref(new Map());

/* ===== derived ===== */
const joinedCount = computed(() => buildings.value.filter(b => !!b.movement).length);

const anomalies = computed(() =>
  buildings.value
    .filter(b => b.isAnomaly)
    .sort((a,b) => Math.abs(b.movement?.rate_mm_yr ?? 0) - Math.abs(a.movement?.rate_mm_yr ?? 0))
);

const filteredAnomalies = computed(() => {
  const q = idSearch.value.trim();
  if (!q) return anomalies.value;
  return anomalies.value.filter(b => String(b.bestJoinId).includes(q));
});

/* ===== GovMap loader ===== */
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
  warnMsg.value = "";

  await loadGovMapScript();
  if (!GOVMAP_TOKEN) throw new Error("חסר GOVMAP_TOKEN.");

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN,
    background: 3,
    layers: showGovLayer.value ? [buildingsLayer.value] : [],
    layersMode: 1,
    showXY: false,
    identifyOnClick: false,
    zoomButtons: true,

    onLoad: () => {
      govReady.value = true;

      // נסיון “קשיח” להדליק שכבה (במקרים שזה לא נדלק רק מ-layers)
      applyGovLayerVisibility();

      // auto refresh
      window.govmap.onEvent(window.govmap.events.EXTENT_CHANGE).progress(async (e) => {
        if (!autoRefresh.value) return;
        const wkt = extentToWkt(e?.extent);
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
    if (showGovLayer.value) {
      // כמה גרסאות API שונות – ננסה מה שיש בלי להפיל את האפליקציה
      window.govmap.setVisibleLayers?.([buildingsLayer.value]);
      window.govmap.addLayers?.([buildingsLayer.value]);
    } else {
      window.govmap.setVisibleLayers?.([]);
    }
  } catch (_) {
    // לא קריטי – עדיין אפשר לעבוד עם JOIN והדגשות
  }
}

onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
  } catch (_) {}
});

/* ===== CSV (headerless) ===== */
async function loadCsv() {
  loadingCsv.value = true;
  errorMsg.value = "";
  warnMsg.value = "";

  try {
    const res = await fetch(csvUrl, { cache: "no-store" });
    if (!res.ok) throw new Error(`CSV לא נמצא (${res.status}). ודא שזה ב: client/public/data/tablecsv.csv`);

    const text = await res.text();
    const parsed = parseHeaderlessCsv3cols(text);

    csvRows.value = parsed.rows;
    csvPreview.value = parsed.preview;

    await rebuildJoinIndex();
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingCsv.value = false;
  }
}

async function rebuildJoinIndex() {
  loadingJoin.value = true;
  warnMsg.value = "";
  try {
    const idx = new Map();

    for (const r of csvRows.value) {
      const idRaw = normalizeId(r.id);
      const rate = toNumberSafe(r.rate);
      if (!idRaw || rate === null) continue;

      const movement = { rate_mm_yr: rate, source: "CSV", raw: r };

      // שומרים כמה וריאנטים של אותו ID כדי להגדיל התאמות
      const variants = new Set();
      variants.add(idRaw);

      const asNum = normalizeIdNumeric(idRaw);
      if (asNum) variants.add(asNum);

      for (const k of variants) idx.set(k, movement);
    }

    movementIndex.value = idx;

    if (buildings.value.length) {
      buildings.value = buildings.value.map(applyJoinAndAnomaly);
      await redrawOverlays();
    }

    if (idx.size < 50) {
      warnMsg.value = "ה-CSV נטען, אבל האינדקס קטן מאוד. בדוק שהעמודה השלישית היא rate מספרי.";
    }
  } finally {
    loadingJoin.value = false;
  }
}

function parseHeaderlessCsv3cols(csvText) {
  const lines = csvText.split(/\r?\n/).filter(l => l.trim().length);
  const rows = [];
  const preview = [];

  for (let i = 0; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i], ",");
    if (cells.length < 3) continue;

    const obj = {
      id: String(cells[0] ?? "").trim(),
      val2: String(cells[1] ?? "").trim(),
      rate: String(cells[2] ?? "").trim(),
    };

    rows.push(obj);
    if (preview.length < 10) preview.push(obj);
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

/* ===== GovMap query + JOIN ===== */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  errorMsg.value = "";
  warnMsg.value = "";

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

async function loadFromCurrentExtent() {
  if (!govReady.value) return;
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

async function refreshFromLastQuery() {
  if (!lastQueryWkt.value) return;
  await loadBuildingsByWkt(lastQueryWkt.value);
}

async function loadBuildingsByWkt(wkt) {
  if (!govReady.value || !wkt) return;

  loadingQuery.value = true;
  errorMsg.value = "";
  warnMsg.value = "";
  selected.value = null;

  try {
    const fields = uniq([buildingIdField.value, "ID", "BLDG_ID"].filter(Boolean));

    const resp = await window.govmap.intersectFeatures({
      layerName: buildingsLayer.value,
      geometry: wkt,
      fields,
      getShapes: true,
    });

    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.data) ? resp.data : resp?.Data || [];
    if (!items.length) warnMsg.value = "לא התקבלו ישויות באזור. נסה זום/אזור אחר.";

    const parsed = [];
    for (const it of items) {
      const objectId = String(it?.ObjectID ?? it?.objectId ?? it?.OBJECTID ?? it?.id ?? "").trim();

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

      // אם אין joinKey – עדיין אפשר JOIN לפי objectId
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
        "נשלפו ישויות אבל JOIN hits = 0. כנראה שה-CSV לא תואם לשדה ID בשכבה. הקוד כבר מנסה גם OBJECTID – אם עדיין 0, אז ה-CSV הוא מזהה אחר.";
    }
  } catch (err) {
    errorMsg.value = err?.message || String(err);
  } finally {
    loadingQuery.value = false;
  }
}

function applyJoinAndAnomaly(b) {
  // מנסים כמה מפתחות: joinKey ואז objectId, עם וריאנטים נומריים
  const keys = [];
  if (b.joinKey) keys.push(normalizeId(b.joinKey), normalizeIdNumeric(b.joinKey));
  if (b.objectId) keys.push(normalizeId(b.objectId), normalizeIdNumeric(b.objectId));
  const candidates = keys.filter(Boolean);

  let m = null;
  let best = "";
  for (const k of candidates) {
    const hit = movementIndex.value.get(k);
    if (hit) { m = hit; best = k; break; }
  }

  const rate = m?.rate_mm_yr;
  const isAnom = typeof rate === "number" && Number.isFinite(rate) ? Math.abs(rate) >= Number(rateThreshold.value) : false;

  return { ...b, movement: m || null, isAnomaly: !!m && isAnom, bestJoinId: best || (b.joinKey || b.objectId || "") };
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

function uniq(arr) {
  return [...new Set(arr.map(x => String(x)))];
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

/* ===== Draw overlays ===== */
const MAX_DRAW_ANOMALIES = 800;
const MAX_DRAW_NORMALS = 800;

async function clearOverlays() {
  if (!govReady.value) return;
  try {
    window.govmap.clearGeometriesByName(["anom_poly", "norm_poly", "sel_poly"]);
  } catch (_) {}
}

function isPolygonWkt(wkt) {
  const s = String(wkt || "").trim().toUpperCase();
  return s.startsWith("POLYGON") || s.startsWith("MULTIPOLYGON");
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

  if (norm.length) {
    const list = norm.slice(0, MAX_DRAW_NORMALS);
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
    const list = anom.slice(0, MAX_DRAW_ANOMALIES);
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

/* ===== UI ===== */
function formatRate(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2)} mm/yr`;
}

/* ===== lifecycle ===== */
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

watch([buildingsLayer], () => {
  // אם משנים שכבה – נדליק/נכבה מחדש
  if (govReady.value) applyGovLayerVisibility();
});
</script>

<style scoped>
.app{height:100vh;width:100%;display:grid;grid-template-columns:400px 1fr;background:#f6f7fb;overflow:hidden}
.panel{height:100%;overflow:auto;background:#fff;border-left:1px solid #e7e9f2;padding:14px}
.panelTop{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:12px}
.titles .appTitle{font-weight:900;font-size:16px}
.titles .appSub{margin-top:4px;font-size:12px;color:#5b6073;line-height:1.35}
.iconBtn{border:1px solid #e2e5f0;background:#fff;border-radius:10px;width:36px;height:36px;cursor:pointer}
.box{border:1px solid #eef0f7;border-radius:14px;padding:12px;margin-bottom:12px;background:#fbfbfe}
.boxTitle{font-weight:900;margin-bottom:10px}
.row{display:grid;grid-template-columns:1fr 150px;gap:10px;align-items:center;margin:8px 0}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.lbl{font-size:13px;color:#2b2f3a}
.inp{width:100%;padding:9px 10px;border:1px solid #e2e5f0;border-radius:10px;outline:none;background:#fff}
.btn{padding:10px 12px;border-radius:12px;border:1px solid #2a62ff;background:#2a62ff;color:#fff;cursor:pointer;font-weight:900}
.btn:disabled{opacity:.6;cursor:not-allowed}
.btn.ghost{background:#fff;color:#2a62ff}
.sep{height:1px;background:#eef0f7;margin:12px 0}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.stat{border:1px solid #eef0f7;border-radius:12px;padding:10px;background:#fff}
.stat .k{font-size:12px;color:#6a7187}
.stat .v{font-size:14px;font-weight:900;margin-top:2px}
.err{margin-top:10px;padding:10px;border-radius:12px;background:#fff1f1;border:1px solid #ffd0d0;color:#b3261e;font-size:13px}
.warn{margin-top:10px;padding:10px;border-radius:12px;background:#fff7e6;border:1px solid #ffe2a8;color:#7a4b00;font-size:13px}
.muted{color:#6a7187;font-size:13px}
.muted.small{font-size:12px;line-height:1.5}
.mono{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;background:#f3f5fb;border:1px solid #e9ecf7;border-radius:10px;padding:8px 10px;margin-top:6px;direction:ltr;text-align:left;overflow:auto}
.monoInline{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;background:#f3f5fb;border:1px solid #e9ecf7;border-radius:8px;padding:2px 6px}
.previewWrap{margin-top:10px}
.tableWrap{margin-top:6px;border:1px solid #eef0f7;border-radius:12px;background:#fff;overflow:auto;max-height:220px}
.miniTable{width:100%;border-collapse:collapse;font-size:12px}
.miniTable th,.miniTable td{border-bottom:1px solid #eef0f7;padding:8px 10px;white-space:nowrap}
.miniTable th{position:sticky;top:0;background:#fbfbfe;z-index:1;font-weight:900}
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
.kv .v{font-size:13px;font-weight:900;color:#232633}
.mapWrap{position:relative;height:100%;width:100%}
.map{height:100%;width:100%;background:#dfe6f6}
.legend{position:absolute;left:12px;bottom:12px;background:rgba(255,255,255,.92);border:1px solid #e7e9f2;border-radius:14px;padding:10px 12px;display:grid;gap:8px;box-shadow:0 8px 30px rgba(0,0,0,.08)}
.legItem{display:flex;align-items:center;gap:8px;font-size:12px;color:#2b2f3a;font-weight:900}
.swatch{width:14px;height:14px;border-radius:4px;border:1px solid rgba(0,0,0,.15)}
.swatch.red{background:rgba(255,0,0,.35)}
.swatch.blue{background:rgba(0,80,255,.18)}
.swatch.gold{background:rgba(255,215,0,.18)}
.switch{position:relative;width:46px;height:26px;display:inline-block}
.switch input{display:none}
.switch span{position:absolute;inset:0;background:#d7dbea;border-radius:999px;transition:.2s}
.switch span::after{content:"";position:absolute;top:3px;right:3px;width:20px;height:20px;background:#fff;border-radius:999px;transition:.2s;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.switch input:checked + span{background:#2a62ff}
.switch input:checked + span::after{transform:translateX(-20px)}
@media (max-width:980px){
  .app{grid-template-columns:1fr;grid-template-rows:auto 1fr}
  .panel{position:sticky;top:0;z-index:2}
}
</style>

<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Buildings Joined (GeoJSON) – status / Vel_mean / coer_mean / Vel_count</div>
        </div>
        <div class="topBtns">
          <button class="btn ghost" @click="fitToLayer" :disabled="!allBoundsValid">התמקד בשכבה</button>
          <button class="btn" @click="reload">טען מחדש</button>
        </div>
      </div>

      <div class="box">
        <div class="row2">
          <div>
            <label>רקע מפה</label>
            <select v-model="basemap" @change="applyBasemap">
              <option value="osm">OSM</option>
              <option value="esri">Satellite (Esri)</option>
            </select>
          </div>
          <div>
            <label>GeoJSON נטען מ־</label>
            <div class="mono smallLine">{{ loadedFrom || "—" }}</div>
          </div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <div class="kpis">
          <div class="kpi"><div class="k">סה״כ בניינים</div><div class="v">{{ stats.total }}</div></div>
          <div class="kpi sink"><div class="k">שוקע/חשוד</div><div class="v">{{ stats.sinking }}</div></div>
          <div class="kpi stable"><div class="k">יציב</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi lowq"><div class="k">איכות נמוכה</div><div class="v">{{ stats.lowq }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.noData }}</div></div>
        </div>

        <div class="row2" style="margin-top:10px">
          <label class="chk">
            <input type="checkbox" v-model="showSinking" @change="applyVisibility" />
            להציג שוקע/חשוד
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showStable" @change="applyVisibility" />
            להציג יציב
          </label>
        </div>
        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showLowQ" @change="applyVisibility" />
            להציג איכות נמוכה
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showNoData" @change="applyVisibility" />
            להציג אין נתון
          </label>
        </div>

        <div class="row2" style="margin-top:10px">
          <div>
            <label>חיפוש (OBJECTID / שם)</label>
            <input v-model="q" type="text" placeholder="לדוגמה: 188" />
          </div>
          <div>
            <label>מינימום coherence</label>
            <input v-model.number="minCoh" type="number" step="0.05" min="0" max="1" />
          </div>
        </div>

        <div class="legend">
          <div class="legRow"><span class="sw sw-sink"></span> שוקע/חשוד</div>
          <div class="legRow"><span class="sw sw-stable"></span> יציב</div>
          <div class="legRow"><span class="sw sw-lowq"></span> איכות נמוכה</div>
          <div class="legRow"><span class="sw sw-nodata"></span> אין נתון</div>
        </div>
      </div>

      <details class="box" open>
        <summary class="sumTitle">רשימת “חשודים” (מהיר למצוא)</summary>

        <div class="mini muted">מראה רק סטטוס חשוד + coherence ≥ {{ minCoh }}</div>

        <div class="list">
          <button
            v-for="r in suspectsList"
            :key="r.key"
            class="listItem"
            @click="zoomToRow(r)"
            :title="'זום + פרטים'"
          >
            <div class="liTop">
              <div class="liName">{{ r.name }}</div>
              <div class="badge">{{ r.status }}</div>
            </div>
            <div class="liMeta">
              <span class="mono">Vel_mean {{ r.velLabel }}</span>
              <span class="dot">•</span>
              <span class="mono">coer_mean {{ r.cohLabel }}</span>
              <span class="dot">•</span>
              <span class="mono">pts {{ r.countLabel }}</span>
            </div>
          </button>

          <div v-if="!suspectsList.length" class="mini muted" style="margin-top:10px">
            אין תוצאות כרגע (נסה להוריד מינימום coherence או לנקות חיפוש).
          </div>
        </div>
      </details>

      <div class="box" v-if="selected">
        <div class="selHeader">
          <div class="mini"><b>{{ selected.name }}</b></div>
          <button class="btn ghost small" @click="clearSelection">נקה בחירה</button>
        </div>

        <div class="selGrid">
          <div class="selCard">
            <div class="k">status</div>
            <div class="v">{{ selected.status }}</div>
          </div>

          <div class="selCard">
            <div class="k">Vel_mean</div>
            <div class="v mono">{{ selected.velMean }}</div>
          </div>

          <div class="selCard">
            <div class="k">coer_mean</div>
            <div class="v mono">{{ selected.cohMean }}</div>
          </div>

          <div class="selCard">
            <div class="k">Vel_count</div>
            <div class="v mono">{{ selected.velCount }}</div>
          </div>
        </div>

        <div class="mini muted" style="margin-top:10px">
          טיפ: אם חסר שדה, זה אומר שהשם בעמודה שונה (אותיות גדולות/קטנות). הקוד מחפש גם בצורה “חכמה”.
        </div>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const BASE = import.meta.env.BASE_URL;

// חשוב: אצלך הקובץ בשורש של ה-Repo, אז אנחנו מנסים קודם את השורש ואז data/
function buildingsCandidates() {
  const ts = Date.now();
  return [
    `${BASE}buildings_joined.geojson?ts=${ts}`,        // <-- זה הנתיב שמתאים לקובץ אצלך
    `${BASE}data/buildings_joined.geojson?ts=${ts}`,   // fallback אם תשים בעתיד בתוך data/
    // fallback אחרון: raw מגיטהאב (רק אם הקובץ לא באמת עולה בפריסה)
    `https://raw.githubusercontent.com/ShakkedG/SatMap/main/buildings_joined.geojson?ts=${ts}`,
  ];
}

/** UI */
const basemap = ref("esri");
const loadMsg = ref("");
const loadErr = ref("");
const loadedFrom = ref("");

const showSinking = ref(true);
const showStable = ref(true);
const showLowQ = ref(true);
const showNoData = ref(false);

const q = ref("");
const minCoh = ref(0.35);

const stats = ref({ total: 0, sinking: 0, stable: 0, lowq: 0, noData: 0 });
const selected = ref(null);

/** Leaflet */
let map = null;
let osmLayer = null;
let esriLayer = null;

let sinkingGroup = null;
let stableGroup = null;
let lowqGroup = null;
let noDataGroup = null;

let allBounds = null;
const allBoundsValid = ref(false);

const rows = ref([]); // for list/search

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmt2(n) {
  return n == null ? "—" : Number(n).toFixed(2);
}

function pickField(props, candidates) {
  if (!props) return "";
  for (const k of candidates) {
    if (Object.prototype.hasOwnProperty.call(props, k)) return k;
  }
  const keys = Object.keys(props);
  const lower = new Map(keys.map(k => [k.toLowerCase(), k]));
  for (const c of candidates) {
    const real = lower.get(String(c).toLowerCase());
    if (real) return real;
  }
  return "";
}

function normalizeStatus(raw) {
  const s = String(raw ?? "").trim().toLowerCase();
  if (!s) return "no_data";
  if (s.includes("suspected") || s.includes("sink")) return "suspected_subsidence";
  if (s.includes("stable") || s.includes("uplift")) return "stable";
  if (s.includes("low_quality") || s.includes("low quality") || s.includes("low")) return "low_quality";
  if (s.includes("no_data") || s.includes("nodata") || s === "null") return "no_data";
  return s; // keep original-ish
}

function bucketFromStatus(norm) {
  if (norm === "suspected_subsidence" || norm === "sinking") return "sinking";
  if (norm === "stable") return "stable";
  if (norm === "low_quality") return "lowq";
  return "nodata";
}

function styleFor(bucket) {
  if (bucket === "sinking") {
    return { color: "#b91c1c", weight: 2.4, opacity: 0.95, fill: true, fillColor: "#ef4444", fillOpacity: 0.45 };
  }
  if (bucket === "stable") {
    return { color: "#1d4ed8", weight: 2.0, opacity: 0.9, fill: true, fillColor: "#60a5fa", fillOpacity: 0.25 };
  }
  if (bucket === "lowq") {
    return { color: "#b45309", weight: 2.0, opacity: 0.9, fill: true, fillColor: "#f59e0b", fillOpacity: 0.20, dashArray: "5 4" };
  }
  return { color: "#64748b", weight: 2.0, opacity: 0.85, fill: true, fillColor: "#cbd5e1", fillOpacity: 0.18, dashArray: "6 6" };
}

function applyHover(pathLayer, baseStyle) {
  pathLayer.on("mouseover", () => {
    try {
      pathLayer.setStyle?.({
        weight: Math.max(3, (baseStyle?.weight ?? 2) + 1),
        opacity: 1,
        fillOpacity: Math.min(0.85, (baseStyle?.fillOpacity ?? 0.25) + 0.15),
      });
      pathLayer.bringToFront?.();
    } catch {}
  });
  pathLayer.on("mouseout", () => {
    try { pathLayer.setStyle?.(baseStyle); } catch {}
  });
}

function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, preferCanvas: true }).setView([32.08, 34.78], 12);

  osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19, maxZoom: 22, attribution: "&copy; OpenStreetMap",
  });

  esriLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 22, attribution: "&copy; Esri" }
  );

  applyBasemap();

  sinkingGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup().addTo(map);
  lowqGroup = new L.FeatureGroup().addTo(map);
  noDataGroup = new L.FeatureGroup().addTo(map);
}

function applyBasemap() {
  if (!map) return;
  [osmLayer, esriLayer].forEach(l => { if (l && map.hasLayer(l)) map.removeLayer(l); });
  (basemap.value === "osm" ? osmLayer : esriLayer)?.addTo(map);
}

function applyVisibility() {
  if (!map) return;

  const ensure = (layer, on) => {
    if (!layer) return;
    if (on) { if (!map.hasLayer(layer)) layer.addTo(map); }
    else { if (map.hasLayer(layer)) map.removeLayer(layer); }
  };

  ensure(sinkingGroup, showSinking.value);
  ensure(stableGroup, showStable.value);
  ensure(lowqGroup, showLowQ.value);
  ensure(noDataGroup, showNoData.value);
}

function fitToLayer() {
  if (allBounds?.isValid?.()) {
    try { map.fitBounds(allBounds.pad(0.08)); } catch {}
  }
}

function clearSelection() { selected.value = null; }

async function fetchFirstOk(urls) {
  let lastErr = "";
  for (const url of urls) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) { lastErr = `HTTP ${r.status} (${url})`; continue; }
      const j = await r.json();
      return { url, json: j };
    } catch (e) {
      lastErr = String(e);
    }
  }
  throw new Error(lastErr || "Failed to load GeoJSON");
}

function pickName(props, idx) {
  const f = pickField(props, ["name","NAME","building_id","id","OBJECTID","objectid","UNIQ_ID","uniq_id"]);
  if (f) return String(props[f]);
  return `בניין ${idx + 1}`;
}

async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען GeoJSON…";
  loadedFrom.value = "";
  clearSelection();

  rows.value = [];
  sinkingGroup?.clearLayers?.();
  stableGroup?.clearLayers?.();
  lowqGroup?.clearLayers?.();
  noDataGroup?.clearLayers?.();

  allBounds = null;
  allBoundsValid.value = false;

  try {
    const { url, json } = await fetchFirstOk(buildingsCandidates());
    loadedFrom.value = url;

    const feats = Array.isArray(json?.features) ? json.features : [];
    let sinking = 0, stable = 0, lowq = 0, noData = 0;

    for (let i = 0; i < feats.length; i++) {
      const f = feats[i];
      const props = f?.properties || {};
      const geom = f?.geometry;

      const statusField = pickField(props, ["status","Status","STATUS"]);
      const velMeanField = pickField(props, ["Vel_mean","vel_mean","VEL_MEAN"]);
      const velCountField = pickField(props, ["Vel_count","vel_count","VEL_COUNT"]);
      const cohMeanField = pickField(props, ["coer_mean","Coer_mean","COER_MEAN","coh_mean","Coh_mean"]);

      const rawStatus = statusField ? props[statusField] : "";
      const normStatus = normalizeStatus(rawStatus);
      const bucket = bucketFromStatus(normStatus);

      if (bucket === "sinking") sinking++;
      else if (bucket === "stable") stable++;
      else if (bucket === "lowq") lowq++;
      else noData++;

      const name = pickName(props, i);
      const velMean = velMeanField ? toNum(props[velMeanField]) : null;
      const velCount = velCountField ? toNum(props[velCountField]) : null;
      const cohMean = cohMeanField ? toNum(props[cohMeanField]) : null;

      const baseStyle = styleFor(bucket);

      const layer = L.geoJSON(f, {
        style: baseStyle,
        onEachFeature: (_feat, pathLayer) => {
          applyHover(pathLayer, baseStyle);

          const tt = [
            `status: ${normStatus || "—"}`,
            `Vel_mean: ${fmt2(velMean)}`,
            `coer_mean: ${fmt2(cohMean)}`,
            `Vel_count: ${velCount ?? "—"}`
          ].join(" | ");

          pathLayer.bindTooltip(tt, { sticky: true, direction: "top", opacity: 0.95 });

          pathLayer.on("click", () => {
            selected.value = {
              name,
              status: normStatus || "—",
              velMean: fmt2(velMean),
              cohMean: fmt2(cohMean),
              velCount: velCount ?? "—",
            };
          });
        },
      });

      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) allBounds = allBounds ? allBounds.extend(b) : b;
      } catch {}

      if (bucket === "sinking") layer.addTo(sinkingGroup);
      else if (bucket === "stable") layer.addTo(stableGroup);
      else if (bucket === "lowq") layer.addTo(lowqGroup);
      else layer.addTo(noDataGroup);

      rows.value.push({
        key: `${i}-${name}`,
        name,
        status: normStatus || "—",
        bucket,
        velMean,
        cohMean,
        velCount,
        bounds: (() => { try { return layer.getBounds(); } catch { return null; } })(),
      });
    }

    stats.value = { total: feats.length, sinking, stable, lowq, noData };

    allBoundsValid.value = !!allBounds?.isValid?.();
    if (allBoundsValid.value) {
      try { map.fitBounds(allBounds.pad(0.08)); } catch {}
    }

    applyVisibility();
    loadMsg.value = `נטענו ${feats.length} בניינים`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, sinking: 0, stable: 0, lowq: 0, noData: 0 };
  }
}

function zoomToRow(r) {
  try {
    if (r?.bounds?.isValid?.()) map.fitBounds(r.bounds.pad(0.15));
  } catch {}
  selected.value = {
    name: r.name,
    status: r.status,
    velMean: fmt2(r.velMean),
    cohMean: fmt2(r.cohMean),
    velCount: r.velCount ?? "—",
  };
}

function reload() { loadAndRender(); }

const suspectsList = computed(() => {
  const needle = (q.value || "").trim().toLowerCase();

  return rows.value
    .filter(r => r.bucket === "sinking")
    .filter(r => (r.cohMean ?? 0) >= (minCoh.value ?? 0))
    .filter(r => !needle || String(r.name).toLowerCase().includes(needle) || String(r.name).includes(needle))
    .sort((a, b) => (a.velMean ?? Infinity) - (b.velMean ?? Infinity)) // הכי שלילי ראשון
    .slice(0, 40)
    .map(r => ({
      ...r,
      velLabel: fmt2(r.velMean),
      cohLabel: fmt2(r.cohMean),
      countLabel: r.velCount ?? "—",
    }));
});

onMounted(async () => {
  initMap();
  await loadAndRender();
});
</script>

<style>
.layout { display:grid; grid-template-columns: 460px 1fr; height:100vh; background:#f3f4f6; font-family:system-ui, Arial; }
.panel { background:#fff; border-left:1px solid #e5e7eb; padding:12px; overflow:auto; }
.mapWrap { position:relative; }
#map { width:100%; height:100vh; }

.top { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:10px; }
.topBtns { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.title { font-weight:900; font-size:18px; }
.sub { font-size:12px; opacity:0.72; margin-top:2px; }

.box { border:1px solid #e5e7eb; border-radius:16px; padding:10px; background:#fff; margin-bottom:10px; }
label { display:block; font-size:12px; opacity:0.85; margin-bottom:6px; }

input, select { width:100%; padding:10px; border-radius:12px; border:1px solid #e5e7eb; font-size:14px; background:#fff; }
select { cursor:pointer; }

.btn { cursor:pointer; background:#111827; color:#fff; border:1px solid #111827; font-weight:700; padding:10px; border-radius:12px; width:auto; }
.btn.ghost { background:#fff; color:#111827; border-color:#e5e7eb; }
.btn.small { padding:8px 10px; font-size:12px; border-radius:10px; }
.btn:disabled { opacity:0.55; cursor:not-allowed; }

.row2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:6px; }
.chk { display:flex; align-items:center; gap:8px; font-size:12px; opacity:0.9; margin-top:8px; }
.chk input[type="checkbox"] { width:auto; padding:0; margin:0; }

.kpis { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:10px; }
.kpi { border:1px solid #e5e7eb; border-radius:12px; padding:10px; background:#f9fafb; }
.kpi .k { font-size:12px; opacity:0.7; }
.kpi .v { font-weight:900; font-size:18px; }
.kpi.sink { border-color:#fecaca; background:#fef2f2; }
.kpi.stable { border-color:#bfdbfe; background:#eff6ff; }
.kpi.lowq { border-color:#fed7aa; background:#fff7ed; }
.kpi.nodata { border-color:#e2e8f0; background:#f8fafc; }

.legend { margin-top:10px; border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; display:grid; gap:6px; }
.legRow { display:flex; align-items:center; gap:10px; font-size:12px; opacity:0.92; }
.sw { width:18px; height:10px; border-radius:4px; border:1px solid #e5e7eb; }
.sw-sink { background:#fee2e2; border-color:#b91c1c; }
.sw-stable { background:#dbeafe; border-color:#1d4ed8; }
.sw-lowq { background:#fff7ed; border-color:#b45309; }
.sw-nodata { background:#e2e8f0; border-color:#64748b; }

.selHeader { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
.selGrid { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px; }
.selCard { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#f9fafb; }
.selCard .k { font-size:12px; opacity:0.7; }
.selCard .v { font-weight:900; font-size:14px; margin-top:4px; }

.mini { font-size:12px; opacity:0.92; margin-top:8px; }
.muted { opacity:0.72; }
.err { color:#b91c1c; opacity:1; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.mono.smallLine { font-size:12px; opacity:0.9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

.sumTitle { cursor:pointer; font-weight:900; list-style:none; user-select:none; }
details > summary::-webkit-details-marker { display:none; }

/* List */
.list { display:grid; gap:8px; margin-top:10px; }
.listItem { text-align:right; border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; cursor:pointer; }
.listItem:hover { border-color:#cbd5e1; background:#f8fafc; }
.liTop { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.liName { font-weight:900; font-size:13px; }
.liMeta { margin-top:6px; font-size:12px; opacity:0.85; display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.dot { opacity:0.55; }
.badge { font-size:11px; font-weight:900; padding:4px 8px; border-radius:999px; border:1px solid #e5e7eb; background:#f8fafc; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 54vh; border-left:none; border-bottom:1px solid #e5e7eb; }
  #map { height: 46vh; }
}
</style>

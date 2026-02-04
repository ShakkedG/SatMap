<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Prototype – Buildings Joined (GeoJSON) → Status / Vel_mean / coer_mean / Vel_count</div>
        </div>
        <div class="topBtns">
          <button class="btn ghost" @click="fitAll" :disabled="!allBoundsValid">התמקד בשכבה</button>
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
            <label>מקור סטטוס</label>
            <select v-model="statusMode" @change="scheduleRender">
              <option value="geojson">לפי שדה status מהקובץ</option>
              <option value="compute">חשב באתר לפי ספים</option>
            </select>
            <div class="hint">
              נטען מ־<span class="mono">{{ buildingsUrl }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="box">
        <div class="kpis">
          <div class="kpi"><div class="k">סה״כ</div><div class="v">{{ stats.total }}</div></div>
          <div class="kpi sink"><div class="k">חשוד/שוקע</div><div class="v">{{ stats.suspected }}</div></div>
          <div class="kpi stable"><div class="k">יציב</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi lowq"><div class="k">איכות נמוכה</div><div class="v">{{ stats.lowq }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.nodata }}</div></div>
        </div>

        <div v-if="loadMsg" class="mini muted">{{ loadMsg }}</div>
        <div v-if="loadErr" class="mini err">{{ loadErr }}</div>
      </div>

      <details class="box" open>
        <summary class="sumTitle">סינון + איתור מהיר</summary>

        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showStable" @change="applyVisibility" />
            להציג יציב
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showNoData" @change="applyVisibility" />
            להציג אין נתון
          </label>
        </div>

        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showLowQ" @change="applyVisibility" />
            להציג איכות נמוכה
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showSuspected" @change="applyVisibility" />
            להציג חשוד/שוקע
          </label>
        </div>

        <div class="row2" style="margin-top:10px">
          <div>
            <label>חיפוש (OBJECTID / שם)</label>
            <input v-model="q" placeholder="לדוגמה: 188" />
          </div>
          <div>
            <label>מיון</label>
            <select v-model="sortBy">
              <option value="vel">Vel_mean (הכי שלילי קודם)</option>
              <option value="coh">coer_mean (הכי גבוה קודם)</option>
              <option value="pts">Vel_count (הכי גבוה קודם)</option>
            </select>
          </div>
        </div>

        <div class="box2" v-if="statusMode === 'compute'">
          <div class="mini muted" style="margin-bottom:8px">
            מצב “חשב באתר” (מומלץ אם ה-status בקובץ יצא לך לא נכון).
          </div>

          <div class="row2">
            <div>
              <label>סף שקיעה (Vel_mean ≤)</label>
              <input type="number" v-model.number="velThreshold" step="0.5" />
              <div class="hint">אם הערכים אצלך חיוביים/הפוכים – נסה “היפוך סימן”.</div>
            </div>
            <div>
              <label class="chk" style="margin-top:24px">
                <input type="checkbox" v-model="flipVelSign" @change="scheduleRender" />
                היפוך סימן ל-Vel_mean
              </label>
            </div>
          </div>

          <div class="row2">
            <div>
              <label>מינימום נק׳ (Vel_count ≥)</label>
              <input type="number" v-model.number="minPoints" step="1" min="0" />
            </div>
            <div>
              <label>מינימום קוהרנס (coer_mean ≥)</label>
              <input type="number" v-model.number="minCoh" step="0.05" min="0" max="1" />
            </div>
          </div>
        </div>

        <div class="mini muted" style="margin-top:10px">
          רשימת “חשודים” (לחיצה = זום + בחירה)
        </div>

        <div class="list">
          <button
            v-for="b in suspectedList"
            :key="b.key"
            class="listItem"
            @click="zoomToItem(b)"
          >
            <div class="liTop">
              <div class="liName">{{ b.name }}</div>
              <div class="badge bSus">חשוד</div>
            </div>
            <div class="liMeta">
              <span class="mono">Vel {{ b.velLabel }}</span>
              <span class="dot">•</span>
              <span class="mono">pts {{ b.ptsLabel }}</span>
              <span class="dot">•</span>
              <span class="mono">coh {{ b.cohLabel }}</span>
            </div>
          </button>

          <div v-if="!suspectedList.length" class="mini muted" style="margin-top:10px">
            אין תוצאות כרגע (נסה לשנות ספים/להציג עוד קטגוריות).
          </div>
        </div>
      </details>

      <div class="box" v-if="selected">
        <div class="selHeader">
          <div class="mini"><b>{{ selected.title }}</b></div>
          <button class="btn ghost small" @click="clearSelection">נקה</button>
        </div>

        <div class="selGrid">
          <div class="selCard">
            <div class="k">סטטוס</div>
            <div class="v" :class="{ danger: selected.status === 'suspected' }">{{ selected.statusLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">OBJECTID</div>
            <div class="v mono">{{ selected.objectId }}</div>
          </div>

          <div class="selCard">
            <div class="k">Vel_mean</div>
            <div class="v mono">{{ selected.velLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">Vel_count</div>
            <div class="v mono">{{ selected.ptsLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">coer_mean</div>
            <div class="v mono">{{ selected.cohLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">שדות נוספים</div>
            <div class="v" style="font-weight:700;font-size:12px;line-height:1.4">
              {{ selected.extra }}
            </div>
          </div>
        </div>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const BASE = import.meta.env.BASE_URL;

// אם שמת את הקובץ בנתיב אחר – תשנה כאן:
const buildingsUrl = (import.meta.env.VITE_BUILDINGS_URL || `${BASE}data/buildings_joined.geojson`);

/** UI */
const basemap = ref("esri");
const statusMode = ref("geojson"); // "geojson" | "compute"

const showStable = ref(true);
const showNoData = ref(false);
const showLowQ = ref(true);
const showSuspected = ref(true);

const q = ref("");
const sortBy = ref("vel");

/** Compute mode thresholds */
const velThreshold = ref(-2);
const minPoints = ref(3);
const minCoh = ref(0.35);
const flipVelSign = ref(false);

const loadMsg = ref("");
const loadErr = ref("");

const stats = ref({ total: 0, suspected: 0, stable: 0, lowq: 0, nodata: 0 });
const selected = ref(null);

/** Leaflet */
let map = null;
let osmLayer = null;
let esriLayer = null;

let gSuspected = null;
let gStable = null;
let gLowQ = null;
let gNoData = null;

let allBounds = null;
const allBoundsValid = ref(false);

/** cache for list */
const rows = ref([]); // [{ key, name, objectId, vel, pts, coh, status, bounds, props, feature }]

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmt(n, d=2) {
  return n == null ? "—" : Number(n).toFixed(d);
}
function pickFirst(props, keys) {
  for (const k of keys) {
    if (props && props[k] != null && String(props[k]).trim() !== "") return props[k];
  }
  return null;
}

/** Status mapping */
function normalizeStatus(raw) {
  const s = String(raw ?? "").toLowerCase().trim();
  if (!s) return "nodata";

  if (["suspected_subsidence","suspected","sinking","sink"].includes(s)) return "suspected";
  if (["stable","ok"].includes(s)) return "stable";
  if (["low_quality","lowq","bad_quality"].includes(s)) return "lowq";
  if (["no_data","nodata","no data","null"].includes(s)) return "nodata";

  // fallback:
  return "nodata";
}

function computeStatusFromProps(props) {
  // expected fields from your joined layer:
  const vel0 = toNum(props?.Vel_mean ?? props?.vel_mean ?? props?.VEL_MEAN);
  const pts  = toNum(props?.Vel_count ?? props?.vel_count ?? props?.VEL_COUNT);
  const coh  = toNum(props?.coer_mean ?? props?.Coer_mean ?? props?.COER_MEAN ?? props?.coh_mean);

  const vel = vel0 == null ? null : (flipVelSign.value ? -vel0 : vel0);

  // “no data”
  if (pts == null || pts < (minPoints.value ?? 0)) return { status: "nodata", vel, pts, coh };
  // “low quality”
  if (coh == null || coh < (minCoh.value ?? 0)) return { status: "lowq", vel, pts, coh };
  // suspected subsidence
  if (vel != null && vel <= (velThreshold.value ?? -2)) return { status: "suspected", vel, pts, coh };
  return { status: "stable", vel, pts, coh };
}

function statusLabel(s) {
  if (s === "suspected") return "חשוד/שוקע";
  if (s === "stable") return "יציב";
  if (s === "lowq") return "איכות נמוכה";
  return "אין נתון";
}

function styleFor(status) {
  if (status === "suspected") return { color: "#b91c1c", weight: 2.2, opacity: 0.95, fill: true, fillColor: "#ef4444", fillOpacity: 0.40 };
  if (status === "stable")    return { color: "#1e293b", weight: 2.0, opacity: 0.85, fill: true, fillColor: "#60a5fa", fillOpacity: 0.22 };
  if (status === "lowq")      return { color: "#92400e", weight: 2.0, opacity: 0.90, fill: true, fillColor: "#fb923c", fillOpacity: 0.25, dashArray: "6 6" };
  return { color: "#64748b", weight: 2.0, opacity: 0.85, fill: true, fillColor: "#cbd5e1", fillOpacity: 0.18, dashArray: "4 6" };
}

function buildSelected(feature, derived) {
  const props = feature?.properties || {};
  const objectId = pickFirst(props, ["OBJECTID","objectid","id","Id"]) ?? "—";

  const title =
    pickFirst(props, ["FNAME","NAME","name","LATIN_NAME","ADDR_ID","UNIQ_ID"]) ??
    `בניין ${objectId}`;

  const vel = derived?.vel ?? toNum(props?.Vel_mean ?? props?.vel_mean);
  const pts = derived?.pts ?? toNum(props?.Vel_count ?? props?.vel_count);
  const coh = derived?.coh ?? toNum(props?.coer_mean ?? props?.COER_MEAN ?? props?.coh_mean);

  // show a small extra summary of other fields (first ~6 keys)
  const keys = Object.keys(props || {});
  const extras = [];
  for (const k of keys) {
    if (["status","Vel_mean","Vel_count","coer_mean","OBJECTID"].includes(k)) continue;
    const v = props[k];
    if (v == null || String(v).trim() === "") continue;
    extras.push(`${k}: ${v}`);
    if (extras.length >= 6) break;
  }

  return {
    title,
    objectId,
    status: derived?.status ?? normalizeStatus(props.status),
    statusLabel: statusLabel(derived?.status ?? normalizeStatus(props.status)),
    velLabel: fmt(vel, 3),
    ptsLabel: pts == null ? "—" : String(Math.round(pts)),
    cohLabel: coh == null ? "—" : fmt(coh, 3),
    extra: extras.length ? extras.join(" | ") : "—",
  };
}

/** Map init */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, preferCanvas: true }).setView([32.08, 34.78], 13);

  osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19, maxZoom: 22, attribution: "&copy; OpenStreetMap",
  });

  esriLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 22, attribution: "&copy; Esri" }
  );

  applyBasemap();

  gSuspected = new L.FeatureGroup().addTo(map);
  gStable    = new L.FeatureGroup().addTo(map);
  gLowQ      = new L.FeatureGroup().addTo(map);
  gNoData    = new L.FeatureGroup().addTo(map);
}

function applyBasemap() {
  if (!map) return;
  [osmLayer, esriLayer].forEach(l => { if (l && map.hasLayer(l)) map.removeLayer(l); });
  (basemap.value === "osm" ? osmLayer : esriLayer).addTo(map);
}

function applyVisibility() {
  if (!map) return;

  if (showSuspected.value) { if (!map.hasLayer(gSuspected)) gSuspected.addTo(map); }
  else { if (map.hasLayer(gSuspected)) map.removeLayer(gSuspected); }

  if (showStable.value) { if (!map.hasLayer(gStable)) gStable.addTo(map); }
  else { if (map.hasLayer(gStable)) map.removeLayer(gStable); }

  if (showLowQ.value) { if (!map.hasLayer(gLowQ)) gLowQ.addTo(map); }
  else { if (map.hasLayer(gLowQ)) map.removeLayer(gLowQ); }

  if (showNoData.value) { if (!map.hasLayer(gNoData)) gNoData.addTo(map); }
  else { if (map.hasLayer(gNoData)) map.removeLayer(gNoData); }
}

function clearSelection() {
  selected.value = null;
}

function fitAll() {
  if (allBounds?.isValid?.()) {
    try { map.fitBounds(allBounds.pad(0.08)); } catch {}
  }
}

/** Load + render */
async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען GeoJSON…";
  clearSelection();
  rows.value = [];

  gSuspected?.clearLayers?.();
  gStable?.clearLayers?.();
  gLowQ?.clearLayers?.();
  gNoData?.clearLayers?.();

  allBounds = null;
  allBoundsValid.value = false;

  try {
    const r = await fetch(buildingsUrl, { cache: "no-store" });
    if (!r.ok) throw new Error(`GeoJSON HTTP ${r.status}`);
    const gj = await r.json();
    const feats = Array.isArray(gj?.features) ? gj.features : [];

    let cSus = 0, cSt = 0, cLq = 0, cNd = 0;

    for (let i=0; i<feats.length; i++) {
      const f = feats[i];
      const props = f?.properties || {};
      const geom = f?.geometry;

      // derive status + key metrics
      let derived = null;
      if (statusMode.value === "compute") derived = computeStatusFromProps(props);

      const status =
        statusMode.value === "compute"
          ? derived.status
          : normalizeStatus(props.status);

      const objectId = pickFirst(props, ["OBJECTID","objectid","id","Id"]) ?? i + 1;
      const name =
        pickFirst(props, ["FNAME","NAME","name","LATIN_NAME","ADDR_ID","UNIQ_ID"]) ??
        `בניין ${objectId}`;

      const st = styleFor(status);

      const layer = L.geoJSON(f, {
        style: st,
        onEachFeature: (feat, pathLayer) => {
          pathLayer.bindTooltip(
            `סטטוס: ${statusLabel(status)} | Vel_mean: ${fmt(derived?.vel ?? toNum(props?.Vel_mean), 3)} | pts: ${derived?.pts ?? props?.Vel_count ?? "—"} | coh: ${fmt(derived?.coh ?? toNum(props?.coer_mean), 3)}`,
            { sticky: true, direction: "top", opacity: 0.95 }
          );

          pathLayer.on("click", () => {
            selected.value = buildSelected(f, derived);
          });

          pathLayer.on("mouseover", () => {
            try {
              pathLayer.setStyle?.({ weight: (st.weight ?? 2) + 1, opacity: 1, fillOpacity: Math.min(0.85, (st.fillOpacity ?? 0.25) + 0.15) });
              pathLayer.bringToFront?.();
            } catch {}
          });
          pathLayer.on("mouseout", () => {
            try { pathLayer.setStyle?.(st); } catch {}
          });
        }
      });

      let bounds = null;
      try {
        bounds = layer.getBounds();
        if (bounds?.isValid?.()) allBounds = allBounds ? allBounds.extend(bounds) : bounds;
      } catch {}

      // count + add to group
      if (status === "suspected") { cSus++; layer.addTo(gSuspected); }
      else if (status === "stable") { cSt++; layer.addTo(gStable); }
      else if (status === "lowq") { cLq++; layer.addTo(gLowQ); }
      else { cNd++; layer.addTo(gNoData); }

      const vel = derived?.vel ?? toNum(props?.Vel_mean ?? props?.vel_mean);
      const pts = derived?.pts ?? toNum(props?.Vel_count ?? props?.vel_count);
      const coh = derived?.coh ?? toNum(props?.coer_mean ?? props?.coh_mean);

      rows.value.push({
        key: `${objectId}-${i}`,
        name,
        objectId,
        vel,
        pts,
        coh,
        status,
        bounds,
        props,
        feature: f,
        derived,
      });
    }

    stats.value = { total: feats.length, suspected: cSus, stable: cSt, lowq: cLq, nodata: cNd };

    allBoundsValid.value = !!allBounds?.isValid?.();
    if (allBoundsValid.value) {
      try { map.fitBounds(allBounds.pad(0.08)); } catch {}
    }

    applyVisibility();
    loadMsg.value = `נטענו ${feats.length} בניינים`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, suspected: 0, stable: 0, lowq: 0, nodata: 0 };
  }
}

function reload() {
  loadAndRender();
}

function zoomToItem(item) {
  try {
    if (item?.bounds?.isValid?.()) map.fitBounds(item.bounds.pad(0.15));
  } catch {}
  selected.value = buildSelected(item.feature, item.derived);
}

/** list */
const suspectedList = computed(() => {
  const needle = (q.value || "").trim().toLowerCase();

  let list = rows.value.filter(r => r.status === "suspected");

  if (needle) {
    list = list.filter(r =>
      String(r.objectId).toLowerCase().includes(needle) ||
      String(r.name).toLowerCase().includes(needle)
    );
  }

  const k = sortBy.value;
  list.sort((a,b) => {
    if (k === "coh") return (b.coh ?? -Infinity) - (a.coh ?? -Infinity);
    if (k === "pts") return (b.pts ?? -Infinity) - (a.pts ?? -Infinity);
    // vel: most negative first
    return (a.vel ?? Infinity) - (b.vel ?? Infinity);
  });

  return list.slice(0, 60).map(r => ({
    ...r,
    velLabel: fmt(r.vel, 3),
    ptsLabel: r.pts == null ? "—" : String(Math.round(r.pts)),
    cohLabel: fmt(r.coh, 3),
  }));
});

/** re-render debounce */
let t = null;
function scheduleRender() {
  if (t) clearTimeout(t);
  t = setTimeout(() => loadAndRender(), 200);
}

watch([velThreshold, minPoints, minCoh, flipVelSign], () => {
  if (statusMode.value === "compute") scheduleRender();
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
.box2 { border:1px dashed #e5e7eb; border-radius:16px; padding:10px; background:#fafafa; margin-top:10px; }

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

.kpis { display:grid; grid-template-columns: 1fr 1fr; gap:8px; }
.kpi { border:1px solid #e5e7eb; border-radius:12px; padding:10px; background:#f9fafb; }
.kpi .k { font-size:12px; opacity:0.7; }
.kpi .v { font-weight:900; font-size:18px; }
.kpi.sink { border-color:#fecaca; background:#fef2f2; }
.kpi.stable { border-color:#bfdbfe; background:#eff6ff; }
.kpi.lowq { border-color:#fed7aa; background:#fff7ed; }
.kpi.nodata { border-color:#e2e8f0; background:#f8fafc; }

.selHeader { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
.selGrid { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px; }
.selCard { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#f9fafb; }
.selCard .k { font-size:12px; opacity:0.7; }
.selCard .v { font-weight:900; font-size:14px; margin-top:4px; }
.selCard .v.danger { color:#991b1b; }

.mini { font-size:12px; opacity:0.92; margin-top:8px; }
.muted { opacity:0.72; }
.err { color:#b91c1c; opacity:1; }
.hint { font-size:11px; opacity:0.7; margin-top:6px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

.sumTitle { cursor:pointer; font-weight:900; list-style:none; user-select:none; }
details > summary::-webkit-details-marker { display:none; }

.list { display:grid; gap:8px; margin-top:10px; }
.listItem { text-align:right; border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; cursor:pointer; }
.listItem:hover { border-color:#cbd5e1; background:#f8fafc; }
.liTop { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.liName { font-weight:900; font-size:13px; }
.liMeta { margin-top:6px; font-size:12px; opacity:0.85; display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.dot { opacity:0.55; }
.badge { font-size:11px; font-weight:900; padding:4px 8px; border-radius:999px; border:1px solid #e5e7eb; }
.bSus { background:#fef2f2; border-color:#fecaca; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 54vh; border-left:none; border-bottom:1px solid #e5e7eb; }
  #map { height: 46vh; }
}
</style>

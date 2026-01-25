<template>
  <div class="wrap" dir="rtl">
    <aside class="panel">
      <div class="head">
        <div>
          <h3>SatMap – Sentinel-1 (ASF Search)</h3>
          <div class="small">
            מציירים AOI על המפה (מלבן/פוליגון), בוחרים תאריכים ולוחצים “חפש”.
            <br />
            התוצאות מוצגות גם כרשימה וגם כ-Footprints על המפה.
          </div>
        </div>

        <button class="btnGhost" @click="togglePanelMobile" title="סגור/פתח">
          ☰
        </button>
      </div>

      <div class="row grid2">
        <div>
          <label>התחלה</label>
          <input type="date" v-model="start" />
        </div>
        <div>
          <label>סוף</label>
          <input type="date" v-model="end" />
        </div>
      </div>

      <div class="row grid2">
        <div>
          <label>כיוון מסלול</label>
          <select v-model="flightDirection">
            <option value="">ללא</option>
            <option value="ASCENDING">עולה</option>
            <option value="DESCENDING">יורד</option>
          </select>
        </div>
        <div>
          <label>מקסימום תוצאות להצגה</label>
          <select v-model.number="limit">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>

      <div class="row grid2">
        <button @click="resetIsraelAOI" class="btnGhost">Reset לישראל</button>
        <button @click="clearAOI" class="btnGhost">נקה AOI</button>
      </div>

      <div class="row">
        <button class="btnPrimary" @click="doSearch" :disabled="busy">
          {{ busy ? "מחפש…" : "חפש סצנות" }}
        </button>
      </div>

      <div class="row grid2">
        <div>
          <label>סינון לפי ID</label>
          <input v-model="q" placeholder="חפש בתוך התוצאות…" />
        </div>
        <div class="toggleBox">
          <label class="chk">
            <input type="checkbox" v-model="showFootprints" @change="applyFootprintsVisibility" />
            להציג Footprints
          </label>
        </div>
      </div>

      <div class="row actions">
        <button class="btnGhost" @click="downloadGeoJSON" :disabled="!features.length">
          הורד GeoJSON
        </button>
        <button class="btnGhost" @click="downloadCSV" :disabled="!features.length">
          הורד CSV
        </button>
      </div>

      <div class="row">
        <div class="small">
          תוצאות: <b>{{ filtered.length }}</b> (מציג {{ shown.length }}).
        </div>

        <div class="list">
          <button
            class="card"
            v-for="r in shown"
            :key="r.key"
            :class="{ active: r.key === selectedKey }"
            @click="focusResult(r.key)"
            title="Zoom + הדגשה במפה"
          >
            <div class="mono line">
              <span class="ell">{{ r.gid }}</span>
              <span class="pill" v-if="r.flightDirection">{{ r.flightDirection }}</span>
            </div>
            <div class="small line">
              <span>{{ formatTime(r.time) }}</span>
              <span class="muted" v-if="r.relativeOrbit"> | מסלול: {{ r.relativeOrbit }}</span>
            </div>
          </button>
        </div>
      </div>
      <div class="row grid2">
  <div>
    <label>GovMap X</label>
    <input v-model="govX" placeholder="למשל 220000 או lon" />
  </div>
  <div>
    <label>GovMap Y</label>
    <input v-model="govY" placeholder="למשל 630000 או lat" />
  </div>
</div>

<div class="row grid2">
  <button class="btnGhost" @click="useGovmapPoint">המר לנקודה (WGS84)</button>
  <button class="btnGhost" @click="clearGovmapPoint">נקה נקודה</button>
</div>

<div class="small" v-if="govPoint">
  נקודה: {{ govPoint.lat.toFixed(6) }}, {{ govPoint.lng.toFixed(6) }} (מקור {{ govPoint.crs }})
</div>


      <div class="row">
        <div class="small">סטטוס</div>
        <pre class="status">{{ status }}</pre>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
  import { govmapXYToWgs84, bufferPointToWktRect } from "./utils/govmapCrs.js";
import { computed, onMounted, ref } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";

const start = ref(daysAgoISO(60));
const end = ref(todayISO());
const flightDirection = ref("");

const status = ref("—");
const busy = ref(false);

const q = ref("");
const limit = ref(50);
const showFootprints = ref(true);

const features = ref([]); // raw GeoJSON features
const selectedKey = ref("");
const govX = ref("");
const govY = ref("");
const govPoint = ref(null);

let govMarker = null;
let map, drawn, footprintsGroup;
const footprintLayers = new Map(); // key -> leaflet layer

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoISO(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function formatTime(t) {
  if (!t) return "";
  try {
    const d = new Date(t);
    return d.toLocaleString("he-IL");
  } catch {
    return String(t);
  }
}
function useGovmapPoint() {
  try {
    const p = govmapXYToWgs84(govX.value, govY.value);
    govPoint.value = p;

    // שים סמן במפה
    if (govMarker) {
      govMarker.remove();
      govMarker = null;
    }
    govMarker = L.marker([p.lat, p.lng]).addTo(map);
    map.setView([p.lat, p.lng], Math.max(map.getZoom(), 14));

    status.value = `המרה הצליחה: ${p.lat.toFixed(6)}, ${p.lng.toFixed(6)} (מקור ${p.crs})`;
  } catch (e) {
    status.value = `שגיאה בהמרת GovMap: ${String(e)}`;
  }
}

function clearGovmapPoint() {
  govPoint.value = null;
  govX.value = "";
  govY.value = "";
  if (govMarker) {
    govMarker.remove();
    govMarker = null;
  }
}
function initMap() {
  map = L.map("map", { zoomControl: true }).setView([31.5, 35.0], 7);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  drawn = new L.FeatureGroup().addTo(map);

  footprintsGroup = new L.FeatureGroup().addTo(map);

  // AOI ברירת מחדל סביב ישראל
  resetIsraelAOI();

  const drawControl = new L.Control.Draw({
    draw: { polyline: false, circle: false, marker: false, circlemarker: false },
    edit: { featureGroup: drawn },
  });
  map.addControl(drawControl);

  map.on(L.Draw.Event.CREATED, (e) => {
    drawn.clearLayers();
    drawn.addLayer(e.layer);
  });
}

function resetIsraelAOI() {
  if (!drawn) return;
  drawn.clearLayers();
  const rect = L.rectangle([
    [29.45, 34.2],
    [33.4, 35.95],
  ]);
  drawn.addLayer(rect);
  if (map) map.fitBounds(rect.getBounds(), { padding: [20, 20] });
}

function clearAOI() {
  if (!drawn) return;
  drawn.clearLayers();
}

function layerToWkt(layer) {
  // WKT POLYGON((lon lat, ...)) — lon קודם
  const arr = layer.getLatLngs();
  const ring = Array.isArray(arr[0]) ? arr[0] : arr;
  const pts = ring.map((p) => [p.lng, p.lat]);

  if (pts.length) {
    const [x0, y0] = pts[0];
    const [xn, yn] = pts[pts.length - 1];
    if (x0 !== xn || y0 !== yn) pts.push([x0, y0]);
  }

  const body = pts.map(([x, y]) => `${x} ${y}`).join(",");
  return `POLYGON((${body}))`;
}

function parseTimeMs(feature) {
  const p = feature.properties || {};
  const t = p.startTime || p.start || p.sceneStartTime || p.acquisitionDate;
  return t ? new Date(t).getTime() : 0;
}

function extractGranuleId(feature) {
  const p = feature?.properties || {};
  const candidates = [p.sceneName, p.fileID, p.granuleUR, p.name, p.id].filter(Boolean);
  const re = /^S1[AB]_/;

  for (const c of candidates) if (typeof c === "string" && re.test(c)) return c;
  for (const v of Object.values(p)) if (typeof v === "string" && re.test(v)) return v;

  // fallback קצר
  return p.fileID || p.sceneName || "unknown";
}

const normalized = computed(() => {
  return features.value
    .map((f) => {
      const p = f.properties || {};
      const gid = extractGranuleId(f);
      const time = p.startTime || p.start || "";
      const key = `${gid}__${time || ""}`;
      return {
        key,
        gid,
        time,
        flightDirection: p.flightDirection || "",
        relativeOrbit: p.relativeOrbit || "",
        _feature: f,
      };
    })
    .sort((a, b) => parseTimeMs(b._feature) - parseTimeMs(a._feature));
});

const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase();
  if (!needle) return normalized.value;
  return normalized.value.filter((r) => r.gid.toLowerCase().includes(needle));
});

const shown = computed(() => filtered.value.slice(0, limit.value));

function clearFootprints() {
  footprintsGroup.clearLayers();
  footprintLayers.clear();
  selectedKey.value = "";
}

function applyFootprintsVisibility() {
  if (!map || !footprintsGroup) return;
  if (showFootprints.value) {
    if (!map.hasLayer(footprintsGroup)) footprintsGroup.addTo(map);
  } else {
    if (map.hasLayer(footprintsGroup)) map.removeLayer(footprintsGroup);
  }
}

function addFootprintsToMap(geojsonFeatures) {
  clearFootprints();

  const gj = L.geoJSON(
    { type: "FeatureCollection", features: geojsonFeatures },
    {
      style: () => ({
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.08,
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        const gid = extractGranuleId(feature);
        const time = p.startTime || p.start || "";
        const key = `${gid}__${time || ""}`;

        footprintLayers.set(key, layer);

        layer.on("click", () => {
          setSelected(key);
          const html = `
            <div style="font-family: system-ui; font-size: 12px;">
              <div style="font-weight:700; margin-bottom:6px;">${gid}</div>
              <div>${time ? formatTime(time) : ""}</div>
              <div>${p.flightDirection ? "כיוון: " + p.flightDirection : ""}${p.relativeOrbit ? " | מסלול: " + p.relativeOrbit : ""}</div>
            </div>
          `;
          layer.bindPopup(html).openPopup();
        });
      },
    }
  );

  gj.eachLayer((l) => footprintsGroup.addLayer(l));

  applyFootprintsVisibility();

  // אם יש תוצאות – נתאים זום לגבולות שלהן (רק אם המשתמש לא בזום ממש קרוב)
  if (footprintsGroup.getLayers().length) {
    try {
      const b = footprintsGroup.getBounds();
      if (b.isValid()) map.fitBounds(b, { padding: [20, 20] });
    } catch {}
  }
}

function setSelected(key) {
  // החזרת סגנון קודם
  if (selectedKey.value && footprintLayers.has(selectedKey.value)) {
    const prev = footprintLayers.get(selectedKey.value);
    prev.setStyle({ weight: 2, fillOpacity: 0.08 });
  }
  selectedKey.value = key;
  if (footprintLayers.has(key)) {
    const cur = footprintLayers.get(key);
    cur.setStyle({ weight: 4, fillOpacity: 0.15 });
  }
}

function focusResult(key) {
  setSelected(key);
  const layer = footprintLayers.get(key);
  if (layer) {
    try {
      map.fitBounds(layer.getBounds(), { padding: [20, 20] });
    } catch {}
  }
}

async function doSearch() {
  try {
    busy.value = true;
    features.value = [];
    clearFootprints();
    status.value = "מחפש…";
    const layer = drawn.getLayers()[0];

let wkt = "";
if (layer) {
  wkt = layerToWkt(layer);
} else if (govPoint.value) {
  // אם אין AOI מצויר, נחפש סביב הנקודה (300m)
  wkt = bufferPointToWktRect(govPoint.value.lat, govPoint.value.lng, 300);
} else {
  throw new Error("אין AOI על המפה וגם לא הוזנה נקודת GovMap");
}



    const qs = new URLSearchParams({
      dataset: "SENTINEL-1",
      processingLevel: "SLC",
      intersectsWith: wkt,
      start: start.value,
      end: end.value,
      output: "geojson",
      maxResults: "500",
    });
    if (flightDirection.value) qs.set("flightDirection", flightDirection.value);

    const url = `https://api.daac.asf.alaska.edu/services/search/param?${qs.toString()}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());

    const data = await r.json();
    const feats = data?.features || [];

    features.value = feats;
    addFootprintsToMap(feats);

    status.value = feats.length ? `נמצאו ${feats.length} סצנות.` : "אין תוצאות.";
  } catch (e) {
    status.value = `שגיאה: ${String(e)}`;
  } finally {
    busy.value = false;
  }
}

function downloadBlob(name, blob) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
}

function downloadGeoJSON() {
  const fc = { type: "FeatureCollection", features: features.value };
  const blob = new Blob([JSON.stringify(fc, null, 2)], { type: "application/geo+json" });
  downloadBlob(`satmap_s1_${start.value}_${end.value}.geojson`, blob);
}

function downloadCSV() {
  const rows = normalized.value.map((r) => ({
    id: r.gid,
    time: r.time,
    flightDirection: r.flightDirection,
    relativeOrbit: r.relativeOrbit,
  }));

  const header = Object.keys(rows[0] || { id: "", time: "", flightDirection: "", relativeOrbit: "" });
  const esc = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const csv =
    header.join(",") +
    "\n" +
    rows.map((row) => header.map((h) => esc(row[h])).join(",")).join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  downloadBlob(`satmap_s1_${start.value}_${end.value}.csv`, blob);
}

function togglePanelMobile() {
  document.body.classList.toggle("panelOpen");
}

onMounted(() => {
  initMap();
});
</script>

<style>
.wrap {
  display: grid;
  grid-template-columns: 420px 1fr;
  height: 100vh;
  font-family: system-ui, Arial;
  background: #f6f6f6;
}
.panel {
  padding: 12px;
  overflow: auto;
  border-left: 1px solid #e9e9e9;
  background: #fff;
}
.mapWrap {
  position: relative;
}
#map {
  height: 100vh;
  width: 100%;
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
h3 { margin: 0 0 6px; }

.row { margin: 10px 0; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

label { display: block; font-size: 12px; opacity: 0.85; margin-bottom: 6px; }

input, select, button {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border-radius: 10px;
  border: 1px solid #e2e2e2;
}
button { cursor: pointer; }

.btnPrimary {
  background: #111;
  color: #fff;
  border: 1px solid #111;
}
.btnGhost {
  background: #fff;
  border: 1px solid #e2e2e2;
}

.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

.small { font-size: 12px; opacity: 0.85; line-height: 1.35; }
.muted { opacity: 0.7; }

.status {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f7f7f7;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid #eee;
}

.list { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.card {
  text-align: right;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}
.card.active {
  border-color: #111;
  box-shadow: 0 0 0 2px rgba(0,0,0,0.05);
}
.line { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
.ell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 290px; }
.pill { font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid #e2e2e2; opacity: .9; }

.toggleBox { display: flex; align-items: end; justify-content: end; }
.chk { display:flex; align-items:center; gap:8px; font-size:12px; opacity:.85; }

@media (max-width: 900px) {
  .wrap { grid-template-columns: 1fr; }
  .panel {
    position: absolute;
    inset: 0;
    z-index: 999;
    transform: translateX(110%);
    transition: transform 200ms ease;
    max-width: 92vw;
    width: 92vw;
  }
  body.panelOpen .panel { transform: translateX(0); }
}
</style>

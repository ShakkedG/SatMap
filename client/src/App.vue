<template>
  <div class="wrap" dir="rtl">
    <aside class="panel">
      <h3>SatMap – Sentinel-1 (ASF Search)</h3>

      <div class="small">
        מציירים אזור על המפה (מלבן/פוליגון), בוחרים תאריכים ולוחצים חיפוש.
        <br />
        כרגע זה מחפש סצנות SAR (Sentinel-1 SLC) באזור שבחרת.
      </div>

      <div class="row">
        <label>התחלה</label>
        <input type="date" v-model="start" />
      </div>

      <div class="row">
        <label>סוף</label>
        <input type="date" v-model="end" />
      </div>

      <div class="row">
        <label>כיוון מסלול (אופציונלי)</label>
        <select v-model="flightDirection">
          <option value="">ללא</option>
          <option value="ASCENDING">עולה</option>
          <option value="DESCENDING">יורד</option>
        </select>
      </div>

      <div class="row">
        <button @click="doSearch" :disabled="busy">
          {{ busy ? "מחפש…" : "חפש סצנות" }}
        </button>
      </div>

      <div class="row">
        <div class="small">תוצאות ({{ results.length }})</div>
        <div class="list">
          <div class="card" v-for="r in results" :key="r.gid + r.time">
            <div class="mono">{{ r.gid }}</div>
            <div class="small">{{ r.time }}</div>
            <div class="small">
              {{ r.flightDirection ? `כיוון: ${r.flightDirection}` : "" }}
              {{ r.relativeOrbit ? ` | מסלול: ${r.relativeOrbit}` : "" }}
            </div>
          </div>
        </div>
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
import { onMounted, ref } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";

const start = ref(daysAgoISO(60));
const end = ref(todayISO());
const flightDirection = ref("");

const status = ref("—");
const busy = ref(false);
const results = ref([]);

let map, drawn;

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoISO(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function initMap() {
  map = L.map("map").setView([31.5, 35.0], 7);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  drawn = new L.FeatureGroup().addTo(map);

  // AOI ברירת מחדל סביב ישראל
  const defaultRect = L.rectangle([
    [29.45, 34.2],
    [33.4, 35.95],
  ]);
  drawn.addLayer(defaultRect);

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

function layerToWkt(layer) {
  // WKT POLYGON((lon lat, ...)) — שים לב: lon קודם
  const arr = layer.getLatLngs();
  const ring = Array.isArray(arr[0]) ? arr[0] : arr;
  const pts = ring.map((p) => [p.lng, p.lat]);

  // close ring
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

  return "unknown";
}

async function doSearch() {
  try {
    busy.value = true;
    results.value = [];
    status.value = "מחפש…";

    const layer = drawn.getLayers()[0];
    if (!layer) throw new Error("אין AOI על המפה");
    const wkt = layerToWkt(layer);

    const qs = new URLSearchParams({
      dataset: "SENTINEL-1",
      processingLevel: "SLC",
      intersectsWith: wkt,
      start: start.value,
      end: end.value,
      output: "geojson",
      maxResults: "200",
    });
    if (flightDirection.value) qs.set("flightDirection", flightDirection.value);

    const url = `https://api.daac.asf.alaska.edu/services/search/param?${qs.toString()}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());

    const data = await r.json();
    const feats = data?.features || [];

    const newest = [...feats].sort((a, b) => parseTimeMs(b) - parseTimeMs(a)).slice(0, 50);

    results.value = newest.map((f) => {
      const p = f.properties || {};
      return {
        gid: extractGranuleId(f),
        time: p.startTime || p.start || "",
        flightDirection: p.flightDirection || "",
        relativeOrbit: p.relativeOrbit || "",
      };
    });

    status.value = feats.length ? `נמצאו ${feats.length} סצנות (מציג עד 50 החדשות).` : "אין תוצאות.";
  } catch (e) {
    status.value = `שגיאה: ${String(e)}`;
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  initMap();
});
</script>

<style>
.wrap {
  display: grid;
  grid-template-columns: 380px 1fr;
  height: 100vh;
  font-family: system-ui, Arial;
}
.panel {
  padding: 12px;
  overflow: auto;
  border-left: 1px solid #eee;
  background: #fff;
}
#map {
  height: 100vh;
  width: 100%;
}
.row { margin: 10px 0; }
input, select, button {
  width: 100%;
  padding: 10px;
  font-size: 14px;
}
button { cursor: pointer; }
.small { font-size: 12px; opacity: 0.85; line-height: 1.35; }
.status {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f7f7f7;
  padding: 10px;
  border-radius: 10px;
}
.list { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.card { border: 1px solid #eee; border-radius: 10px; padding: 10px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
</style>

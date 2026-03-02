<template>
  <div class="map-wrap" dir="rtl">
    <div ref="mapEl" class="map"></div>

    <div class="hud">
      <div class="hudTitle">SatMap</div>

      <div class="row">
        <label>רקע</label>
        <select v-model="baseMapMode" @change="applyBaseLayer()">
          <option value="osm">מפה (OSM)</option>
          <option value="imagery">לוויין (Esri)</option>
        </select>
      </div>

      <div class="row">
        <label>בניינים</label>
        <select v-model="buildingsMode" @change="applyBuildingsLayer(true)">
          <option value="auto">אוטומטי (מומלץ)</option>
          <option value="tiles">Vector Tiles (שרת)</option>
          <option value="osm">OSM סביב קליק</option>
          <option value="none">ללא</option>
        </select>

        <div class="hint">
          <div class="statusLine">
            <span class="dot" :class="{ on: tilesReady }"></span>
            <span>
              Tiles:
              <span v-if="tilesChecking">בודק…</span>
              <span v-else>{{ tilesReady ? "מוכן" : "לא מוכן" }}</span>
            </span>
          </div>
          <div class="small">{{ tilesMsg }}</div>
        </div>

        <div class="btnRow">
          <button class="btn" @click="checkTilesStatus" :disabled="tilesChecking">
            רענן מצב Tiles
          </button>
          <button class="btn ghost" @click="fitToBuildings" :disabled="!buildingsLayer">
            התאם לשכבה
          </button>
        </div>
      </div>

      <hr class="sep" />

      <div class="row">
        <div class="small">
          טיפ: אם Tiles עובדים, תראה בניינים בעיקר בזום <b>15–16</b>.
        </div>
      </div>

      <div v-if="lastClick" class="row">
        <div class="small">
          לחיצה: {{ lastClick.lat.toFixed(6) }}, {{ lastClick.lng.toFixed(6) }}
        </div>
      </div>

      <div v-if="subsidence !== null" class="row">
        <div class="small">
          שקיעה (דמו): <b>{{ subsidence.toFixed(2) }}</b> mm/yr
        </div>
      </div>

      <div v-if="osmMsg" class="row">
        <div class="small warn">{{ osmMsg }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// חשוב ל-Vite: VectorGrid bundle
import "leaflet.vectorgrid/dist/Leaflet.VectorGrid.bundled.js";

// Fix marker icons in Vite
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

// ====== CONFIG (prod-friendly) ======
const TILES_BASE_URL =
  import.meta.env.VITE_TILES_BASE_URL || "https://satmap-tiles.onrender.com";

const BUILDINGS_TILES_TEMPLATE =
  `${TILES_BASE_URL}/tiles/buildings/{z}/{x}/{y}.pbf`;

// Overpass endpoint (לפעמים אחד נופל/נחסם – אפשר להחליף)
const OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter";

// ====== STATE ======
const mapEl = ref(null);
let map = null;

let baseLayer = null;
let buildingsLayer = null;
let clickMarker = null;

const baseMapMode = ref("imagery"); // "osm" | "imagery"

// buildings: "auto" | "tiles" | "osm" | "none"
const buildingsMode = ref("auto");

const tilesReady = ref(false);
const tilesChecking = ref(false);
const tilesMsg = ref("");

// OSM fallback
const osmMsg = ref("");
let osmAbort = null;
let lastOsmFetchAt = 0;
const OSM_THROTTLE_MS = 1500;

// click info
const lastClick = ref(null);
const subsidence = ref(null);

// ====== DEMO subsidence ======
async function getSubsidenceAt(lat, lng) {
  return (Math.sin(lat * 10) + Math.cos(lng * 10)) * 5;
}

// ====== Base layer ======
function applyBaseLayer() {
  if (!map) return;

  if (baseLayer) {
    try { map.removeLayer(baseLayer); } catch {}
    baseLayer = null;
  }

  if (baseMapMode.value === "osm") {
    baseLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
  } else {
    baseLayer = L.tileLayer(
      "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 19, attribution: "Tiles © Esri" }
    ).addTo(map);
  }
}

// ====== Tiles status ======
async function checkTilesStatus() {
  tilesChecking.value = true;
  tilesMsg.value = "";
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 5000);

    const res = await fetch(`${TILES_BASE_URL}/status`, {
      cache: "no-store",
      signal: ctrl.signal,
    });

    clearTimeout(t);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const j = await res.json();

    tilesReady.value = !!j.ready;

    if (tilesReady.value) {
      tilesMsg.value = "שרת ה-tiles מוכן (ready=true).";
    } else {
      tilesMsg.value = "שרת ה-tiles פעיל אבל עדיין בלי נתונים (ready=false).";
    }
  } catch (e) {
    tilesReady.value = false;
    tilesMsg.value = "לא מצליח להגיע לשרת ה-tiles כרגע.";
  } finally {
    tilesChecking.value = false;
  }
}

// ====== OSM (Overpass) ======
async function fetchBuildingsFromOSM(lat, lng) {
  // throttle כדי לא להפציץ את Overpass
  const now = Date.now();
  if (now - lastOsmFetchAt < OSM_THROTTLE_MS) {
    throw new Error("OSM_THROTTLED");
  }
  lastOsmFetchAt = now;

  const around = 140; // מטרים סביב הלחיצה
  const query = `
[out:json][timeout:25];
(
  way["building"](around:${around},${lat},${lng});
  relation["building"](around:${around},${lat},${lng});
);
out body;
>;
out skel qt;
`.trim();

  if (osmAbort) osmAbort.abort();
  osmAbort = new AbortController();

  const res = await fetch(OVERPASS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: new URLSearchParams({ data: query }),
    signal: osmAbort.signal,
  });

  if (!res.ok) throw new Error("Overpass failed: " + res.status);
  return await res.json();
}

function osmToSimpleGeoJson(osmJson) {
  const nodes = new Map();
  for (const el of osmJson.elements) {
    if (el.type === "node") nodes.set(el.id, [el.lon, el.lat]);
  }

  const features = [];
  for (const el of osmJson.elements) {
    if (el.type !== "way") continue;
    if (!el.tags || !el.tags.building) continue;

    const coords = [];
    for (const nid of el.nodes || []) {
      const c = nodes.get(nid);
      if (c) coords.push(c);
    }
    if (coords.length < 4) continue;

    const first = coords[0];
    const last = coords[coords.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) coords.push(first);

    features.push({
      type: "Feature",
      properties: { ...el.tags, osm_id: el.id },
      geometry: { type: "Polygon", coordinates: [coords] },
    });
  }

  return { type: "FeatureCollection", features };
}

async function updateBuildingsAt(lat, lng) {
  osmMsg.value = "";
  try {
    const osm = await fetchBuildingsFromOSM(lat, lng);
    const gj = osmToSimpleGeoJson(osm);

    // שקט: אם אין בניינים סביב קליק
    if (!gj.features.length) {
      osmMsg.value = "לא נמצאו בניינים סביב הלחיצה (OSM).";
    }

    if (buildingsLayer) {
      try { map.removeLayer(buildingsLayer); } catch {}
      buildingsLayer = null;
    }

    buildingsLayer = L.geoJSON(gj, {
      style: { weight: 1, fillOpacity: 0.2, color: "#00ffff" },
    }).addTo(map);
  } catch (err) {
    if (String(err?.message || err) === "OSM_THROTTLED") {
      osmMsg.value = "יותר מדי בקשות ל-OSM. נסה שוב עוד רגע.";
      return;
    }
    if (err?.name === "AbortError") return;
    console.error(err);
    osmMsg.value = "שגיאה מול Overpass (OSM).";
  }
}

// ====== Buildings layer (Tiles / OSM / none) ======
function removeBuildingsLayer() {
  if (buildingsLayer) {
    try { map.removeLayer(buildingsLayer); } catch {}
    buildingsLayer = null;
  }
}

function applyTilesLayer() {
  removeBuildingsLayer();

  // VectorGrid: שם שכבה צפוי "buildings". אם אצלך זה שם אחר, עדיין יש "*" fallback.
  const layer = L.vectorGrid.protobuf(BUILDINGS_TILES_TEMPLATE, {
    maxNativeZoom: 16,
    interactive: true,
    vectorTileLayerStyles: {
      buildings: {
        fill: true,
        fillColor: "#00ffff",
        fillOpacity: 0.18,
        stroke: true,
        color: "#00ffff",
        weight: 1,
      },
      "*": {
        fill: true,
        fillColor: "#00ffff",
        fillOpacity: 0.18,
        stroke: true,
        color: "#00ffff",
        weight: 1,
      },
    },
  });

  buildingsLayer = layer.addTo(map);
}

async function applyBuildingsLayer(fromUi = false) {
  if (!map) return;

  // Auto: tiles אם מוכן, אחרת OSM
  let effective = buildingsMode.value;

  if (effective === "auto") {
    // אם באים מ-UI נבדוק; אם לא, נשתמש בסטטוס האחרון
    if (fromUi || tilesMsg.value === "") await checkTilesStatus();
    effective = tilesReady.value ? "tiles" : "osm";
    tilesMsg.value = tilesReady.value
      ? "אוטומטי: מציג Tiles."
      : "אוטומטי: Tiles לא מוכנים → מציג OSM סביב קליק.";
  }

  if (effective === "none") {
    removeBuildingsLayer();
    osmMsg.value = "";
    return;
  }

  if (effective === "tiles") {
    if (!tilesReady.value) {
      if (fromUi) await checkTilesStatus();
      if (!tilesReady.value) {
        // fallback
        tilesMsg.value = "בחרת Tiles אבל השרת לא מוכן → מעבר ל-OSM סביב קליק.";
        buildingsMode.value = "osm";
        removeBuildingsLayer();
        return;
      }
    }
    applyTilesLayer();
    osmMsg.value = "";
    return;
  }

  // OSM: לא נטען שכבה עד קליק (שומר על ביצועים)
  removeBuildingsLayer();
  osmMsg.value = "OSM: לחץ על המפה כדי למשוך בניינים סביב הנקודה.";
}

// ====== UX helpers ======
function fitToBuildings() {
  if (!map || !buildingsLayer) return;
  try {
    const b = buildingsLayer.getBounds?.();
    if (b && b.isValid && b.isValid()) map.fitBounds(b.pad(0.15));
  } catch {}
}

async function onMapClick(e) {
  const { lat, lng } = e.latlng;
  lastClick.value = { lat, lng };

  const val = await getSubsidenceAt(lat, lng);
  subsidence.value = val;

  if (clickMarker) clickMarker.remove();
  clickMarker = L.marker([lat, lng])
    .addTo(map)
    .bindPopup(`📍 ${lat.toFixed(6)}, ${lng.toFixed(6)}<br/>שקיעה (דמו): ${val.toFixed(2)} mm/yr`)
    .openPopup();

  // אם אנחנו במצב OSM (או auto שנפל ל-OSM) — נטען סביב הקליק
  const eff = buildingsMode.value === "auto" ? (tilesReady.value ? "tiles" : "osm") : buildingsMode.value;
  if (eff === "osm") {
    await updateBuildingsAt(lat, lng);
  }
}

onMounted(async () => {
  map = L.map(mapEl.value, { zoomControl: true }).setView([32.0853, 34.7818], 13);

  applyBaseLayer();

  map.on("click", onMapClick);

  // בדיקה ראשונית + הפעלת שכבה לפי בחירה
  await checkTilesStatus();
  await applyBuildingsLayer(false);
});

onBeforeUnmount(() => {
  if (osmAbort) osmAbort.abort();
  if (map) map.off("click", onMapClick);
  if (map) map.remove();
});
</script>

<style scoped>
.map-wrap { position: relative; height: 100vh; width: 100%; }
.map { height: 100%; width: 100%; }

.hud{
  position:absolute;
  top:12px;
  right:12px;
  z-index:1000;
  width:min(360px, calc(100vw - 24px));
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(0,0,0,0.08);
  padding: 12px;
  border-radius: 14px;
  display: grid;
  gap: 10px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  backdrop-filter: blur(6px);
}

.hudTitle{
  font-weight: 800;
  font-size: 16px;
  letter-spacing: .2px;
}

.row{ display:grid; gap:6px; }
label{ font-size: 13px; opacity: .85; }
select{
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0,0,0,0.15);
  background: white;
}

.btnRow{ display:flex; gap:8px; }
.btn{
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0,0,0,0.18);
  background: #111;
  color: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn:disabled{ opacity: .55; cursor: not-allowed; }
.btn.ghost{
  background: #fff;
  color: #111;
}

.sep{ border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 2px 0; }

.hint{ display:grid; gap:4px; }
.statusLine{ display:flex; align-items:center; gap:8px; font-size: 13px; }
.dot{
  width: 10px; height: 10px; border-radius: 99px;
  background: #bbb;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.12);
}
.dot.on{ background: #2ecc71; }

.small{ font-size: 12px; opacity: .85; line-height: 1.35; }
.warn{ color: #8a4b00; }
</style>

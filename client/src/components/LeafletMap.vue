<template>
  <div class="map-wrap">
    <div ref="mapEl" class="map"></div>

    <div class="hud">
      <button @click="toggleBuildings">
        {{ showBuildings ? "הסתר בניינים (OSM)" : "הצג בניינים (OSM)" }}
      </button>

      <div v-if="lastClick">
        לחיצה: {{ lastClick.lat.toFixed(6) }}, {{ lastClick.lng.toFixed(6) }}
      </div>

      <div v-if="subsidence !== null">
        שקיעה (דמו): {{ subsidence.toFixed(2) }} mm/yr
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix marker icons in Vite
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

const mapEl = ref(null);
let map = null;
let clickMarker = null;
let buildingsLayer = null;

const showBuildings = ref(false);
const lastClick = ref(null);
const subsidence = ref(null);

async function getSubsidenceAt(lat, lng) {
  // TODO: פה תחליף למקור אמיתי של שקיעה.
  // בינתיים דמו כדי שתראה שהכל עובד מקצה לקצה.
  return (Math.sin(lat * 10) + Math.cos(lng * 10)) * 5;
}

async function fetchBuildingsFromOSM(lat, lng) {
  const around = 120; // מטרים סביב הלחיצה
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

  // אינסטנס של Overpass שלרוב עובד ב-CORS (אם זה יחסם—נחליף כתובת)
  const url = "https://overpass.kumi.systems/api/interpreter";

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: new URLSearchParams({ data: query }),
  });

  if (!res.ok) throw new Error("Overpass failed: " + res.status);
  return await res.json();
}

// המרה “מינימלית” מ-OSM JSON ל-GeoJSON (מספיק ל-way פשוטים סביב קליק)
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
  const osm = await fetchBuildingsFromOSM(lat, lng);
  const gj = osmToSimpleGeoJson(osm);

  if (buildingsLayer) buildingsLayer.remove();
  buildingsLayer = L.geoJSON(gj, { style: { weight: 1, fillOpacity: 0.2 } }).addTo(map);
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

  if (showBuildings.value) {
    try {
      await updateBuildingsAt(lat, lng);
    } catch (err) {
      console.error(err);
    }
  }
}

function toggleBuildings() {
  showBuildings.value = !showBuildings.value;

  if (!showBuildings.value && buildingsLayer) {
    buildingsLayer.remove();
    buildingsLayer = null;
  }
}

onMounted(() => {
  map = L.map(mapEl.value).setView([32.0853, 34.7818], 13); // ת"א כנקודת התחלה

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  map.on("click", onMapClick);
});

onBeforeUnmount(() => {
  if (map) map.off("click", onMapClick);
  if (map) map.remove();
});
</script>

<style scoped>
.map-wrap { position: relative; height: 100vh; width: 100%; }
.map { height: 100%; width: 100%; }
.hud {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1000;
  background: rgba(255,255,255,0.9);
  padding: 10px;
  border-radius: 10px;
  display: grid;
  gap: 6px;
  font-size: 14px;
}
button { cursor: pointer; }
</style>

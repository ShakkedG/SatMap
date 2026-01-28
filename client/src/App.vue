<template>
  <div class="wrap" dir="rtl">
    <aside class="panel">
      <div class="head">
        <div class="titleBlock">
          <h3>SatMap – Sentinel-1 (ASF Search)</h3>
          <div class="small">
            מצב חיפוש: מציירים AOI (מלבן/פוליגון), בוחרים תאריכים ולוחצים “חפש”.
            <br />
            מצב שקיעה: מציירים מלבן ואז “סרוק את המלבן” כדי למצוא בניינים שוקעים.
          </div>

          <a class="earthLink" :href="earthUrl" target="_blank" rel="noopener">
            פתיחה ב-Google Earth (מיקום נוכחי)
          </a>
        </div>

        <button class="btnGhost menuBtn" @click="togglePanelMobile" title="סגור/פתח">☰</button>
      </div>

      <div class="row grid2">
        <button class="btnGhost" :class="{ activeBtn: mode === 'search' }" @click="mode = 'search'">
          חיפוש סצנות
        </button>
        <button class="btnGhost" :class="{ activeBtn: mode === 'subsidence' }" @click="mode = 'subsidence'">
          בדיקת שקיעה
        </button>
      </div>

      <!-- מצב חיפוש -->
      <div v-if="mode === 'search'">
        <div class="section">
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
            <button class="btnGhost" @click="downloadGeoJSON" :disabled="!features.length">הורד GeoJSON</button>
            <button class="btnGhost" @click="downloadCSV" :disabled="!features.length">הורד CSV</button>
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
        </div>
      </div>

      <!-- GovMap point -->
      <div class="section">
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
      </div>

      <!-- מצב שקיעה -->
      <div class="section" v-if="mode === 'subsidence'">
        <div class="small">
          מצב שקיעה: צייר <b>מלבן</b> על המפה ואז לחץ “סרוק את המלבן”.
        </div>

        <div class="row actions" style="margin-top:10px;">
          <button class="btnGhost" @click="scanSubsidenceInRect" :disabled="subsBusy">סרוק את המלבן</button>
          <button class="btnGhost" @click="clearSubsidenceAll">נקה הכל</button>
        </div>

        <div class="row grid2" style="margin-top:10px;">
          <div>
            <label>סף “שוקע” (mm/yr)</label>
            <input type="number" v-model.number="subsThreshold" step="1" />
          </div>
          <div class="small" style="display:flex;align-items:end;justify-content:end;">
            בניינים שוקעים במלבן: <b style="margin-inline-start:6px;">{{ subsBuildings.length }}</b>
          </div>
        </div>

        <div class="small" v-if="lastClick">
          נקודה: {{ lastClick.lat.toFixed(6) }}, {{ lastClick.lng.toFixed(6) }}<br />
          שקיעה משוערת:
          <b v-if="subsMmPerYear != null">{{ subsMmPerYear.toFixed(2) }}</b><span v-else> N/A</span> mm/yr<br />
          תוצאה: <b>{{ subsResultText }}</b>
        </div>

        <div class="list" v-if="subsBuildings.length" style="margin-top:10px;">
          <button class="card" v-for="(b, i) in subsBuildings" :key="i" @click="focusSubsBuilding(b)">
            <div class="mono line">
              <span class="ell">{{ b.name }}</span>
              <span class="pill danger">שוקע</span>
            </div>
            <div class="small line">
              <span>שקיעה: {{ b.rate.toFixed(2) }} מ״מ/שנה</span>
            </div>
          </button>
        </div>
      </div>

      <div class="section">
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
import { computed, onMounted, ref, watch } from "vue";
import { govmapXYToWgs84, bufferPointToWktRect } from "./utils/govmapCrs.js";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";

/** Leaflet marker icons fix (מונע 404 ב-GitHub Pages / Vite) */
import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker1x from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: marker2x,
  iconUrl: marker1x,
  shadowUrl: markerShadow,
});

/** תיקון Leaflet.draw readableArea (מונע 'type is not defined') */
function patchLeafletDrawReadableArea() {
  if (!L?.GeometryUtil) return;

  // מחליפים תמיד למימוש בטוח (בלי תלויות/גלובלים)
  L.GeometryUtil.readableArea = function (area, isMetric = true, precision = 2) {
    const p = Number.isFinite(precision) ? precision : 2;
    const a = Number(area);
    if (!Number.isFinite(a) || a <= 0) return isMetric ? "0 מ״ר" : "0 ft²";

    if (isMetric) {
      if (a >= 1_000_000) return `${(a / 1_000_000).toFixed(p)} קמ״ר`;
      return `${a.toFixed(p)} מ״ר`;
    } else {
      const ft2 = a * 10.763910416709722;
      if (ft2 >= 27_878_400) return `${(ft2 / 27_878_400).toFixed(p)} mi²`;
      return `${ft2.toFixed(p)} ft²`;
    }
  };
}
patchLeafletDrawReadableArea();

/** -------------------- מצב כללי -------------------- */
const mode = ref("search"); // 'search' | 'subsidence'
const status = ref("—");
const busy = ref(false);

/** -------------------- חיפוש סצנות -------------------- */
const start = ref(daysAgoISO(60));
const end = ref(todayISO());
const flightDirection = ref("");

const q = ref("");
const limit = ref(50);
const showFootprints = ref(false); // ברירת מחדל: בלי עומס

const features = ref([]); // raw GeoJSON features
const selectedKey = ref("");

/** -------------------- GovMap -------------------- */
const govX = ref("");
const govY = ref("");
const govPoint = ref(null);
let govMarker = null;

/** -------------------- שקיעה -------------------- */
const subsThreshold = ref(-5);
const lastClick = ref(null);
const subsMmPerYear = ref(null);
const subsBusy = ref(false);
const subsBuildings = ref([]);

/** Google Earth link */
const earthPoint = ref({ lat: 31.78, lng: 35.22 }); // ברירת מחדל: אזור ישראל
const earthUrl = computed(() => {
  const p = earthPoint.value;
  return p ? `https://earth.google.com/web/search/${p.lat},${p.lng}` : "https://earth.google.com/web/";
});

const subsResultText = computed(() => {
  if (subsMmPerYear.value == null) return "אין נתון";
  return subsMmPerYear.value <= subsThreshold.value ? "שוקע" : "יציב/עולה";
});

/** -------------------- Leaflet state -------------------- */
let map = null;
let drawControl = null;

let drawn = null;
let footprintsGroup = null;
let subsAoiGroup = null;
let buildingsGroup = null;

let subsAoi = null;
let subsMarker = null;

const footprintLayers = new Map();

/** -------------------- utils תאריכים -------------------- */
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
    return new Date(t).toLocaleString("he-IL");
  } catch {
    return String(t);
  }
}

function setEarthPoint(lat, lng) {
  earthPoint.value = { lat: Number(lat), lng: Number(lng) };
}

/** -------------------- placeholder נתוני שקיעה/גובה -------------------- */
async function getSubsidenceRateMmPerYear(lat, lng) {
  return (Math.sin(lat * 8) + Math.cos(lng * 8)) * 6;
}
async function getEstimatedHeightMeters(lat, lng, dateISO) {
  const base = 120 + (Math.sin(lat) + Math.cos(lng)) * 8;
  const day = (new Date(dateISO).getTime() / 86400000) % 30;
  return base + (day / 30) * 0.3;
}

/** -------------------- GovMap point -------------------- */
function useGovmapPoint() {
  try {
    const p = govmapXYToWgs84(govX.value, govY.value);
    govPoint.value = p;

    if (govMarker) {
      govMarker.remove();
      govMarker = null;
    }
    govMarker = L.marker([p.lat, p.lng]).addTo(map);

    setEarthPoint(p.lat, p.lng);
    map.setView([p.lat, p.lng], Math.max(map.getZoom(), 15));

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

/** -------------------- Overpass בניינים -------------------- */
async function fetchBuildingsOSM(bbox) {
  const query = `
    [out:json][timeout:25];
    (
      way["building"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
      relation["building"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});
    );
    out body;
    >;
    out skel qt;
  `;

  const url = "https://overpass-api.de/api/interpreter";
  const res = await fetch(url, {
    method: "POST",
    body: query,
    headers: { "Content-Type": "text/plain;charset=UTF-8" },
  });

  if (!res.ok) throw new Error("Overpass failed: " + res.status);
  return res.json();
}

function overpassToGeoJSON(osm) {
  const elements = osm?.elements || [];
  const nodes = new Map();

  for (const el of elements) {
    if (el.type === "node" && typeof el.lat === "number" && typeof el.lon === "number") {
      nodes.set(el.id, [el.lon, el.lat]);
    }
  }

  const feats = [];
  for (const el of elements) {
    if (el.type !== "way") continue;
    if (!el.tags || !el.tags.building) continue;
    if (!Array.isArray(el.nodes) || el.nodes.length < 3) continue;

    const coords = el.nodes.map((nid) => nodes.get(nid)).filter(Boolean);
    if (coords.length < 3) continue;

    const first = coords[0];
    const last = coords[coords.length - 1];
    if (!last || first[0] !== last[0] || first[1] !== last[1]) coords.push(first);

    feats.push({
      type: "Feature",
      properties: { ...(el.tags || {}), osm_id: el.id },
      geometry: { type: "Polygon", coordinates: [coords] },
    });
  }

  return { type: "FeatureCollection", features: feats };
}

function featureCentroidLatLng(feature) {
  const coords = feature?.geometry?.coordinates?.[0];
  if (!coords || coords.length < 3) return null;

  let sumLng = 0,
    sumLat = 0,
    n = 0;
  for (const [lng, lat] of coords) {
    sumLng += lng;
    sumLat += lat;
    n++;
  }
  return { lat: sumLat / n, lng: sumLng / n };
}

function buildingLabel(tags = {}) {
  const street = tags["addr:street"];
  const num = tags["addr:housenumber"];
  const addr = [street, num].filter(Boolean).join(" ");
  return tags.name || addr || "בניין";
}

/** -------------------- שכבות שקיעה -------------------- */
function clearSubsidenceResults() {
  subsBuildings.value = [];
  if (buildingsGroup) buildingsGroup.clearLayers();
}

function clearSubsidenceAll() {
  clearSubsidenceResults();
  if (subsAoiGroup) subsAoiGroup.clearLayers();
  subsAoi = null;

  if (subsMarker) {
    subsMarker.remove();
    subsMarker = null;
  }
  lastClick.value = null;
  subsMmPerYear.value = null;
}

/** -------------------- ציור AOI (Leaflet.draw) -------------------- */
function rebuildDrawControl() {
  if (!map) return;

  patchLeafletDrawReadableArea();

  if (drawControl) {
    try {
      map.removeControl(drawControl);
    } catch {}
    drawControl = null;
  }

  const isSubs = mode.value === "subsidence";

  const aoiStyle = { color: "#111827", weight: 2, opacity: 0.9, fillOpacity: 0.06 };
  const subsStyle = { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.06 };

  drawControl = new L.Control.Draw({
    draw: isSubs
      ? {
          rectangle: { shapeOptions: subsStyle },
          polygon: false,
          polyline: false,
          circle: false,
          marker: false,
          circlemarker: false,
        }
      : {
          rectangle: { shapeOptions: aoiStyle },
          polygon: { allowIntersection: false, showArea: true, shapeOptions: aoiStyle },
          polyline: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
    edit: { featureGroup: isSubs ? subsAoiGroup : drawn },
  });

  map.addControl(drawControl);
}

/** -------------------- initMap -------------------- */
function initMap() {
  map = L.map("map", {
    zoomControl: true,
    maxZoom: 22,
    zoomSnap: 0.25,
  }).setView([31.78, 35.22], 11); // זום התחלתי הרבה יותר קרוב

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const esri = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "Tiles &copy; Esri",
  });

  L.control.layers({ "מפה (OSM)": osm, "לוויין (Esri)": esri }, {}, { position: "topleft" }).addTo(map);

  drawn = new L.FeatureGroup().addTo(map);
  footprintsGroup = new L.FeatureGroup().addTo(map);
  subsAoiGroup = new L.FeatureGroup().addTo(map);
  buildingsGroup = new L.FeatureGroup().addTo(map);

  resetIsraelAOI();
  rebuildDrawControl();

  map.on("moveend", () => {
    const c = map.getCenter();
    setEarthPoint(c.lat, c.lng);
  });

  map.on(L.Draw.Event.CREATED, async (e) => {
    if (mode.value === "subsidence") {
      subsAoiGroup.clearLayers();
      subsAoi = e.layer;
      subsAoiGroup.addLayer(subsAoi);

      const c = subsAoi.getBounds().getCenter();
      setEarthPoint(c.lat, c.lng);

      await scanSubsidenceInRect();
    } else {
      drawn.clearLayers();
      drawn.addLayer(e.layer);

      try {
        const c = e.layer.getBounds().getCenter();
        setEarthPoint(c.lat, c.lng);
      } catch {}
    }
  });

  map.on("click", async (e) => {
    if (mode.value !== "subsidence") return;

    const { lat, lng } = e.latlng;
    lastClick.value = { lat, lng };
    setEarthPoint(lat, lng);

    if (subsMarker) subsMarker.remove();
    subsMarker = L.marker([lat, lng]).addTo(map);

    try {
      subsMmPerYear.value = await getSubsidenceRateMmPerYear(lat, lng);
      status.value = `שקיעה משוערת: ${subsMmPerYear.value.toFixed(2)} mm/yr`;
    } catch (err) {
      subsMmPerYear.value = null;
      status.value = `שגיאה בדגימת שקיעה: ${String(err)}`;
    }
  });
}

/** -------------------- AOI חיפוש -------------------- */
function resetIsraelAOI() {
  if (!drawn) return;
  drawn.clearLayers();
  const rect = L.rectangle([
    [29.45, 34.2],
    [33.4, 35.95],
  ]);
  drawn.addLayer(rect);
  if (map) map.fitBounds(rect.getBounds(), { padding: [20, 20], maxZoom: 11 });

  const c = rect.getBounds().getCenter();
  setEarthPoint(c.lat, c.lng);
}

function clearAOI() {
  if (!drawn) return;
  drawn.clearLayers();
}

/** -------------------- WKT לחיפוש ASF -------------------- */
function layerToWkt(layer) {
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

/** -------------------- Normalization תוצאות ASF -------------------- */
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

/** -------------------- Footprints -------------------- */
function clearFootprints() {
  if (!footprintsGroup) return;
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
      // בלי “בלוק כחול”: רק קווי מתאר
      style: () => ({
        weight: 1,
        opacity: 0.6,
        fillOpacity: 0.0,
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        const gid = extractGranuleId(feature);
        const time = p.startTime || p.start || "";
        const key = `${gid}__${time || ""}`;

        footprintLayers.set(key, layer);

        layer.on("click", () => {
          setSelected(key);

          // עדכון Google Earth למרכז footprint
          try {
            const c = layer.getBounds().getCenter();
            setEarthPoint(c.lat, c.lng);
          } catch {}

          const html = `
            <div style="font-family: system-ui; font-size: 12px;">
              <div style="font-weight:700; margin-bottom:6px;">${gid}</div>
              <div>${time ? formatTime(time) : ""}</div>
              <div>${p.flightDirection ? "כיוון: " + p.flightDirection : ""}${
                p.relativeOrbit ? " | מסלול: " + p.relativeOrbit : ""
              }</div>
            </div>
          `;
          layer.bindPopup(html).openPopup();
        });
      },
    }
  );

  gj.eachLayer((l) => footprintsGroup.addLayer(l));
  applyFootprintsVisibility();

  if (footprintsGroup.getLayers().length) {
    try {
      const b = footprintsGroup.getBounds();
      if (b.isValid()) map.fitBounds(b, { padding: [24, 24], maxZoom: 12 });
    } catch {}
  }
}

function setSelected(key) {
  if (selectedKey.value && footprintLayers.has(selectedKey.value)) {
    footprintLayers.get(selectedKey.value).setStyle({ weight: 1, opacity: 0.6, fillOpacity: 0.0 });
  }
  selectedKey.value = key;
  if (footprintLayers.has(key)) {
    footprintLayers.get(key).setStyle({ weight: 4, opacity: 0.95, fillOpacity: 0.0 });
  }
}

function focusResult(key) {
  setSelected(key);
  const layer = footprintLayers.get(key);
  if (layer) {
    try {
      map.fitBounds(layer.getBounds(), { padding: [24, 24], maxZoom: 14 });
    } catch {}
  }
}

/** -------------------- חיפוש ASF -------------------- */
async function doSearch() {
  try {
    busy.value = true;
    features.value = [];
    clearFootprints();
    status.value = "מחפש…";

    const layer = drawn?.getLayers?.()[0];

    let wkt = "";
    if (layer) {
      wkt = layerToWkt(layer);
      try {
        const c = layer.getBounds().getCenter();
        setEarthPoint(c.lat, c.lng);
      } catch {}
    } else if (govPoint.value) {
      wkt = bufferPointToWktRect(govPoint.value.lat, govPoint.value.lng, 300);
      setEarthPoint(govPoint.value.lat, govPoint.value.lng);
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

    // מציירים במפה עד limit (כדי לא להעמיס)
    addFootprintsToMap(feats.slice(0, limit.value));

    // ברירת מחדל: כן להראות footprints אחרי חיפוש (אבל רק קווי מתאר)
    showFootprints.value = true;
    applyFootprintsVisibility();

    status.value = feats.length
      ? `נמצאו ${feats.length} סצנות. מציג על המפה ${Math.min(feats.length, limit.value)}.`
      : "אין תוצאות.";
  } catch (e) {
    status.value = `שגיאה: ${String(e)}`;
  } finally {
    busy.value = false;
  }
}

/** -------------------- שקיעה: סריקה במלבן -------------------- */
function approxBboxAreaKm2(b) {
  const meanLat = (b.getNorth() + b.getSouth()) / 2;
  const kmPerDegLat = 111.32;
  const kmPerDegLng = 111.32 * Math.cos((meanLat * Math.PI) / 180);
  const w = Math.abs(b.getEast() - b.getWest()) * kmPerDegLng;
  const h = Math.abs(b.getNorth() - b.getSouth()) * kmPerDegLat;
  return w * h;
}

async function scanSubsidenceInRect() {
  if (!subsAoi) {
    status.value = "אין מלבן שקיעה. במצב שקיעה צייר מלבן על המפה.";
    return;
  }

  try {
    subsBusy.value = true;
    status.value = "טוען בניינים (OSM)…";
    clearSubsidenceResults();

    subsAoiGroup.clearLayers();
    subsAoiGroup.addLayer(subsAoi);

    const b = subsAoi.getBounds();
    const c = b.getCenter();
    setEarthPoint(c.lat, c.lng);

    const area = approxBboxAreaKm2(b);
    if (area > 25) {
      throw new Error("המלבן גדול מדי לסריקה. תצמצם לאזור קטן יותר (כדי לא להפיל את Overpass).");
    }

    const bbox = { south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() };
    const osm = await fetchBuildingsOSM(bbox);
    const gj = overpassToGeoJSON(osm);

    status.value = `נמצאו ${gj.features.length} בניינים. בודק שקיעה…`;

    const sinking = [];
    const max = 300;
    const list = gj.features.slice(0, max);

    for (let i = 0; i < list.length; i++) {
      const f = list[i];
      const cc = featureCentroidLatLng(f);
      if (!cc) continue;

      const rate = await getSubsidenceRateMmPerYear(cc.lat, cc.lng);
      if (rate <= subsThreshold.value) sinking.push({ feature: f, centroid: cc, rate });

      if ((i + 1) % 30 === 0) status.value = `בודק שקיעה… ${i + 1}/${list.length}`;
    }

    buildingsGroup.clearLayers();

    for (const item of sinking) {
      const tags = item.feature.properties || {};
      const name = buildingLabel(tags);

      const layer = L.geoJSON(item.feature, {
        style: { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.18 },
      });

      layer.on("click", async () => {
        try {
          map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 19 });
        } catch {}

        const years =
          Math.max(0, (new Date(end.value) - new Date(start.value)) / (1000 * 60 * 60 * 24 * 365.25)) || 0;

        const deltaM = (item.rate / 1000) * years;

        const hPast = await getEstimatedHeightMeters(item.centroid.lat, item.centroid.lng, start.value);
        const hNow = hPast + deltaM;

        const html = `
          <div style="font-family:system-ui;font-size:12px;">
            <div style="font-weight:700;margin-bottom:6px;">${name}</div>
            <div>שקיעה: <b>${item.rate.toFixed(2)}</b> מ״מ/שנה</div>
            <div style="margin-top:6px;">תאריך עבר: ${start.value}</div>
            <div>תאריך נוכחי: ${end.value}</div>
            <div style="margin-top:6px;">גובה בעבר (משוער): <b>${hPast.toFixed(2)}</b> מ׳</div>
            <div>גובה נוכחי (משוער): <b>${hNow.toFixed(2)}</b> מ׳</div>
          </div>
        `;
        layer.bindPopup(html).openPopup();

        setEarthPoint(item.centroid.lat, item.centroid.lng);
      });

      layer.addTo(buildingsGroup);

      subsBuildings.value.push({
        name,
        rate: item.rate,
        lat: item.centroid.lat,
        lng: item.centroid.lng,
        _layer: layer,
      });
    }

    status.value = `בתוך המלבן: ${subsBuildings.value.length} בניינים שוקעים (סף ${subsThreshold.value}).`;

    if (subsBuildings.value.length) {
      try {
        map.fitBounds(buildingsGroup.getBounds(), { padding: [20, 20], maxZoom: 18 });
      } catch {}
    }
  } catch (e) {
    status.value = `שגיאה בסריקת שקיעה: ${String(e)}`;
  } finally {
    subsBusy.value = false;
  }
}

function focusSubsBuilding(b) {
  try {
    map.setView([b.lat, b.lng], Math.max(map.getZoom(), 18));
  } catch {}
  try {
    b._layer?.openPopup?.();
  } catch {}
  setEarthPoint(b.lat, b.lng);
}

/** -------------------- הורדות -------------------- */
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
  const csv = header.join(",") + "\n" + rows.map((row) => header.map((h) => esc(row[h])).join(",")).join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  downloadBlob(`satmap_s1_${start.value}_${end.value}.csv`, blob);
}

/** -------------------- UI -------------------- */
function togglePanelMobile() {
  document.body.classList.toggle("panelOpen");
}

/** -------------------- mode switching -------------------- */
watch(mode, (m) => {
  rebuildDrawControl();

  if (m === "subsidence") {
    showFootprints.value = false;
    applyFootprintsVisibility();
    clearFootprints();

    clearSubsidenceAll();
    status.value = "מצב שקיעה: צייר מלבן על המפה.";
  } else {
    clearSubsidenceAll();
    applyFootprintsVisibility();
    status.value = "מצב חיפוש: צייר AOI וחפש סצנות.";
  }
});

/** -------------------- mount -------------------- */
onMounted(() => {
  initMap();
  applyFootprintsVisibility();
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
h3 {
  margin: 0 0 6px;
}

.row {
  margin: 10px 0;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

label {
  display: block;
  font-size: 12px;
  opacity: 0.85;
  margin-bottom: 6px;
}

input,
select,
button {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border-radius: 10px;
  border: 1px solid #e2e2e2;
}
button {
  cursor: pointer;
}

.btnPrimary {
  background: #111;
  color: #fff;
  border: 1px solid #111;
}
.btnGhost {
  background: #fff;
  border: 1px solid #e2e2e2;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.small {
  font-size: 12px;
  opacity: 0.85;
  line-height: 1.35;
}
.muted {
  opacity: 0.7;
}

.status {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f7f7f7;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid #eee;
}

.activeBtn {
  border-color: #111 !important;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.06);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.card {
  text-align: right;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}
.card.active {
  border-color: #111;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.05);
}
.line {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.ell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 290px;
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #e2e2e2;
  opacity: 0.9;
}

.toggleBox {
  display: flex;
  align-items: end;
  justify-content: end;
}
.chk {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  opacity: 0.85;
}

@media (max-width: 900px) {
  .wrap {
    grid-template-columns: 1fr;
  }
  .panel {
    position: absolute;
    inset: 0;
    z-index: 999;
    transform: translateX(110%);
    transition: transform 200ms ease;
    max-width: 92vw;
    width: 92vw;
  }
  body.panelOpen .panel {
    transform: translateX(0);
  }
}
</style>

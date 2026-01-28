<template>
  <div class="layout" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div>
          <div class="appTitle">SatMap</div>
          <div class="appSub">Sentinel-1 Scenes + בדיקת בניינים לשקיעה</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ on: mode === 'search' }" @click="mode = 'search'">חיפוש סצנות</button>
        <button class="tab" :class="{ on: mode === 'subsidence' }" @click="mode = 'subsidence'">איתור בניינים שוקעים</button>
        <button class="tab" :class="{ on: mode === 'settings' }" @click="mode = 'settings'">הגדרות</button>
      </div>

      <!-- SEARCH MODE -->
      <section v-if="mode === 'search'" class="section">
        <div class="banner info">
          <div class="bannerTitle">מה זה עושה?</div>
          <div class="bannerText">
            כאן אתה רק <b>מחפש סצנות Sentinel-1</b> באזור ותאריכים. זה <b>לא מחשב שקיעה</b>.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">1</div>
          <div class="stepBody">
            <div class="stepTitle">בחר אזור</div>
            <div class="stepText">
              צייר מלבן/פוליגון על המפה. לחלופין: הזן נקודת GovMap ולחץ “המר לנקודה”.
            </div>

            <div class="row grid2">
              <button class="btnGhost" @click="resetIsraelAOI">Reset לישראל</button>
              <button class="btnGhost" @click="clearAOI">נקה AOI</button>
            </div>

            <div class="row grid2">
              <div>
                <label>GovMap X</label>
                <input v-model="govX" placeholder="220000 או lon" />
              </div>
              <div>
                <label>GovMap Y</label>
                <input v-model="govY" placeholder="630000 או lat" />
              </div>
            </div>

            <div class="row grid2">
              <button class="btnGhost" @click="useGovmapPoint">המר לנקודה (WGS84)</button>
              <button class="btnGhost" @click="clearGovmapPoint">נקה נקודה</button>
            </div>

            <div class="mini" v-if="govPoint">
              נקודה: {{ govPoint.lat.toFixed(6) }}, {{ govPoint.lng.toFixed(6) }} (מקור {{ govPoint.crs }})
            </div>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">2</div>
          <div class="stepBody">
            <div class="stepTitle">בחר תאריכים וסינון</div>

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
              <div class="toggleLine">
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

            <div class="mini">
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
                <div class="mini line">
                  <span>{{ formatTime(r.time) }}</span>
                  <span class="muted" v-if="r.relativeOrbit"> | מסלול: {{ r.relativeOrbit }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- SUBSIDENCE MODE -->
      <section v-if="mode === 'subsidence'" class="section">
        <div class="banner warn">
          <div class="bannerTitle">איך “איתור שקיעה” עובד?</div>
          <div class="bannerText">
            <b>שלב א׳:</b> מושך בניינים מ-OpenStreetMap (Overpass).<br />
            <b>שלב ב׳:</b> דוגם “קצב שקיעה” לכל בניין לפי <b>מקור נתונים</b> (DEMO או API).<br />
            <b>שלב ג׳:</b> כל בניין עם קצב ≤ הסף מסומן “שוקע”.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">1</div>
          <div class="stepBody">
            <div class="stepTitle">צייר מלבן שקיעה</div>
            <div class="stepText">
              במצב הזה אפשר לצייר <b>רק מלבן</b>. אחרי ציור – הסריקה יכולה להתחיל אוטומטית או בלחיצה על הכפתור.
            </div>

            <div class="row actions">
              <button class="btnGhost" @click="scanSubsidenceInRect" :disabled="subsBusy">
                {{ subsBusy ? "סורק…" : "סרוק את המלבן" }}
              </button>
              <button class="btnGhost" @click="stopSubsidenceScan" :disabled="!subsBusy">עצור</button>
            </div>

            <div class="row actions">
              <button class="btnGhost" @click="clearSubsidenceAll">נקה הכל</button>
              <button class="btnGhost" @click="clearSubsidenceResults">נקה תוצאות</button>
            </div>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">2</div>
          <div class="stepBody">
            <div class="stepTitle">סף + מגבלות</div>

            <div class="row grid2">
              <div>
                <label>סף “שוקע” (mm/yr)</label>
                <input type="number" v-model.number="subsThreshold" step="1" />
              </div>
              <div>
                <label>מקס׳ בניינים לבדיקה</label>
                <input type="number" v-model.number="subsMaxBuildings" step="50" min="50" />
              </div>
            </div>

            <div class="row grid2">
              <div>
                <label>מקור נתוני שקיעה</label>
                <select v-model="subsSource">
                  <option value="demo">DEMO (מדומה)</option>
                  <option value="api">API (שלך)</option>
                </select>
              </div>
              <div>
                <label>תוצאות במלבן</label>
                <div class="kpi">{{ subsBuildings.length }}</div>
              </div>
            </div>

            <div class="row" v-if="subsSource === 'api'">
              <label>תבנית URL ל-API</label>
              <input
                v-model="subsApiUrl"
                placeholder='למשל: https://yourdomain/api/subsidence?lat={lat}&lng={lng}'
              />
              <div class="mini muted" style="margin-top:6px;">
                ה-API צריך להחזיר JSON כמו: <span class="mono">{ "mmPerYear": -7.2 }</span>
              </div>
            </div>

            <div class="progressBox" v-if="subsProgress.stage">
              <div class="mini"><b>{{ subsProgress.stage }}</b></div>
              <div class="progressBar">
                <div class="progressFill" :style="{ width: subsProgressPercent + '%' }"></div>
              </div>
              <div class="mini muted">
                {{ subsProgress.done }} / {{ subsProgress.total }}
              </div>
            </div>

            <details class="details">
              <summary>למה זה לא “באמת” סנטינל-1 כרגע?</summary>
              <div class="mini" style="margin-top:8px; line-height:1.5;">
                חישוב שקיעה מסנטינל-1 דורש עיבוד InSAR של הרבה סצנות (לא רק “חיפוש”).<br />
                כאן האתר מוכן להתחבר ל-API שלך (או בעתיד לשכבת מהירויות), ואז הוא ידע לצבוע בניינים אמיתיים.
              </div>
            </details>
          </div>
        </div>

        <div class="step" v-if="subsBuildings.length">
          <div class="stepNum">3</div>
          <div class="stepBody">
            <div class="stepTitle">רשימת בניינים “שוקעים”</div>
            <div class="stepText">לחיצה על בניין תעשה Zoom ותפתח חלונית עם ההסבר.</div>

            <div class="list">
              <button class="card" v-for="(b, i) in subsBuildings" :key="i" @click="focusSubsBuilding(b)">
                <div class="mono line">
                  <span class="ell">{{ b.name }}</span>
                  <span class="pill danger">שוקע</span>
                </div>
                <div class="mini line">
                  <span>קצב: <b>{{ b.rate.toFixed(2) }}</b> mm/yr</span>
                  <span class="muted">{{ b.lat.toFixed(4) }}, {{ b.lng.toFixed(4) }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div class="mini muted" v-if="lastClick" style="margin-top:10px;">
          לחיצה אחרונה במפה: {{ lastClick.lat.toFixed(6) }}, {{ lastClick.lng.toFixed(6) }}
          | דגימה: <b v-if="subsMmPerYear != null">{{ subsMmPerYear.toFixed(2) }}</b><span v-else>—</span> mm/yr
          | תוצאה: <b>{{ subsResultText }}</b>
        </div>
      </section>

      <!-- SETTINGS -->
      <section v-if="mode === 'settings'" class="section">
        <div class="banner info">
          <div class="bannerTitle">כלים קטנים</div>
          <div class="bannerText">
            לינק ל-Google Earth מתעדכן לפי מרכז המפה / בחירות.
          </div>
        </div>

        <a class="earthLink" :href="earthUrl" target="_blank" rel="noopener">פתיחה ב-Google Earth (מיקום נוכחי)</a>

        <div class="row grid2" style="margin-top:12px;">
          <button class="btnGhost" @click="fitAllLayers">התאם זום לכל השכבות</button>
          <button class="btnGhost" @click="resetViewHome">חזור לתצוגת בית</button>
        </div>

        <details class="details" style="margin-top:12px;">
          <summary>מקורות נתונים</summary>
          <div class="mini" style="margin-top:8px; line-height:1.5;">
            <b>בניינים:</b> OpenStreetMap דרך Overpass.<br />
            <b>סצנות:</b> ASF Search API (Sentinel-1 SLC).<br />
            <b>שקיעה:</b> DEMO (מדומה) או API שאתה מספק.
          </div>
        </details>
      </section>

      <!-- STATUS -->
      <section class="section">
        <div class="mini muted">סטטוס</div>
        <pre class="status">{{ status }}</pre>
      </section>
    </aside>

    <main class="mapWrap" @click="maybeClosePanelOnMobile">
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

/** תיקון Leaflet.draw readableArea (מונע תלויות גלובליות) */
function patchLeafletDrawReadableArea() {
  if (!L?.GeometryUtil) return;

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

/** -------------------- UI state -------------------- */
const panelOpen = ref(true);
const mode = ref("search"); // 'search' | 'subsidence' | 'settings'
const status = ref("—");
const busy = ref(false);

/** -------------------- Search (ASF) -------------------- */
const start = ref(daysAgoISO(60));
const end = ref(todayISO());
const flightDirection = ref("");
const q = ref("");
const limit = ref(50);
const showFootprints = ref(true);

const features = ref([]);
const selectedKey = ref("");

/** -------------------- GovMap point -------------------- */
const govX = ref("");
const govY = ref("");
const govPoint = ref(null);
let govMarker = null;

/** -------------------- Subsidence -------------------- */
const subsThreshold = ref(-5);
const subsMaxBuildings = ref(250);
const subsBusy = ref(false);
const subsBuildings = ref([]);
const lastClick = ref(null);
const subsMmPerYear = ref(null);

const subsSource = ref("demo"); // 'demo' | 'api'
const subsApiUrl = ref("https://yourdomain/api/subsidence?lat={lat}&lng={lng}");

const subsProgress = ref({ stage: "", done: 0, total: 0 });
const subsProgressPercent = computed(() => {
  const t = subsProgress.value.total || 0;
  if (!t) return 0;
  return Math.max(0, Math.min(100, Math.round((subsProgress.value.done / t) * 100)));
});

const subsResultText = computed(() => {
  if (subsMmPerYear.value == null) return "אין נתון";
  return subsMmPerYear.value <= subsThreshold.value ? "שוקע" : "יציב/עולה";
});

/** Google Earth link */
const earthPoint = ref({ lat: 31.78, lng: 35.22 });
const earthUrl = computed(() => {
  const p = earthPoint.value;
  return p ? `https://earth.google.com/web/search/${p.lat},${p.lng}` : "https://earth.google.com/web/";
});
function setEarthPoint(lat, lng) {
  earthPoint.value = { lat: Number(lat), lng: Number(lng) };
}

/** -------------------- Leaflet state -------------------- */
let map = null;
let drawControl = null;

let drawn = null; // AOI for search
let footprintsGroup = null;
let subsAoiGroup = null;
let buildingsGroup = null;

let subsAoi = null;
let subsMarker = null;

const footprintLayers = new Map();

/** Abort controller for subsidence scan */
let subsAbort = null;

/** -------------------- Date utils -------------------- */
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

/** -------------------- Subsidence provider -------------------- */
/**
 * DEMO: מדומה (כמו שהיה אצלך) אבל עכשיו זה מוצג במפורש למשתמש.
 * API: קריאה ל-URL שאתה מספק שמחזיר { mmPerYear }.
 */
async function getSubsidenceRateMmPerYear(lat, lng) {
  if (subsSource.value === "api") {
    const url = subsApiUrl.value
      .replaceAll("{lat}", encodeURIComponent(String(lat)))
      .replaceAll("{lng}", encodeURIComponent(String(lng)));

    const r = await fetch(url, { signal: subsAbort?.signal });
    if (!r.ok) throw new Error("API failed: " + r.status);
    const j = await r.json();
    const v = Number(j?.mmPerYear);
    if (!Number.isFinite(v)) throw new Error("API returned invalid mmPerYear");
    return v;
  }

  // DEMO
  return (Math.sin(lat * 8) + Math.cos(lng * 8)) * 6;
}

/** -------------------- Overpass buildings -------------------- */
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
    signal: subsAbort?.signal,
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

/** -------------------- Clear subsidence -------------------- */
function clearSubsidenceResults() {
  subsBuildings.value = [];
  if (buildingsGroup) buildingsGroup.clearLayers();
}
function clearSubsidenceAll() {
  stopSubsidenceScan();
  clearSubsidenceResults();
  if (subsAoiGroup) subsAoiGroup.clearLayers();
  subsAoi = null;

  if (subsMarker) {
    subsMarker.remove();
    subsMarker = null;
  }
  lastClick.value = null;
  subsMmPerYear.value = null;
  subsProgress.value = { stage: "", done: 0, total: 0 };
}
function stopSubsidenceScan() {
  try {
    subsAbort?.abort?.();
  } catch {}
}

/** -------------------- Draw control -------------------- */
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
  map = L.map("map", { zoomControl: true, maxZoom: 22, zoomSnap: 0.25 }).setView([31.78, 35.22], 11);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const esri = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxNativeZoom: 19, maxZoom: 22, attribution: "Tiles &copy; Esri" }
  );

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

      // סריקה אוטומטית לאחר ציור (ברור למשתמש עם פס התקדמות)
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
      status.value = `דגימה בנקודה: ${subsMmPerYear.value.toFixed(2)} mm/yr (${subsSource.value.toUpperCase()})`;
    } catch (err) {
      subsMmPerYear.value = null;
      status.value = `שגיאה בדגימה: ${String(err)}`;
    }
  });
}

/** -------------------- AOI search -------------------- */
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

/** -------------------- WKT for ASF -------------------- */
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

/** -------------------- Normalize ASF results -------------------- */
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
      style: () => ({ weight: 1, opacity: 0.6, fillOpacity: 0.0 }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        const gid = extractGranuleId(feature);
        const time = p.startTime || p.start || "";
        const key = `${gid}__${time || ""}`;

        footprintLayers.set(key, layer);

        layer.on("click", () => {
          setSelected(key);
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

/** -------------------- ASF Search -------------------- */
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

    addFootprintsToMap(feats.slice(0, limit.value));
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

/** -------------------- Subsidence scan -------------------- */
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
    // init abort
    subsAbort?.abort?.();
    subsAbort = new AbortController();

    subsBusy.value = true;
    subsProgress.value = { stage: "טוען בניינים (OSM)…", done: 0, total: 1 };
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

    const all = gj.features || [];
    const list = all.slice(0, Math.max(50, Number(subsMaxBuildings.value) || 250));

    subsProgress.value = { stage: "בודק שקיעה לכל בניין…", done: 0, total: list.length };
    status.value = `נמצאו ${all.length} בניינים. בודק עד ${list.length}…`;

    // דגימה סדרתית (פשוט/בטוח). אם תרצה נוכל להפוך את זה ל-concurrency מוגבל.
    const sinking = [];
    for (let i = 0; i < list.length; i++) {
      if (subsAbort.signal.aborted) throw new Error("בוטל");
      const f = list[i];
      const cc = featureCentroidLatLng(f);
      if (!cc) {
        subsProgress.value.done = i + 1;
        continue;
      }

      const rate = await getSubsidenceRateMmPerYear(cc.lat, cc.lng);
      if (rate <= subsThreshold.value) sinking.push({ feature: f, centroid: cc, rate });

      subsProgress.value.done = i + 1;
      if ((i + 1) % 25 === 0) status.value = `בודק… ${i + 1}/${list.length}`;
    }

    buildingsGroup.clearLayers();

    const results = [];
    for (const item of sinking) {
      const tags = item.feature.properties || {};
      const name = buildingLabel(tags);

      const layer = L.geoJSON(item.feature, {
        style: { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.18 },
      });

      const expl = `
        <div style="font-family:system-ui;font-size:12px;line-height:1.45;">
          <div style="font-weight:800;margin-bottom:6px;">${name}</div>
          <div><b>קצב שקיעה:</b> ${item.rate.toFixed(2)} mm/yr</div>
          <div style="margin-top:8px;">
            <div style="font-weight:700;margin-bottom:4px;">איך נקבע?</div>
            <div>1) הבניין הגיע מ-OSM (Overpass)</div>
            <div>2) דגמנו שקיעה במרכז הבניין ממקור: <b>${subsSource.value.toUpperCase()}</b></div>
            <div>3) הסף שלך: <b>${subsThreshold.value}</b> mm/yr</div>
          </div>
        </div>
      `;

      layer.on("click", () => {
        try {
          map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 19 });
        } catch {}
        layer.bindPopup(expl).openPopup();
        setEarthPoint(item.centroid.lat, item.centroid.lng);
      });

      layer.addTo(buildingsGroup);

      results.push({
        name,
        rate: item.rate,
        lat: item.centroid.lat,
        lng: item.centroid.lng,
        _layer: layer,
      });
    }

    subsBuildings.value = results.sort((a, b) => a.rate - b.rate);
    status.value = `בתוך המלבן: ${subsBuildings.value.length} בניינים “שוקעים” (סף ${subsThreshold.value}, מקור ${subsSource.value.toUpperCase()}).`;

    subsProgress.value = { stage: "", done: 0, total: 0 };

    if (subsBuildings.value.length) {
      try {
        map.fitBounds(buildingsGroup.getBounds(), { padding: [20, 20], maxZoom: 18 });
      } catch {}
    }
  } catch (e) {
    status.value = `שגיאה בסריקה: ${String(e)}`;
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

/** -------------------- Downloads -------------------- */
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

/** -------------------- Misc UI helpers -------------------- */
function maybeClosePanelOnMobile() {
  if (window.matchMedia("(max-width: 900px)").matches) panelOpen.value = false;
}
function fitAllLayers() {
  try {
    const groups = [footprintsGroup, buildingsGroup, subsAoiGroup, drawn].filter(Boolean);
    let bounds = null;
    for (const g of groups) {
      const b = g.getBounds?.();
      if (!b || !b.isValid?.() || !b.isValid()) continue;
      bounds = bounds ? bounds.extend(b) : b;
    }
    if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 });
  } catch {}
}
function resetViewHome() {
  map.setView([31.78, 35.22], 11);
}

/** -------------------- mode switch -------------------- */
watch(mode, (m) => {
  rebuildDrawControl();

  if (m === "subsidence") {
    showFootprints.value = false;
    applyFootprintsVisibility();
    clearFootprints();

    clearSubsidenceAll();
    status.value = "מצב בניינים שוקעים: צייר מלבן על המפה.";
  } else if (m === "search") {
    clearSubsidenceAll();
    showFootprints.value = true;
    applyFootprintsVisibility();
    status.value = "מצב חיפוש: צייר AOI וחפש סצנות.";
  } else {
    // settings
    status.value = "הגדרות.";
  }
});

/** -------------------- mount -------------------- */
onMounted(() => {
  initMap();
  applyFootprintsVisibility();
});
</script>

<style>
.layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  height: 100vh;
  font-family: system-ui, Arial;
  background: #f3f4f6;
}
.panel {
  background: #fff;
  border-left: 1px solid #e5e7eb;
  padding: 12px;
  overflow: auto;
}
.mapWrap {
  position: relative;
}
#map {
  height: 100vh;
  width: 100%;
}

/* top */
.panelTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.appTitle {
  font-weight: 900;
  font-size: 18px;
}
.appSub {
  font-size: 12px;
  opacity: 0.75;
}
.iconBtn {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  cursor: pointer;
  width: auto;
}

/* tabs */
.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.tab {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 12px;
  padding: 10px;
  cursor: pointer;
}
.tab.on {
  border-color: #111827;
  box-shadow: 0 0 0 2px rgba(17, 24, 39, 0.08);
}

/* sections */
.section {
  margin: 12px 0;
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
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}
button {
  cursor: pointer;
}
.btnPrimary {
  background: #111827;
  color: #fff;
  border-color: #111827;
}
.btnGhost {
  background: #fff;
}
.row {
  margin: 10px 0;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* banners */
.banner {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  margin-bottom: 12px;
}
.bannerTitle {
  font-weight: 800;
  margin-bottom: 6px;
}
.bannerText {
  font-size: 12px;
  opacity: 0.9;
  line-height: 1.45;
}
.banner.info {
  background: #f8fafc;
}
.banner.warn {
  background: #fff7ed;
  border-color: #fed7aa;
}

/* steps */
.step {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 10px;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  margin-bottom: 12px;
  background: #fff;
}
.stepNum {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #111827;
  color: #fff;
  font-weight: 900;
}
.stepTitle {
  font-weight: 800;
  margin-bottom: 4px;
}
.stepText {
  font-size: 12px;
  opacity: 0.85;
  line-height: 1.45;
}

/* list cards */
.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.card {
  text-align: right;
  border: 1px solid #eee;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
}
.card.active {
  border-color: #111827;
  box-shadow: 0 0 0 2px rgba(17, 24, 39, 0.08);
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
  max-width: 280px;
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  opacity: 0.95;
}
.pill.danger {
  border-color: #fecaca;
  background: #fef2f2;
}

/* misc */
.mini {
  font-size: 12px;
  opacity: 0.85;
  line-height: 1.35;
}
.muted {
  opacity: 0.7;
}
.toggleLine {
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
.status {
  white-space: pre-wrap;
  word-break: break-word;
  background: #f9fafb;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #eee;
}
.earthLink {
  display: inline-block;
  margin-top: 6px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  text-decoration: none;
  color: inherit;
  background: #fff;
}

.kpi {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
  font-weight: 900;
  text-align: center;
}

/* progress */
.progressBox {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
}
.progressBar {
  height: 10px;
  border-radius: 999px;
  background: #eef2ff;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  margin: 8px 0;
}
.progressFill {
  height: 100%;
  background: #111827;
  width: 0%;
}

/* details */
.details {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
}
.details summary {
  cursor: pointer;
  font-weight: 800;
}

/* mobile */
@media (max-width: 900px) {
  .layout {
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
  .panel.open {
    transform: translateX(0);
  }
}
</style>

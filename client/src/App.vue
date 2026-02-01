<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Prototype – שקיעה + גובה (מ־DEM לווייני)</div>
        </div>
        <div class="topBtns">
          <button class="btn ghost" @click="fitToLayer" :disabled="!allBoundsValid">התמקד בשכבה</button>
          <button class="btn" @click="reload">טען מחדש</button>
        </div>
      </div>

      <div class="box">
        <div class="row2">
          <div>
            <label>סף “שוקע” (mm/yr)</label>
            <input type="number" v-model.number="rateThreshold" step="0.5" />
          </div>
          <div>
            <label>X שנים אחורה להשוואת גובה</label>
            <input type="number" v-model.number="yearsBack" step="0.5" min="0.5" />
            <div class="hint">מומלץ: 3–5 שנים</div>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>סף “שוקע” לפי Δh מצטבר (mm)</label>
            <input type="number" v-model.number="deltaThreshold" step="1" />
            <div class="hint">אם אין שדה Δh בקובץ → Δh = v×שנים</div>
          </div>
          <div>
            <label>צביעה לפי</label>
            <select v-model="colorBy">
              <option value="status">סטטוס</option>
              <option value="rate">מהירות</option>
              <option value="delta">Δh מצטבר</option>
            </select>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>שם שדה מהירות (אופציונלי)</label>
            <input v-model="forcedRateField" placeholder="למשל mmPerYear" />
          </div>
          <div>
            <label>שם שדה Δh מצטבר (אופציונלי)</label>
            <input v-model="forcedDeltaField" placeholder="למשל dH_mm / delta_mm" />
          </div>
        </div>

        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showStable" @change="applyVisibility" />
            להציג יציב/עולה
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showNoData" @change="applyVisibility" />
            להציג אין נתון
          </label>
        </div>

        <div class="kpis">
          <div class="kpi"><div class="k">סה״כ</div><div class="v">{{ stats.total }}</div></div>
          <div class="kpi sink"><div class="k">שוקעים/חשודים</div><div class="v">{{ stats.sinking }}</div></div>
          <div class="kpi stable"><div class="k">יציב/עולה</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.noData }}</div></div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <div class="legend">
          <div class="legRow"><span class="sw sw-sink"></span> שוקע/חשוד (v ≤ {{ rateThreshold }} או Δh ≤ {{ deltaThreshold }})</div>
          <div class="legRow"><span class="sw sw-stable"></span> יציב/עולה</div>
          <div class="legRow"><span class="sw sw-nodata"></span> אין נתון</div>
        </div>

        <div class="hint">
          גובה (m) מחושב בלחיצה ע״י Elevation API (DEM לווייני). זה לרוב גובה קרקע/שטח ברזולוציה גסה – לא גובה גג מדויק.
        </div>
      </div>

      <div class="box" v-if="selected">
        <div class="selHeader">
          <div class="mini"><b>{{ selected.name }}</b></div>
          <button class="btn ghost small" @click="clearSelection">נקה בחירה</button>
        </div>

        <div class="selGrid">
          <div class="selCard">
            <div class="k">סטטוס</div>
            <div class="v" :class="{ danger: selected.status === 'sinking' }">{{ selected.statusLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">מהירות (mm/yr)</div>
            <div class="v mono">{{ selected.rateLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">Δh ב־{{ yearsBack }} שנים (mm)</div>
            <div class="v mono">{{ selected.deltaLabel }}</div>
            <div class="hint" v-if="selected.deltaSourceLabel">מקור: {{ selected.deltaSourceLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">גובה עכשיו (m) – מהלווין</div>
            <div class="v mono">{{ selected.heightNowLabel }}</div>
            <div class="hint" v-if="selected.heightErr" style="color:#b91c1c">שגיאת גובה: {{ selected.heightErr }}</div>
          </div>

          <div class="selCard">
            <div class="k">גובה לפני {{ yearsBack }} שנים (m)</div>
            <div class="v mono">{{ selected.heightPastLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">Δגובה (m)</div>
            <div class="v mono">{{ selected.heightDiffLabel }}</div>
          </div>
        </div>

        <div class="mini muted" v-if="selected.heightInfo">
          {{ selected.heightInfo }}
        </div>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const tlvGeoUrl = `${import.meta.env.BASE_URL}data/tlvex.geojson`;

/** ===== UI state ===== */
const yearsBack = ref(3);
const rateThreshold = ref(-5);
const deltaThreshold = ref(-10);
const colorBy = ref("status");

const forcedRateField = ref("");
const forcedDeltaField = ref("");

const showStable = ref(true);
const showNoData = ref(false);

const loadMsg = ref("");
const loadErr = ref("");

const stats = ref({ total: 0, sinking: 0, stable: 0, noData: 0 });
const selected = ref(null);

/** ===== Leaflet state ===== */
let map = null;
let sinkingGroup = null;
let stableGroup = null;
let noDataGroup = null;

let allBounds = null;
const allBoundsValid = ref(false);

/** ===== Height from satellite DEM (Elevation API) =====
 * ברירת מחדל: open-elevation (חינמי; לפעמים מוגבל)
 * אפשר להחליף לשירות אחר עם API key.
 */
const elevationCache = new Map(); // key -> number (meters)
const elevPending = new Set();    // key currently fetching

async function fetchElevationMeters(lat, lon) {
  // open-elevation single lookup
  const url = `https://api.open-elevation.com/api/v1/lookup?locations=${lat},${lon}`;
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error("Elevation API HTTP " + r.status);
  const j = await r.json();
  const elev = j?.results?.[0]?.elevation;
  const n = Number(elev);
  if (!Number.isFinite(n)) throw new Error("Elevation missing/invalid");
  return n;
}

async function getHeightNowFromSatellite(key, latlng) {
  if (elevationCache.has(key)) return elevationCache.get(key);

  if (elevPending.has(key)) return null; // כבר נשלח — יחזור בעדכון הבא
  elevPending.add(key);

  try {
    const h = await fetchElevationMeters(latlng.lat, latlng.lng);
    elevationCache.set(key, h);
    return h;
  } finally {
    elevPending.delete(key);
  }
}

/** ===== Helpers ===== */
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmt2(n) {
  return n == null ? "—" : Number(n).toFixed(2);
}

function fmt1(n) {
  return n == null ? "—" : Number(n).toFixed(1);
}

function pickRateField(props) {
  const forced = String(forcedRateField.value || "").trim();
  if (forced && props && Object.prototype.hasOwnProperty.call(props, forced)) return forced;

  const candidates = [
    "mmPerYear","mm_per_year","mm_yr","mmYr",
    "rate","velocity","vel","subsidence","sink","value","v"
  ];
  for (const k of candidates) {
    if (props && Object.prototype.hasOwnProperty.call(props, k)) return k;
  }
  return "";
}

function pickDeltaField(props) {
  const forced = String(forcedDeltaField.value || "").trim();
  if (forced && props && Object.prototype.hasOwnProperty.call(props, forced)) return forced;

  const candidates = [
    "dH_mm","dh_mm","delta_mm","delta",
    "disp_mm","displacement_mm","cumulative_mm","cum_mm",
    "deformation_mm","subs_mm"
  ];
  for (const k of candidates) {
    if (props && Object.prototype.hasOwnProperty.call(props, k)) return k;
  }
  return "";
}

function computeDeltaMm(rate, props) {
  const df = pickDeltaField(props);
  if (df) {
    const n = toNum(props[df]);
    return { deltaMm: n, deltaField: df, source: n == null ? "none" : "field" };
  }
  if (rate == null) return { deltaMm: null, deltaField: "", source: "none" };

  const yrs = Math.max(0.25, toNum(yearsBack.value) ?? 3);
  return { deltaMm: rate * yrs, deltaField: "", source: "rate*years" };
}

function classify(rate, deltaMm) {
  if (rate == null && deltaMm == null) return "nodata";
  const byRate = rate != null && rate <= rateThreshold.value;
  const byDelta = deltaMm != null && deltaMm <= deltaThreshold.value;
  return (byRate || byDelta) ? "sinking" : "stable";
}

function statusLabel(status) {
  if (status === "sinking") return "שוקע/חשוד";
  if (status === "stable") return "יציב/עולה";
  return "אין נתון";
}

function styleFor(status, rate, deltaMm) {
  if (status === "nodata") return { color: "#64748b", weight: 1, opacity: 0.65, fillOpacity: 0.06, dashArray: "4 4" };
  if (status === "stable") return { color: "#111827", weight: 1, opacity: 0.65, fillOpacity: 0.08 };

  // sinking
  let s = 0.5;
  if (colorBy.value === "rate" && rate != null && rateThreshold.value) {
    const ratio = Math.abs(rate / rateThreshold.value);
    s = Math.max(0, Math.min(1, (ratio - 1) / 2));
  } else if (colorBy.value === "delta" && deltaMm != null && deltaThreshold.value) {
    const ratio = Math.abs(deltaMm / deltaThreshold.value);
    s = Math.max(0, Math.min(1, (ratio - 1) / 2));
  }

  const fillOpacity = 0.35 + s * 0.35;
  const weight = 1.4 + s * 1.2;
  const stroke = s >= 0.75 ? "#7f1d1d" : s >= 0.40 ? "#b91c1c" : "#dc2626";
  return { color: stroke, weight, opacity: 0.95, fillOpacity };
}

function pickName(props, idx) {
  return props?.name ?? props?.building_id ?? props?.id ?? `בניין ${idx + 1}`;
}

function featureKey(props, idx) {
  return String(props?.building_id ?? props?.id ?? props?.tile_id ?? `f_${idx}`);
}

/** נקודה מייצגת לגובה: מרכז ה-bounds (מספיק לפרוטוטייפ) */
function representativeLatLng(layer) {
  try {
    const b = layer.getBounds();
    return b.getCenter();
  } catch {
    return null;
  }
}

/** ===== Map init ===== */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, preferCanvas: true }).setView([32.08, 34.78], 12);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  sinkingGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup();
  noDataGroup = new L.FeatureGroup();

  L.control.layers({ OSM: osm }, {}, { position: "topleft" }).addTo(map);
}

function applyVisibility() {
  if (!map) return;

  if (!map.hasLayer(sinkingGroup)) sinkingGroup.addTo(map);

  if (showStable.value) {
    if (!map.hasLayer(stableGroup)) stableGroup.addTo(map);
  } else {
    if (map.hasLayer(stableGroup)) map.removeLayer(stableGroup);
  }

  if (showNoData.value) {
    if (!map.hasLayer(noDataGroup)) noDataGroup.addTo(map);
  } else {
    if (map.hasLayer(noDataGroup)) map.removeLayer(noDataGroup);
  }
}

function clearSelection() {
  selected.value = null;
}

function fitToLayer() {
  if (allBounds?.isValid?.()) {
    try { map.fitBounds(allBounds.pad(0.08)); } catch {}
  }
}

/** ===== Load + render ===== */
async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען שכבת בניינים…";
  clearSelection();

  sinkingGroup?.clearLayers?.();
  stableGroup?.clearLayers?.();
  noDataGroup?.clearLayers?.();

  allBounds = null;
  allBoundsValid.value = false;

  try {
    const r = await fetch(tlvGeoUrl, { cache: "no-store" });
    if (!r.ok) throw new Error("GeoJSON load failed: " + r.status);
    const gj = await r.json();

    const feats = Array.isArray(gj?.features) ? gj.features : [];
    let sinking = 0, stable = 0, noData = 0;

    for (let i = 0; i < feats.length; i++) {
      const f = feats[i];
      const props = f?.properties || {};

      const key = featureKey(props, i);
      const name = pickName(props, i);

      const rateField = pickRateField(props);
      const rate = rateField ? toNum(props[rateField]) : null;

      const deltaObj = computeDeltaMm(rate, props);
      const deltaMm = deltaObj.deltaMm;

      const st = classify(rate, deltaMm);
      if (st === "sinking") sinking++;
      else if (st === "stable") stable++;
      else noData++;

      const layer = L.geoJSON(f, { style: styleFor(st, rate, deltaMm), interactive: true });

      // bounds
      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) allBounds = allBounds ? allBounds.extend(b) : b;
      } catch {}

      // tooltip
      layer.bindTooltip(
        `v: ${fmt2(rate)} mm/yr | Δh: ${fmt1(deltaMm)} mm | (גובה מהלווין בלחיצה)`,
        { sticky: true, direction: "top", opacity: 0.92 }
      );

      // click -> select + fetch height now from satellite
      layer.on("click", async () => {
        const latlng = representativeLatLng(layer);
        const yrs = Math.max(0.25, toNum(yearsBack.value) ?? 3);

        // מיד מציגים נתוני שקיעה
        selected.value = {
          key,
          name,
          status: st,
          statusLabel: statusLabel(st),
          rate,
          rateLabel: fmt2(rate),
          deltaMm,
          deltaLabel: fmt1(deltaMm),
          deltaSourceLabel: deltaObj.source === "field" ? "שדה בקובץ" : deltaObj.source === "rate*years" ? "חישוב v×שנים" : "",
          heightNowM: null,
          heightPastM: null,
          heightDiffM: null,
          heightNowLabel: latlng ? "טוען…" : "—",
          heightPastLabel: "—",
          heightDiffLabel: "—",
          heightErr: "",
          heightInfo: latlng ? `נקודת דגימה: ${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}` : "לא הצלחתי לחשב נקודת דגימה לגובה.",
        };

        if (!latlng) return;

        try {
          const hNow = await getHeightNowFromSatellite(key, latlng);
          if (hNow == null) return; // עדיין בהמתנה

          // גובה בעבר מחושב ע"י Δh (מ״מ) -> מטרים
          const hPast =
            (hNow == null || deltaMm == null) ? null : (hNow - (deltaMm / 1000));

          const hDiff =
            (hNow == null || hPast == null) ? null : (hNow - hPast);

          // מעדכנים בחירה (אם עדיין אותו בניין נבחר)
          if (selected.value?.key === key) {
            selected.value.heightNowM = hNow;
            selected.value.heightPastM = hPast;
            selected.value.heightDiffM = hDiff;

            selected.value.heightNowLabel = fmt2(hNow);
            selected.value.heightPastLabel = fmt2(hPast);
            selected.value.heightDiffLabel = hDiff == null ? "—" : hDiff.toFixed(4);

            selected.value.heightInfo =
              `גובה (DEM) מחושב מהלווין בנקודת הדגימה. גובה בעבר = גובה עכשיו - (Δh/1000) עבור ${yrs.toFixed(2)} שנים.`;
          }
        } catch (e) {
          if (selected.value?.key === key) {
            selected.value.heightErr = String(e);
            selected.value.heightNowLabel = "—";
            selected.value.heightPastLabel = "—";
            selected.value.heightDiffLabel = "—";
          }
        }
      });

      if (st === "sinking") layer.addTo(sinkingGroup);
      else if (st === "stable") layer.addTo(stableGroup);
      else layer.addTo(noDataGroup);
    }

    stats.value = { total: feats.length, sinking, stable, noData };
    applyVisibility();

    allBoundsValid.value = !!allBounds?.isValid?.();
    if (allBoundsValid.value) {
      try { map.fitBounds(allBounds.pad(0.08)); } catch {}
    }

    loadMsg.value = `נטענו ${feats.length} בניינים.`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, sinking: 0, stable: 0, noData: 0 };
  }
}

function reload() {
  loadAndRender();
}

watch([rateThreshold, deltaThreshold, yearsBack, forcedRateField, forcedDeltaField, colorBy], () => {
  if (!map) return;
  loadAndRender();
});

onMounted(async () => {
  initMap();
  await loadAndRender();
});
</script>

<style>
.layout { display:grid; grid-template-columns: 440px 1fr; height:100vh; background:#f3f4f6; font-family:system-ui, Arial; }
.panel { background:#fff; border-left:1px solid #e5e7eb; padding:12px; overflow:auto; }
.mapWrap { position:relative; }
#map { width:100%; height:100vh; }

.top { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:10px; }
.topBtns { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.title { font-weight:900; font-size:18px; }
.sub { font-size:12px; opacity:0.72; margin-top:2px; }

.box { border:1px solid #e5e7eb; border-radius:16px; padding:10px; background:#fff; margin-bottom:10px; }
label { display:block; font-size:12px; opacity:0.85; margin-bottom:6px; }

input, select, .btn { width:100%; padding:10px; border-radius:12px; border:1px solid #e5e7eb; font-size:14px; background:#fff; }
select { cursor:pointer; }

.btn { cursor:pointer; background:#111827; color:#fff; border-color:#111827; font-weight:700; }
.btn.ghost { background:#fff; color:#111827; border-color:#e5e7eb; }
.btn.small { padding:8px 10px; font-size:12px; border-radius:10px; }
.btn:disabled { opacity:0.55; cursor:not-allowed; }

.row2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:6px; }
.chk { display:flex; align-items:center; gap:8px; font-size:12px; opacity:0.9; margin-top:8px; }

.kpis { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:10px; }
.kpi { border:1px solid #e5e7eb; border-radius:12px; padding:10px; background:#f9fafb; }
.kpi .k { font-size:12px; opacity:0.7; }
.kpi .v { font-weight:900; font-size:18px; }
.kpi.sink { border-color:#fecaca; background:#fef2f2; }
.kpi.stable { border-color:#e5e7eb; background:#f8fafc; }
.kpi.nodata { border-color:#e2e8f0; background:#f8fafc; }

.legend { margin-top:10px; border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; display:grid; gap:6px; }
.legRow { display:flex; align-items:center; gap:10px; font-size:12px; opacity:0.9; }
.sw { width:18px; height:10px; border-radius:4px; border:1px solid #e5e7eb; }
.sw-sink { background:#fef2f2; border-color:#b91c1c; }
.sw-stable { background:#f8fafc; border-color:#111827; }
.sw-nodata { background:#f8fafc; border-color:#64748b; }

.selHeader { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
.selGrid { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px; }
.selCard { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#f9fafb; }
.selCard .k { font-size:12px; opacity:0.7; }
.selCard .v { font-weight:900; font-size:14px; margin-top:4px; }
.selCard .v.danger { color:#991b1b; }

.mini { font-size:12px; opacity:0.9; margin-top:8px; }
.muted { opacity:0.72; }
.err { color:#b91c1c; opacity:1; }
.hint { font-size:11px; opacity:0.68; margin-top:6px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 52vh; border-left:none; border-bottom:1px solid #e5e7eb; }
  #map { height: 48vh; }
}
</style>

<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Prototype – יציבות בניינים + שינוי גובה (Δh)</div>
        </div>
        <button class="btn" @click="reload">טען מחדש</button>
      </div>

      <div class="box">
        <div class="row2">
          <div>
            <label>סף “לא יציב” מהירות (mm/yr)</label>
            <input type="number" v-model.number="rateThreshold" step="0.5" />
          </div>
          <div>
            <label>חלון זמן לחישוב שינוי גובה (שנים)</label>
            <input type="number" v-model.number="timeSpanYears" step="0.25" min="0.25" />
          </div>
        </div>

        <div class="row2">
          <div>
            <label>סף “לא יציב” שינוי גובה מצטבר (mm)</label>
            <input type="number" v-model.number="deltaThreshold" step="1" />
          </div>
          <div>
            <label>מדד לצביעה במפה</label>
            <select v-model="colorBy">
              <option value="rate">מהירות (mm/yr)</option>
              <option value="delta">שינוי מצטבר (mm)</option>
            </select>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>שם שדה מהירות קבוע (אופציונלי)</label>
            <input v-model="forcedRateField" placeholder="למשל mmPerYear" />
          </div>
          <div>
            <label>שם שדה שינוי מצטבר (אופציונלי)</label>
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
          <div class="kpi unstable"><div class="k">לא יציב</div><div class="v">{{ stats.unstable }}</div></div>
          <div class="kpi stable"><div class="k">יציב/עולה</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.noData }}</div></div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <div class="legend">
          <div class="legRow">
            <span class="sw sw-unstable"></span>
            לא יציב (מהירות ≤ {{ rateThreshold }} או Δh ≤ {{ deltaThreshold }})
          </div>
          <div class="legRow"><span class="sw sw-stable"></span> יציב/עולה</div>
          <div class="legRow"><span class="sw sw-nodata"></span> אין נתון</div>
        </div>

        <div class="mini muted">
          Δh מחושב כך:
          <span class="mono">אם יש שדה Δh בקובץ → משתמשים בו</span>,
          אחרת <span class="mono">Δh = rate × years</span>.
        </div>
      </div>

      <div class="box" v-if="selected">
        <div class="mini"><b>{{ selected.name }}</b></div>
        <div class="mini">סטטוס: <b>{{ selected.statusLabel }}</b></div>
        <div class="mini">מהירות (mm/yr): <b>{{ selected.rateLabel }}</b></div>
        <div class="mini">Δh בתקופה (mm): <b>{{ selected.deltaLabel }}</b></div>
        <div class="mini muted">תקופה: <span class="mono">{{ timeSpanYears }}</span> שנים</div>
        <div class="mini muted" v-if="selected.rateField">שדה מהירות: <span class="mono">{{ selected.rateField }}</span></div>
        <div class="mini muted" v-if="selected.deltaField">שדה Δh: <span class="mono">{{ selected.deltaField }}</span></div>
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
const rateThreshold = ref(-5);     // mm/yr: שלילי = שוקע
const deltaThreshold = ref(-10);   // mm בתקופה: שלילי = ירידה/שקיעה
const timeSpanYears = ref(1);      // כמה שנים לצבירה אם אין שדה Δh
const colorBy = ref("delta");      // "rate" | "delta"

const forcedRateField = ref("");
const forcedDeltaField = ref("");

const showStable = ref(false);
const showNoData = ref(false);

const loadMsg = ref("");
const loadErr = ref("");

const stats = ref({ total: 0, unstable: 0, stable: 0, noData: 0 });
const selected = ref(null);

/** ===== Leaflet state ===== */
let map = null;
let unstableGroup = null;
let stableGroup = null;
let noDataGroup = null;
let allBounds = null;

/** ===== Helpers ===== */
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
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

  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (toNum(v) != null) return k;
    }
  }
  return "";
}

function pickDeltaField(props) {
  const forced = String(forcedDeltaField.value || "").trim();
  if (forced && props && Object.prototype.hasOwnProperty.call(props, forced)) return forced;

  const candidates = [
    "dH_mm","dh_mm","delta_mm","delta",
    "deltaH","delta_h","heightChange","height_change",
    "disp_mm","displacement_mm","cumulative_mm","cum_mm",
    "deformation_mm","subs_mm"
  ];
  for (const k of candidates) {
    if (props && Object.prototype.hasOwnProperty.call(props, k)) return k;
  }
  return "";
}

function computeDelta(rate, props) {
  const df = pickDeltaField(props);
  if (df) {
    const n = toNum(props[df]);
    return { value: n, field: df, source: "field" };
  }
  if (rate == null) return { value: null, field: "", source: "none" };
  const years = Math.max(0.01, toNum(timeSpanYears.value) ?? 1);
  return { value: rate * years, field: "", source: "rate*years" };
}

function classify(rate, delta) {
  if (rate == null && delta == null) return "nodata";
  const unstableByRate = rate != null && rate <= rateThreshold.value;
  const unstableByDelta = delta != null && delta <= deltaThreshold.value;
  return (unstableByRate || unstableByDelta) ? "unstable" : "stable";
}

function severity01From(metricValue, thresholdValue) {
  // metricValue ושלילי בדרך כלל. מחשבים "כמה חזק" מתחת לסף.
  if (metricValue == null || thresholdValue == null) return 0.4;
  if (metricValue > thresholdValue) return 0.2;
  const exceed = Math.abs(metricValue - thresholdValue);
  // נורמליזציה פשוטה: כל 10mm מעבר לסף מעלה "חומרה"
  const t = Math.min(1, exceed / 10);
  return 0.35 + t * 0.45;
}

function styleFor(status, rate, delta) {
  if (status === "unstable") {
    const metric = (colorBy.value === "rate") ? rate : delta;
    const thr = (colorBy.value === "rate") ? rateThreshold.value : deltaThreshold.value;
    const fo = severity01From(metric, thr);
    return { color: "#b91c1c", weight: 1.6, opacity: 0.95, fillOpacity: fo };
  }
  if (status === "stable") {
    return { color: "#111827", weight: 1, opacity: 0.75, fillOpacity: 0.08 };
  }
  return { color: "#64748b", weight: 1, opacity: 0.6, fillOpacity: 0.05, dashArray: "4 4" };
}

function statusLabel(status) {
  if (status === "unstable") return "לא יציב";
  if (status === "stable") return "יציב/עולה";
  return "אין נתון";
}

function getNameFromProps(props) {
  return props?.name || props?.id || props?.building_id || props?.tile_id || props?.cell_id || "תא/בניין";
}

function fmt(n) {
  return (n == null) ? "—" : Number(n).toFixed(2);
}

/** ===== Map init ===== */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22 }).setView([32.08, 34.78], 12);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  unstableGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup();
  noDataGroup = new L.FeatureGroup();

  L.control.layers({ OSM: osm }, {}, { position: "topleft" }).addTo(map);
}

function applyVisibility() {
  if (!map) return;

  if (!map.hasLayer(unstableGroup)) unstableGroup.addTo(map);

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

/** ===== Load + render ===== */
async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען שכבת פוליגונים…";
  selected.value = null;

  unstableGroup?.clearLayers?.();
  stableGroup?.clearLayers?.();
  noDataGroup?.clearLayers?.();
  allBounds = null;

  try {
    const r = await fetch(tlvGeoUrl, { cache: "no-store" });
    if (!r.ok) throw new Error("GeoJSON load failed: " + r.status);
    const gj = await r.json();

    const feats = Array.isArray(gj?.features) ? gj.features : [];
    let unstable = 0, stable = 0, noData = 0;

    for (const f of feats) {
      const props = f?.properties || {};

      const rf = pickRateField(props);
      const rate = rf ? toNum(props[rf]) : null;

      const deltaObj = computeDelta(rate, props);
      const delta = deltaObj.value;

      const st = classify(rate, delta);

      if (st === "unstable") unstable++;
      else if (st === "stable") stable++;
      else noData++;

      const layer = L.geoJSON(f, { style: styleFor(st, rate, delta) });

      layer.on("click", () => {
        const name = getNameFromProps(props);

        selected.value = {
          name,
          status: st,
          statusLabel: statusLabel(st),
          rate,
          rateLabel: fmt(rate),
          delta,
          deltaLabel: fmt(delta),
          rateField: rf || "",
          deltaField: deltaObj.field || "",
        };

        layer
          .bindPopup(
            `<div style="font-family:system-ui;font-size:12px;line-height:1.45">
              <div style="font-weight:800;margin-bottom:6px">${name}</div>
              <div><b>סטטוס:</b> ${statusLabel(st)}</div>
              <div><b>מהירות:</b> ${fmt(rate)} mm/yr</div>
              <div><b>Δh (מצטבר):</b> ${fmt(delta)} mm</div>
              <div style="opacity:.7;margin-top:6px">תקופה: ${Number(timeSpanYears.value).toFixed(2)} שנים</div>
            </div>`
          )
          .openPopup();
      });

      layer.bindTooltip(
        `Δh: ${fmt(delta)} mm | v: ${fmt(rate)} mm/yr`,
        { sticky: true, direction: "top", opacity: 0.9 }
      );

      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) allBounds = allBounds ? allBounds.extend(b) : b;
      } catch {}

      if (st === "unstable") layer.addTo(unstableGroup);
      else if (st === "stable") layer.addTo(stableGroup);
      else layer.addTo(noDataGroup);
    }

    stats.value = { total: feats.length, unstable, stable, noData };
    applyVisibility();

    if (allBounds?.isValid?.()) {
      try {
        map.fitBounds(allBounds.pad(0.08));
      } catch {}
    }

    loadMsg.value = `נטענו ${feats.length} פוליגונים.`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, unstable: 0, stable: 0, noData: 0 };
  }
}

function reload() {
  loadAndRender();
}

watch([rateThreshold, deltaThreshold, timeSpanYears, forcedRateField, forcedDeltaField, colorBy], () => {
  if (!map) return;
  loadAndRender();
});

onMounted(async () => {
  initMap();
  await loadAndRender();
});
</script>

<style>
.layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  height: 100vh;
  background: #f3f4f6;
  font-family: system-ui, Arial;
}
.panel {
  background: #fff;
  border-left: 1px solid #e5e7eb;
  padding: 12px;
  overflow: auto;
}
.mapWrap { position: relative; }
#map { width: 100%; height: 100vh; }

.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.title { font-weight: 900; font-size: 18px; }
.sub { font-size: 12px; opacity: 0.7; }

.box {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
  margin-bottom: 10px;
}

label { display: block; font-size: 12px; opacity: 0.85; margin-bottom: 6px; }
input, select, .btn {
  width: 100%;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  font-size: 14px;
}
select { background: #fff; }
.btn { cursor: pointer; background: #111827; color: #fff; border-color: #111827; }

.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 6px; }
.chk { display: flex; align-items: center; gap: 8px; font-size: 12px; opacity: 0.85; margin-top: 8px; }

.kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}
.kpi {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  background: #f9fafb;
}
.kpi .k { font-size: 12px; opacity: 0.7; }
.kpi .v { font-weight: 900; font-size: 18px; }

.kpi.unstable { border-color: #fecaca; background: #fef2f2; }
.kpi.stable { border-color: #e5e7eb; background: #f8fafc; }
.kpi.nodata { border-color: #e2e8f0; background: #f8fafc; }

.legend {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
  display: grid;
  gap: 6px;
}
.legRow { display: flex; align-items: center; gap: 10px; font-size: 12px; opacity: 0.85; }
.sw { width: 18px; height: 10px; border-radius: 4px; border: 1px solid #e5e7eb; }
.sw-unstable { background: #fef2f2; border-color: #b91c1c; }
.sw-stable { background: #f8fafc; border-color: #111827; }
.sw-nodata { background: #f8fafc; border-color: #64748b; }

.mini { font-size: 12px; opacity: 0.85; margin-top: 8px; }
.muted { opacity: 0.7; }
.err { color: #b91c1c; opacity: 1; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 46vh; border-left: none; border-bottom: 1px solid #e5e7eb; }
  #map { height: 54vh; }
}
</style>

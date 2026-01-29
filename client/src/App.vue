<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Prototype – שקיעה לפי שכבת פוליגונים</div>
        </div>
        <button class="btn" @click="reload">טען מחדש</button>
      </div>

      <div class="box">
        <div class="row2">
          <div>
            <label>סף “שוקע” (mm/yr)</label>
            <input type="number" v-model.number="threshold" step="1" />
          </div>
          <div>
            <label>שם שדה קבוע (אופציונלי)</label>
            <input v-model="forcedField" placeholder="למשל mmPerYear" />
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
          <div class="kpi sink"><div class="k">שוקעים</div><div class="v">{{ stats.sinking }}</div></div>
          <div class="kpi stable"><div class="k">יציב/עולה</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.noData }}</div></div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <div class="legend">
          <div class="legRow"><span class="sw sw-sink"></span> שוקע (≤ {{ threshold }})</div>
          <div class="legRow"><span class="sw sw-stable"></span> יציב/עולה</div>
          <div class="legRow"><span class="sw sw-nodata"></span> אין נתון</div>
        </div>
      </div>

      <div class="box" v-if="selected">
        <div class="mini"><b>{{ selected.name }}</b></div>
        <div class="mini">סטטוס: <b>{{ selected.statusLabel }}</b></div>
        <div class="mini">mm/yr: <b>{{ selected.rateLabel }}</b></div>
        <div class="mini muted" v-if="selected.field">שדה: <span class="mono">{{ selected.field }}</span></div>
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

// ✅ אם הקובץ נמצא תחת src/
// path: SatMap/client/src/tlvex.geojson
const tlvGeoUrl = `${import.meta.env.BASE_URL}data/tlvex.geojson`;

/** ===== UI state ===== */
const threshold = ref(-5);
const forcedField = ref(""); // אם אתה יודע בדיוק איך נקרא השדה, שים פה
const showStable = ref(false);
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

/** ===== Helpers ===== */
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function pickRateField(props) {
  // אם המשתמש הגדיר שם שדה ידוע – לוקחים אותו
  const forced = String(forcedField.value || "").trim();
  if (forced && props && Object.prototype.hasOwnProperty.call(props, forced)) return forced;

  // אחרת: מחפשים שמות נפוצים
  const candidates = [
    "mmPerYear",
    "mm_per_year",
    "mm_yr",
    "mmYr",
    "rate",
    "velocity",
    "vel",
    "subsidence",
    "sink",
    "value",
    "v",
  ];
  for (const k of candidates) {
    if (props && Object.prototype.hasOwnProperty.call(props, k)) return k;
  }

  // fallback: אם יש מספר יחיד בתוך properties – ניקח אותו
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (toNum(v) != null) return k;
    }
  }
  return "";
}

function classify(rate) {
  if (rate == null) return "nodata";
  return rate <= threshold.value ? "sinking" : "stable";
}

function styleFor(status) {
  if (status === "sinking") {
    return { color: "#b91c1c", weight: 1.5, opacity: 0.95, fillOpacity: 0.55 };
  }
  if (status === "stable") {
    return { color: "#111827", weight: 1, opacity: 0.75, fillOpacity: 0.08 };
  }
  return { color: "#64748b", weight: 1, opacity: 0.6, fillOpacity: 0.05, dashArray: "4 4" };
}

function statusLabel(status) {
  if (status === "sinking") return "שוקע";
  if (status === "stable") return "יציב/עולה";
  return "אין נתון";
}

function getNameFromProps(props) {
  return props?.name || props?.id || props?.tile_id || props?.cell_id || "תא/פוליגון";
}

/** ===== Map init ===== */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22 }).setView([32.08, 34.78], 12);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  sinkingGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup(); // לא בהכרח מוצג
  noDataGroup = new L.FeatureGroup(); // לא בהכרח מוצג

  L.control.layers({ OSM: osm }, {}, { position: "topleft" }).addTo(map);
}

function applyVisibility() {
  if (!map) return;

  // תמיד מציגים שוקעים
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

/** ===== Load + render ===== */
async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען שכבת פוליגונים…";
  selected.value = null;

  sinkingGroup?.clearLayers?.();
  stableGroup?.clearLayers?.();
  noDataGroup?.clearLayers?.();
  allBounds = null;

  try {
    const r = await fetch(tlvGeoUrl, { cache: "no-store" });
    if (!r.ok) throw new Error("GeoJSON load failed: " + r.status);
    const gj = await r.json();

    const feats = Array.isArray(gj?.features) ? gj.features : [];
    let sinking = 0,
      stable = 0,
      noData = 0;

    for (const f of feats) {
      const props = f?.properties || {};
      const field = pickRateField(props);
      const rate = field ? toNum(props[field]) : null;
      const st = classify(rate);

      if (st === "sinking") sinking++;
      else if (st === "stable") stable++;
      else noData++;

      const layer = L.geoJSON(f, { style: styleFor(st) });

      layer.on("click", () => {
        const name = getNameFromProps(props);
        const rateLabel = rate == null ? "—" : rate.toFixed(2);
        selected.value = {
          name,
          status: st,
          statusLabel: statusLabel(st),
          rate,
          rateLabel,
          field: field || "",
        };

        layer
          .bindPopup(
            `<div style="font-family:system-ui;font-size:12px;line-height:1.45">
              <div style="font-weight:800;margin-bottom:6px">${name}</div>
              <div><b>סטטוס:</b> ${statusLabel(st)}</div>
              <div><b>mm/yr:</b> ${rate == null ? "—" : rate.toFixed(2)}</div>
            </div>`
          )
          .openPopup();
      });

      // הובר קל כדי להבין מה רואים
      layer.bindTooltip(
        rate == null ? `אין נתון` : `${rate.toFixed(2)} mm/yr`,
        { sticky: true, direction: "top", opacity: 0.9 }
      );

      // לנהל bounds
      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) allBounds = allBounds ? allBounds.extend(b) : b;
      } catch {}

      if (st === "sinking") layer.addTo(sinkingGroup);
      else if (st === "stable") layer.addTo(stableGroup);
      else layer.addTo(noDataGroup);
    }

    stats.value = { total: feats.length, sinking, stable, noData };
    applyVisibility();

    // zoom לשכבה
    if (allBounds?.isValid?.()) {
      try {
        map.fitBounds(allBounds.pad(0.08));
      } catch {}
    }

    loadMsg.value = `נטענו ${feats.length} פוליגונים.`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, sinking: 0, stable: 0, noData: 0 };
  }
}

function reload() {
  loadAndRender();
}

/** אם משנים סף/שדה – צריך לבנות מחדש סיווג וסגנון */
watch([threshold, forcedField], () => {
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
input, .btn {
  width: 100%;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  font-size: 14px;
}
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

.kpi.sink { border-color: #fecaca; background: #fef2f2; }
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
.sw-sink { background: #fef2f2; border-color: #b91c1c; }
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

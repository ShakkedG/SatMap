<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Prototype – בניינים + שקיעה + גובה עכשיו/בעבר</div>
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
            <label>שנים אחורה להשוואת גובה</label>
            <input type="number" v-model.number="yearsBack" step="0.5" min="0.5" />
            <div class="hint">ברירת מחדל מומלצת: 3 שנים</div>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>סף “שוקע” לפי Δh מצטבר (mm)</label>
            <input type="number" v-model.number="deltaThreshold" step="1" />
            <div class="hint">אם יש Δh בקובץ – משתמשים בו; אחרת Δh = v×שנים</div>
          </div>

          <div>
            <label>צביעה לפי</label>
            <select v-model="colorBy">
              <option value="status">סטטוס</option>
              <option value="rate">מהירות (mm/yr)</option>
              <option value="delta">Δh מצטבר (mm)</option>
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
          <div>
            <label>שם שדה גובה במטרים (אופציונלי)</label>
            <input v-model="forcedHeightField" placeholder="למשל height_m / elev_m / z_m" />
          </div>

          <div>
            <label>שדה שם/מזהה לבניין (אופציונלי)</label>
            <input v-model="forcedNameField" placeholder="למשל name / building_id" />
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
          <div class="kpi">
            <div class="k">סה״כ</div>
            <div class="v">{{ stats.total }}</div>
          </div>
          <div class="kpi sink">
            <div class="k">שוקעים/חשודים</div>
            <div class="v">{{ stats.sinking }}</div>
          </div>
          <div class="kpi stable">
            <div class="k">יציב/עולה</div>
            <div class="v">{{ stats.stable }}</div>
          </div>
          <div class="kpi nodata">
            <div class="k">אין נתון</div>
            <div class="v">{{ stats.noData }}</div>
          </div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <div class="legend">
          <div class="legRow"><span class="sw sw-sink"></span> שוקע/חשוד (v ≤ {{ rateThreshold }} או Δh ≤ {{ deltaThreshold }})</div>
          <div class="legRow"><span class="sw sw-stable"></span> יציב/עולה</div>
          <div class="legRow"><span class="sw sw-nodata"></span> אין נתון</div>
        </div>
      </div>

      <div class="box">
        <div class="row2">
          <div style="grid-column: 1 / -1;">
            <label>חיפוש בניין</label>
            <input v-model="searchQuery" placeholder="הקלד שם/מזהה…" />
            <div class="hint">אפשר ללחוץ על בניין במפה או מתוך הרשימה למטה</div>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>מיון רשימה</label>
            <select v-model="sortMode">
              <option value="severity">הכי בעייתיים</option>
              <option value="rate">מהירות (שלילי יותר קודם)</option>
              <option value="delta">Δh (שלילי יותר קודם)</option>
              <option value="name">שם</option>
            </select>
          </div>
          <div>
            <label>כמות ברשימה</label>
            <input type="number" v-model.number="listLimit" min="10" step="10" />
          </div>
        </div>

        <div class="list">
          <button
            v-for="item in filteredList"
            :key="item.key"
            class="listItem"
            :class="{ on: selected?.key === item.key, sink: item.status === 'sinking' }"
            @click="selectByKey(item.key, true)"
          >
            <div class="liTop">
              <div class="liName">{{ item.name }}</div>
              <div class="badge" :class="item.status">{{ item.statusLabel }}</div>
            </div>
            <div class="liMeta">
              <span class="mono">v: {{ fmt(item.rate) }}</span>
              <span class="mono">Δh: {{ fmt(item.deltaMm) }}</span>
              <span class="mono">h: {{ fmtM(item.heightNowM) }}</span>
            </div>
          </button>

          <div class="mini muted" v-if="!filteredList.length">אין תוצאות לחיפוש/סינון.</div>
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
            <div class="k">גובה עכשיו (m)</div>
            <div class="v mono">{{ selected.heightNowLabel }}</div>
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

        <div class="mini muted" v-if="selected.heightNowM == null">
          אין שדה גובה בקובץ (מטרים). אם תוסיף `height_m`/`elev_m`—יופיע פה “גובה עכשיו/בעבר”.
        </div>

        <div class="mini muted" v-if="selected.rateField">שדה מהירות: <span class="mono">{{ selected.rateField }}</span></div>
        <div class="mini muted" v-if="selected.deltaField">שדה Δh: <span class="mono">{{ selected.deltaField }}</span></div>
        <div class="mini muted" v-if="selected.heightField">שדה גובה: <span class="mono">{{ selected.heightField }}</span></div>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, watch, computed } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// === GeoJSON (מומלץ לשים ב-public/data/tlvex.geojson) ===
const tlvGeoUrl = `${import.meta.env.BASE_URL}data/tlvex.geojson`;

/** ===== UI state ===== */
const yearsBack = ref(3);
const rateThreshold = ref(-5);
const deltaThreshold = ref(-10);
const colorBy = ref("status");

const forcedRateField = ref("");
const forcedDeltaField = ref("");
const forcedHeightField = ref("");
const forcedNameField = ref("");

const showStable = ref(true);
const showNoData = ref(false);

const searchQuery = ref("");
const sortMode = ref("severity");
const listLimit = ref(60);

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

const layerByKey = new Map(); // key -> layerGroup created by L.geoJSON (for one feature)
const metaByKey = new Map();  // key -> computed metadata for list/selection

let lastSelectedLayer = null;

/** ===== Helpers ===== */
function clamp01(x) {
  return Math.max(0, Math.min(1, x));
}
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmt(n) {
  return n == null ? "—" : Number(n).toFixed(2);
}
function fmt1(n) {
  return n == null ? "—" : Number(n).toFixed(1);
}
function fmtM(n) {
  return n == null ? "—" : Number(n).toFixed(2) + "m";
}
function escHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pickFieldByForcedOrCandidates(props, forcedValue, candidates) {
  const forced = String(forcedValue || "").trim();
  if (forced && props && Object.prototype.hasOwnProperty.call(props, forced)) return forced;

  for (const k of candidates) {
    if (props && Object.prototype.hasOwnProperty.call(props, k)) return k;
  }
  return "";
}

function pickRateField(props) {
  // forced
  const forced = String(forcedRateField.value || "").trim();
  if (forced && props && Object.prototype.hasOwnProperty.call(props, forced)) return forced;

  // candidates
  const candidates = [
    "mmPerYear","mm_per_year","mm_yr","mmYr",
    "rate","velocity","vel","subsidence","sink","value","v"
  ];
  for (const k of candidates) {
    if (props && Object.prototype.hasOwnProperty.call(props, k)) return k;
  }

  // fallback: pick first numeric-ish
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (toNum(v) != null) return k;
    }
  }
  return "";
}

function pickDeltaField(props) {
  return pickFieldByForcedOrCandidates(
    props,
    forcedDeltaField.value,
    [
      "dH_mm","dh_mm","delta_mm","delta",
      "deltaH","delta_h","heightChange","height_change",
      "disp_mm","displacement_mm","cumulative_mm","cum_mm",
      "deformation_mm","subs_mm"
    ]
  );
}

function pickHeightField(props) {
  return pickFieldByForcedOrCandidates(
    props,
    forcedHeightField.value,
    [
      "height_m","height","h_m",
      "elev_m","elevation_m","elevation",
      "z_m","z",
      "roof_m","roof_height","building_h","building_height"
    ]
  );
}

function pickName(props, idx) {
  const forced = String(forcedNameField.value || "").trim();
  if (forced && props && props[forced] != null) return String(props[forced]);

  return (
    props?.name ??
    props?.building_id ??
    props?.id ??
    props?.tile_id ??
    props?.cell_id ??
    `בניין ${idx + 1}`
  );
}

function featureKey(props, idx) {
  // key יציב לבחירה/רשימה
  const base =
    props?.building_id ??
    props?.id ??
    props?.tile_id ??
    props?.cell_id ??
    null;

  // אם אין מזהה טוב, נייצר key לפי אינדקס
  return base != null ? String(base) : `f_${idx}`;
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
  // "שוקע/חשוד" אם אחד מהם מצביע על שקיעה מעבר לסף
  const byRate = rate != null && rate <= rateThreshold.value;
  const byDelta = deltaMm != null && deltaMm <= deltaThreshold.value;

  if (rate == null && deltaMm == null) return "nodata";
  return (byRate || byDelta) ? "sinking" : "stable";
}

function statusLabel(status) {
  if (status === "sinking") return "שוקע/חשוד";
  if (status === "stable") return "יציב/עולה";
  return "אין נתון";
}

function severityScore(rate, deltaMm) {
  // ככל שיותר שלילי ביחס לסף -> יותר בעייתי
  const s1 =
    rate == null || rateThreshold.value === 0
      ? 0
      : Math.max(0, (rateThreshold.value - rate) / Math.max(1e-6, Math.abs(rateThreshold.value)));

  const s2 =
    deltaMm == null || deltaThreshold.value === 0
      ? 0
      : Math.max(0, (deltaThreshold.value - deltaMm) / Math.max(1e-6, Math.abs(deltaThreshold.value)));

  // נותנים עדיפות קלה לדלתא (כי מצטבר)
  return s1 * 0.9 + s2 * 1.1;
}

function styleFor(status, rate, deltaMm) {
  if (status === "nodata") {
    return { color: "#64748b", weight: 1, opacity: 0.65, fillOpacity: 0.06, dashArray: "4 4" };
  }

  if (status === "stable") {
    return { color: "#111827", weight: 1, opacity: 0.65, fillOpacity: 0.08 };
  }

  // sinking: צבע לפי חומרה (בהתאם למה שנבחר לצביעה)
  let metric = null;
  let thr = null;

  if (colorBy.value === "rate") {
    metric = rate;
    thr = rateThreshold.value;
  } else if (colorBy.value === "delta") {
    metric = deltaMm;
    thr = deltaThreshold.value;
  } else {
    // status: ניקח את החמור מבין שניהם
    const sR = severityScore(rate, null);
    const sD = severityScore(null, deltaMm);
    metric = sD >= sR ? deltaMm : rate;
    thr = sD >= sR ? deltaThreshold.value : rateThreshold.value;
  }

  let s = 0;
  if (metric != null && thr != null && thr !== 0) {
    const ratio = Math.abs(metric / thr); // שניים שליליים -> ratio חיובי
    // יותר גדול = יותר חמור
    s = clamp01((ratio - 1) / 2); // 1..3 -> 0..1
  } else {
    s = 0.5;
  }

  const fillOpacity = 0.35 + s * 0.35;
  const weight = 1.4 + s * 1.2;

  // 3 דרגות אדום
  const stroke =
    s >= 0.75 ? "#7f1d1d" :
    s >= 0.40 ? "#b91c1c" :
    "#dc2626";

  return { color: stroke, weight, opacity: 0.95, fillOpacity };
}

function highlightLayer(layer) {
  try {
    layer.setStyle?.({ weight: 3, opacity: 1, fillOpacity: 0.55 });
    layer.bringToFront?.();
  } catch {}
}

function unhighlightLayer(layer, status, rate, deltaMm) {
  try {
    layer.setStyle?.(styleFor(status, rate, deltaMm));
  } catch {}
}

/** ===== Map init ===== */
function initMap() {
  map = L.map("map", {
    zoomControl: true,
    maxZoom: 22,
    preferCanvas: true,
  }).setView([32.08, 34.78], 12);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const esri = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 22,
      attribution: "&copy; Esri",
    }
  );

  sinkingGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup();
  noDataGroup = new L.FeatureGroup();

  L.control.layers({ OSM: osm, "Satellite (Esri)": esri }, {}, { position: "topleft" }).addTo(map);
  L.control.scale({ metric: true, imperial: false, position: "bottomleft" }).addTo(map);
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

/** ===== Selection ===== */
function clearSelection() {
  if (lastSelectedLayer && selected.value) {
    const m = metaByKey.get(selected.value.key);
    if (m) unhighlightLayer(lastSelectedLayer, m.status, m.rate, m.deltaMm);
  }
  lastSelectedLayer = null;
  selected.value = null;
}

function selectByKey(key, zoomTo = false) {
  const meta = metaByKey.get(key);
  const layer = layerByKey.get(key);
  if (!meta || !layer) return;

  // unhighlight previous
  if (lastSelectedLayer && selected.value) {
    const prev = metaByKey.get(selected.value.key);
    if (prev) unhighlightLayer(lastSelectedLayer, prev.status, prev.rate, prev.deltaMm);
  }

  selected.value = {
    key,
    name: meta.name,
    status: meta.status,
    statusLabel: meta.statusLabel,
    rate: meta.rate,
    rateLabel: meta.rate == null ? "—" : meta.rate.toFixed(2),
    deltaMm: meta.deltaMm,
    deltaLabel: meta.deltaMm == null ? "—" : meta.deltaMm.toFixed(1),
    deltaField: meta.deltaField,
    deltaSourceLabel: meta.deltaSource === "field" ? "שדה בקובץ" : meta.deltaSource === "rate*years" ? "חישוב v×שנים" : "",
    heightNowM: meta.heightNowM,
    heightNowLabel: meta.heightNowM == null ? "—" : meta.heightNowM.toFixed(2),
    heightPastM: meta.heightPastM,
    heightPastLabel: meta.heightPastM == null ? "—" : meta.heightPastM.toFixed(2),
    heightDiffM: meta.heightDiffM,
    heightDiffLabel: meta.heightDiffM == null ? "—" : meta.heightDiffM.toFixed(4),
    rateField: meta.rateField,
    heightField: meta.heightField,
  };

  // highlight current
  lastSelectedLayer = layer;
  highlightLayer(layer);

  if (zoomTo && meta.bounds && meta.bounds.isValid?.()) {
    try {
      map.fitBounds(meta.bounds.pad(0.12));
    } catch {}
  }

  // open popup
  try {
    layer.openPopup?.();
  } catch {}
}

function fitToLayer() {
  if (!map) return;
  if (allBounds?.isValid?.()) {
    try {
      map.fitBounds(allBounds.pad(0.08));
    } catch {}
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

  layerByKey.clear();
  metaByKey.clear();

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

      const heightField = pickHeightField(props);
      const heightNowM = heightField ? toNum(props[heightField]) : null;

      // אם יש גובה מוחלט וגם Δh, נחשב גובה בעבר:
      // heightPast = heightNow - (deltaMm/1000)
      const heightPastM =
        heightNowM == null || deltaMm == null ? null : (heightNowM - (deltaMm / 1000));

      const heightDiffM =
        heightNowM == null || heightPastM == null ? null : (heightNowM - heightPastM); // אמור להיות deltaMm/1000

      const status = classify(rate, deltaMm);
      const label = statusLabel(status);

      if (status === "sinking") sinking++;
      else if (status === "stable") stable++;
      else noData++;

      // Create layer (one feature)
      const layer = L.geoJSON(f, {
        style: styleFor(status, rate, deltaMm),
        interactive: true,
      });

      // bounds / meta
      let bounds = null;
      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) {
          bounds = b;
          allBounds = allBounds ? allBounds.extend(b) : b;
        }
      } catch {}

      // tooltip & popup
      const tip = `v: ${fmt(rate)} mm/yr | Δh: ${fmt1(deltaMm)} mm | h: ${heightNowM == null ? "—" : heightNowM.toFixed(2)} m`;
      layer.bindTooltip(tip, { sticky: true, direction: "top", opacity: 0.92 });

      const popupHtml = `
        <div style="font-family:system-ui;font-size:12px;line-height:1.55;min-width:220px">
          <div style="font-weight:900;margin-bottom:6px">${escHtml(name)}</div>
          <div><b>סטטוס:</b> ${escHtml(label)}</div>
          <div><b>מהירות:</b> ${rate == null ? "—" : rate.toFixed(2)} mm/yr</div>
          <div><b>Δh ב-${Number(yearsBack.value).toFixed(1)} שנים:</b> ${deltaMm == null ? "—" : deltaMm.toFixed(1)} mm</div>
          <div style="margin-top:6px"><b>גובה עכשיו:</b> ${heightNowM == null ? "—" : heightNowM.toFixed(2)} m</div>
          <div><b>גובה בעבר:</b> ${heightPastM == null ? "—" : heightPastM.toFixed(2)} m</div>
          <div><b>Δגובה (m):</b> ${heightDiffM == null ? "—" : heightDiffM.toFixed(4)}</div>
          <div style="opacity:.7;margin-top:6px">מקור Δh: ${
            deltaObj.source === "field" ? "שדה בקובץ" : deltaObj.source === "rate*years" ? "חישוב v×שנים" : "—"
          }</div>
        </div>
      `;
      layer.bindPopup(popupHtml);

      // click -> select
      layer.on("click", () => selectByKey(key, false));

      // store meta for list
      metaByKey.set(key, {
        key,
        name,
        status,
        statusLabel: label,
        rate,
        deltaMm,
        rateField: rateField || "",
        deltaField: deltaObj.deltaField || "",
        deltaSource: deltaObj.source,
        heightNowM,
        heightPastM,
        heightDiffM,
        heightField: heightField || "",
        bounds,
        score: severityScore(rate, deltaMm),
      });

      // store layer reference (the L.geoJSON layer)
      layerByKey.set(key, layer);

      // add to group
      if (status === "sinking") layer.addTo(sinkingGroup);
      else if (status === "stable") layer.addTo(stableGroup);
      else layer.addTo(noDataGroup);
    }

    stats.value = { total: feats.length, sinking, stable, noData };
    applyVisibility();

    allBoundsValid.value = !!allBounds?.isValid?.();
    if (allBoundsValid.value) {
      try {
        map.fitBounds(allBounds.pad(0.08));
      } catch {}
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

/** ===== List (search + sort) ===== */
const filteredList = computed(() => {
  const q = String(searchQuery.value || "").trim().toLowerCase();

  let arr = Array.from(metaByKey.values());

  // filter: prioritize sinking by default but still show all
  if (q) {
    arr = arr.filter((x) => String(x.name).toLowerCase().includes(q) || String(x.key).toLowerCase().includes(q));
  }

  // sort
  const mode = sortMode.value;
  arr.sort((a, b) => {
    if (mode === "name") return String(a.name).localeCompare(String(b.name), "he");
    if (mode === "rate") return (a.rate ?? 999999) - (b.rate ?? 999999); // הכי שלילי קודם
    if (mode === "delta") return (a.deltaMm ?? 999999) - (b.deltaMm ?? 999999);
    // severity
    return (b.score ?? 0) - (a.score ?? 0);
  });

  // show sinking first when severity or rate/delta
  if (mode !== "name") {
    arr.sort((a, b) => {
      const as = a.status === "sinking" ? 0 : a.status === "stable" ? 1 : 2;
      const bs = b.status === "sinking" ? 0 : b.status === "stable" ? 1 : 2;
      if (as !== bs) return as - bs;
      // then by selected mode
      if (mode === "rate") return (a.rate ?? 999999) - (b.rate ?? 999999);
      if (mode === "delta") return (a.deltaMm ?? 999999) - (b.deltaMm ?? 999999);
      return (b.score ?? 0) - (a.score ?? 0);
    });
  }

  const lim = Math.max(10, Number(listLimit.value) || 60);
  return arr.slice(0, lim);
});

/** ===== Reactivity ===== */
watch([rateThreshold, deltaThreshold, yearsBack, forcedRateField, forcedDeltaField, forcedHeightField, forcedNameField, colorBy], () => {
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
  grid-template-columns: 440px 1fr;
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
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.topBtns {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.title { font-weight: 900; font-size: 18px; }
.sub { font-size: 12px; opacity: 0.72; margin-top: 2px; }

.box {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 10px;
  background: #fff;
  margin-bottom: 10px;
}

label {
  display: block;
  font-size: 12px;
  opacity: 0.85;
  margin-bottom: 6px;
}

input, select, .btn {
  width: 100%;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  font-size: 14px;
  background: #fff;
}

select { cursor: pointer; }

.btn {
  cursor: pointer;
  background: #111827;
  color: #fff;
  border-color: #111827;
  font-weight: 700;
}

.btn.ghost {
  background: #fff;
  color: #111827;
  border-color: #e5e7eb;
}

.btn.small {
  padding: 8px 10px;
  font-size: 12px;
  border-radius: 10px;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 6px;
}

.chk {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  opacity: 0.9;
  margin-top: 8px;
}

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

.legRow { display: flex; align-items: center; gap: 10px; font-size: 12px; opacity: 0.9; }
.sw { width: 18px; height: 10px; border-radius: 4px; border: 1px solid #e5e7eb; }
.sw-sink { background: #fef2f2; border-color: #b91c1c; }
.sw-stable { background: #f8fafc; border-color: #111827; }
.sw-nodata { background: #f8fafc; border-color: #64748b; }

.list {
  margin-top: 10px;
  display: grid;
  gap: 8px;
  max-height: 280px;
  overflow: auto;
  padding-right: 2px;
}

.listItem {
  width: 100%;
  text-align: right;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.05s ease, border-color 0.1s ease;
}

.listItem:hover { transform: translateY(-1px); border-color: #cbd5e1; }
.listItem.on { border-color: #111827; box-shadow: 0 0 0 2px rgba(17,24,39,0.08) inset; }
.listItem.sink { border-color: #fecaca; background: #fff7f7; }

.liTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.liName {
  font-weight: 900;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  white-space: nowrap;
}
.badge.sinking { border-color: #fecaca; background: #fef2f2; color: #991b1b; }
.badge.stable { border-color: #e5e7eb; background: #f8fafc; color: #111827; }
.badge.nodata { border-color: #e2e8f0; background: #f8fafc; color: #334155; }

.liMeta {
  display: flex;
  gap: 10px;
  margin-top: 8px;
  opacity: 0.9;
  flex-wrap: wrap;
}

.selHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.selGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}

.selCard {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #f9fafb;
}

.selCard .k { font-size: 12px; opacity: 0.7; }
.selCard .v { font-weight: 900; font-size: 14px; margin-top: 4px; }
.selCard .v.danger { color: #991b1b; }

.mini { font-size: 12px; opacity: 0.9; margin-top: 8px; }
.muted { opacity: 0.72; }
.err { color: #b91c1c; opacity: 1; }
.hint { font-size: 11px; opacity: 0.68; margin-top: 6px; }

.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 52vh; border-left: none; border-bottom: 1px solid #e5e7eb; }
  #map { height: 48vh; }
}
</style>

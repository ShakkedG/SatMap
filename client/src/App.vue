<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ closed: !panelOpen }">
      <div class="panelHeader">
        <div class="brand">
          <div class="title">SatMap</div>
          <div class="sub">בניינים + סטטיסטיקות InSAR + Tiles (מוכן לפרודקשן)</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ on: activeTab === 'controls' }" @click="activeTab='controls'">בקרה</button>
        <button class="tab" :class="{ on: activeTab === 'legend' }" @click="activeTab='legend'">מקרא</button>
        <button class="tab" :class="{ on: activeTab === 'about' }" @click="activeTab='about'">הסבר</button>
      </div>

      <!-- CONTROLS -->
      <section v-show="activeTab==='controls'" class="tabPage">
        <div class="card">
          <div class="cardTitle">שכבות ותצוגה</div>

          <div class="row2">
            <div>
              <label>רקע</label>
              <select v-model="ui.baseMap" @change="applyBaseLayer()">
                <option value="imagery">לוויין (Esri)</option>
                <option value="osm">מפה (OSM)</option>
              </select>
              <div class="hint mini">ברירת מחדל: לוויין</div>
            </div>

            <div>
              <label>מקור בניינים</label>
              <select v-model="ui.buildingsMode" @change="applyBuildingsSource(true)">
                <option value="auto">אוטומטי (מומלץ)</option>
                <option value="tiles">Vector Tiles (שרת)</option>
                <option value="geojson">GeoJSON (קובץ)</option>
                <option value="osm">OSM סביב קליק (fallback)</option>
                <option value="none">ללא</option>
              </select>
              <div class="hint mini">
                בפועל: <b>{{ buildingsEffectiveLabel }}</b>
              </div>
            </div>
          </div>

          <div class="row2">
            <div class="colSpan2">
              <label>שרת Tiles (Render)</label>
              <input v-model.trim="paths.tilesBase" type="text" />
              <div class="hint mini">
                בדיקה: <code>{{ sanitizeUrl(paths.tilesBase) }}/status</code>
              </div>

              <div class="statusBox" style="margin-top:8px;">
                <div class="statusLine">
                  <span class="statusDot" :class="{ on: tilesReady }"></span>
                  <span>
                    Tiles:
                    <span v-if="tilesChecking">בודק…</span>
                    <span v-else>{{ tilesReady ? "מוכן (ready=true)" : "לא מוכן (ready=false/לא זמין)" }}</span>
                  </span>
                </div>
                <div class="hint mini" v-if="tilesMsg">{{ tilesMsg }}</div>
              </div>

              <div class="rowBtns" style="margin-top:8px;">
                <button class="btn ghost" @click="checkTilesStatus" :disabled="tilesChecking">בדוק שרת</button>
                <button class="btn" @click="applyBuildingsSource(true)" :disabled="loading">החל</button>
              </div>
            </div>
          </div>

          <div class="rowBtns">
            <button class="btn ghost" @click="fitToLayer" :disabled="!mapReady">התמקד (שכבה/ישראל)</button>
            <button class="btn" @click="recolorAll" :disabled="!mapReady || loading">רענן צבעים</button>
          </div>

          <div class="hint" v-if="ui.buildingsMode==='osm' || buildingsEffective==='osm'">
            במצב OSM: לחץ על המפה כדי למשוך בניינים סביב הנקודה (שימוש זמני בלבד).
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">GeoJSON (רק אם משתמשים במקור קובץ)</div>

          <div class="row2">
            <div class="colSpan2">
              <label>GeoJSON (בניינים + Vel_mean + coer_mean + Vel_count)</label>
              <input v-model.trim="paths.buildings" type="text" :disabled="buildingsEffective !== 'geojson'" />
              <div class="hint mini">
                הקובץ צריך להיות בתוך <b>client/public/data</b> ואז הנתיב יהיה:
                <code>{{ baseUrl }}data/buildings_joined.geojson</code>
              </div>
            </div>
          </div>

          <div class="statusBox">
            <div class="statusLine">
              <span class="statusDot" :class="{ on: geojsonLoaded }"></span>
              <span>{{ geojsonLoaded ? "GeoJSON נטען" : "GeoJSON לא נטען" }}</span>
            </div>
            <div class="hint mini" v-if="lastLoadedUrl">
              נטען מ: <code>{{ lastLoadedUrl }}</code>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">ספים לחישוב סטטוס</div>

          <div class="row2">
            <div>
              <label>סף “שוקע/חשוד” v (mm/yr)</label>
              <input v-model.number="params.thrVel" type="number" step="0.5" />
              <div class="hint mini">יותר שלילי = יותר שקיעה</div>
            </div>
            <div>
              <label>איכות מינימלית (coherence)</label>
              <input v-model.number="params.thrCoh" type="number" step="0.05" min="0" max="1" />
              <div class="hint mini">0–1. מתחת לסף = איכות נמוכה</div>
            </div>
          </div>

          <div class="row2">
            <div>
              <label>מינימום נקודות לבניין (Vel_count)</label>
              <input v-model.number="params.minPts" type="number" step="1" min="1" />
              <div class="hint mini">מעט נקודות = פחות אמין</div>
            </div>

            <label class="check">
              <input v-model="ui.filterSubs" type="checkbox" />
              הצג רק “שוקע/חשוד”
            </label>
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">מידע על בניין</div>

          <div v-if="!selected" class="emptyState">
            <div class="emptyIcon">⌖</div>
            <div class="emptyText">
              <b>רחף</b> מעל בניין כדי לראות טולטיפ.<br />
              <b>לחץ</b> על בניין כדי להצמיד כאן נתונים.
            </div>
          </div>

          <div v-else class="infoCard">
            <div class="infoTop">
              <div class="idBlock">
                <div class="idLabel">מזהה</div>
                <div class="idValue">{{ selected.id }}</div>
              </div>

              <div class="badges">
                <span class="badge" :class="'b-' + selected.st.status">
                  {{ statusLabel(selected.st.status) }}
                </span>
                <span v-if="qualityTag" class="badge ghost">
                  {{ qualityTag }}
                </span>
              </div>
            </div>

            <div class="kvGrid">
              <div class="kv">
                <div class="k">Vel_mean</div>
                <div class="v">{{ fmtVel(selected.st.velMean) }}</div>
                <div class="u">mm/yr</div>
              </div>

              <div class="kv">
                <div class="k">coer_mean</div>
                <div class="v">{{ fmtCoh(selected.st.cohMean) }}</div>
                <div class="u">0–1</div>
              </div>

              <div class="kv">
                <div class="k">Vel_count</div>
                <div class="v">{{ fmtCount(selected.st.count) }}</div>
                <div class="u">נק׳</div>
              </div>

              <div class="kv">
                <div class="k">סף שקיעה</div>
                <div class="v">{{ params.thrVel }}</div>
                <div class="u">mm/yr</div>
              </div>
            </div>

            <div class="meterWrap" v-if="selected.st.cohMean != null">
              <div class="meterTop">
                <div class="meterLabel">איכות (coherence)</div>
                <div class="meterValue" :class="{ bad: !cohOk }">
                  {{ fmtCoh(selected.st.cohMean) }}
                  <span class="miniNote">({{ cohOk ? "עבר סף" : "מתחת לסף" }})</span>
                </div>
              </div>
              <div class="meter">
                <div class="meterFill" :style="{ width: Math.max(0, Math.min(1, selected.st.cohMean)) * 100 + '%' }"></div>
                <div class="meterThr" :style="{ left: Math.max(0, Math.min(1, params.thrCoh)) * 100 + '%' }" title="סף"></div>
              </div>
            </div>

            <div class="checks">
              <div class="checkRow" :class="{ ok: countOk, bad: !countOk }">
                <span class="dot"></span>
                מינימום נקודות: {{ selected.st.count }} / {{ params.minPts }}
              </div>
              <div class="checkRow" :class="{ ok: cohOk, bad: !cohOk }">
                <span class="dot"></span>
                איכות מינימלית: {{ fmtCoh(selected.st.cohMean) }} / {{ params.thrCoh }}
              </div>
            </div>

            <div class="miniExplain">
              <span class="miniTag">low_quality</span> = coherence נמוך או מעט נקודות<br />
              <span class="miniTag">no_data</span> = חסרים נתונים לבניין במקור הנתונים
            </div>

            <div class="rowBtns" style="margin-top:10px;">
              <button class="btn ghost" @click="clearSelection">נקה בחירה</button>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">מצב</div>
          <div class="statusBox">
            <div class="statusLine">
              <span class="statusDot" :class="{ on: mapReady }"></span>
              <span>{{ status }}</span>
            </div>
            <div class="hint mini" v-if="loading">
              {{ loadingText }}
            </div>
          </div>
        </div>
      </section>

      <!-- LEGEND -->
      <section v-show="activeTab==='legend'" class="tabPage">
        <div class="card">
          <div class="cardTitle">מקרא צבעים</div>

          <div class="legend">
            <div class="legRow"><span class="sw s-subs"></span> שוקע (v &lt; סף)</div>
            <div class="legRow"><span class="sw s-sus"></span> חשוד (קרוב לסף)</div>
            <div class="legRow"><span class="sw s-stable"></span> יציב</div>
            <div class="legRow"><span class="sw s-lowq"></span> איכות נמוכה (coh/נק׳)</div>
            <div class="legRow"><span class="sw s-nodata"></span> אין נתונים</div>
          </div>

          <div class="hint mini">
            טיפ: כדי לראות בניינים מ־Tiles — לרוב צריך זום <b>15–16</b>.
          </div>
        </div>
      </section>

      <!-- ABOUT -->
      <section v-show="activeTab==='about'" class="tabPage">
        <div class="card">
          <div class="cardTitle">איך זה עובד</div>
          <div class="about">
            <p>
              האתר מציג שכבת בניינים ומחשב לכל בניין סטטוס על בסיס השדות:
              <b>Vel_mean</b>, <b>coer_mean</b>, <b>Vel_count</b>.
            </p>
            <p>
              לפרודקשן: שכבת הבניינים צריכה להיות <b>Vector Tiles</b> (מהשרת). ה-GeoJSON נשאר רק כ-fallback/בדיקות.
            </p>
          </div>
        </div>
      </section>
    </aside>

    <main class="main">
      <div id="map"></div>

      <!-- Tooltip -->
      <div ref="hoverRef" v-show="hover.show" class="tip" :style="tipStyle" v-html="hover.html"></div>

      <div v-if="loading" class="loadingOverlay">
        <div class="spinner"></div>
        <div class="loadingText">{{ loadingText }}</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from "vue";

/**
 * חשוב: זה מוסיף VectorGrid ל-Leaflet הגלובלי (window.L).
 * דורש שהוספת leaflet.vectorgrid ל-package.json
 */
import "leaflet.vectorgrid/dist/Leaflet.VectorGrid.bundled.js";

const baseUrl = import.meta.env.BASE_URL || "/";

const paths = reactive({
  // חשוב: בלי סלש בסוף
  buildings: baseUrl + "data/buildings_joined.geojson",
  tilesBase: "https://satmap-tiles.onrender.com",
});

const params = reactive({
  thrVel: -2,
  thrCoh: 0.35,
  minPts: 8,
});

const ui = reactive({
  filterSubs: false,
  baseMap: "imagery",         // imagery | osm
  buildingsMode: "auto",      // auto | tiles | geojson | osm | none
});

const panelOpen = ref(true);
const activeTab = ref("controls");

const status = ref("טוען…");
const loading = ref(false);
const loadingText = ref("טוען…");

const tilesReady = ref(false);
const tilesChecking = ref(false);
const tilesMsg = ref("");

const selected = ref(null); // { id, st, feature?, props? }

const hover = reactive({ show: false, x: 0, y: 0, html: "", _flip: false, _w: 260 });
const hoverRef = ref(null);

const mapReady = ref(false);
const geojsonLoaded = ref(false);

let map = null;
let baseLayer = null;
let labelsLayer = null;

let buildingsLayer = null;   // GeoJSON layer OR VectorGrid layer
let buildingsFC = null;      // GeoJSON cache
let osmLayer = null;         // OSM-around-click fallback

let reloadTimer = null;
let lastLoadedUrl = ref("");

let lastHoverId = null;
let osmAbort = null;
let lastOsmFetchAt = 0;

const L = () => window.L;

/* ---------- helpers ---------- */
function setLoading(on, text = "טוען…") {
  loading.value = on;
  loadingText.value = text;
}
function setStatus(msg) {
  status.value = msg;
}
function sanitizeUrl(u) {
  return String(u || "").trim().replace(/\/+$/, "");
}
function isFiniteNum(v) {
  return typeof v === "number" && Number.isFinite(v);
}

function normFC(any) {
  if (!any) throw new Error("GeoJSON ריק");
  if (any.type === "FeatureCollection") return any;
  if (any.type === "Feature") return { type: "FeatureCollection", features: [any] };
  throw new Error("פורמט GeoJSON לא נתמך");
}

function buildingIdFromProps(p) {
  return (
    p?.id ??
    p?.ID ??
    p?.objectid ??
    p?.OBJECTID ??
    p?.fid ??
    p?.FID ??
    p?.osm_id ??
    p?.Name ??
    p?.name ??
    "building"
  );
}
function buildingId(f) {
  const p = f?.properties || {};
  return buildingIdFromProps(p);
}

/* מיפוי שמות שדות בצורה גמישה (case-insensitive + וריאנטים נפוצים) */
function getNum(props, keys) {
  if (!props) return null;

  for (const k of keys) {
    if (props[k] != null) {
      const v = Number(props[k]);
      if (Number.isFinite(v)) return v;
    }
  }

  // case-insensitive fallback
  const lower = Object.keys(props).reduce((acc, k) => ((acc[String(k).toLowerCase()] = k), acc), {});
  for (const k of keys) {
    const real = lower[String(k).toLowerCase()];
    if (real && props[real] != null) {
      const v = Number(props[real]);
      if (Number.isFinite(v)) return v;
    }
  }
  return null;
}
function getInt(props, keys) {
  const v = getNum(props, keys);
  if (v == null) return null;
  const n = Math.round(v);
  return Number.isFinite(n) ? n : null;
}

function deriveStatsFromProps(featureLike) {
  const p = featureLike?.properties || {};

  const velMean = getNum(p, ["Vel_mean", "vel_mean", "VEL_MEAN", "velocity_mean", "v_mean", "velMean"]);
  const cohMean = getNum(p, ["coer_mean", "Coer_mean", "COER_MEAN", "coh_mean", "coherence_mean", "cohMean"]);
  const count = getInt(p, ["Vel_count", "vel_count", "VEL_COUNT", "count", "n_points", "n", "VelCount"]);

  if (!isFiniteNum(velMean) || !Number.isFinite(count) || count <= 0) {
    return { status: "no_data", velMean: velMean ?? null, cohMean: cohMean ?? null, count: count ?? 0 };
  }

  const cohOkLocal = (cohMean == null) ? true : (cohMean >= Number(params.thrCoh));
  const cntOkLocal = count >= Number(params.minPts);

  let status = "stable";
  if (!cohOkLocal || !cntOkLocal) status = "low_quality";
  else if (velMean < Number(params.thrVel)) status = "subsiding";
  else if (Math.abs(velMean - Number(params.thrVel)) <= 0.5) status = "suspect";
  else status = "stable";

  return { status, velMean, cohMean: cohMean ?? null, count };
}

function statusLabel(s) {
  const m = {
    subsiding: "שוקע",
    suspect: "חשוד",
    stable: "יציב",
    low_quality: "איכות נמוכה",
    no_data: "אין נתונים",
  };
  return m[s] || s;
}

/* צבעים: cache קטן כדי לא לקרוא getComputedStyle מיליון פעם */
let cachedColors = null;
function refreshColorsCache() {
  const css = getComputedStyle(document.documentElement);
  cachedColors = {
    subsiding: css.getPropertyValue("--c-subs").trim(),
    suspect: css.getPropertyValue("--c-sus").trim(),
    stable: css.getPropertyValue("--c-stable").trim(),
    low_quality: css.getPropertyValue("--c-lowq").trim(),
    no_data: css.getPropertyValue("--c-nodata").trim(),
  };
}
function styleByStatus(statusName) {
  if (!cachedColors) refreshColorsCache();
  const c = cachedColors[statusName] || cachedColors.no_data;

  return {
    weight: 2,
    opacity: 0.95,
    fillOpacity: 0.25,
    color: c,
    fillColor: c,
  };
}

function shouldShowByFilter(st) {
  // רק שוקע/חשוד
  return st?.status === "subsiding" || st?.status === "suspect";
}

function tipHtml(st) {
  return `
    <div class="tipTitle">${statusLabel(st.status)}</div>
    <div class="tipGrid">
      <div><span class="k">Vel_mean</span> <span class="v">${fmtVel(st.velMean)}</span> <span class="u">mm/yr</span></div>
      <div><span class="k">coer_mean</span> <span class="v">${fmtCoh(st.cohMean)}</span></div>
      <div><span class="k">Vel_count</span> <span class="v">${fmtCount(st.count)}</span></div>
    </div>
  `;
}

function fmtVel(v) {
  return (v == null || !Number.isFinite(v)) ? "—" : Number(v).toFixed(2);
}
function fmtCoh(v) {
  return (v == null || !Number.isFinite(v)) ? "—" : Number(v).toFixed(2);
}
function fmtCount(v) {
  return (v == null || !Number.isFinite(v)) ? "—" : String(v);
}

/* ---------- UI computed ---------- */
const cohOk = computed(() => {
  if (!selected.value) return true;
  const c = selected.value.st.cohMean;
  return c == null ? true : c >= Number(params.thrCoh);
});
const countOk = computed(() => {
  if (!selected.value) return true;
  return Number(selected.value.st.count) >= Number(params.minPts);
});
const qualityTag = computed(() => {
  if (!selected.value) return "";
  if (selected.value.st.status === "low_quality") return "low_quality";
  if (selected.value.st.status === "no_data") return "no_data";
  return "";
});

const buildingsEffective = ref("geojson"); // geojson | tiles | osm | none
const buildingsEffectiveLabel = computed(() => {
  const m = {
    geojson: "GeoJSON (קובץ)",
    tiles: "Vector Tiles (שרת)",
    osm: "OSM סביב קליק",
    none: "ללא",
  };
  return m[buildingsEffective.value] || buildingsEffective.value;
});

/* tooltip positioning */
function onMouseMove(ev) {
  hover.x = ev.clientX;
  hover.y = ev.clientY;
}
function fixTipFlip() {
  const el = hoverRef.value;
  if (!el) return;
  hover._w = el.offsetWidth || 260;

  const pad = 12;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const right = hover.x + hover._w + pad;
  hover._flip = right > vw;

  // prevent vertical overflow (simple)
  if (hover.y + 140 > vh) hover.y = Math.max(pad, vh - 140);
}
const tipStyle = computed(() => {
  const pad = 14;
  const x = hover._flip ? (hover.x - hover._w - pad) : (hover.x + pad);
  const y = hover.y + pad;
  return { transform: `translate(${x}px, ${y}px)` };
});

/* ---------- base layers ---------- */
function applyBaseLayer() {
  if (!map) return;

  if (baseLayer) { try { map.removeLayer(baseLayer); } catch {} baseLayer = null; }
  if (labelsLayer) { try { map.removeLayer(labelsLayer); } catch {} labelsLayer = null; }

  if (ui.baseMap === "osm") {
    baseLayer = L().tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
  } else {
    baseLayer = L().tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 20, attribution: "Tiles © Esri" }
    ).addTo(map);

    labelsLayer = L().tileLayer(
      "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 20, opacity: 0.9, attribution: "Labels © Esri" }
    ).addTo(map);
  }
}

/* ---------- tiles status ---------- */
async function checkTilesStatus() {
  tilesChecking.value = true;
  tilesMsg.value = "";
  try {
    const base = sanitizeUrl(paths.tilesBase);
    if (!base) throw new Error("חסר tilesBase");

    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 5000);

    const res = await fetch(`${base}/status`, { cache: "no-store", signal: ctrl.signal });
    clearTimeout(t);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const j = await res.json();

    tilesReady.value = !!j.ready;
    tilesMsg.value = tilesReady.value
      ? "שרת ה-tiles מוכן."
      : "השרת עלה אבל עדיין אין נתונים (ready=false).";
  } catch (e) {
    tilesReady.value = false;
    tilesMsg.value = "לא מצליח להגיע לשרת ה-tiles כרגע.";
  } finally {
    tilesChecking.value = false;
  }
}

/* ---------- buildings layer: remove ---------- */
function clearBuildingsLayers() {
  // remove main buildings layer
  if (buildingsLayer) { try { map.removeLayer(buildingsLayer); } catch {} buildingsLayer = null; }
  // remove OSM layer
  if (osmLayer) { try { map.removeLayer(osmLayer); } catch {} osmLayer = null; }
  // reset hover highlight for vectorgrid
  lastHoverId = null;
  hover.show = false;
}

/* ---------- GeoJSON load & draw ---------- */
async function loadBuildings({ drawIfActive = true } = {}) {
  try {
    setLoading(true, "טוען GeoJSON…");
    setStatus("טוען קובץ…");

    const url = sanitizeUrl(paths.buildings);
    if (!url) throw new Error("נתיב GeoJSON ריק");

    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);

    const js = await r.json();
    buildingsFC = normFC(js);
    geojsonLoaded.value = true;
    lastLoadedUrl.value = url;

    setStatus(`נטען: ${buildingsFC.features.length} בניינים`);

    if (drawIfActive && buildingsEffective.value === "geojson") {
      drawBuildingsGeoJson(buildingsFC);
    }
  } catch (e) {
    console.error(e);
    geojsonLoaded.value = false;
    setStatus("שגיאה בטעינה: " + (e?.message || e));
  } finally {
    setLoading(false);
  }
}

function drawBuildingsGeoJson(fc) {
  if (!map) return;

  clearBuildingsLayers();

  buildingsLayer = L().geoJSON(fc, {
    style: (feature) => {
      const st = deriveStatsFromProps(feature);
      const base = styleByStatus(st.status);
      if (ui.filterSubs) {
        const show = shouldShowByFilter(st);
        return { ...base, fillOpacity: show ? 0.35 : 0.0, opacity: show ? 0.95 : 0.0 };
      }
      return base;
    },
    onEachFeature: (feature, layer) => {
      layer.on("mouseover", () => {
        layer.setStyle({ weight: 3, fillOpacity: 0.33 });
        const st = deriveStatsFromProps(feature);
        hover.html = tipHtml(st);
        hover.show = true;
        requestAnimationFrame(fixTipFlip);
      });

      layer.on("mousemove", () => {
        if (hover.show) requestAnimationFrame(fixTipFlip);
      });

      layer.on("mouseout", () => {
        buildingsLayer?.resetStyle(layer);
        hover.show = false;
      });

      layer.on("click", () => {
        const st = deriveStatsFromProps(feature);
        selected.value = { id: buildingId(feature), st, feature };
      });
    },
  }).addTo(map);

  buildingsEffective.value = "geojson";
}

/* ---------- Vector Tiles draw ---------- */
function drawBuildingsTiles() {
  if (!map) return;

  clearBuildingsLayers();

  const base = sanitizeUrl(paths.tilesBase);
  if (!base) {
    tilesMsg.value = "חסר tilesBase";
    buildingsEffective.value = "none";
    return;
  }

  // חשוב: template תואם לשרת שלך
  const template = `${base}/tiles/buildings/{z}/{x}/{y}.pbf`;

  if (!L().vectorGrid || !L().vectorGrid.protobuf) {
    tilesMsg.value = "VectorGrid לא נטען (ודא leaflet.vectorgrid מותקן).";
    buildingsEffective.value = "none";
    return;
  }

  const layer = L().vectorGrid.protobuf(template, {
    maxNativeZoom: 16,
    interactive: true,
    getFeatureId: (f) => String(buildingIdFromProps(f?.properties || {})),
    vectorTileLayerStyles: {
      buildings: (props) => vectorStyleFromProps(props),
      "*": (props) => vectorStyleFromProps(props),
    },
  });

  function vectorStyleFromProps(props) {
    const st = deriveStatsFromProps({ properties: props || {} });
    const base = styleByStatus(st.status);

    // VectorGrid צריך גם flags
    const styled = {
      ...base,
      fill: true,
      stroke: true,
      // filter only subsiding/suspect
      ...(ui.filterSubs
        ? (shouldShowByFilter(st)
            ? { fillOpacity: 0.35, opacity: 0.95, weight: 2 }
            : { fillOpacity: 0.0, opacity: 0.0, weight: 0 })
        : {}),
    };

    return styled;
  }

  layer.on("mouseover", (e) => {
    const props = e?.layer?.properties || {};
    const id = String(buildingIdFromProps(props));
    lastHoverId = id;

    // highlight
    try {
      layer.setFeatureStyle(id, { weight: 3, fillOpacity: 0.33, opacity: 1, stroke: true, fill: true });
    } catch {}

    const st = deriveStatsFromProps({ properties: props });
    hover.html = tipHtml(st);
    hover.show = true;
    requestAnimationFrame(fixTipFlip);
  });

  layer.on("mouseout", (e) => {
    const props = e?.layer?.properties || {};
    const id = String(buildingIdFromProps(props));
    try { layer.resetFeatureStyle(id); } catch {}
    hover.show = false;
    lastHoverId = null;
  });

  layer.on("mousemove", () => {
    if (hover.show) requestAnimationFrame(fixTipFlip);
  });

  layer.on("click", (e) => {
    const props = e?.layer?.properties || {};
    const st = deriveStatsFromProps({ properties: props });
    selected.value = { id: buildingIdFromProps(props), st, props };
  });

  buildingsLayer = layer.addTo(map);
  buildingsEffective.value = "tiles";
}

/* ---------- OSM around click (fallback) ---------- */
const OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter";
const OSM_THROTTLE_MS = 1500;

async function fetchBuildingsFromOSM(lat, lng) {
  const now = Date.now();
  if (now - lastOsmFetchAt < OSM_THROTTLE_MS) throw new Error("OSM_THROTTLED");
  lastOsmFetchAt = now;

  const around = 140;
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

async function updateOsmBuildingsAt(lat, lng) {
  try {
    setLoading(true, "טוען OSM סביב קליק…");
    const osm = await fetchBuildingsFromOSM(lat, lng);
    const gj = osmToSimpleGeoJson(osm);

    if (osmLayer) { try { map.removeLayer(osmLayer); } catch {} osmLayer = null; }

    osmLayer = L().geoJSON(gj, {
      style: (feature) => {
        const st = deriveStatsFromProps(feature); // לרוב no_data כי אין Vel_mean
        const base = styleByStatus(st.status);
        return { ...base, weight: 1, fillOpacity: 0.2 };
      },
      onEachFeature: (feature, layer) => {
        layer.on("mouseover", () => {
          const st = deriveStatsFromProps(feature);
          hover.html = tipHtml(st);
          hover.show = true;
          requestAnimationFrame(fixTipFlip);
        });
        layer.on("mouseout", () => (hover.show = false));
        layer.on("click", () => {
          const st = deriveStatsFromProps(feature);
          selected.value = { id: buildingId(feature), st, feature };
        });
      },
    }).addTo(map);

    buildingsEffective.value = "osm";
    setStatus(`OSM: ${gj.features.length} בניינים סביב קליק`);
  } catch (e) {
    if (e?.name === "AbortError") return;
    if (String(e?.message || e) === "OSM_THROTTLED") {
      setStatus("OSM: יותר מדי בקשות. נסה שוב עוד רגע.");
      return;
    }
    console.error(e);
    setStatus("שגיאה מול OSM/Overpass.");
  } finally {
    setLoading(false);
  }
}

/* ---------- apply source (auto/tiles/geojson/osm/none) ---------- */
async function applyBuildingsSource(verifyTilesNow = false) {
  if (!map) return;

  refreshColorsCache(); // כדי ש-style functions יהיו מהירים

  let mode = ui.buildingsMode;

  if (mode === "auto") {
    if (verifyTilesNow || tilesMsg.value === "") await checkTilesStatus();
    mode = tilesReady.value ? "tiles" : "geojson";
  }

  if (mode === "none") {
    clearBuildingsLayers();
    buildingsEffective.value = "none";
    setStatus("ללא שכבת בניינים");
    return;
  }

  if (mode === "tiles") {
    if (verifyTilesNow) await checkTilesStatus();
    if (!tilesReady.value) {
      // fallback
      tilesMsg.value = "Tiles לא מוכנים → מעבר ל-GeoJSON.";
      mode = "geojson";
      ui.buildingsMode = "auto";
    } else {
      drawBuildingsTiles();
      setStatus("בניינים: Vector Tiles");
      return;
    }
  }

  if (mode === "geojson") {
    // אם אין cache – נטען, אחרת נצייר
    if (!buildingsFC) await loadBuildings({ drawIfActive: true });
    else drawBuildingsGeoJson(buildingsFC);
    setStatus("בניינים: GeoJSON");
    return;
  }

  if (mode === "osm") {
    // לא מציירים עד קליק
    clearBuildingsLayers();
    buildingsEffective.value = "osm";
    setStatus("OSM: לחץ על המפה כדי למשוך בניינים סביב נקודה");
    return;
  }
}

/* ---------- recolor / selection / fit ---------- */
function recolorAll() {
  refreshColorsCache();

  if (!map) return;

  // Tiles: הכי אמין לבנות מחדש כדי שספים/פילטר יחולו
  if (buildingsEffective.value === "tiles") {
    drawBuildingsTiles();
    return;
  }

  // GeoJSON: setStyle מחדש
  if (buildingsEffective.value === "geojson" && buildingsLayer?.setStyle) {
    buildingsLayer.setStyle((feature) => {
      const st = deriveStatsFromProps(feature);
      const base = styleByStatus(st.status);
      if (ui.filterSubs) {
        const show = shouldShowByFilter(st);
        return { ...base, fillOpacity: show ? 0.35 : 0.0, opacity: show ? 0.95 : 0.0 };
      }
      return base;
    });
  }

  // OSM: לצבוע מחדש (אם קיים)
  if (buildingsEffective.value === "osm" && osmLayer?.setStyle) {
    osmLayer.setStyle((feature) => {
      const st = deriveStatsFromProps(feature);
      const base = styleByStatus(st.status);
      return { ...base, weight: 1, fillOpacity: 0.2 };
    });
  }
}

function clearSelection() {
  selected.value = null;
}

function fitToLayer() {
  if (!map) return;

  // אם שכבת GeoJSON קיימת ויש לה bounds
  const b = buildingsLayer?.getBounds?.();
  if (b && b.isValid && b.isValid()) {
    map.fitBounds(b.pad(0.12));
    return;
  }

  // אחרת: ישראל (קירוב)
  const israelSW = [29.45, 34.2];
  const israelNE = [33.35, 35.95];
  map.fitBounds([israelSW, israelNE], { padding: [18, 18] });
}

/* ---------- map init ---------- */
function onMapClick(e) {
  if (buildingsEffective.value !== "osm") return;
  const { lat, lng } = e.latlng;
  updateOsmBuildingsAt(lat, lng);
}

onMounted(async () => {
  map = L().map("map", { zoomControl: true, preferCanvas: true }).setView([32.0853, 34.7818], 16);

  applyBaseLayer();

  window.addEventListener("mousemove", onMouseMove);

  map.on("click", onMapClick);

  mapReady.value = true;

  await checkTilesStatus();

  // ברירת מחדל: auto -> tiles אם מוכן, אחרת geojson
  await applyBuildingsSource(false);

  // אם בפועל יצא GeoJSON – נטען אוטומטית
  if (buildingsEffective.value === "geojson" && !buildingsFC) {
    await loadBuildings({ drawIfActive: true });
  }
});

onBeforeUnmount(() => {
  if (osmAbort) osmAbort.abort();
  window.removeEventListener("mousemove", onMouseMove);
  if (map) map.off("click", onMapClick);
  if (map) map.remove();
});

/* שינוי נתיב GeoJSON => טעינה מחדש (רק אם המצב הפעיל הוא geojson) */
watch(
  () => paths.buildings,
  () => {
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(() => {
      const u = sanitizeUrl(paths.buildings);
      if (!u) return;
      buildingsFC = null;
      geojsonLoaded.value = false;
      if (buildingsEffective.value === "geojson") loadBuildings({ drawIfActive: true });
    }, 900);
  }
);

/* שינוי ספים / פילטר */
watch(() => ui.filterSubs, () => recolorAll());
watch(() => [params.thrVel, params.thrCoh, params.minPts], () => recolorAll());
</script>

<style>
:root{
  --bg:#0b1220;
  --line:#223152;
  --muted:#9fb0d0;
  --text:#e8eefc;

  --c-subs:#e24b4b;
  --c-sus:#f08a24;
  --c-stable:#2f6fe4;
  --c-lowq:#9b7bd4;
  --c-nodata:#93a0b8;
}

*{ box-sizing:border-box; }
html,body,#app{ height:100%; margin:0; }
body{
  font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  overflow:hidden;
}

.app{
  height:100%;
  display:grid;
  grid-template-columns: 360px 1fr;
}

.panel{
  border-left: 1px solid var(--line);
  background: #0e172a;
  display:flex;
  flex-direction: column;
  min-width: 320px;
}
.panel.closed{ transform: translateX(100%); position:absolute; right:0; top:0; bottom:0; z-index:2000; }

.panelHeader{
  padding: 14px 14px 10px;
  display:flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--line);
}
.brand .title{ font-weight: 800; font-size: 18px; }
.brand .sub{ font-size: 12px; color: var(--muted); margin-top:4px; }

.iconBtn{
  background: transparent;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 6px 10px;
  cursor: pointer;
}

.tabs{
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
}
.tab{
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.tab.on{
  background: #111c35;
  color: var(--text);
  border-color: #33518f;
}

.tabPage{
  padding: 12px 14px 16px;
  overflow:auto;
  flex: 1;
}

.card{
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255,255,255,0.03);
  padding: 12px;
  margin-bottom: 12px;
}
.cardTitle{ font-weight: 800; margin-bottom: 10px; }

.row2{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  align-items: end;
}
.colSpan2{ grid-column: 1 / -1; }

label{
  display:block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}

input, select{
  width:100%;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(0,0,0,0.2);
  color: var(--text);
  padding: 10px;
  outline: none;
}

.hint{
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
}
.hint code{
  background: rgba(0,0,0,0.25);
  padding: 2px 6px;
  border-radius: 8px;
}
.mini{ font-size: 11px; }

.rowBtns{
  display:flex;
  gap: 8px;
  margin-top: 10px;
}
.btn{
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.14);
  background: #1a2b55;
  color: var(--text);
  padding: 9px 10px;
  cursor: pointer;
}
.btn.ghost{
  background: transparent;
}

.check{
  display:flex;
  gap: 8px;
  align-items:center;
  font-size: 13px;
  color: var(--text);
}
.check input{ width:auto; }

.statusBox{
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 12px;
  padding: 10px;
  background: rgba(0,0,0,0.18);
}
.statusLine{
  display:flex;
  gap: 10px;
  align-items:center;
}
.statusDot{
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #667;
}
.statusDot.on{ background: #2ecc71; }

.legend .legRow{ display:flex; align-items:center; gap: 10px; margin: 8px 0; }
.sw{ width: 18px; height: 12px; border-radius: 6px; display:inline-block; }
.s-subs{ background: var(--c-subs); }
.s-sus{ background: var(--c-sus); }
.s-stable{ background: var(--c-stable); }
.s-lowq{ background: var(--c-lowq); }
.s-nodata{ background: var(--c-nodata); }

.emptyState{
  display:grid;
  place-items:center;
  gap: 10px;
  padding: 16px 8px;
  text-align:center;
  color: var(--muted);
}
.emptyIcon{ font-size: 24px; }
.emptyText{ font-size: 13px; line-height: 1.4; }

.infoCard{ display:grid; gap: 10px; }
.infoTop{ display:flex; justify-content: space-between; align-items:flex-start; gap: 10px; }
.idBlock .idLabel{ font-size: 12px; color: var(--muted); }
.idBlock .idValue{ font-weight: 900; font-size: 16px; }

.badges{ display:flex; gap: 8px; flex-wrap: wrap; justify-content:flex-end; }
.badge{
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid rgba(255,255,255,0.14);
}
.badge.ghost{ background: transparent; color: var(--muted); }

.b-subsiding{ background: rgba(226,75,75,0.18); border-color: rgba(226,75,75,0.35); }
.b-suspect{ background: rgba(240,138,36,0.18); border-color: rgba(240,138,36,0.35); }
.b-stable{ background: rgba(47,111,228,0.18); border-color: rgba(47,111,228,0.35); }
.b-low_quality{ background: rgba(155,123,212,0.18); border-color: rgba(155,123,212,0.35); }
.b-no_data{ background: rgba(147,160,184,0.18); border-color: rgba(147,160,184,0.35); }

.kvGrid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.kv{
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 12px;
  padding: 10px;
  background: rgba(0,0,0,0.12);
}
.kv .k{ font-size: 11px; color: var(--muted); }
.kv .v{ font-size: 16px; font-weight: 900; margin-top: 4px; }
.kv .u{ font-size: 11px; color: var(--muted); margin-top: 2px; }

.meterWrap{ margin-top: 6px; }
.meterTop{ display:flex; justify-content: space-between; align-items:center; }
.meterLabel{ font-size: 12px; color: var(--muted); }
.meterValue{ font-size: 12px; }
.meterValue.bad{ color: #ffbf70; }
.miniNote{ color: var(--muted); margin-right: 6px; font-size: 11px; }
.meter{
  margin-top: 8px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  position: relative;
  overflow:hidden;
}
.meterFill{
  height: 100%;
  background: rgba(46,204,113,0.65);
}
.meterThr{
  position:absolute;
  top: -2px;
  width: 2px;
  height: 14px;
  background: rgba(240,138,36,0.9);
}

.checks{ display:grid; gap: 8px; margin-top: 8px; }
.checkRow{
  display:flex; align-items:center; gap: 10px;
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 12px;
  padding: 8px 10px;
  background: rgba(0,0,0,0.12);
  font-size: 12px;
  color: var(--muted);
}
.checkRow .dot{
  width: 9px; height: 9px; border-radius: 999px;
  background: #667;
}
.checkRow.ok .dot{ background: #2ecc71; }
.checkRow.bad .dot{ background: #f08a24; }

.miniExplain{
  font-size: 11px;
  color: var(--muted);
  line-height: 1.4;
}
.miniTag{
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: rgba(0,0,0,0.25);
  padding: 1px 6px;
  border-radius: 8px;
}

.main{
  position: relative;
  overflow:hidden;
}
#map{ height: 100%; width: 100%; }

.tip{
  position: fixed;
  z-index: 1500;
  pointer-events: none;
  width: 260px;
  background: rgba(15,22,39,0.92);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 14px;
  padding: 10px 10px;
  box-shadow: 0 14px 40px rgba(0,0,0,0.35);
}
.tipTitle{ font-weight: 900; margin-bottom: 8px; }
.tipGrid{ display:grid; gap: 6px; font-size: 12px; color: var(--muted); }
.tipGrid .k{ color: var(--muted); }
.tipGrid .v{ color: var(--text); font-weight: 800; }
.tipGrid .u{ color: var(--muted); margin-right: 4px; }

.loadingOverlay{
  position:absolute;
  inset:0;
  display:grid;
  place-items:center;
  gap: 10px;
  background: rgba(0,0,0,0.35);
  z-index: 1400;
}
.spinner{
  width: 28px; height: 28px;
  border-radius: 999px;
  border: 3px solid rgba(255,255,255,0.18);
  border-top-color: rgba(255,255,255,0.9);
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loadingText{ color: var(--text); font-weight: 700; }
</style>

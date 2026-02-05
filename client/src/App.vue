<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ closed: !panelOpen }">
      <div class="panelHeader">
        <div class="brand">
          <div class="title">SatMap</div>
          <div class="sub">קובץ משולב: בניינים + סטטיסטיקות InSAR</div>
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
          <div class="cardTitle">קובץ משולב</div>

          <div class="row2">
            <div class="colSpan2">
              <label>GeoJSON (בניינים + Vel_mean + coer_mean + Vel_count)</label>
              <input v-model.trim="paths.buildings" type="text" />
              <div class="hint mini">
                נטען אוטומטית בעת פתיחת העמוד. שינוי נתיב כאן יטען מחדש תוך שנייה.
              </div>
            </div>
          </div>

          <div class="rowBtns">
            <button class="btn ghost" @click="fitToLayer" :disabled="!hasBounds">התמקד בשכבה</button>
            <button class="btn" @click="recolorAll" :disabled="!ready || loading">רענן צבעים</button>
          </div>

          <div class="hint">
            הקובץ צריך להיות בתוך <b>client/public/data</b> ואז הנתיב יהיה:
            <code>{{ baseUrl }}data/buildings_joined.geojson</code>
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
              <span class="miniTag">no_data</span> = חסרים נתונים לבניין בקובץ
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
              <span class="statusDot" :class="{ on: ready }"></span>
              <span>{{ status }}</span>
            </div>
            <div class="hint mini" v-if="lastLoadedUrl">
              נטען מ: <code>{{ lastLoadedUrl }}</code>
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
            <div class="legRow"><span class="sw s-lowq"></span> איכות נמוכה</div>
            <div class="legRow"><span class="sw s-nodata"></span> אין נתונים</div>
          </div>
        </div>
      </section>

      <!-- ABOUT -->
      <section v-show="activeTab==='about'" class="tabPage">
        <div class="card">
          <div class="cardTitle">איך מחושב הסטטוס</div>
          <div class="p">
            משתמשים בשדות שכבר קיימים לכל בניין בקובץ המשולב:
            <ul class="ul">
              <li><b>Vel_mean</b> – ממוצע מהירות (mm/yr)</li>
              <li><b>coer_mean</b> – ממוצע coherence (0–1)</li>
              <li><b>Vel_count</b> – כמות נקודות שהשתתפו</li>
            </ul>

            סטטוס:
            <ul class="ul">
              <li><b>no_data</b>: חסרים נתונים או 0 נקודות</li>
              <li><b>low_quality</b>: coher_mean מתחת לסף או Vel_count קטן מהמינימום</li>
              <li><b>subsiding</b>: איכות תקינה ו־Vel_mean קטן (שלילי יותר) מהסף</li>
              <li><b>suspect</b>: איכות תקינה ו־Vel_mean קרוב לסף (±0.5)</li>
              <li><b>stable</b>: איכות תקינה ו־Vel_mean לא עובר את הסף</li>
            </ul>
          </div>
        </div>
      </section>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>

      <div class="topRight">
        <div class="pill">רחף: טולטיפ (ימינה מהעכבר) • קליק: פירוט</div>
      </div>

      <!-- Hover tooltip -->
      <div
        v-show="hover.show"
        ref="hoverRef"
        class="hoverTip"
        :style="hoverStyle"
        v-html="hover.html"
      />

      <div v-show="loading" class="loader">
        <div class="spin"></div>
        <div class="txt">{{ loadingText }}</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from "vue";

const baseUrl = import.meta.env.BASE_URL || "/";

const paths = reactive({
  // חשוב: בלי סלש בסוף
  buildings: baseUrl + "data/buildings_joined.geojson",
});

const params = reactive({
  thrVel: -2,
  thrCoh: 0.35,
  minPts: 8,
});

const ui = reactive({
  filterSubs: false,
});

const panelOpen = ref(true);
const activeTab = ref("controls");

const status = ref("טוען אוטומטית…");
const loading = ref(false);
const loadingText = ref("טוען…");
const lastLoadedUrl = ref("");

const hover = reactive({ show: false, x: 0, y: 0, html: "", _flip: false, _w: 260 });
const hoverRef = ref(null);

const selected = ref(null); // { id, st, feature }
const ready = ref(false);
const hasBounds = ref(false);

let map = null;
let buildingsLayer = null;
let buildingsFC = null;

const L = () => window.L;

function setLoading(on, text = "טוען…") {
  loading.value = on;
  loadingText.value = text;
}

function setStatus(msg) {
  status.value = msg;
}

function sanitizeUrl(u) {
  return String(u || "").trim().replace(/\/+$/, ""); // מוריד / בסוף (זה גורם ל-404)
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

function buildingId(f) {
  const p = f?.properties || {};
  return (
    p.id ?? p.ID ?? p.objectid ?? p.OBJECTID ?? p.fid ?? p.FID ?? p.Name ?? p.name ?? "building"
  );
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

  const lower = Object.keys(props).reduce((acc, k) => (acc[k.toLowerCase()] = k, acc), {});
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

function deriveStatsFromProps(feature) {
  const p = feature?.properties || {};

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

function getCss(varName) {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

function styleByStatus(statusName) {
  const colors = {
    subsiding: getCss("--c-subs"),
    suspect: getCss("--c-sus"),
    stable: getCss("--c-stable"),
    low_quality: getCss("--c-lowq"),
    no_data: getCss("--c-nodata"),
  };
  const c = colors[statusName] || colors.no_data;

  return {
    weight: 2,
    opacity: 0.95,
    fillOpacity: 0.25,
    color: c,
    fillColor: c,
  };
}

function shouldShowByFilter(st) {
  if (!ui.filterSubs) return true;
  return st.status === "subsiding" || st.status === "suspect";
}

function applyLayerStyle(layer, st) {
  const base = styleByStatus(st.status);
  if (ui.filterSubs) {
    const show = shouldShowByFilter(st);
    layer.setStyle({
      ...base,
      fillOpacity: show ? 0.35 : 0.0,
      opacity: show ? 0.95 : 0.0,
    });
  } else {
    layer.setStyle(base);
  }
}

/* ---------- Tooltip positioning: right of cursor + auto-flip ---------- */
const hoverStyle = computed(() => ({
  left: hover.x + "px",
  top: hover.y + "px",
  transform: hover._flip ? `translate(${-hover._w - 14}px, -12px)` : `translate(14px, -12px)`,
}));

function onMouseMove(e) {
  hover.x = e.clientX;
  hover.y = e.clientY;
  if (hover.show) requestAnimationFrame(fixTipFlip);
}

function fixTipFlip() {
  const el = hoverRef.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  hover._w = rect.width || 260;
  hover._flip = rect.right > window.innerWidth - 10;
}

function fmtVel(v) {
  if (v == null || !Number.isFinite(v)) return "—";
  return Number(v).toFixed(2);
}
function fmtCoh(v) {
  if (v == null || !Number.isFinite(v)) return "—";
  return Number(v).toFixed(2);
}
function fmtCount(v) {
  if (v == null || !Number.isFinite(v)) return "—";
  return String(v);
}

function tipHtml(st) {
  const velTxt = st.velMean == null ? "—" : st.velMean.toFixed(2);
  const cohTxt = st.cohMean == null ? "—" : st.cohMean.toFixed(2);

  const badgeCls = "tipBadge t-" + st.status;
  return `
    <div class="tipRow">
      <span class="${badgeCls}">${statusLabel(st.status)}</span>
      <span class="tipK">Vel</span><span class="tipV">${velTxt}</span>
      <span class="tipK">coh</span><span class="tipV">${cohTxt}</span>
      <span class="tipK">n</span><span class="tipV">${st.count}</span>
    </div>
  `;
}

/* ---------- Selection helpers ---------- */
const cohOk = computed(() => {
  const st = selected.value?.st;
  if (!st) return true;
  if (st.cohMean == null) return true; // אם אין - לא נפסול
  return st.cohMean >= Number(params.thrCoh);
});
const countOk = computed(() => {
  const st = selected.value?.st;
  if (!st) return true;
  return (st.count ?? 0) >= Number(params.minPts);
});
const qualityTag = computed(() => {
  const st = selected.value?.st;
  if (!st) return "";
  if (st.status === "no_data") return "חסר נתונים";
  if (st.status === "low_quality") return "איכות/כמות לא מספיקה";
  if (!cohOk.value) return "coherence נמוך";
  if (!countOk.value) return "מעט נקודות";
  return "איכות תקינה";
});

function clearSelection() {
  selected.value = null;
}

/* ---------- Load & draw (AUTO) ---------- */
async function loadBuildings() {
  const url = sanitizeUrl(paths.buildings);

  try {
    setLoading(true, "טוען GeoJSON…");
    setStatus("טוען שכבה אוטומטית…");
    ready.value = false;
    lastLoadedUrl.value = "";

    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`לא הצלחתי לטעון: ${url} (HTTP ${r.status})`);

    const js = await r.json();
    buildingsFC = normFC(js);

    drawBuildings(buildingsFC);
    ready.value = true;
    lastLoadedUrl.value = url;
    setStatus(`נטען: ${buildingsFC.features.length} בניינים`);
  } catch (e) {
    console.error(e);
    setStatus("שגיאה בטעינה: " + (e?.message || e));
  } finally {
    setLoading(false);
  }
}

function drawBuildings(fc) {
  if (!map) return;

  if (buildingsLayer) buildingsLayer.remove();

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

  const b = buildingsLayer.getBounds();
  hasBounds.value = b?.isValid?.() === true;
  if (hasBounds.value) map.fitBounds(b.pad(0.08));
}

function recolorAll() {
  if (!buildingsLayer) return;
  buildingsLayer.eachLayer((layer) => {
    const f = layer.feature;
    if (!f) return;
    const st = deriveStatsFromProps(f);
    applyLayerStyle(layer, st);
  });
}

function fitToLayer() {
  if (!buildingsLayer) return;
  const b = buildingsLayer.getBounds();
  if (b && b.isValid()) map.fitBounds(b.pad(0.08));
}

/* ---------- init map + AUTO load ---------- */
onMounted(async () => {
  map = L().map("map", { zoomControl: true, preferCanvas: true }).setView([32.0853, 34.7818], 16);

  L().tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 20, attribution: "Tiles © Esri" }
  ).addTo(map);

  L().tileLayer(
    "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 20, opacity: 0.9, attribution: "Labels © Esri" }
  ).addTo(map);

  window.addEventListener("mousemove", onMouseMove, { passive: true });

  // ✅ AUTO LOAD
  await loadBuildings();
});

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onMouseMove);
  if (map) map.remove();
});

/* אם משנים נתיב — טען אוטומטית בלי כפתור */
let reloadTimer = null;
watch(
  () => paths.buildings,
  () => {
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(() => {
      // לא נטען אם המשתמש מחק הכל
      const u = sanitizeUrl(paths.buildings);
      if (!u) return;
      loadBuildings();
    }, 900);
  }
);

/* שינוי ספים / פילטר => רק צביעה מחדש */
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
  display:grid;
  grid-template-columns: 380px 1fr;
  height:100%;
}

.panel{
  background: linear-gradient(180deg, rgba(17,28,52,.96), rgba(13,18,32,.96));
  border-left:1px solid var(--line);
  overflow:auto;
  box-shadow: 0 14px 40px rgba(0,0,0,.32);
}

.panelHeader{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  padding:14px 14px 10px;
  position:sticky;
  top:0;
  background: rgba(15, 23, 42, .92);
  backdrop-filter: blur(10px);
  border-bottom:1px solid var(--line);
  z-index: 5;
}

.brand .title{ font-size:18px; font-weight:900; letter-spacing:.2px; }
.brand .sub{ font-size:12px; color:var(--muted); margin-top:2px; }

.iconBtn{
  border:1px solid var(--line);
  background: rgba(255,255,255,.06);
  color:var(--text);
  border-radius:10px;
  padding:8px 10px;
  cursor:pointer;
}
.iconBtn:hover{ background: rgba(255,255,255,.10); }

.tabs{
  display:flex;
  gap:8px;
  padding:10px 14px 12px;
  border-bottom:1px solid var(--line);
}
.tab{
  border:1px solid var(--line);
  background: rgba(255,255,255,.06);
  color:var(--text);
  border-radius:999px;
  padding:8px 12px;
  cursor:pointer;
  font-size:13px;
}
.tab.on{
  background: rgba(110,168,254,.18);
  border-color: rgba(110,168,254,.45);
}

.tabPage{ padding:12px 14px 18px; }

.card{
  background: rgba(255,255,255,.04);
  border:1px solid var(--line);
  border-radius:16px;
  padding:12px;
  margin-bottom:12px;
}
.cardTitle{
  font-weight:900;
  font-size:13px;
  margin-bottom:10px;
  color:#f4f7ff;
}

label{ display:block; font-size:12px; color:var(--muted); margin-bottom:6px; }
input[type="text"], input[type="number"]{
  width:100%;
  background: rgba(0,0,0,.22);
  border:1px solid rgba(255,255,255,.10);
  color:var(--text);
  border-radius:12px;
  padding:10px 10px;
  outline:none;
}
input[type="text"]:focus, input[type="number"]:focus{
  border-color: rgba(110,168,254,.55);
  box-shadow: 0 0 0 4px rgba(110,168,254,.12);
}

.row2{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:10px;
  align-items:end;
}
.colSpan2{ grid-column: 1 / -1; }

.rowBtns{
  display:flex;
  gap:10px;
  margin-top:10px;
}
.btn{
  border:none;
  background: linear-gradient(180deg, rgba(110,168,254,.95), rgba(110,168,254,.78));
  color:#061024;
  font-weight:900;
  border-radius:12px;
  padding:10px 12px;
  cursor:pointer;
  flex:1;
}
.btn:hover{ filter: brightness(1.05); }
.btn:disabled{ opacity:.55; cursor:not-allowed; }
.btn.ghost{
  background: rgba(255,255,255,.06);
  color: var(--text);
  border:1px solid var(--line);
}
.btn.ghost:hover{ background: rgba(255,255,255,.10); }

.hint{ color:var(--muted); font-size:12px; margin-top:8px; line-height:1.35; }
.hint.mini{ margin-top:6px; font-size:11px; }
code{ background: rgba(0,0,0,.25); padding:2px 6px; border-radius:8px; }

.check{
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 10px;
  border:1px solid rgba(255,255,255,.08);
  border-radius:12px;
  background: rgba(0,0,0,.14);
  cursor:pointer;
  user-select:none;
}
.check input{ transform: scale(1.1); }

/* ------------ Improved info UI ------------ */
.emptyState{
  display:flex;
  gap:12px;
  align-items:center;
  padding:12px;
  border-radius:14px;
  background: rgba(0,0,0,.18);
  border:1px dashed rgba(255,255,255,.12);
}
.emptyIcon{
  width:36px; height:36px;
  display:grid; place-items:center;
  border-radius:12px;
  background: rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.10);
  font-weight:900;
}
.emptyText{ color: var(--muted); font-size:12px; line-height:1.45; }

.infoCard{
  border-radius:16px;
  background: rgba(0,0,0,.18);
  border:1px solid rgba(255,255,255,.10);
  padding:12px;
}
.infoTop{
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:flex-start;
  margin-bottom:10px;
}
.idBlock .idLabel{
  font-size:11px;
  color: var(--muted);
}
.idBlock .idValue{
  font-size:15px;
  font-weight:900;
  letter-spacing:.2px;
}

.badges{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  justify-content:flex-end;
}
.badge{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 10px;
  border-radius:999px;
  font-size:12px;
  font-weight:900;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.06);
}
.badge.ghost{
  background: rgba(0,0,0,.20);
  color: var(--muted);
}
.b-subsiding{ background: rgba(226,75,75,.18); border-color: rgba(226,75,75,.35); }
.b-suspect{ background: rgba(240,138,36,.18); border-color: rgba(240,138,36,.35); }
.b-stable{ background: rgba(47,111,228,.18); border-color: rgba(47,111,228,.35); }
.b-low_quality{ background: rgba(155,123,212,.18); border-color: rgba(155,123,212,.35); }
.b-no_data{ background: rgba(147,160,184,.18); border-color: rgba(147,160,184,.35); }

.kvGrid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:10px;
}
.kv{
  background: rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.10);
  border-radius:14px;
  padding:10px;
}
.kv .k{ font-size:11px; color: var(--muted); }
.kv .v{ font-size:16px; font-weight:900; margin-top:4px; }
.kv .u{ font-size:11px; color: var(--muted); margin-top:2px; }

.meterWrap{
  margin-top:12px;
  padding:10px;
  border-radius:14px;
  background: rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.10);
}
.meterTop{
  display:flex;
  justify-content:space-between;
  align-items:baseline;
  gap:10px;
  margin-bottom:8px;
}
.meterLabel{ font-size:12px; color: var(--muted); }
.meterValue{ font-weight:900; }
.meterValue.bad{ color: #ffd1d1; }
.miniNote{ font-size:11px; color: var(--muted); font-weight:700; margin-right:6px; }

.meter{
  position:relative;
  height:10px;
  border-radius:999px;
  background: rgba(0,0,0,.25);
  border:1px solid rgba(255,255,255,.10);
  overflow:hidden;
}
.meterFill{
  height:100%;
  background: rgba(110,168,254,.55);
}
.meterThr{
  position:absolute;
  top:-3px;
  width:2px;
  height:16px;
  background: rgba(255,255,255,.70);
  box-shadow: 0 0 0 2px rgba(0,0,0,.25);
}

.checks{
  margin-top:10px;
  display:flex;
  flex-direction:column;
  gap:8px;
}
.checkRow{
  display:flex;
  align-items:center;
  gap:10px;
  padding:8px 10px;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(0,0,0,.12);
  font-size:12px;
  color: var(--muted);
}
.checkRow .dot{
  width:8px; height:8px;
  border-radius:999px;
  background: rgba(147,160,184,.9);
}
.checkRow.ok{ color:#e8eefc; border-color: rgba(110,168,254,.25); }
.checkRow.ok .dot{ background: rgba(110,168,254,.95); }
.checkRow.bad{ color:#ffe6e6; border-color: rgba(226,75,75,.25); }
.checkRow.bad .dot{ background: rgba(226,75,75,.95); }

.miniExplain{
  margin-top:10px;
  color: var(--muted);
  font-size:11px;
  line-height:1.35;
}
.miniTag{
  display:inline-block;
  padding:2px 8px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.06);
  font-weight:900;
  margin-left:6px;
}

.statusBox{
  padding:10px;
  border-radius:14px;
  background: rgba(0,0,0,.18);
  border:1px solid rgba(255,255,255,.10);
  font-size:12px;
  line-height:1.45;
}
.statusLine{
  display:flex;
  align-items:center;
  gap:10px;
}
.statusDot{
  width:10px; height:10px;
  border-radius:999px;
  background: rgba(147,160,184,.7);
}
.statusDot.on{
  background: rgba(110,168,254,.95);
}

/* legend */
.legend{ display:flex; flex-direction:column; gap:10px; }
.legRow{ display:flex; align-items:center; gap:10px; font-size:13px; color:#eaf1ff; }
.sw{ width:16px; height:16px; border-radius:6px; border:1px solid rgba(255,255,255,.18); }
.s-subs{ background: var(--c-subs); }
.s-sus{ background: var(--c-sus); }
.s-stable{ background: var(--c-stable); }
.s-lowq{ background: var(--c-lowq); }
.s-nodata{ background: var(--c-nodata); }

.p{ color:#d9e6ff; font-size:13px; line-height:1.55; }
.ul{ margin:8px 0 0 0; padding-right:18px; color:#d9e6ff; }

/* map */
.mapWrap{ position:relative; }
#map{ width:100%; height:100%; }

.topRight{
  position:absolute;
  top:12px;
  left:12px;
  z-index: 500;
}
.pill{
  background: rgba(15, 23, 42, .85);
  border:1px solid rgba(255,255,255,.10);
  border-radius:999px;
  padding:8px 12px;
  font-size:12px;
  color: var(--muted);
  backdrop-filter: blur(10px);
}

/* Tooltip */
.hoverTip{
  position: fixed;
  z-index: 2000;
  pointer-events: none;
  background: rgba(10, 14, 24, .92);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 12px;
  padding: 8px 10px;
  font-size: 12px;
  color: #eef4ff;
  box-shadow: 0 12px 30px rgba(0,0,0,.35);
  white-space: nowrap;
}
.tipRow{
  display:flex;
  align-items:center;
  gap:10px;
}
.tipK{ color: rgba(255,255,255,.70); font-weight:800; font-size:11px; }
.tipV{ color:#eef4ff; font-weight:900; }
.tipBadge{
  padding:4px 10px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.10);
  font-weight:900;
  font-size:11px;
  margin-left:4px;
}
.t-subsiding{ background: rgba(226,75,75,.18); border-color: rgba(226,75,75,.35); }
.t-suspect{ background: rgba(240,138,36,.18); border-color: rgba(240,138,36,.35); }
.t-stable{ background: rgba(47,111,228,.18); border-color: rgba(47,111,228,.35); }
.t-low_quality{ background: rgba(155,123,212,.18); border-color: rgba(155,123,212,.35); }
.t-no_data{ background: rgba(147,160,184,.18); border-color: rgba(147,160,184,.35); }

/* Loader */
.loader{
  position:absolute;
  inset:0;
  display:flex;
  align-items:center;
  justify-content:center;
  flex-direction:column;
  gap:10px;
  background: rgba(0,0,0,.35);
  z-index: 1200;
}
.spin{
  width:34px; height:34px;
  border-radius:50%;
  border: 4px solid rgba(255,255,255,.18);
  border-top-color: rgba(255,255,255,.75);
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loader .txt{ color:#eaf1ff; font-weight:900; }

/* responsive panel */
@media (max-width: 980px){
  .app{ grid-template-columns: 1fr; }
  .panel{
    position:absolute;
    right:0; top:0; bottom:0;
    width:min(420px, 92vw);
    transform: translateX(0);
    transition: transform .2s ease;
    z-index: 1000;
  }
  .panel.closed{ transform: translateX(105%); }
}
</style>

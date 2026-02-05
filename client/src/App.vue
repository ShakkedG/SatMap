<template>
  <div class="app" dir="rtl">
    <aside class="panel" :class="{ closed: !panelOpen }">
      <div class="panelHeader">
        <div class="brand">
          <div class="title">SatMap</div>
          <div class="sub">בניינים + InSAR • חישוב שקיעה לפי בניין</div>
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
          <div class="cardTitle">קבצים</div>

          <div class="row2">
            <div>
              <label>שכבת בניינים (GeoJSON)</label>
              <input v-model.trim="paths.buildings" type="text" />
            </div>
            <div>
              <label>נקודות InSAR (CSV/GeoJSON)</label>
              <input v-model.trim="paths.points" type="text" />
            </div>
          </div>

          <div class="rowBtns">
            <button class="btn" @click="loadAll" :disabled="loading">טען נתונים</button>
            <button class="btn ghost" @click="fitToLayer" :disabled="!hasBounds">התמקד בשכבה</button>
          </div>

          <div class="hint">
            שים את הדאטה ב־<b>public/data</b>.
            ב־GitHub Pages הנתיבים עובדים הכי טוב כך: <code>{{ baseUrl }}data/…</code>
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">ספים וחישוב סטטוס</div>

          <div class="row2">
            <div>
              <label>סף “שוקע/חשוד” v (mm/yr)</label>
              <input v-model.number="params.thrVel" type="number" step="0.5" />
              <div class="hint mini">יותר שלילי = יותר שקיעה</div>
            </div>
            <div>
              <label>איכות מינימלית (coherence)</label>
              <input v-model.number="params.thrCoh" type="number" step="0.05" min="0" max="1" />
              <div class="hint mini">0–1. נמוך מדי = “איכות נמוכה”</div>
            </div>
          </div>

          <div class="row2">
            <div>
              <label>מינימום נקודות לבניין</label>
              <input v-model.number="params.minPts" type="number" step="1" min="1" />
              <div class="hint mini">מעט מדי נקודות = לא אמין</div>
            </div>
            <div>
              <label>Buffer סביב בניין (מטר)</label>
              <input v-model.number="params.bufM" type="number" step="1" min="0" />
              <div class="hint mini">אם נקודות “קצת ליד הגג”</div>
            </div>
          </div>

          <div class="rowBtns">
            <button class="btn" @click="recolorHard" :disabled="!ready || loading">רענן צבעים</button>
            <button class="btn ghost" @click="computeVisible" :disabled="!ready || loading">חשב לאזור במסך</button>
          </div>

          <div class="row2">
            <label class="check">
              <input v-model="ui.showPoints" type="checkbox" />
              הצג נקודות InSAR
            </label>
            <label class="check">
              <input v-model="ui.filterSubs" type="checkbox" />
              סנן ל“שוקע/חשוד” בלבד
            </label>
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">בחירה</div>
          <div class="selBox" :class="{ muted: !selected }">
            <template v-if="!selected">
              לחץ על בניין כדי לראות פירוט. ריחוף יציג טולטיפ.
            </template>
            <template v-else>
              {{ selectedText }}
            </template>
          </div>
        </div>

        <div class="card">
          <div class="cardTitle">מצב</div>
          <div class="statusBox">{{ status }}</div>
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

          <div class="hint">
            “איכות נמוכה” = coherence נמוך או מעט נקודות → לא מציגים מסקנה אמינה.
          </div>
        </div>
      </section>

      <!-- ABOUT -->
      <section v-show="activeTab==='about'" class="tabPage">
        <div class="card">
          <div class="cardTitle">איך זה עובד</div>
          <div class="p">
            לכל בניין (פוליגון) אוספים נקודות InSAR שבתוך הבניין (או בתוך buffer).
            מחשבים:
            <ul class="ul">
              <li><b>Vel_mean</b> – ממוצע Velocity (mm/yr)</li>
              <li><b>coer_mean</b> – ממוצע coherence/quality (0–1)</li>
              <li><b>Vel_count</b> – מספר נקודות שהשתתפו</li>
            </ul>
            סטטוס:
            <ul class="ul">
              <li><b>no_data</b>: אין נקודות בתוך הבניין</li>
              <li><b>low_quality</b>: coher_mean מתחת לסף או count מתחת למינימום</li>
              <li><b>subsiding</b>: איכות תקינה ו־Vel_mean קטן (שלילי יותר) מהסף</li>
              <li><b>suspect</b>: איכות תקינה ו־Vel_mean קרוב לסף (±0.5)</li>
              <li><b>stable</b>: איכות תקינה ו־Vel_mean לא עובר את הסף</li>
            </ul>
          </div>

          <div class="hint">
            למה לא לכל הבניינים יש נתונים?
            כי InSAR נותן נקודות אמינות רק בחלק מהגגות/משטחים; לפעמים אין נקודות “טובות” או שהפילטרים מסירים אותן.
          </div>
        </div>
      </section>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>

      <div class="topRight">
        <div class="pill">רחף: טולטיפ • קליק: פירוט • “חשב לאזור במסך” לצביעה מלאה</div>
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
  buildings: baseUrl + "data/buildings.geojson",
  points: baseUrl + "data/insar.csv",
});

const params = reactive({
  thrVel: -2,
  thrCoh: 0.35,
  minPts: 8,
  bufM: 0,
});

const ui = reactive({
  showPoints: false,
  filterSubs: false,
});

const panelOpen = ref(true);
const activeTab = ref("controls");

const status = ref("עדיין לא נטענו נתונים.");
const loading = ref(false);
const loadingText = ref("טוען נתונים…");

const hover = reactive({ show: false, x: 0, y: 0, html: "" });
const hoverRef = ref(null);

const selected = ref(null);
const selectedText = ref("");

const ready = ref(false);
const hasBounds = ref(false);

let map = null;
let buildingsLayer = null;
let pointsLayer = null;

let buildingsFC = null;
let pointsFC = null;

let pointTree = null; // RBush
let pointsCount = 0;

const statsCache = new Map(); // id -> {key, stats}
const bufferCache = new Map(); // id|buf -> feature

// globals from CDN
const L = () => window.L;
const turf = () => window.turf;
const Papa = () => window.Papa;
const RBush = () => window.RBush;
const proj4 = () => window.proj4;

// EPSG:2039 definition
function ensureProj() {
  if (!proj4()) return;
  try {
    proj4().defs(
      "EPSG:2039",
      "+proj=tmerc +lat_0=31.73439361111111 +lon_0=35.20451694444445 +k=1.0000067 +x_0=219529.584 +y_0=626907.39 +ellps=GRS80 +towgs84=-24.0024,-17.1032,-17.8444,-0.33077,-1.85269,1.66969,5.4248 +units=m +no_defs"
    );
  } catch {}
}

const hoverStyle = computed(() => {
  // default: right of cursor
  return {
    left: hover.x + "px",
    top: hover.y + "px",
    transform: hover._flip ? `translate(${-hover._w - 14}px, -12px)` : `translate(14px, -12px)`,
  };
});

function setLoading(on, text = "טוען…") {
  loading.value = on;
  loadingText.value = text;
}

function setStatus(msg) {
  status.value = msg;
}

function paramKey() {
  return `${params.thrVel}|${params.thrCoh}|${params.minPts}|${params.bufM}`;
}

function buildingId(f) {
  const p = f?.properties || {};
  return (
    p.id ??
    p.ID ??
    p.objectid ??
    p.OBJECTID ??
    p.fid ??
    p.FID ??
    p.Name ??
    p.name ??
    JSON.stringify(f.geometry).length
  );
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

function getCss(varName) {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

function styleByStatus(st) {
  const status = st?.status || "no_data";
  const colors = {
    subsiding: getCss("--c-subs"),
    suspect: getCss("--c-sus"),
    stable: getCss("--c-stable"),
    low_quality: getCss("--c-lowq"),
    no_data: getCss("--c-nodata"),
  };
  const c = colors[status] || colors.no_data;

  return {
    weight: 2,
    opacity: 0.95,
    fillOpacity: ui.filterSubs ? 0.0 : 0.25,
    color: c,
    fillColor: c,
  };
}

function shouldShowByFilter(st) {
  if (!ui.filterSubs) return true;
  return st.status === "subsiding" || st.status === "suspect";
}

function applyLayerStyle(layer, st) {
  const base = styleByStatus(st);
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

// ----- Tooltip positioning (right of cursor + auto flip)
function onMouseMove(e) {
  hover.x = e.clientX;
  hover.y = e.clientY;
  if (!hover.show) return;
  requestAnimationFrame(fixTipFlip);
}

function fixTipFlip() {
  const el = hoverRef.value;
  if (!el) return;

  const rect = el.getBoundingClientRect();
  hover._w = rect.width || 220;
  hover._flip = rect.right > window.innerWidth - 10;
}

// ----- Loaders
async function loadAll() {
  try {
    ensureProj();
    setLoading(true, "טוען בניינים…");
    setStatus("טוען…");
    selected.value = null;
    selectedText.value = "";

    const bPath = paths.buildings;
    const pPath = paths.points;

    const [bRes, pRes] = await Promise.all([
      fetch(bPath).then((r) => {
        if (!r.ok) throw new Error(`בניינים: לא הצלחתי לטעון ${bPath}`);
        return r.json();
      }),
      fetch(pPath).then(async (r) => {
        if (!r.ok) throw new Error(`נקודות: לא הצלחתי לטעון ${pPath}`);
        const ct = r.headers.get("content-type") || "";
        if (pPath.toLowerCase().endsWith(".geojson") || ct.includes("application/json")) return r.json();
        return r.text();
      }),
    ]);

    buildingsFC = normFC(bRes);

    setLoading(true, "טוען נקודות InSAR…");
    if (typeof pRes === "string") {
      pointsFC = parseCsvToPointsFC(pRes);
    } else {
      pointsFC = normFC(pRes);
      for (const f of pointsFC.features) f.properties ||= {};
    }

    setLoading(true, "בונה אינדקס נקודות…");
    buildPointIndex(pointsFC);

    setLoading(true, "מצייר שכבות…");
    drawBuildings(buildingsFC);
    redrawPoints();

    statsCache.clear();
    bufferCache.clear();
    recolorAll();

    ready.value = true;
    setStatus(`נטען: ${buildingsFC.features.length} בניינים, ${pointsCount} נקודות InSAR.`);
  } catch (e) {
    console.error(e);
    setStatus("שגיאה: " + (e?.message || e));
    alert("שגיאה בטעינה. פתח קונסול (F12) לפרטים.\n\n" + (e?.message || e));
  } finally {
    setLoading(false);
  }
}

function parseCsvToPointsFC(csvText) {
  const parsed = Papa().parse(csvText, { header: true, dynamicTyping: true, skipEmptyLines: true });
  if (parsed.errors?.length) console.warn("CSV warnings:", parsed.errors);

  const rows = parsed.data || [];
  if (!rows.length) throw new Error("CSV נקודות ריק");

  const cols = Object.keys(rows[0] || {}).map((c) => c.trim());
  const pick = (cands) => cols.find((c) => cands.includes(c)) || cols.find((c) => cands.includes(String(c).toLowerCase()));

  const xCol = pick(["lon","longitude","LONGITUDE","Lon","LON","x","X","E","east","EAST","Easting","EASTING"]);
  const yCol = pick(["lat","latitude","LATITUDE","Lat","LAT","y","Y","N","north","NORTH","Northing","NORTHING"]);
  const vCol = pick(["vel","VEL","velocity","Velocity","v","V","rate","RATE","mm/yr","mm_yr"]);
  const cCol = pick(["coh","COH","coherence","Coherence","coer","COER","quality","QUALITY"]);

  if (!xCol || !yCol) throw new Error(`לא מצאתי עמודות קואורדינטות. יש לי: ${cols.join(", ")}`);

  const sample = rows.find((r) => isFiniteNum(r[xCol]) && isFiniteNum(r[yCol]));
  const sx = sample?.[xCol], sy = sample?.[yCol];
  const seemsLonLat = Math.abs(sx) <= 180 && Math.abs(sy) <= 90;

  const feats = [];
  for (const r of rows) {
    const x = r[xCol], y = r[yCol];
    if (!isFiniteNum(x) || !isFiniteNum(y)) continue;

    let lon = x, lat = y;
    if (!seemsLonLat) {
      const out = proj4() ? proj4()("EPSG:2039", "WGS84", [x, y]) : null;
      if (out) { lon = out[0]; lat = out[1]; }
    }

    if (Math.abs(lon) > 180 || Math.abs(lat) > 90) continue;

    const vel = vCol ? Number(r[vCol]) : null;
    const coh = cCol ? Number(r[cCol]) : null;

    feats.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        vel: isFiniteNum(vel) ? vel : null,
        coh: isFiniteNum(coh) ? coh : null,
      },
    });
  }

  if (!feats.length) throw new Error("לא הצלחתי להפיק נקודות תקינות מה-CSV");
  return { type: "FeatureCollection", features: feats };
}

function buildPointIndex(fc) {
  pointTree = new (RBush())();
  const items = [];
  let c = 0;

  for (const f of fc.features) {
    const co = f?.geometry?.coordinates;
    if (!co || co.length < 2) continue;
    const lon = co[0], lat = co[1];
    if (!isFiniteNum(lon) || !isFiniteNum(lat)) continue;

    items.push({ minX: lon, minY: lat, maxX: lon, maxY: lat, f });
    c++;
  }
  pointTree.load(items);
  pointsCount = c;
}

function drawBuildings(fc) {
  if (!map) return;

  if (buildingsLayer) buildingsLayer.remove();
  buildingsLayer = L().geoJSON(fc, {
    style: (feature) => {
      const id = buildingId(feature);
      const cached = statsCache.get(id);
      const st = (cached && cached.key === paramKey()) ? cached.stats : { status: "no_data" };
      const base = styleByStatus(st);
      if (ui.filterSubs) {
        const show = shouldShowByFilter(st);
        return { ...base, fillOpacity: show ? 0.35 : 0.0, opacity: show ? 0.95 : 0.0 };
      }
      return base;
    },
    onEachFeature: (feature, layer) => {
      layer.on("mouseover", async () => {
        layer.setStyle({ weight: 3, fillOpacity: 0.33 });

        const st = await getOrComputeStats(feature);
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

      layer.on("click", async () => {
        const st = await getOrComputeStats(feature);
        selected.value = { feature, st };
        selectedText.value = selectionText(feature, st);
      });
    },
  }).addTo(map);

  const b = buildingsLayer.getBounds();
  hasBounds.value = b?.isValid?.() === true;
  if (hasBounds.value) map.fitBounds(b.pad(0.08));
}

function redrawPoints() {
  if (!map) return;
  if (!pointsLayer) return;

  pointsLayer.clearLayers();
  if (!ui.showPoints || !pointsFC) return;

  const max = 12000;
  const feats = pointsFC.features.slice(0, max);

  for (const f of feats) {
    const co = f?.geometry?.coordinates;
    if (!co) continue;

    const vel = f.properties?.vel;
    const coh = f.properties?.coh;

    const m = L().circleMarker([co[1], co[0]], {
      radius: 2.5,
      weight: 0,
      fillOpacity: 0.7,
    });

    m.on("click", () => {
      const velTxt = isFiniteNum(vel) ? vel.toFixed(2) : "—";
      const cohTxt = isFiniteNum(coh) ? coh.toFixed(2) : "—";
      m.bindPopup(
        `<div style="font-size:12px;direction:rtl">
          <b>InSAR point</b><br/>
          vel: ${velTxt}<br/>
          coh: ${cohTxt}
        </div>`
      ).openPopup();
    });

    pointsLayer.addLayer(m);
  }

  setStatus(`מוצגות נקודות: ${Math.min(pointsFC.features.length, max)} (מתוך ${pointsFC.features.length}).`);
}

function fitToLayer() {
  if (!buildingsLayer) return;
  const b = buildingsLayer.getBounds();
  if (b && b.isValid()) map.fitBounds(b.pad(0.08));
}

function recolorAll() {
  if (!buildingsLayer) return;
  buildingsLayer.eachLayer((layer) => {
    const f = layer.feature;
    if (!f) return;

    const id = buildingId(f);
    const cached = statsCache.get(id);
    const st = (cached && cached.key === paramKey()) ? cached.stats : { status: "no_data" };
    applyLayerStyle(layer, st);
  });
}

function recolorHard() {
  // thresholds changed => drop caches so hover/click recompute
  statsCache.clear();
  bufferCache.clear();
  recolorAll();
  setStatus("רעננתי צבעים. רחף/לחץ או 'חשב לאזור במסך' כדי לחשב מחדש.");
}

function getBufferedBuilding(buildingFeature) {
  const bm = Number(params.bufM) || 0;
  if (bm <= 0) return buildingFeature;

  const id = buildingId(buildingFeature);
  const k = `${id}|${bm}`;
  if (bufferCache.has(k)) return bufferCache.get(k);

  let out = buildingFeature;
  try {
    out = turf().buffer(buildingFeature, bm, { units: "meters" });
  } catch (e) {
    console.warn("Buffer failed:", e);
    out = buildingFeature;
  }
  bufferCache.set(k, out);
  return out;
}

async function getOrComputeStats(buildingFeature) {
  const id = buildingId(buildingFeature);
  const key = paramKey();

  const cached = statsCache.get(id);
  if (cached && cached.key === key) return cached.stats;

  const st = computeStatsForBuilding(buildingFeature);
  statsCache.set(id, { key, stats: st });
  return st;
}

function computeStatsForBuilding(buildingFeature) {
  if (!pointsFC || !pointTree) return { status: "no_data", count: 0, velMean: null, cohMean: null };

  const bf = getBufferedBuilding(buildingFeature);

  const bb = turf().bbox(bf); // [minX,minY,maxX,maxY]
  const candidates = pointTree.search({ minX: bb[0], minY: bb[1], maxX: bb[2], maxY: bb[3] });

  let cnt = 0, vSum = 0, cSum = 0, vCnt = 0, cCnt = 0;

  for (const it of candidates) {
    const pf = it.f;
    if (!pf?.geometry) continue;

    if (!turf().booleanPointInPolygon(pf, bf)) continue;

    const vel = pf.properties?.vel;
    const coh = pf.properties?.coh;

    if (isFiniteNum(vel)) { vSum += vel; vCnt++; }
    if (isFiniteNum(coh)) { cSum += coh; cCnt++; }

    cnt++;
  }

  if (cnt === 0) return { status: "no_data", count: 0, velMean: null, cohMean: null };

  const velMean = vCnt ? vSum / vCnt : null;
  const cohMean = cCnt ? cSum / cCnt : null;

  const cohOk = (cohMean == null) ? true : (cohMean >= Number(params.thrCoh));
  const cntOk = cnt >= Number(params.minPts);

  let status = "stable";
  if (!cntOk || !cohOk) status = "low_quality";
  else if (velMean == null) status = "no_data";
  else if (velMean < Number(params.thrVel)) status = "subsiding";
  else if (Math.abs(velMean - Number(params.thrVel)) <= 0.5) status = "suspect";
  else status = "stable";

  return { status, count: cnt, velMean, cohMean };
}

function tipHtml(st) {
  const velTxt = st.velMean == null ? "—" : st.velMean.toFixed(2);
  const cohTxt = st.cohMean == null ? "—" : st.cohMean.toFixed(2);
  return `<b>status:</b> ${st.status}
    &nbsp;|&nbsp; <b>Vel_mean:</b> ${velTxt}
    &nbsp;|&nbsp; <b>coer_mean:</b> ${cohTxt}
    &nbsp;|&nbsp; <b>Vel_count:</b> ${st.count}`;
}

function selectionText(feature, st) {
  const id = buildingId(feature);
  const velTxt = st.velMean == null ? "—" : st.velMean.toFixed(2) + " mm/yr";
  const cohTxt = st.cohMean == null ? "—" : st.cohMean.toFixed(2);

  return `מזהה: ${id}
סטטוס: ${st.status}

Vel_mean: ${velTxt}
coer_mean: ${cohTxt}
Vel_count: ${st.count}

הערות:
• low_quality = coherence נמוך או מעט נקודות → לא אמין להסיק.
• no_data = אין נקודות בתוך הבניין/ה-buffer.
`;
}

async function computeVisible() {
  if (!buildingsFC || !map) return;

  setLoading(true, "מחשב סטטיסטיקות לאזור במסך…");
  try {
    const b = map.getBounds();
    const viewPoly = turf().bboxPolygon([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);

    const inView = buildingsFC.features.filter((f) => {
      try {
        const bb = turf().bbox(f);
        const fp = turf().bboxPolygon(bb);
        return turf().booleanIntersects(fp, viewPoly);
      } catch {
        return false;
      }
    });

    const cap = 2500;
    const list = inView.slice(0, cap);

    let done = 0;
    for (const f of list) {
      await getOrComputeStats(f);
      done++;
      if (done % 80 === 0) {
        loadingText.value = `מחשב… ${done}/${list.length}`;
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    recolorAll();
    setStatus(`חישבתי לאזור במסך: ${done}/${inView.length} (מוגבל ל-${cap}).`);
  } finally {
    setLoading(false);
  }
}

// ----- Leaflet init
onMounted(() => {
  ensureProj();

  map = L().map("map", { zoomControl: true, preferCanvas: true }).setView([32.0853, 34.7818], 15);

  L().tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 20, attribution: "Tiles © Esri" }
  ).addTo(map);

  L().tileLayer(
    "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 20, opacity: 0.9, attribution: "Labels © Esri" }
  ).addTo(map);

  pointsLayer = L().layerGroup().addTo(map);

  window.addEventListener("mousemove", onMouseMove, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onMouseMove);
  if (map) map.remove();
});

// Watchers
watch(() => ui.showPoints, () => redrawPoints());
watch(() => ui.filterSubs, () => recolorAll());

// אם משנים ספים – לא מחשבים אוטומטית (כדי לא להכביד). הכפתור “רענן צבעים” עושה reset.
</script>

<style>
:root{
  --bg:#0b1220;
  --panel:#0f172a;
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

/* layout */
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
}
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

.selBox{
  background: rgba(0,0,0,.18);
  border:1px dashed rgba(255,255,255,.12);
  border-radius:14px;
  padding:10px;
  line-height:1.45;
  font-size:12px;
  white-space: pre-wrap;
}
.muted{ color: var(--muted); }

.statusBox{
  padding:10px;
  border-radius:14px;
  background: rgba(0,0,0,.18);
  border:1px solid rgba(255,255,255,.10);
  font-size:12px;
  line-height:1.45;
}

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

/* responsive: panel slide on small screens */
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

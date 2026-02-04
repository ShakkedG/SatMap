<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Buildings Joined (GeoJSON) – תצוגה + סיווג + מקרא + “איך זה עובד”</div>
        </div>
        <div class="topBtns">
          <button class="btn ghost" @click="fitToLayer" :disabled="!allBoundsValid">התמקד בשכבה</button>
          <button class="btn" @click="reload">טען מחדש</button>
        </div>
      </div>

      <!-- ===== Data source / diagnostics ===== -->
      <div class="box">
        <div class="row2">
          <div>
            <label>רקע מפה</label>
            <select v-model="basemap" @change="applyBasemap">
              <option value="esri">Satellite (Esri)</option>
              <option value="osm">OSM</option>
            </select>
          </div>

          <div>
            <label>GeoJSON נטען מ־</label>
            <div class="mono smallLine" :title="loadedFrom || ''">{{ loadedFrom || "—" }}</div>
          </div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <details class="miniBox" v-if="attempts.length">
          <summary class="sumTitle">בדיקת נתיבים (Debug)</summary>
          <div class="dbg">
            <div v-for="(a,i) in attempts" :key="i" class="dbgRow">
              <span class="mono">{{ a.url }}</span>
              <span class="dbgTag" :class="a.ok ? 'ok' : 'bad'">{{ a.ok ? "OK" : a.note }}</span>
            </div>
          </div>
        </details>
      </div>

      <!-- ===== KPIs ===== -->
      <div class="box">
        <div class="kpis">
          <div class="kpi"><div class="k">סה״כ בניינים</div><div class="v">{{ stats.total }}</div></div>
          <div class="kpi sink"><div class="k">שוקע/חשוד</div><div class="v">{{ stats.sinking }}</div></div>
          <div class="kpi stable"><div class="k">יציב</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi lowq"><div class="k">איכות נמוכה</div><div class="v">{{ stats.lowq }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.noData }}</div></div>
        </div>

        <div class="row2" style="margin-top:10px">
          <label class="chk">
            <input type="checkbox" v-model="showSinking" @change="applyVisibility" />
            להציג שוקע/חשוד
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showStable" @change="applyVisibility" />
            להציג יציב
          </label>
        </div>
        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showLowQ" @change="applyVisibility" />
            להציג איכות נמוכה
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showNoData" @change="applyVisibility" />
            להציג אין נתון
          </label>
        </div>
      </div>

      <!-- ===== Classification controls ===== -->
      <div class="box">
        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="useQgisStatus" @change="scheduleReload" />
            להשתמש ב־status מהקובץ (QGIS)
          </label>

          <label class="chk">
            <input type="checkbox" v-model="flipSign" :disabled="useQgisStatus" @change="scheduleReload" />
            Flip sign ל־Vel_mean
          </label>
        </div>

        <div class="row2">
          <div>
            <label>סף חשוד (Vel_mean ≤)</label>
            <input
              type="number"
              v-model.number="rateThreshold"
              step="0.5"
              :disabled="useQgisStatus"
              @input="scheduleReload"
            />
            <div class="hint">בשביל InSAR לרוב זה במ״מ/שנה. אם אצלך זה יוצא “חיובי”, נסה Flip sign.</div>
          </div>

          <div>
            <label>מינימום coherence (coer_mean)</label>
            <input
              type="number"
              v-model.number="minCoh"
              step="0.05"
              min="0"
              max="1"
              :disabled="useQgisStatus"
              @input="scheduleReload"
            />
            <div class="hint">מתחת לזה → “איכות נמוכה”</div>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>מינימום נק׳ (Vel_count)</label>
            <input
              type="number"
              v-model.number="minPts"
              step="1"
              min="0"
              :disabled="useQgisStatus"
              @input="scheduleReload"
            />
            <div class="hint">מתחת לזה → “אין נתון” (או לא יציב)</div>
          </div>

          <div>
            <label>שדה לצביעה</label>
            <select v-model="colorMode" @change="scheduleReload">
              <option value="status">לפי סטטוס</option>
              <option value="rate">חומרה לפי Vel_mean</option>
              <option value="coh">שקיפות לפי coherence</option>
            </select>
          </div>
        </div>
      </div>

      <!-- ===== Legend ===== -->
      <div class="box">
        <div class="boxTitle">מקרא (Legend)</div>

        <div class="legend">
          <div class="legRow">
            <span class="sw sw-sink"></span>
            <div class="legText">
              <b>שוקע/חשוד</b>
              <div class="hint">
                <span v-if="useQgisStatus">לפי השדה <span class="mono">status</span> בקובץ</span>
                <span v-else>Vel_mean ≤ {{ rateThreshold }} וגם coher_mean ≥ {{ minCoh }} וגם Vel_count ≥ {{ minPts }}</span>
              </div>
            </div>
          </div>

          <div class="legRow">
            <span class="sw sw-stable"></span>
            <div class="legText">
              <b>יציב</b>
              <div class="hint">
                <span v-if="useQgisStatus">לפי <span class="mono">status</span></span>
                <span v-else>Vel_mean &gt; {{ rateThreshold }} (ועובר איכות/כמות)</span>
              </div>
            </div>
          </div>

          <div class="legRow">
            <span class="sw sw-lowq"></span>
            <div class="legText">
              <b>איכות נמוכה</b>
              <div class="hint">
                <span v-if="useQgisStatus">לפי <span class="mono">status</span></span>
                <span v-else>coer_mean &lt; {{ minCoh }}</span>
              </div>
            </div>
          </div>

          <div class="legRow">
            <span class="sw sw-nodata"></span>
            <div class="legText">
              <b>אין נתון</b>
              <div class="hint">
                <span v-if="useQgisStatus">לפי <span class="mono">status</span></span>
                <span v-else>Vel_count &lt; {{ minPts }} או שדה חסר/Null</span>
              </div>
            </div>
          </div>
        </div>

        <div class="mini muted" style="margin-top:10px">
          מצב צביעה:
          <b>{{ colorMode === "status" ? "סטטוס" : colorMode === "rate" ? "Vel_mean" : "Coherence" }}</b>
          <span v-if="colorMode === 'rate'"> — יותר “חשוד” = אדום חזק יותר</span>
          <span v-if="colorMode === 'coh'"> — coherence גבוה = אטום יותר</span>
        </div>
      </div>

      <!-- ===== How it works ===== -->
      <details class="box" open>
        <summary class="sumTitle">איך זה עובד (Data dictionary + לוגיקה)</summary>

        <div class="gloss">
          <div class="glRow">
            <div class="glKey">מאיפה נטען הקובץ?</div>
            <div class="glVal">
              האתר מנסה כמה נתיבים עד שאחד מצליח:
              <ul>
                <li class="mono">{{ baseUrl }}buildings_joined.geojson</li>
                <li class="mono">{{ baseUrl }}data/buildings_joined.geojson</li>
                <li class="mono">raw.githubusercontent.com (fallback)</li>
              </ul>
              הסיבה: GitHub Pages בפרויקט (repo) יושב תחת <span class="mono">/SatMap/</span>, אז צריך לעבוד עם <span class="mono">BASE_URL</span>.
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">אילו שדות אנחנו משתמשים?</div>
            <div class="glVal">
              הקוד מחפש את השמות בצורה “חכמה” (לא רגיש לאותיות גדולות/קטנות):
              <ul>
                <li><b>status</b> → <span class="mono">status / STATUS / Status</span></li>
                <li><b>Vel_mean</b> → <span class="mono">Vel_mean / vel_mean / VEL_MEAN</span></li>
                <li><b>Vel_count</b> → <span class="mono">Vel_count / vel_count / VEL_COUNT</span></li>
                <li><b>coer_mean</b> → <span class="mono">coer_mean / COER_MEAN / coh_mean</span></li>
              </ul>
              אם חסר שדה — יופיע “—” בכלי־עזר (tooltip) ובפאנל.
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">איך נקבע סטטוס?</div>
            <div class="glVal">
              יש 2 מצבים:
              <ul>
                <li><b>Use QGIS status</b>: משתמשים ב־<span class="mono">status</span> שכבר חישבת ב־QGIS.</li>
                <li><b>Recompute</b>: מחשבים מחדש לפי הספים בפאנל:
                  <div class="mono" style="margin-top:6px">
                    אם Vel_count &lt; minPts → no_data<br/>
                    אחרת אם coer_mean &lt; minCoh → low_quality<br/>
                    אחרת אם Vel_mean ≤ rateThreshold → suspected_subsidence<br/>
                    אחרת → stable
                  </div>
                </li>
              </ul>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">למה יש Flip sign?</div>
            <div class="glVal">
              לפעמים בדאטה כיוון הסימן הפוך (למשל שקיעה יוצאת חיובית).  
              Flip sign מאפשר לבדוק מהר אם זה “מתיישר” עם ההיגיון, בלי לחזור ל־QGIS.
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">למה הצבעים/מקווקו?</div>
            <div class="glVal">
              “איכות נמוכה” ו“אין נתון” מקבלים דפוס מקווקו כדי להבדיל ברור מהמצבים האחרים גם כשיש זום רחוק.
            </div>
          </div>
        </div>
      </details>

      <!-- ===== Search + list ===== -->
      <details class="box" open>
        <summary class="sumTitle">רשימת חשודים (חיפוש מהיר)</summary>

        <div class="row2">
          <div>
            <label>חיפוש (OBJECTID / שם)</label>
            <input v-model="q" type="text" placeholder="לדוגמה: 188" />
          </div>
          <div>
            <label>מינימום coherence לרשימה</label>
            <input v-model.number="listMinCoh" type="number" step="0.05" min="0" max="1" />
          </div>
        </div>

        <div class="mini muted" style="margin-top:8px">
          מציג רק “שוקע/חשוד” וגם coher_mean ≥ {{ listMinCoh }}.
        </div>

        <div class="list">
          <button
            v-for="r in suspectsList"
            :key="r.key"
            class="listItem"
            @click="zoomToRow(r)"
            :title="'זום + פרטים'"
          >
            <div class="liTop">
              <div class="liName">{{ r.name }}</div>
              <div class="badge danger">חשוד</div>
            </div>
            <div class="liMeta">
              <span class="mono">Vel_mean {{ r.velLabel }}</span>
              <span class="dot">•</span>
              <span class="mono">coer_mean {{ r.cohLabel }}</span>
              <span class="dot">•</span>
              <span class="mono">pts {{ r.countLabel }}</span>
            </div>
          </button>

          <div v-if="!suspectsList.length" class="mini muted" style="margin-top:10px">
            אין תוצאות כרגע — נסה להוריד listMinCoh או לנקות חיפוש.
          </div>
        </div>
      </details>

      <!-- ===== Selected ===== -->
      <div class="box" v-if="selected">
        <div class="selHeader">
          <div class="mini"><b>{{ selected.name }}</b></div>
          <button class="btn ghost small" @click="clearSelection">נקה בחירה</button>
        </div>

        <div class="selGrid">
          <div class="selCard">
            <div class="k">status (בשימוש)</div>
            <div class="v" :class="{ danger: selected.bucket === 'sinking' }">{{ selected.status }}</div>
          </div>

          <div class="selCard">
            <div class="k">Vel_mean</div>
            <div class="v mono">{{ selected.velMean }}</div>
          </div>

          <div class="selCard">
            <div class="k">coer_mean</div>
            <div class="v mono">{{ selected.cohMean }}</div>
          </div>

          <div class="selCard">
            <div class="k">Vel_count</div>
            <div class="v mono">{{ selected.velCount }}</div>
          </div>
        </div>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const baseUrl = import.meta.env.BASE_URL;

// ===== UI state =====
const basemap = ref("esri");

const loadMsg = ref("");
const loadErr = ref("");
const loadedFrom = ref("");
const attempts = ref([]);

const showSinking = ref(true);
const showStable = ref(true);
const showLowQ = ref(true);
const showNoData = ref(false);

const useQgisStatus = ref(true);

const rateThreshold = ref(-2);
const minCoh = ref(0.35);
const minPts = ref(3);
const flipSign = ref(false);

const colorMode = ref("status"); // status | rate | coh

const q = ref("");
const listMinCoh = ref(0.35);

const stats = ref({ total: 0, sinking: 0, stable: 0, lowq: 0, noData: 0 });
const selected = ref(null);

// ===== Leaflet =====
let map = null;
let osmLayer = null;
let esriLayer = null;

let sinkingGroup = null;
let stableGroup = null;
let lowqGroup = null;
let noDataGroup = null;

let allBounds = null;
const allBoundsValid = ref(false);

// In-memory rows for list/search
const rows = ref([]);

// ===== helpers =====
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmt2(n) {
  return n == null ? "—" : Number(n).toFixed(2);
}
function pickField(props, candidates) {
  if (!props) return "";
  for (const k of candidates) {
    if (Object.prototype.hasOwnProperty.call(props, k)) return k;
  }
  const keys = Object.keys(props);
  const lower = new Map(keys.map(k => [k.toLowerCase(), k]));
  for (const c of candidates) {
    const real = lower.get(String(c).toLowerCase());
    if (real) return real;
  }
  return "";
}

function buildingsCandidates() {
  const ts = Date.now();
  return [
    `${baseUrl}buildings_joined.geojson?ts=${ts}`,
    `${baseUrl}data/buildings_joined.geojson?ts=${ts}`,
    `https://raw.githubusercontent.com/ShakkedG/SatMap/main/buildings_joined.geojson?ts=${ts}`,
  ];
}

async function fetchFirstOk(urls) {
  const localAttempts = [];
  for (const url of urls) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) {
        localAttempts.push({ url, ok: false, note: `HTTP ${r.status}` });
        continue;
      }
      const j = await r.json();
      localAttempts.push({ url, ok: true, note: "OK" });
      attempts.value = localAttempts;
      return { url, json: j };
    } catch (e) {
      localAttempts.push({ url, ok: false, note: "ERR" });
    }
  }
  attempts.value = localAttempts;
  throw new Error(localAttempts.at(-1)?.note ? `Load failed (${localAttempts.at(-1).note})` : "Load failed");
}

function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, preferCanvas: true }).setView([32.08, 34.78], 12);

  osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19, maxZoom: 22, attribution: "&copy; OpenStreetMap",
  });

  esriLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 22, attribution: "&copy; Esri" }
  );

  applyBasemap();

  sinkingGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup().addTo(map);
  lowqGroup = new L.FeatureGroup().addTo(map);
  noDataGroup = new L.FeatureGroup().addTo(map);
}

function applyBasemap() {
  if (!map) return;
  [osmLayer, esriLayer].forEach(l => { if (l && map.hasLayer(l)) map.removeLayer(l); });
  (basemap.value === "osm" ? osmLayer : esriLayer)?.addTo(map);
}

function applyVisibility() {
  if (!map) return;

  const ensure = (layer, on) => {
    if (!layer) return;
    if (on) { if (!map.hasLayer(layer)) layer.addTo(map); }
    else { if (map.hasLayer(layer)) map.removeLayer(layer); }
  };

  ensure(sinkingGroup, showSinking.value);
  ensure(stableGroup, showStable.value);
  ensure(lowqGroup, showLowQ.value);
  ensure(noDataGroup, showNoData.value);
}

function fitToLayer() {
  if (allBounds?.isValid?.()) {
    try { map.fitBounds(allBounds.pad(0.08)); } catch {}
  }
}
function clearSelection() { selected.value = null; }

function pickName(props, idx) {
  const f = pickField(props, ["name","NAME","building_id","id","OBJECTID","objectid","UNIQ_ID","uniq_id"]);
  if (f) return String(props[f]);
  return `בניין ${idx + 1}`;
}

/** Normalize "status" text from QGIS (or anything else) */
function normalizeStatusText(raw) {
  const s = String(raw ?? "").trim().toLowerCase();
  if (!s) return "no_data";
  if (s.includes("suspected") || s.includes("sink")) return "suspected_subsidence";
  if (s.includes("stable") || s.includes("uplift")) return "stable";
  if (s.includes("low_quality") || s.includes("low quality") || s.includes("low")) return "low_quality";
  if (s.includes("no_data") || s.includes("nodata") || s === "null") return "no_data";
  return s;
}

/** Decide bucket (sinking/stable/lowq/nodata) */
function bucketFromStatus(norm) {
  if (norm === "suspected_subsidence" || norm === "sinking") return "sinking";
  if (norm === "stable") return "stable";
  if (norm === "low_quality") return "lowq";
  return "nodata";
}

/** Recompute status from numeric fields (if not using QGIS status) */
function computeStatusFromFields(velMean, cohMean, velCount) {
  const c = velCount ?? null;
  const coh = cohMean ?? null;
  let v = velMean ?? null;

  if (v != null && flipSign.value) v = -v;

  if (c == null || c < (minPts.value ?? 0)) return { normStatus: "no_data", bucket: "nodata", vAdj: v };
  if (coh == null || coh < (minCoh.value ?? 0)) return { normStatus: "low_quality", bucket: "lowq", vAdj: v };
  if (v == null) return { normStatus: "no_data", bucket: "nodata", vAdj: v };
  if (v <= (rateThreshold.value ?? -2)) return { normStatus: "suspected_subsidence", bucket: "sinking", vAdj: v };
  return { normStatus: "stable", bucket: "stable", vAdj: v };
}

/** Styling */
function styleFor(bucket, vAdj, cohMeanVal) {
  // Base styles by category
  if (bucket === "nodata") {
    return { color: "#64748b", weight: 2.0, opacity: 0.85, fill: true, fillColor: "#cbd5e1", fillOpacity: 0.18, dashArray: "6 6" };
  }
  if (bucket === "lowq") {
    return { color: "#b45309", weight: 2.0, opacity: 0.9, fill: true, fillColor: "#f59e0b", fillOpacity: 0.20, dashArray: "5 4" };
  }
  if (bucket === "stable") {
    // stable light
    const fo = colorMode.value === "coh" ? opacityFromCoh(cohMeanVal, 0.15, 0.35) : 0.25;
    return { color: "#1d4ed8", weight: 2.0, opacity: 0.9, fill: true, fillColor: "#60a5fa", fillOpacity: fo };
  }

  // sinking
  let fillOpacity = 0.45;
  if (colorMode.value === "rate" && vAdj != null) {
    // make stronger red when more negative than threshold
    const thr = rateThreshold.value ?? -2;
    const ratio = thr === 0 ? 1 : Math.abs(vAdj / thr);
    const s = clamp01((ratio - 1) / 2); // 0..1
    fillOpacity = 0.28 + s * 0.55;
  } else if (colorMode.value === "coh") {
    fillOpacity = opacityFromCoh(cohMeanVal, 0.25, 0.55);
  }
  return { color: "#b91c1c", weight: 2.4, opacity: 0.95, fill: true, fillColor: "#ef4444", fillOpacity };
}

function clamp01(x) { return Math.max(0, Math.min(1, x)); }
function opacityFromCoh(coh, min=0.2, max=0.7) {
  if (coh == null) return min;
  // coherence 0..1 map
  const t = clamp01(coh);
  return min + (max - min) * t;
}

function applyHover(pathLayer, baseStyle) {
  pathLayer.on("mouseover", () => {
    try {
      pathLayer.setStyle?.({
        weight: Math.max(3, (baseStyle?.weight ?? 2) + 1),
        opacity: 1,
        fillOpacity: Math.min(0.85, (baseStyle?.fillOpacity ?? 0.25) + 0.15),
      });
      pathLayer.bringToFront?.();
    } catch {}
  });
  pathLayer.on("mouseout", () => {
    try { pathLayer.setStyle?.(baseStyle); } catch {}
  });
}

async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען GeoJSON…";
  loadedFrom.value = "";
  clearSelection();
  rows.value = [];

  sinkingGroup?.clearLayers?.();
  stableGroup?.clearLayers?.();
  lowqGroup?.clearLayers?.();
  noDataGroup?.clearLayers?.();

  allBounds = null;
  allBoundsValid.value = false;

  try {
    const { url, json } = await fetchFirstOk(buildingsCandidates());
    loadedFrom.value = url;

    const feats = Array.isArray(json?.features) ? json.features : [];
    let sinking = 0, stable = 0, lowq = 0, noData = 0;

    for (let i = 0; i < feats.length; i++) {
      const f = feats[i];
      const props = f?.properties || {};

      const statusField = pickField(props, ["status","Status","STATUS"]);
      const velMeanField = pickField(props, ["Vel_mean","vel_mean","VEL_MEAN"]);
      const velCountField = pickField(props, ["Vel_count","vel_count","VEL_COUNT"]);
      const cohMeanField = pickField(props, ["coer_mean","Coer_mean","COER_MEAN","coh_mean","Coh_mean"]);

      const velMean = velMeanField ? toNum(props[velMeanField]) : null;
      const velCount = velCountField ? toNum(props[velCountField]) : null;
      const cohMean = cohMeanField ? toNum(props[cohMeanField]) : null;

      let normStatus, bucket, vAdj;

      if (useQgisStatus.value) {
        normStatus = normalizeStatusText(statusField ? props[statusField] : "");
        bucket = bucketFromStatus(normStatus);
        vAdj = flipSign.value && velMean != null ? -velMean : velMean;
      } else {
        const out = computeStatusFromFields(velMean, cohMean, velCount);
        normStatus = out.normStatus;
        bucket = out.bucket;
        vAdj = out.vAdj;
      }

      if (bucket === "sinking") sinking++;
      else if (bucket === "stable") stable++;
      else if (bucket === "lowq") lowq++;
      else noData++;

      const name = pickName(props, i);
      const baseStyle = styleFor(bucket, vAdj, cohMean);

      const layer = L.geoJSON(f, {
        style: baseStyle,
        onEachFeature: (_feat, pathLayer) => {
          applyHover(pathLayer, baseStyle);

          const tt = [
            `status: ${normStatus || "—"}`,
            `Vel_mean: ${fmt2(vAdj)}${flipSign.value ? " (flipped)" : ""}`,
            `coer_mean: ${fmt2(cohMean)}`,
            `Vel_count: ${velCount ?? "—"}`,
          ].join(" | ");

          pathLayer.bindTooltip(tt, { sticky: true, direction: "top", opacity: 0.95 });

          pathLayer.on("click", () => {
            selected.value = {
              name,
              status: normStatus || "—",
              bucket,
              velMean: fmt2(vAdj),
              cohMean: fmt2(cohMean),
              velCount: velCount ?? "—",
            };
          });
        },
      });

      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) allBounds = allBounds ? allBounds.extend(b) : b;
      } catch {}

      if (bucket === "sinking") layer.addTo(sinkingGroup);
      else if (bucket === "stable") layer.addTo(stableGroup);
      else if (bucket === "lowq") layer.addTo(lowqGroup);
      else layer.addTo(noDataGroup);

      rows.value.push({
        key: `${i}-${name}`,
        name,
        bucket,
        status: normStatus,
        velAdj: vAdj,
        cohMean,
        velCount,
        bounds: (() => { try { return layer.getBounds(); } catch { return null; } })(),
      });
    }

    stats.value = { total: feats.length, sinking, stable, lowq, noData };
    allBoundsValid.value = !!allBounds?.isValid?.();

    if (allBoundsValid.value) {
      try { map.fitBounds(allBounds.pad(0.08)); } catch {}
    }

    applyVisibility();
    loadMsg.value = `נטענו ${feats.length} בניינים`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, sinking: 0, stable: 0, lowq: 0, noData: 0 };
  }
}

function zoomToRow(r) {
  try {
    if (r?.bounds?.isValid?.()) map.fitBounds(r.bounds.pad(0.15));
  } catch {}
  selected.value = {
    name: r.name,
    status: r.status,
    bucket: r.bucket,
    velMean: fmt2(r.velAdj),
    cohMean: fmt2(r.cohMean),
    velCount: r.velCount ?? "—",
  };
}

function reload() { loadAndRender(); }

// ===== suspects list =====
const suspectsList = computed(() => {
  const needle = (q.value || "").trim().toLowerCase();

  return rows.value
    .filter(r => r.bucket === "sinking")
    .filter(r => (r.cohMean ?? 0) >= (listMinCoh.value ?? 0))
    .filter(r => !needle || String(r.name).toLowerCase().includes(needle) || String(r.name).includes(needle))
    .sort((a,b) => (a.velAdj ?? Infinity) - (b.velAdj ?? Infinity)) // יותר שלילי ראשון
    .slice(0, 40)
    .map(r => ({
      ...r,
      velLabel: fmt2(r.velAdj),
      cohLabel: fmt2(r.cohMean),
      countLabel: r.velCount ?? "—",
    }));
});

// ===== tiny debounce =====
let t = null;
function scheduleReload() {
  if (t) clearTimeout(t);
  t = setTimeout(() => loadAndRender(), 200);
}

onMounted(async () => {
  initMap();
  await loadAndRender();
});
</script>

<style>
.layout { display:grid; grid-template-columns: 460px 1fr; height:100vh; background:#f3f4f6; font-family:system-ui, Arial; }
.panel { background:#fff; border-left:1px solid #e5e7eb; padding:12px; overflow:auto; }
.mapWrap { position:relative; }
#map { width:100%; height:100vh; }

.top { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:10px; }
.topBtns { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.title { font-weight:900; font-size:18px; }
.sub { font-size:12px; opacity:0.72; margin-top:2px; }

.box { border:1px solid #e5e7eb; border-radius:16px; padding:10px; background:#fff; margin-bottom:10px; }
.boxTitle { font-weight:900; margin-bottom:8px; }
label { display:block; font-size:12px; opacity:0.85; margin-bottom:6px; }

input, select { width:100%; padding:10px; border-radius:12px; border:1px solid #e5e7eb; font-size:14px; background:#fff; }
select { cursor:pointer; }

.btn { cursor:pointer; background:#111827; color:#fff; border:1px solid #111827; font-weight:700; padding:10px; border-radius:12px; width:auto; }
.btn.ghost { background:#fff; color:#111827; border-color:#e5e7eb; }
.btn.small { padding:8px 10px; font-size:12px; border-radius:10px; }
.btn:disabled { opacity:0.55; cursor:not-allowed; }

.row2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:6px; }
.chk { display:flex; align-items:center; gap:8px; font-size:12px; opacity:0.9; margin-top:8px; }
.chk input[type="checkbox"] { width:auto; padding:0; margin:0; }

.kpis { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:4px; }
.kpi { border:1px solid #e5e7eb; border-radius:12px; padding:10px; background:#f9fafb; }
.kpi .k { font-size:12px; opacity:0.7; }
.kpi .v { font-weight:900; font-size:18px; }
.kpi.sink { border-color:#fecaca; background:#fef2f2; }
.kpi.stable { border-color:#bfdbfe; background:#eff6ff; }
.kpi.lowq { border-color:#fed7aa; background:#fff7ed; }
.kpi.nodata { border-color:#e2e8f0; background:#f8fafc; }

.legend { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; display:grid; gap:10px; }
.legRow { display:flex; align-items:flex-start; gap:10px; }
.legText { flex:1; }
.sw { width:18px; height:10px; border-radius:4px; border:1px solid #e5e7eb; margin-top:4px; }
.sw-sink { background:#fee2e2; border-color:#b91c1c; }
.sw-stable { background:#dbeafe; border-color:#1d4ed8; }
.sw-lowq { background:#fff7ed; border-color:#b45309; }
.sw-nodata { background:#e2e8f0; border-color:#64748b; }

.selHeader { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
.selGrid { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px; }
.selCard { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#f9fafb; }
.selCard .k { font-size:12px; opacity:0.7; }
.selCard .v { font-weight:900; font-size:14px; margin-top:4px; }
.selCard .v.danger { color:#991b1b; }

.mini { font-size:12px; opacity:0.92; margin-top:8px; }
.muted { opacity:0.72; }
.err { color:#b91c1c; opacity:1; }
.hint { font-size:11px; opacity:0.7; margin-top:6px; line-height:1.4; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.mono.smallLine { font-size:12px; opacity:0.9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

.sumTitle { cursor:pointer; font-weight:900; list-style:none; user-select:none; }
details > summary::-webkit-details-marker { display:none; }

.gloss { margin-top:10px; display:grid; gap:10px; }
.glRow { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; }
.glKey { font-weight:900; margin-bottom:6px; }
.glVal { font-size:12px; opacity:0.92; line-height:1.55; }
.glVal ul { margin:6px 18px 0 0; padding:0; }
.glVal li { margin:4px 0; }

.list { display:grid; gap:8px; margin-top:10px; }
.listItem { text-align:right; border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; cursor:pointer; }
.listItem:hover { border-color:#cbd5e1; background:#f8fafc; }
.liTop { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.liName { font-weight:900; font-size:13px; }
.liMeta { margin-top:6px; font-size:12px; opacity:0.85; display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.dot { opacity:0.55; }
.badge { font-size:11px; font-weight:900; padding:4px 8px; border-radius:999px; border:1px solid #e5e7eb; background:#f8fafc; }
.badge.danger { background:#fef2f2; border-color:#fecaca; color:#991b1b; }

.miniBox { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; margin-top:10px; }
.dbg { display:grid; gap:8px; margin-top:10px; }
.dbgRow { display:flex; gap:10px; align-items:center; justify-content:space-between; }
.dbgTag { font-size:11px; font-weight:900; padding:3px 8px; border-radius:999px; border:1px solid #e5e7eb; }
.dbgTag.ok { background:#ecfdf5; border-color:#a7f3d0; }
.dbgTag.bad { background:#fef2f2; border-color:#fecaca; color:#991b1b; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 54vh; border-left:none; border-bottom:1px solid #e5e7eb; }
  #map { height: 46vh; }
}
</style>

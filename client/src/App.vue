<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Buildings Joined (GeoJSON) – תצוגה + סיווג + מקרא + חלון נתונים</div>
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
          <summary class="sumTitle">(Debug) בדיקת נתיבים</summary>
          <div class="dbg">
            <div v-for="(a,i) in attempts" :key="i" class="dbgRow">
              <span class="mono">{{ a.url }}</span>
              <span class="dbgTag" :class="a.ok ? 'ok' : 'bad'">{{ a.ok ? "OK" : a.note }}</span>
            </div>
          </div>
          <div class="hint" style="margin-top:10px">
            אם אתה רואה שהטענה מצליחה רק מ־raw.githubusercontent — מומלץ לשים את הקובץ ב־
            <span class="mono">client/public/data/buildings_joined.geojson</span>
            כדי שייטען מהאתר עצמו.
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
            <div class="hint">היחידות תלויות במקור שלך. אם “שקיעה” יוצאת הפוך — נסה Flip sign.</div>
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
            <div class="hint">מתחת לזה → “אין נתון”</div>
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
        </div>
      </div>

      <!-- ===== How it works ===== -->
      <details class="box">
        <summary class="sumTitle">איך זה עובד (לוגיקה)</summary>
        <div class="gloss">
          <div class="glRow">
            <div class="glKey">סטטוס</div>
            <div class="glVal">
              אם מסומן “להשתמש ב־status מהקובץ” — האתר משתמש ישירות ב־<span class="mono">status</span> שאתה חישבת ב־QGIS.<br />
              אחרת — האתר מחשב לפי:
              <div class="mono" style="margin-top:6px">
                אם Vel_count &lt; minPts → no_data<br/>
                אחרת אם coer_mean &lt; minCoh → low_quality<br/>
                אחרת אם Vel_mean ≤ rateThreshold → suspected_subsidence<br/>
                אחרת → stable
              </div>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">Vel_mean / coer_mean / Vel_count</div>
            <div class="glVal">
              אלו שדות שאתה כבר יצרת מתוך שיוך נקודות InSAR לבניינים (למשל Spatial Join + סיכומים).<br />
              בחלון הנתונים של כל בניין תראה גם “מה זה אומר” לכל שדה.
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
            :title="'זום + חלון נתונים'"
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

      <!-- ===== Selected (compact) ===== -->
      <div class="box" v-if="selected">
        <div class="selHeader">
          <div class="mini"><b>{{ selected.name }}</b></div>
          <div class="topBtns">
            <button class="btn ghost small" @click="openInfo">פתח חלון נתונים</button>
            <button class="btn ghost small" @click="clearSelection">נקה</button>
          </div>
        </div>

        <div class="selGrid">
          <div class="selCard">
            <div class="k">סטטוס</div>
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

    <!-- ===== Modal: Feature Info ===== -->
    <div v-if="infoOpen" class="modalBack" @click.self="closeInfo">
      <div class="modal">
        <div class="modalHeader">
          <div class="mhLeft">
            <div class="mhTitle">נתוני בניין</div>
            <div class="mhSub mono">{{ selected?.name || "—" }}</div>
          </div>
          <button class="iconBtn" @click="closeInfo" title="סגור">✕</button>
        </div>

        <div class="modalBody">
          <div class="tabs">
            <button class="tab" :class="{ on: infoTab === 'main' }" @click="infoTab = 'main'">שדות מרכזיים</button>
            <button class="tab" :class="{ on: infoTab === 'all' }" @click="infoTab = 'all'">כל השדות</button>
            <button class="tab" :class="{ on: infoTab === 'logic' }" @click="infoTab = 'logic'">איך נקבע</button>
          </div>

          <!-- ===== MAIN ===== -->
          <div v-if="infoTab === 'main'" class="grid2">
            <div class="infoCard">
              <div class="k">status</div>
              <div class="v">{{ selected?.status || "—" }}</div>
              <div class="desc">
                קטגוריית הבניין (למשל <span class="mono">stable</span>, <span class="mono">suspected_subsidence</span>, <span class="mono">low_quality</span>, <span class="mono">no_data</span>).<br/>
                אם מסומן “להשתמש ב־status מהקובץ” — זה מגיע ישירות מ־QGIS. אחרת זה מחושב לפי הספים בפאנל.
              </div>
            </div>

            <div class="infoCard">
              <div class="k">Vel_mean</div>
              <div class="v mono">{{ selected?.velMean || "—" }}</div>
              <div class="desc">
                ממוצע מהירות/קצב תזוזה שחושב לבניין מתוך נקודות InSAR ששויכו אליו.<br/>
                <b>חשוב:</b> היחידות והכיוון תלויים במקור הנתונים שלך; אם נראה שהסימן הפוך, אפשר להפעיל <b>Flip sign</b> ולבדוק.
              </div>
            </div>

            <div class="infoCard">
              <div class="k">coer_mean</div>
              <div class="v mono">{{ selected?.cohMean || "—" }}</div>
              <div class="desc">
                ממוצע/מדד coherence (לרוב בין 0 ל־1). גבוה יותר בדרך כלל אומר שהמדידה יציבה/אמינה יותר.<br/>
                אם הערך נמוך מהסף בפאנל — האתר יכול לסמן “איכות נמוכה”.
              </div>
            </div>

            <div class="infoCard">
              <div class="k">Vel_count</div>
              <div class="v mono">{{ selected?.velCount || "—" }}</div>
              <div class="desc">
                כמה נקודות InSAR השתתפו בחישוב של הבניין (מספר הדגימות ששויכו לפוליגון).<br/>
                מעט נקודות → אמינות נמוכה יותר; מתחת לסף בפאנל → “אין נתון”.
              </div>
            </div>

            <div class="infoCard" v-if="selected?.objectId != null">
              <div class="k">OBJECTID</div>
              <div class="v mono">{{ selected.objectId }}</div>
              <div class="desc">
                מזהה ייחודי של הפיצ’ר בשכבה (נוח לחיפוש/השוואה).
              </div>
            </div>

            <div class="infoCard">
              <div class="k">טיפ שימושי</div>
              <div class="v">מה לבדוק אם משהו “לא הגיוני”</div>
              <div class="desc">
                1) נסה <b>Flip sign</b>.<br/>
                2) נסה להוריד/להעלות את <b>סף החשוד</b>.<br/>
                3) תסתכל על <b>Vel_count</b> ו־<b>coer_mean</b> כדי להבין אמינות.
              </div>
            </div>
          </div>

          <!-- ===== ALL FIELDS ===== -->
          <div v-if="infoTab === 'all'">
            <div class="mini muted" style="margin-bottom:10px">
              כאן מוצגים כל ה־properties כמו שהם בקובץ (ללא סינון).
            </div>

            <div class="kvTable">
              <div class="kvRow" v-for="(v,k) in selected?.rawProps || {}" :key="k">
                <div class="kvKey mono">{{ k }}</div>
                <div class="kvVal mono">{{ stringifyVal(v) }}</div>
              </div>
              <div v-if="!selected?.rawProps" class="mini muted">אין properties זמינים</div>
            </div>
          </div>

          <!-- ===== LOGIC ===== -->
          <div v-if="infoTab === 'logic'" class="logicBox">
            <div class="lg">
              <div class="lgTitle">מקור הסטטוס הנוכחי</div>
              <div class="lgText">
                <span v-if="useQgisStatus">
                  מסומן “להשתמש ב־status מהקובץ” → הסטטוס נלקח מהשדה <span class="mono">status</span>.
                </span>
                <span v-else>
                  הסטטוס מחושב מהשדות <span class="mono">Vel_mean</span>, <span class="mono">coer_mean</span>, <span class="mono">Vel_count</span>.
                </span>
              </div>
            </div>

            <div class="lg">
              <div class="lgTitle">הספים (כמו בפאנל)</div>
              <div class="lgText mono">
                rateThreshold = {{ rateThreshold }}<br/>
                minCoh = {{ minCoh }}<br/>
                minPts = {{ minPts }}<br/>
                flipSign = {{ flipSign ? "true" : "false" }}
              </div>
            </div>

            <div class="lg" v-if="!useQgisStatus">
              <div class="lgTitle">כלל חישוב</div>
              <div class="lgText mono">
                אם Vel_count &lt; minPts → no_data<br/>
                אחרת אם coer_mean &lt; minCoh → low_quality<br/>
                אחרת אם Vel_mean ≤ rateThreshold → suspected_subsidence<br/>
                אחרת → stable
              </div>
            </div>

            <div class="lg">
              <div class="lgTitle">מה נחשב “אמין” יותר?</div>
              <div class="lgText">
                בדרך כלל: <b>Vel_count גבוה</b> + <b>coer_mean גבוה</b> → תוצאה יציבה יותר.
                אם אחד מהם נמוך — קח את הסיווג בזהירות.
              </div>
            </div>
          </div>
        </div>

        <div class="modalFooter">
          <button class="btn ghost" @click="fitToSelected" :disabled="!selected?.boundsValid">התמקד בבניין</button>
          <button class="btn" @click="closeInfo">סגור</button>
        </div>
      </div>
    </div>
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

// Modal
const infoOpen = ref(false);
const infoTab = ref("main");

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

function stringifyVal(v) {
  if (v == null) return "null";
  if (typeof v === "object") {
    try { return JSON.stringify(v); } catch { return String(v); }
  }
  return String(v);
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
  throw new Error("Load failed (no valid URL)");
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

function clearSelection() {
  selected.value = null;
  infoOpen.value = false;
}

function pickName(props, idx) {
  const f = pickField(props, ["name","NAME","building_id","id","OBJECTID","objectid","UNIQ_ID","uniq_id"]);
  if (f) return String(props[f]);
  return `בניין ${idx + 1}`;
}

/** Normalize "status" text */
function normalizeStatusText(raw) {
  const s = String(raw ?? "").trim().toLowerCase();
  if (!s) return "no_data";
  if (s.includes("suspected") || s.includes("sink")) return "suspected_subsidence";
  if (s.includes("stable") || s.includes("uplift")) return "stable";
  if (s.includes("low_quality") || s.includes("low quality") || s.includes("low")) return "low_quality";
  if (s.includes("no_data") || s.includes("nodata") || s === "null") return "no_data";
  return s;
}
function bucketFromStatus(norm) {
  if (norm === "suspected_subsidence" || norm === "sinking") return "sinking";
  if (norm === "stable") return "stable";
  if (norm === "low_quality") return "lowq";
  return "nodata";
}
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
  if (bucket === "nodata") {
    return { color: "#64748b", weight: 2.0, opacity: 0.85, fill: true, fillColor: "#cbd5e1", fillOpacity: 0.18, dashArray: "6 6" };
  }
  if (bucket === "lowq") {
    return { color: "#b45309", weight: 2.0, opacity: 0.9, fill: true, fillColor: "#f59e0b", fillOpacity: 0.20, dashArray: "5 4" };
  }
  if (bucket === "stable") {
    const fo = colorMode.value === "coh" ? opacityFromCoh(cohMeanVal, 0.15, 0.35) : 0.25;
    return { color: "#1d4ed8", weight: 2.0, opacity: 0.9, fill: true, fillColor: "#60a5fa", fillOpacity: fo };
  }

  // sinking
  let fillOpacity = 0.45;
  if (colorMode.value === "rate" && vAdj != null) {
    const thr = rateThreshold.value ?? -2;
    const ratio = thr === 0 ? 1 : Math.abs(vAdj / thr);
    const s = clamp01((ratio - 1) / 2);
    fillOpacity = 0.28 + s * 0.55;
  } else if (colorMode.value === "coh") {
    fillOpacity = opacityFromCoh(cohMeanVal, 0.25, 0.55);
  }
  return { color: "#b91c1c", weight: 2.4, opacity: 0.95, fill: true, fillColor: "#ef4444", fillOpacity };
}

function clamp01(x) { return Math.max(0, Math.min(1, x)); }
function opacityFromCoh(coh, min=0.2, max=0.7) {
  if (coh == null) return min;
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

function openInfo() {
  if (!selected.value) return;
  infoOpen.value = true;
  infoTab.value = "main";
}
function closeInfo() { infoOpen.value = false; }

function fitToSelected() {
  try {
    if (selected.value?.bounds && selected.value.bounds.isValid()) {
      map.fitBounds(selected.value.bounds.pad(0.15));
    }
  } catch {}
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
      const objectIdField = pickField(props, ["OBJECTID","objectid","ObjectID","id","ID"]);

      const velMean = velMeanField ? toNum(props[velMeanField]) : null;
      const velCount = velCountField ? toNum(props[velCountField]) : null;
      const cohMean = cohMeanField ? toNum(props[cohMeanField]) : null;
      const objectId = objectIdField ? props[objectIdField] : null;

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
            const b = (() => { try { return layer.getBounds(); } catch { return null; } })();
            selected.value = {
              name,
              status: normStatus || "—",
              bucket,
              velMean: fmt2(vAdj),
              cohMean: fmt2(cohMean),
              velCount: velCount ?? "—",
              objectId: objectId,
              rawProps: props,
              bounds: b,
              boundsValid: !!b?.isValid?.()
            };
            openInfo(); // פותח חלון נתונים אוטומטית בלחיצה
          });
        },
      });

      try {
        const b2 = layer.getBounds();
        if (b2?.isValid?.()) allBounds = allBounds ? allBounds.extend(b2) : b2;
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
        objectId: objectId
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

function reload() { loadAndRender(); }

// ===== suspects list =====
const suspectsList = computed(() => {
  const needle = (q.value || "").trim().toLowerCase();

  return rows.value
    .filter(r => r.bucket === "sinking")
    .filter(r => (r.cohMean ?? 0) >= (listMinCoh.value ?? 0))
    .filter(r => !needle || String(r.name).toLowerCase().includes(needle) || String(r.objectId ?? "").includes(needle))
    .sort((a,b) => (a.velAdj ?? Infinity) - (b.velAdj ?? Infinity))
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

function zoomToRow(r) {
  try {
    if (r?.bounds?.isValid?.()) map.fitBounds(r.bounds.pad(0.15));
  } catch {}

  selected.value = {
    name: r.name,
    status: r.status || "—",
    bucket: r.bucket,
    velMean: fmt2(r.velAdj),
    cohMean: fmt2(r.cohMean),
    velCount: r.velCount ?? "—",
    objectId: r.objectId,
    rawProps: null,
    bounds: r.bounds || null,
    boundsValid: !!r.bounds?.isValid?.()
  };
  openInfo();
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

.iconBtn { width:36px; height:36px; border-radius:10px; border:1px solid #e5e7eb; background:#fff; cursor:pointer; font-weight:900; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 54vh; border-left:none; border-bottom:1px solid #e5e7eb; }
  #map { height: 46vh; }
}

/* ===== Modal ===== */
.modalBack {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal {
  width: min(920px, 96vw);
  max-height: 92vh;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modalHeader {
  padding: 12px 12px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.mhTitle { font-weight: 900; font-size: 15px; }
.mhSub { font-size: 12px; opacity: 0.75; margin-top: 2px; }
.modalBody {
  padding: 12px;
  overflow: auto;
}
.modalFooter {
  padding: 12px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.tabs { display:flex; gap:8px; align-items:center; margin-bottom: 10px; flex-wrap: wrap; }
.tab { cursor:pointer; border:1px solid #e5e7eb; background:#fff; padding:8px 10px; border-radius: 999px; font-weight: 900; font-size: 12px; }
.tab.on { border-color:#111827; }

.grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
.infoCard { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#f9fafb; }
.infoCard .k { font-size:12px; opacity:0.7; }
.infoCard .v { font-weight:900; font-size:14px; margin-top:4px; }
.infoCard .desc { margin-top:8px; font-size:12px; line-height:1.5; opacity: 0.92; }
@media (max-width: 820px) {
  .grid2 { grid-template-columns: 1fr; }
}

.kvTable { border:1px solid #e5e7eb; border-radius:14px; overflow:hidden; }
.kvRow { display:grid; grid-template-columns: 240px 1fr; gap:10px; padding:10px; border-top:1px solid #e5e7eb; }
.kvRow:first-child { border-top:none; }
.kvKey { font-weight:900; font-size:12px; opacity:0.9; }
.kvVal { font-size:12px; opacity:0.9; word-break: break-word; }

.logicBox { display:grid; gap:10px; }
.lg { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; }
.lgTitle { font-weight:900; margin-bottom:6px; }
.lgText { font-size:12px; opacity:0.92; line-height: 1.55; }
</style>

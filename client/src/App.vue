<template>
  <div class="layout" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div>
          <div class="appTitle">SatMap</div>
          <div class="appSub">Prototype – בדיקת בניינים לשקיעה</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ on: mode === 'subsidence' }" @click="mode = 'subsidence'">בניינים שוקעים</button>
        <button class="tab" :class="{ on: mode === 'search' }" @click="mode = 'search'">תצפיות לוויין (רשימה)</button>
        <button class="tab" :class="{ on: mode === 'about' }" @click="mode = 'about'">איך זה עובד</button>
      </div>

      <!-- ================= SUBSIDENCE ================= -->
      <section v-if="mode === 'subsidence'" class="section">
        <div class="banner warn">
          <div class="bannerTitle">מה עושה “בניינים שוקעים”?</div>
          <div class="bannerText">
            1) מציירים <b>מלבן</b> על המפה (זה האזור לבדיקה)<br />
            2) המערכת מושכת בניינים מ־OSM (Overpass)<br />
            3) לכל בניין היא דוגמת שקיעה (מ־API או מקובץ מקומי)<br />
            4) מסמנת “שוקע” אם mm/yr ≤ הסף שלך<br /><br />
            <b>שימו לב:</b> אמינות תלויה באיכות/צפיפות הנתונים שלך. אם יש מעט נקודות — זה יהיה “גס”.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">1</div>
          <div class="stepBody">
            <div class="stepTitle">מקור נתוני שקיעה</div>
            <div class="stepText">
              לבדיקות הכי פשוט לעבוד עם <b>קובץ GeoJSON מקומי</b> (בלי Cloudflare). אם רוצים — אפשר גם API חיצוני,
              אבל לפעמים דומיינים כמו <span class="mono">workers.dev</span> חסומים במחשבים/רשתות מסוימות.
            </div>

            <div class="row">
              <label>שיטת דגימה</label>
              <select v-model="subsEngine">
                <option value="local">קובץ GeoJSON מקומי</option>
                <option value="api">API חיצוני (Cloudflare Worker)</option>
              </select>
            </div>

            <div v-if="subsEngine === 'local'">
              <div class="row">
                <label>קישור לקובץ נקודות (GeoJSON)</label>
                <input v-model="localDataUrl" placeholder="/SatMap/data/subsidence_points.geojson" />
                <div class="mini muted" style="margin-top:6px;">
                  הפורמט: <span class="mono">FeatureCollection</span> של נקודות עם <span class="mono">properties.mmPerYear</span>.
                </div>
              </div>

              <div class="row grid2">
                <button class="btnGhost" @click="loadLocalPoints(true)" :disabled="localLoading">
                  {{ localLoading ? "טוען…" : "טען נתונים" }}
                </button>
                <div class="kpi" :class="{ bad: !subsReady, good: subsReady }">
                  {{ subsReady ? ("נטענו " + localPointsCount + " נקודות") : "לא נטען / בעיה" }}
                </div>
              </div>

              <div class="mini" v-if="localErr">{{ localErr }}</div>
            </div>

            <div v-else>
              <div class="row">
                <label>כתובת ה־API (Cloudflare Worker)</label>
                <input v-model="subsApiBase" placeholder="https://xxxxx.workers.dev" />
                <div class="mini muted" style="margin-top:6px;">
                  האתר קורא: <span class="mono">/health</span> ואז <span class="mono">/subsidence?lat=..&lng=..&radius=..</span>
                </div>
              </div>

              <div class="row grid2">
                <button class="btnGhost" @click="testApi" :disabled="apiTesting">
                  {{ apiTesting ? "בודק…" : "בדיקת חיבור" }}
                </button>
                <div class="kpi" :class="{ bad: !apiOk, good: apiOk }">
                  {{ apiOk ? "API מחובר" : "לא בדוק / בעיה" }}
                </div>
              </div>

              <div class="mini" v-if="apiTestMsg">{{ apiTestMsg }}</div>
            </div>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">2</div>
          <div class="stepBody">
            <div class="stepTitle">הגדרות בדיקה</div>

            <div class="row grid2">
              <div>
                <label>סף “שוקע” (mm/yr)</label>
                <input type="number" v-model.number="subsThreshold" step="1" />
              </div>
              <div>
                <label>רדיוס התאמה לנקודה (מ׳)</label>
                <input type="number" v-model.number="subsRadiusM" step="100" min="100" />
              </div>
            </div>

            <div class="row grid2">
              <div>
                <label>מקסימום בניינים לבדיקה</label>
                <input type="number" v-model.number="subsMaxBuildings" step="50" min="50" />
              </div>
              <div>
                <label>סינון “אמינות”</label>
                <select v-model="subsConfidenceMode">
                  <option value="near">רק אם נקודה קרובה (מומלץ)</option>
                  <option value="any">כל תוצאה (גם אם רחוק)</option>
                </select>
              </div>
            </div>

            <div class="row grid2">
              <button class="btnPrimary" @click="scanSubsidenceInRect" :disabled="subsBusy || !subsDataReady">
                {{ subsBusy ? "סורק…" : "סרוק את המלבן" }}
              </button>
              <button class="btnGhost" @click="stopSubsidenceScan" :disabled="!subsBusy">עצור</button>
            </div>

            <div class="row grid2">
              <button class="btnGhost" @click="clearSubsidenceResults">נקה תוצאות</button>
              <button class="btnGhost" @click="clearSubsidenceAll">נקה הכל</button>
            </div>

            <div class="progressBox" v-if="subsProgress.stage">
              <div class="mini"><b>{{ subsProgress.stage }}</b></div>
              <div class="progressBar">
                <div class="progressFill" :style="{ width: subsProgressPercent + '%' }"></div>
              </div>
              <div class="mini muted">{{ subsProgress.done }} / {{ subsProgress.total }}</div>
            </div>

            <div class="mini muted" v-if="subsStats.totalChecked">
              נסרקו: <b>{{ subsStats.totalChecked }}</b> |
              שוקעים: <b>{{ subsStats.sinking }}</b> |
              יציב/עולה: <b>{{ subsStats.stable }}</b> |
              אין נתון: <b>{{ subsStats.noData }}</b> |
              נפסלו (רחוק): <b>{{ subsStats.tooFar }}</b>
            </div>

            <div class="legend">
              <div class="legendRow"><span class="sw sw-sink"></span> שוקע</div>
              <div class="legendRow"><span class="sw sw-stable"></span> יציב/עולה</div>
              <div class="legendRow"><span class="sw sw-nodata"></span> אין נתון</div>
            </div>

            <div class="row grid2">
              <label class="chk">
                <input type="checkbox" v-model="showStableOnMap" @change="applyBuildingsVisibility" />
                להראות יציב/עולה
              </label>
              <label class="chk">
                <input type="checkbox" v-model="showNoDataOnMap" @change="applyBuildingsVisibility" />
                להראות אין נתון
              </label>
            </div>

            <div class="mini muted" style="margin-top:8px;">
              <b>איך להשתמש:</b> צייר <b>מלבן</b> על המפה → בדיקת חיבור → “סרוק את המלבן”.<br />
              (במצב הזה אין פוליגונים, רק מלבן.)
            </div>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">3</div>
          <div class="stepBody">
            <div class="stepTitle">השוואה עם תצלומי עבר (Wayback)</div>
            <div class="stepText">
              להשוואה ויזואלית בלבד (מה השתנה בשטח), לא מדידת שקיעה. מפעיל שכבת “עבר” מעל לוויין Esri ומשחק עם שקיפות.
            </div>

            <label class="chk" style="margin-top:6px;">
              <input type="checkbox" v-model="compareEnabled" />
              להפעיל תצלום עבר
            </label>

            <div v-if="compareEnabled" style="margin-top:10px;">
              <div class="row grid2">
                <div>
                  <label>תאריך עבר</label>
                  <select v-model="waybackSelected">
                    <option v-for="w in waybackItems" :key="w.releaseNum" :value="String(w.releaseNum)">
                      {{ w.releaseDateLabel || w.itemTitle }}
                    </option>
                  </select>
                </div>
                <div>
                  <label>שקיפות ({{ waybackOpacityPct }}%)</label>
                  <input type="range" min="0" max="100" v-model.number="waybackOpacityPct" />
                </div>
              </div>

              <div class="mini muted" v-if="waybackLoading">טוען רשימת תצלומי עבר…</div>
              <div class="mini" v-if="waybackErr">{{ waybackErr }}</div>
            </div>
          
        <div class="step">
          <div class="stepNum">4</div>
          <div class="stepBody">
            <div class="stepTitle">תמונת לוויין לאזור שנבחר</div>
            <div class="stepText">
              לחץ על <b>בניין</b> / <b>המלבן</b> / <b>נקודה</b> במפה – ונציג כאן תמונה מהירה וקישורים לצפייה.
            </div>

            <div class="mini" v-if="satSelLabel"><b>{{ satSelLabel }}</b></div>
            <div class="mini muted" v-if="!satImgUrl">עדיין אין בחירה. לחץ על משהו במפה כדי לראות תצוגה.</div>

            <div v-if="satImgUrl" class="thumbWrap">
              <img class="thumb" :src="satImgUrl" @error="satImgError = true" />
              <div class="mini muted" v-if="satImgError" style="margin-top:6px;">
                לא הצלחתי לטעון תמונה (לפעמים שירות התמונות חסום/מגביל). השתמש בקישורים למטה.
              </div>
            </div>

            <div class="row linkGrid" style="margin-top:10px;" v-if="satLinks.length">
              <button class="btnGhost" v-for="l in satLinks" :key="l.label" @click="openLink(l.url)">{{ l.label }}</button>
            </div>

            <div class="mini muted" style="margin-top:8px;">
              טיפ: אם הפעלת “תצלום עבר” (Wayback) – אפשר גם להחליף תאריך ולשחק עם שקיפות להשוואה.
            </div>
          </div>
        </div>

</div>
        </div>

        <div class="step" v-if="subsResults.length">
          <div class="stepNum">5</div>
          <div class="stepBody">
            <div class="stepTitle">תוצאות</div>

            <div class="row grid2">
              <div>
                <label>הצג</label>
                <select v-model="subsListFilter">
                  <option value="sinking">רק שוקעים</option>
                  <option value="all">הכל</option>
                  <option value="stable">רק יציב/עולה</option>
                  <option value="nodata">רק אין נתון</option>
                </select>
              </div>
              <div>
                <label>מיון</label>
                <select v-model="subsSort">
                  <option value="rateAsc">קצב (שוקע ביותר למעלה)</option>
                  <option value="distAsc">מרחק (הכי קרוב למעלה)</option>
                </select>
              </div>
            </div>

            <div class="list">
              <button class="card" v-for="(b, i) in subsShown" :key="i" @click="focusSubsBuilding(b)">
                <div class="mono line">
                  <span class="ell">{{ b.name }}</span>
                  <span class="pill" :class="pillClass(b.status)">{{ pillText(b.status) }}</span>
                </div>
                <div class="mini line">
                  <span v-if="b.mmPerYear != null">קצב: <b>{{ b.mmPerYear.toFixed(2) }}</b> mm/yr</span>
                  <span v-else>קצב: <b>—</b></span>
                  <span class="muted">מרחק: {{ fmtMeters(b.nearestMeters) }}</span>
                </div>
              </button>
            </div>

            <div class="mini muted" style="margin-top:10px;">
              טיפ: אפשר גם ללחוץ על המפה כדי לקבל “דגימה לנקודה” (לא קשור לבניין).
            </div>
          </div>
        </div>

        <div class="mini muted" v-if="lastClick" style="margin-top:10px;">
          לחיצה אחרונה: {{ lastClick.lat.toFixed(6) }}, {{ lastClick.lng.toFixed(6) }}
          | דגימה: <b v-if="subsMmPerYear != null">{{ subsMmPerYear.toFixed(2) }}</b><span v-else>—</span> mm/yr
        </div>
      </section>

      <!-- ================= SEARCH ================= -->
      <section v-if="mode === 'search'" class="section">
        <div class="banner info">
          <div class="bannerTitle">תצפיות לוויין = רשימה בלבד</div>
          <div class="bannerText">
            כאן המפה שולחת ל־ASF את <b>המלבן + טווח תאריכים</b> ומקבלת <b>רשימת סצנות Sentinel‑1</b> (מטא־דאטה, לא תמונות).<br />
            כדי לא לבלבל, <b>לא מציירים Footprints</b> על המפה (אין פוליגונים).
          </div>
        </div>

        <div class="step">
          <div class="stepNum">1</div>
          <div class="stepBody">
            <div class="stepTitle">בחר מלבן במפה</div>
            <div class="stepText">צייר מלבן על המפה (בכל מצב יש רק מלבן).</div>

            <div class="row grid2">
              <button class="btnGhost" @click="resetIsraelAOI">Reset לישראל</button>
              <button class="btnGhost" @click="clearAOI">נקה מלבן</button>
            </div>

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
              <div class="row actions" style="margin:0;">
                <button class="btnGhost" @click="downloadGeoJSON" :disabled="!features.length">הורד GeoJSON</button>
                <button class="btnGhost" @click="downloadCSV" :disabled="!features.length">הורד CSV</button>
              </div>
            </div>

            <div class="mini">תוצאות: <b>{{ filtered.length }}</b> (מציג {{ shown.length }}).</div>

            <div class="list">
              <div class="card" v-for="r in shown" :key="r.key">
                <div class="mono line">
                  <span class="ell">{{ r.gid }}</span>
                  <span class="pill" v-if="r.flightDirection">{{ r.flightDirection }}</span>
                </div>
                <div class="mini line">
                  <span>{{ formatTime(r.time) }}</span>
                  <span class="muted" v-if="r.relativeOrbit"> | מסלול: {{ r.relativeOrbit }}</span>
                  <span class="muted" v-if="r.polarization"> | פולריזציה: {{ r.polarization }}</span>
                  <span class="muted" v-if="r.beamMode"> | Beam: {{ r.beamMode }}</span>
                </div>
              </div>
            </div>

            <div class="mini muted" style="margin-top:10px;">
              הערה: זה לא מחשב שקיעה. זה רק עוזר להבין אם יש כיסוי Sentinel-1 לאזור.
            </div>
          </div>
        </div>
      </section>

      <!-- ================= ABOUT ================= -->
      <section v-if="mode === 'about'" class="section">
        <div class="banner info">
          <div class="bannerTitle">למה זה עדיין Prototype?</div>
          <div class="bannerText">
            כי התוצאה תלויה במקור הנתונים שלך ל־mm/yr. אם המקור דליל או “nearest point” רחוק — זה לא אמין.
            כדי להפוך את זה למוצר אמיתי צריך שכבת InSAR צפופה + איכות/סטיית תקן + דגימת ראסטר/tiles.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">A</div>
          <div class="stepBody">
            <div class="stepTitle">מה עובד היום</div>
            <ul class="bul">
              <li>בחירת אזור במפה (מלבן פשוט)</li>
              <li>שליפת בניינים מ־OSM</li>
              <li>דגימה דרך ה־Worker שלך + סיווג “שוקע/יציב/אין נתון”</li>
              <li>הצגה על מפה ורשימה ברורה</li>
            </ul>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">B</div>
          <div class="stepBody">
            <div class="stepTitle">מה חסר כדי שזה יהיה “שמיש באמת”</div>
            <ul class="bul">
              <li>שכבת שקיעה אמיתית וצפופה (Velocity mm/yr) לכל המדינה</li>
              <li>איכות (quality/STD/coherence) כדי להחליט אם התוצאה אמינה</li>
              <li>API שמדגם ראסטר/tiles ולא “nearest point” בלבד</li>
              <li>אופטימיזציה: caching, חיתוך אריחים, והפחתת בקשות</li>
            </ul>
          </div>
        </div>
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
  /** ====== Wayback compare (Historical imagery) ====== */
const compareEnabled = ref(false);
const waybackItems = ref([]); // [{releaseNum, releaseDateLabel, itemURL, itemTitle}]
const waybackSelected = ref(""); // releaseNum as string
const waybackOpacity = ref(0.55);
const waybackLoading = ref(false);
const waybackErr = ref("");

const waybackOpacityPct = computed({
  get: () => Math.round(waybackOpacity.value * 100),
  set: (v) => (waybackOpacity.value = Math.max(0, Math.min(1, Number(v) / 100))),
});

let esriLayer = null;
let waybackLayer = null;
  let osmLayer = null;


const WAYBACK_CONFIG_URL = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json";

import { computed, onMounted, ref, watch } from "vue";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";

/** Leaflet marker icons fix */
import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker1x from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: marker2x,
  iconUrl: marker1x,
  shadowUrl: markerShadow,
});

/** Leaflet.draw readableArea patch */
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

/** UI */
const panelOpen = ref(true);
const mode = ref("subsidence"); // subsidence | search | about
const status = ref("צייר מלבן על המפה ואז התחל.");
const busy = ref(false);

/** Search (list only) */
const start = ref(daysAgoISO(60));
const end = ref(todayISO());
const flightDirection = ref("");
const q = ref("");
const limit = ref(50);
const features = ref([]);

/** Subsidence settings */
const subsEngine = ref("local"); // local | api
const localDataUrl = ref(`${import.meta.env.BASE_URL}data/subsidence_points.geojson`);
const localPoints = ref([]); // [{lat,lng,mmPerYear}]
const localLoading = ref(false);
const localErr = ref("");
const localOk = computed(() => Array.isArray(localPoints.value) && localPoints.value.length > 0);
const localCount = computed(() => (Array.isArray(localPoints.value) ? localPoints.value.length : 0));
const localPointsCount = localCount;

const subsApiBase = ref("https://lucky-mouse-9360.shagolan28.workers.dev");
const subsRadiusM = ref(1200);
const subsThreshold = ref(-5);
const subsMaxBuildings = ref(250);
const subsConfidenceMode = ref("near"); // near | any

/** Subsidence runtime */
const apiOk = ref(false);
const apiTesting = ref(false);
const apiTestMsg = ref("");

const subsDataReady = computed(() => (subsEngine.value === "local" ? localOk.value : apiOk.value));


const subsBusy = ref(false);
const lastClick = ref(null);
const subsMmPerYear = ref(null);

const subsProgress = ref({ stage: "", done: 0, total: 0 });
const subsProgressPercent = computed(() => {
  const t = subsProgress.value.total || 0;
  if (!t) return 0;
  return Math.max(0, Math.min(100, Math.round((subsProgress.value.done / t) * 100)));
});

const subsStats = ref({ totalChecked: 0, sinking: 0, stable: 0, noData: 0, tooFar: 0 });

/** Results list */
const subsResults = ref([]);
const subsListFilter = ref("sinking"); // sinking | all | stable | nodata
const subsSort = ref("rateAsc"); // rateAsc | distAsc

const subsShown = computed(() => {
  let arr = subsResults.value.slice();
  if (subsListFilter.value !== "all") {
    arr = arr.filter((x) => x.status === subsListFilter.value);
  }
  if (subsSort.value === "distAsc") {
    arr.sort((a, b) => (a.nearestMeters ?? 9e15) - (b.nearestMeters ?? 9e15));
  } else {
    // rateAsc: sinking more negative first, then nulls last
    arr.sort((a, b) => {
      const ra = a.mmPerYear ?? 9e15;
      const rb = b.mmPerYear ?? 9e15;
      return ra - rb;
    });
  }
  return arr;
});

/** Map state */
let map = null;
let drawControl = null;

let aoiGroup = null;
let aoiRect = null;

let subsAoiGroup = null;
let subsRect = null;

let buildingsSinkingGroup = null;
let buildingsStableGroup = null;
let buildingsNoDataGroup = null;

const showStableOnMap = ref(false);
const showNoDataOnMap = ref(false);

let clickMarker = null;

/** -------- Satellite preview (thumbnail + external links) -------- */
const satSelLabel = ref("");
const satBounds = ref(null); // L.LatLngBounds
const satImgError = ref(false);

const SAT_EXPORT_BASE =
  "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export";

function boundsToBbox4326(b) {
  if (!b) return null;
  const west = b.getWest?.();
  const south = b.getSouth?.();
  const east = b.getEast?.();
  const north = b.getNorth?.();
  if (![west, south, east, north].every((x) => Number.isFinite(x))) return null;
  return { west, south, east, north };
}

const satImgUrl = computed(() => {
  const bb = boundsToBbox4326(satBounds.value);
  if (!bb) return "";
  // Keep bbox small to avoid huge images
  const size = "760,460";
  const qs = new URLSearchParams({
    bbox: `${bb.west},${bb.south},${bb.east},${bb.north}`,
    bboxSR: "4326",
    imageSR: "4326",
    size,
    format: "png",
    f: "image",
  });
  return `${SAT_EXPORT_BASE}?${qs.toString()}`;
});

const satLinks = computed(() => {
  const bb = boundsToBbox4326(satBounds.value);
  if (!bb) return [];
  const lat = (bb.south + bb.north) / 2;
  const lng = (bb.west + bb.east) / 2;
  const z = Math.round(map?.getZoom?.() ?? 17);

  const googleSat = `https://www.google.com/maps/@${lat},${lng},${z}z/data=!3m1!1e3`;
  const osm = `https://www.openstreetmap.org/#map=${z}/${lat}/${lng}`;
  // EO Browser (no key). Dataset defaults to Sentinel-2 L2A.
  const eo = `https://apps.sentinel-hub.com/eo-browser/?zoom=${z}&lat=${lat}&lng=${lng}&datasetId=S2L2A`;

  return [
    { label: "Google (לוויין)", url: googleSat },
    { label: "EO Browser", url: eo },
    { label: "OpenStreetMap", url: osm },
  ];
});

function setSatFromBounds(b, label) {
  satBounds.value = b || null;
  satSelLabel.value = label || "";
  satImgError.value = false;
}

function openLink(url) {
  try {
    window.open(url, "_blank", "noopener,noreferrer");
  } catch {}
}

/** Abort controller */
let subsAbort = null;

/** ------------ Date utils ------------ */
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
function fmtMeters(m) {
  const n = Number(m);
  if (!Number.isFinite(n)) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(2)} ק״מ`;
  return `${Math.round(n)} מ׳`;
}

/** ------------ Pills ------------ */
function pillText(s) {
  if (s === "sinking") return "שוקע";
  if (s === "stable") return "יציב";
  return "אין נתון";
}
function pillClass(s) {
  if (s === "sinking") return "danger";
  if (s === "stable") return "ok";
  return "mutedPill";
}



/** ------------ Local subsidence points (NO server) ------------ */
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
// Haversine meters
function distM(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (x) => (x * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

async function loadLocalPoints(force = false) {
  if (!force && localOk.value) return;
  localLoading.value = true;
  localErr.value = "";
  try {
    const url = String(localDataUrl.value || "").trim();
    if (!url) throw new Error("חסר נתיב לקובץ GeoJSON");

    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error("GeoJSON load failed: " + r.status);
    const gj = await r.json();

    const feats = Array.isArray(gj?.features) ? gj.features : [];
    const pts = [];

    for (const f of feats) {
      if (f?.geometry?.type !== "Point") continue;
      const c = f?.geometry?.coordinates;
      if (!Array.isArray(c) || c.length < 2) continue;
      const lng = Number(c[0]);
      const lat = Number(c[1]);
      const mm = toNum(f?.properties?.mmPerYear);
      if (!Number.isFinite(lat) || !Number.isFinite(lng) || mm == null) continue;
      pts.push({ lat, lng, mmPerYear: mm });
    }

    localPoints.value = pts;
    if (!pts.length) throw new Error("לא נמצאו נקודות בקובץ (בדוק mmPerYear / geometry)");
  } catch (e) {
    localPoints.value = [];
    localErr.value = String(e);
  } finally {
    localLoading.value = false;
  }
}

function sampleFromLocal(lat, lng) {
  const radius = Number(subsRadiusM.value) || 0;
  const pts = Array.isArray(localPoints.value) ? localPoints.value : [];
  if (!pts.length) throw new Error("אין נתונים טעונים. לחץ 'טען נתונים'.");

  let best = null;
  let bestD = Infinity;
  for (const p of pts) {
    const d = distM(lat, lng, p.lat, p.lng);
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }

  if (!best || bestD > radius) {
    return { mmPerYear: null, nearestMeters: bestD };
  }
  return { mmPerYear: best.mmPerYear, nearestMeters: bestD };
}
/** ------------ API test ------------ */
async function testApi() {
  apiTesting.value = true;
  apiTestMsg.value = "";
  try {
    if (subsEngine.value === "local") {
      await loadLocalPoints(true);
      if (!localPoints.value.length) {
        apiOk.value = false;
        apiTestMsg.value = localErr.value || "לא נטענו נקודות";
        return;
      }
      // quick sanity sample (ירושלים)
      const sample = await fetchSubsidenceSample(31.778, 35.235);
      apiOk.value = true;
      apiTestMsg.value = `נטענו ${localPoints.value.length} נקודות | דגימה: ${sample.mmPerYear ?? "-"} mm/yr | nearest ${Math.round(sample.nearestMeters)}m`;
      status.value = "נתוני שקיעה זמינים. עכשיו צייר מלבן ולחץ 'סרוק את המלבן'.";
      return;
    }

    if (!subsApiBase.value) {
      apiOk.value = false;
      apiTestMsg.value = "הכנס כתובת API";
      return;
    }

    const base = subsApiBase.value.replace(/\/$/, "");
    const health = await fetch(`${base}/health`, { cache: "no-store" });
    if (!health.ok) throw new Error("/health failed: " + health.status);

    // sample point (ירושלים)
    const t = await fetch(`${base}/subsidence?lat=31.778&lng=35.235&radius=${subsRadiusM.value}`, {
      cache: "no-store",
    });
    if (!t.ok) throw new Error("/subsidence failed: " + t.status);
    const j = await t.json();

    apiOk.value = true;
    apiTestMsg.value = "OK: " + JSON.stringify(j);
    status.value = "API מחובר. עכשיו צייר מלבן ולחץ 'סרוק את המלבן'.";
  } catch (e) {
    apiOk.value = false;
    apiTestMsg.value = "שגיאה: " + String(e);
  } finally {
    apiTesting.value = false;
  }
}

/** ------------ Subsidence API call ------------ */
async function fetchSubsidenceSample(lat, lng) {
  // Local GeoJSON mode (no external API)
  if (subsEngine.value === "local") {
    if (!localPoints.value.length) {
      try {
        await loadLocalPoints(false);
      } catch {
        // ignore; localErr already set
      }
    }

    const pts = localPoints.value;
    if (!Array.isArray(pts) || !pts.length) {
      return { mmPerYear: null, nearestMeters: Infinity, usedRadiusMeters: subsRadiusM.value, source: "local-geojson" };
    }

    let best = null;
    let bestD = Infinity;
    for (const p of pts) {
      const d = distM(lat, lng, p.lat, p.lng);
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    }

    return {
      mmPerYear: best ? best.mmPerYear : null,
      nearestMeters: bestD,
      usedRadiusMeters: subsRadiusM.value,
      source: "local-geojson",
      point: best ? { lat: best.lat, lng: best.lng } : null,
    };
  }

  // API mode
  const base = subsApiBase.value.replace(/\/$/, "");
  const u = `${base}/subsidence?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}&radius=${encodeURIComponent(subsRadiusM.value)}`;
  const res = await fetch(u, { cache: "no-store" });
  if (!res.ok) throw new Error("API failed: " + res.status);
  return await res.json();
}

/** ------------ Overpass buildings ------------ */
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

/** ------------ Clear / stop ------------ */
function clearSubsidenceResults() {
  subsResults.value = [];
  subsStats.value = { totalChecked: 0, sinking: 0, stable: 0, noData: 0, tooFar: 0 };
  subsProgress.value = { stage: "", done: 0, total: 0 };
  buildingsSinkingGroup?.clearLayers?.();
  buildingsStableGroup?.clearLayers?.();
  buildingsNoDataGroup?.clearLayers?.();
}
function clearSubsidenceAll() {
  stopSubsidenceScan();
  clearSubsidenceResults();
  subsAoiGroup?.clearLayers?.();
  subsRect = null;

  if (clickMarker) {
    clickMarker.remove();
    clickMarker = null;
  }
  lastClick.value = null;
  subsMmPerYear.value = null;
  setSatFromBounds(null, "");
}
function stopSubsidenceScan() {
  try {
    subsAbort?.abort?.();
  } catch {}
  subsBusy.value = false;
  subsProgress.value = { stage: "", done: 0, total: 0 };
}

/** ------------ Draw control (RECTANGLE ONLY) ------------ */
function rebuildDrawControl() {
  const aoiStyle = { color: "#111827", weight: 2, opacity: 0.9, fillOpacity: 0.06 };
const subsStyle = { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.06 };

  if (!map) return;

  patchLeafletDrawReadableArea();

  if (drawControl) {
    try {
      map.removeControl(drawControl);
    } catch {}
    drawControl = null;
  }

  const isSubs = mode.value === "subsidence";
  const style = isSubs ? { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.06 } : { color: "#111827", weight: 2, opacity: 0.9, fillOpacity: 0.06 };

drawControl = new L.Control.Draw({
  draw: {
    rectangle: { shapeOptions: isSubs ? subsStyle : aoiStyle },
    polygon: false,
    polyline: false,
    circle: false,
    marker: false,
    circlemarker: false,
  },
  edit: { featureGroup: isSubs ? subsAoiGroup : aoiGroup },
});


  map.addControl(drawControl);
}
  async function loadWaybackConfigOnce() {
  if (waybackItems.value.length) return;

  waybackLoading.value = true;
  waybackErr.value = "";
  try {
    const r = await fetch(WAYBACK_CONFIG_URL);
    if (!r.ok) throw new Error("Wayback config failed: " + r.status);
    const cfg = await r.json();

    const arr = Object.values(cfg || {})
      .map((x) => ({
        releaseNum: x.releaseNum,
        releaseDateLabel: x.releaseDateLabel,
        itemURL: x.itemURL,
        itemTitle: x.itemTitle,
      }))
      .filter((x) => x.releaseNum && x.itemURL);

    // newest first
    arr.sort((a, b) => (b.releaseNum || 0) - (a.releaseNum || 0));

    waybackItems.value = arr;

    if (!waybackSelected.value && arr[0]) waybackSelected.value = String(arr[0].releaseNum);
  } catch (e) {
    waybackErr.value = "לא הצלחתי לטעון רשימת תצלומי עבר. " + String(e);
  } finally {
    waybackLoading.value = false;
  }
}

const WaybackTileLayer = L.TileLayer.extend({
  initialize(item, options) {
    this._item = item;
    L.TileLayer.prototype.initialize.call(this, "", options);
  },
  getTileUrl(coords) {
  const z = coords.z, x = coords.x, y = coords.y;
  return this._item.itemURL
    .replace("{releaseNum}", String(this._item.releaseNum))
    .replace("{level}", String(z))
    .replace("{row}", String(y))
    .replace("{col}", String(x));
}
,
});

function removeWaybackLayer() {
  if (waybackLayer && map) {
    try {
      map.removeLayer(waybackLayer);
    } catch {}
  }
  waybackLayer = null;
}

function applyWaybackLayer() {
  if (!map) return;
  removeWaybackLayer();

  if (!compareEnabled.value) return;

  const rel = Number(waybackSelected.value);
  const item = waybackItems.value.find((x) => Number(x.releaseNum) === rel);
  if (!item) return;

  // מומלץ להשוואה: לעבוד על שכבת הלוויין הרגילה ואז להלביש “עבר” מעליה
  if (esriLayer && !map.hasLayer(esriLayer)) esriLayer.addTo(map);

  waybackLayer = new WaybackTileLayer(item, {
    opacity: waybackOpacity.value,
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "Historical imagery: Esri Wayback",
  });

  waybackLayer.addTo(map);
}


/** ------------ initMap ------------ */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, zoomSnap: 0.25 }).setView([31.78, 35.22], 11);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

 esriLayer = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxNativeZoom: 19, maxZoom: 22, attribution: "Tiles © Esri" }
);


  L.control.layers({ "מפה (OSM)": osm, "לוויין (Esri)": esriLayer }, {}, { position: "topleft" }).addTo(map);

  aoiGroup = new L.FeatureGroup().addTo(map);
  subsAoiGroup = new L.FeatureGroup().addTo(map);

  buildingsSinkingGroup = new L.FeatureGroup().addTo(map);
  buildingsStableGroup = new L.FeatureGroup().addTo(map);
  buildingsNoDataGroup = new L.FeatureGroup().addTo(map);

  resetIsraelAOI();
  rebuildDrawControl();
  applyBuildingsVisibility();

  map.on(L.Draw.Event.CREATED, (e) => {
    if (mode.value === "subsidence") {
      subsAoiGroup.clearLayers();
      subsRect = e.layer;
      subsAoiGroup.addLayer(subsRect);
      status.value = "מלבן נבחר. עכשיו לחץ “סרוק את המלבן”.";
      setSatFromBounds(subsRect.getBounds(), "מלבן בדיקה");
    } else {
      aoiGroup.clearLayers();
      aoiRect = e.layer;
      aoiGroup.addLayer(aoiRect);
      status.value = "מלבן נבחר. לחץ “חפש סצנות”.";
      setSatFromBounds(aoiRect.getBounds(), "מלבן חיפוש");
    }
  });
  map.on(L.Draw.Event.EDITED, () => {
  status.value = "המלבן עודכן.";
});

map.on(L.Draw.Event.DELETED, () => {
  if (mode.value === "subsidence") {
    subsRect = null;
    subsAoiGroup?.clearLayers?.();
    status.value = "מלבן בדיקה נמחק.";
    setSatFromBounds(null, "");
  } else {
    aoiRect = null;
    aoiGroup?.clearLayers?.();
    status.value = "מלבן חיפוש נמחק.";
    setSatFromBounds(null, "");
  }
});


  map.on("click", async (e) => {
    if (mode.value !== "subsidence") return;

    const { lat, lng } = e.latlng;
    lastClick.value = { lat, lng };

    if (clickMarker) clickMarker.remove();
    clickMarker = L.marker([lat, lng]).addTo(map);

    // Satellite preview around the clicked point (~350m box)
    try {
      const d = 0.0032;
      const b = L.latLngBounds([lat - d, lng - d], [lat + d, lng + d]);
      setSatFromBounds(b, `נקודה (${lat.toFixed(5)}, ${lng.toFixed(5)})`);
    } catch {}

    try {
      const s = await fetchSubsidenceSample(lat, lng);
      subsMmPerYear.value = s.mmPerYear;
      status.value =
        s.mmPerYear == null
          ? `אין נתון קרוב לנקודה (nearest=${fmtMeters(s.nearestMeters)})`
          : `דגימה לנקודה: ${s.mmPerYear.toFixed(2)} mm/yr | nearest=${fmtMeters(s.nearestMeters)}`;
    } catch (err) {
      subsMmPerYear.value = null;
      status.value = `שגיאה בדגימה: ${String(err)}`;
    }
  });
}

/** ------------ AOI helpers ------------ */
function resetIsraelAOI() {
  aoiGroup?.clearLayers?.();
  subsAoiGroup?.clearLayers?.();

  const rect = L.rectangle([
    [29.45, 34.2],
    [33.4, 35.95],
  ]);

  if (mode.value === "subsidence") {
    subsRect = rect;
    subsAoiGroup.addLayer(rect);
  } else {
    aoiRect = rect;
    aoiGroup.addLayer(rect);
  }

  map?.fitBounds?.(rect.getBounds(), { padding: [20, 20], maxZoom: 11 });
  setSatFromBounds(rect.getBounds(), mode.value === "subsidence" ? "מלבן בדיקה (ברירת מחדל)" : "מלבן חיפוש (ברירת מחדל)");
}
function clearAOI() {
  aoiGroup?.clearLayers?.();
  aoiRect = null;
  setSatFromBounds(null, "");
}

/** ------------ ASF search (NO MAP POLYGONS) ------------ */
function layerToWktRect(layer) {
  const b = layer.getBounds();
  // POLYGON((lng lat, ...))
  const pts = [
    [b.getWest(), b.getSouth()],
    [b.getEast(), b.getSouth()],
    [b.getEast(), b.getNorth()],
    [b.getWest(), b.getNorth()],
    [b.getWest(), b.getSouth()],
  ];
  const body = pts.map(([x, y]) => `${x} ${y}`).join(",");
  return `POLYGON((${body}))`;
}

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
        polarization: p.polarization || p.polarizations || "",
        platform: p.platform || p.sensor || p.mission || "",
        beamMode: p.beamModeType || p.beamMode || "",
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

async function doSearch() {
  try {
    busy.value = true;
    features.value = [];
    status.value = "מחפש…";

    const layer = aoiGroup?.getLayers?.()?.[0];
    if (!layer) throw new Error("אין מלבן. צייר מלבן על המפה.");

    const wkt = layerToWktRect(layer);

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

    status.value = feats.length ? `נמצאו ${feats.length} סצנות. מציג ${Math.min(feats.length, limit.value)} ברשימה.` : "אין תוצאות.";
  } catch (e) {
    status.value = `שגיאה: ${String(e)}`;
  } finally {
    busy.value = false;
  }
}

/** ------------ Subsidence scan ------------ */
function approxBboxAreaKm2(b) {
  const meanLat = (b.getNorth() + b.getSouth()) / 2;
  const kmPerDegLat = 111.32;
  const kmPerDegLng = 111.32 * Math.cos((meanLat * Math.PI) / 180);
  const w = Math.abs(b.getEast() - b.getWest()) * kmPerDegLng;
  const h = Math.abs(b.getNorth() - b.getSouth()) * kmPerDegLat;
  return w * h;
}

function applyBuildingsVisibility() {
  if (!map) return;
  // sinking always visible
  if (!map.hasLayer(buildingsSinkingGroup)) buildingsSinkingGroup.addTo(map);

  if (showStableOnMap.value) {
    if (!map.hasLayer(buildingsStableGroup)) buildingsStableGroup.addTo(map);
  } else {
    if (map.hasLayer(buildingsStableGroup)) map.removeLayer(buildingsStableGroup);
  }

  if (showNoDataOnMap.value) {
    if (!map.hasLayer(buildingsNoDataGroup)) buildingsNoDataGroup.addTo(map);
  } else {
    if (map.hasLayer(buildingsNoDataGroup)) map.removeLayer(buildingsNoDataGroup);
  }
}

async function scanSubsidenceInRect() {
  // קח מלבן מה-state או מה-group
  const rect = subsRect || (subsAoiGroup?.getLayers?.()?.[0] ?? null);
  if (!rect) {
    status.value = "אין מלבן. במצב 'בניינים שוקעים' צייר מלבן על המפה ואז נסה שוב.";
    return;
  }
  subsRect = rect;

  if (!subsDataReady.value) {
    status.value = "אין נתונים לדגימה. טען קובץ (מקומי) או בדוק API ואז סרוק.";
    return;
  }

  try {
    subsAbort?.abort?.();
    subsAbort = new AbortController();

    subsBusy.value = true;
    clearSubsidenceResults();
    applyBuildingsVisibility();

    subsProgress.value = { stage: "טוען בניינים (OSM)…", done: 0, total: 1 };
    status.value = "טוען בניינים (OSM)…";

    const b = rect.getBounds();   // ✅ לא subsRect / לא subsAoi
    const area = approxBboxAreaKm2(b);
    if (area > 25) throw new Error("המלבן גדול מדי. תצמצם כדי לא להפיל את Overpass.");

    const bbox = { south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() };
    const osm = await fetchBuildingsOSM(bbox);
    const gj = overpassToGeoJSON(osm);

    const all = gj.features || [];
    const list = all.slice(0, Math.max(50, Number(subsMaxBuildings.value) || 250));

    subsProgress.value = { stage: "בודק שקיעה לכל בניין…", done: 0, total: list.length };
    status.value = `נמצאו ${all.length} בניינים. בודק עד ${list.length}…`;

    let noData = 0, tooFar = 0, sinking = 0, stable = 0;
    const results = [];

    for (let i = 0; i < list.length; i++) {
      if (subsAbort.signal.aborted) throw new Error("בוטל");

      const f = list[i];
      const cc = featureCentroidLatLng(f);
      if (!cc) { subsProgress.value.done = i + 1; continue; }

      const s = await fetchSubsidenceSample(cc.lat, cc.lng);

      let statusKey = "nodata";
      if (s.mmPerYear == null) {
        noData++;
      } else {
        if (subsConfidenceMode.value === "near") {
          if (s.nearestMeters == null || s.nearestMeters > subsRadiusM.value) {
            tooFar++;
            subsProgress.value.done = i + 1;
            continue;
          }
        }
        if (s.mmPerYear <= subsThreshold.value) { statusKey = "sinking"; sinking++; }
        else { statusKey = "stable"; stable++; }
      }

      const name = buildingLabel(f.properties || {});
      results.push({
        name,
        status: statusKey,
        mmPerYear: s.mmPerYear,
        nearestMeters: s.nearestMeters,
        lat: cc.lat,
        lng: cc.lng,
        feature: f,
      });

      subsProgress.value.done = i + 1;
      if ((i + 1) % 25 === 0) status.value = `בודק… ${i + 1}/${list.length}`;
    }

    // ציור שכבות (כמו אצלך) – נשאר אותו רעיון
    for (const r of results) {
      const style =
        r.status === "sinking"
          ? { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.18 }
          : r.status === "stable"
          ? { color: "#334155", weight: 1, opacity: 0.7, fillOpacity: 0.04 }
          : { color: "#64748b", weight: 1, opacity: 0.55, dashArray: "4 4", fillOpacity: 0.02 };

      const layer = L.geoJSON(r.feature, { style });

      layer.on("click", () => {
        setSatFromBounds(layer.getBounds(), r.name);
        try { map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 19 }); } catch {}
        layer.bindPopup(`
          <div style="font-family:system-ui;font-size:12px;line-height:1.45;">
            <div style="font-weight:800;margin-bottom:6px;">${r.name}</div>
            <div><b>סטטוס:</b> ${pillText(r.status)}</div>
            <div><b>קצב:</b> ${r.mmPerYear == null ? "—" : r.mmPerYear.toFixed(2) + " mm/yr"}</div>
            <div><b>מרחק:</b> ${fmtMeters(r.nearestMeters)}</div>
          </div>
        `).openPopup();
      });

      r._layer = layer;
      if (r.status === "sinking") layer.addTo(buildingsSinkingGroup);
      else if (r.status === "stable") layer.addTo(buildingsStableGroup);
      else layer.addTo(buildingsNoDataGroup);
    }

    subsResults.value = results;
    subsStats.value = { totalChecked: results.length, sinking, stable, noData, tooFar };
    subsProgress.value = { stage: "", done: 0, total: 0 };

    status.value = `סיום: שוקעים=${sinking} | יציב=${stable} | אין נתון=${noData} | נפסלו(רחוק)=${tooFar}`;

    applyBuildingsVisibility();
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
}

/** ------------ Downloads ------------ */
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

/** ------------ UI helpers ------------ */
function maybeClosePanelOnMobile() {
  if (window.matchMedia("(max-width: 900px)").matches) panelOpen.value = false;
}

/** ------------ mode switch ------------ */
  watch(compareEnabled, async (v) => {
  if (!v) {
    removeWaybackLayer();
    return;
  }
  await loadWaybackConfigOnce();
  applyWaybackLayer();
});

watch(waybackSelected, () => {
  if (compareEnabled.value) applyWaybackLayer();
});

watch(waybackOpacity, () => {
  if (waybackLayer) {
    try {
      waybackLayer.setOpacity(waybackOpacity.value);
    } catch {}
  }
});

watch(mode, (m) => {
  rebuildDrawControl();

  if (m === "subsidence") {
    status.value = "בניינים שוקעים: צייר מלבן → טען נתונים/בדוק API → סרוק.";
    if (subsEngine.value === "local" && !localOk.value) {
      loadLocalPoints(false).catch(() => {});
    }
  } else if (m === "search") {
    status.value = "תצפיות לוויין: צייר מלבן → חפש → קבל רשימה (בלי פוליגונים).";
  } else {
    status.value = "הסבר: מה יש היום ומה צריך כדי שזה יהיה מוצר אמיתי.";
  }
});

/** ------------ mount ------------ */
onMounted(async () => {
  initMap();
  try {
    if (subsEngine.value === "local") await loadLocalPoints(false);
  } catch {}
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

/* satellite preview */
.linkGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.thumbWrap {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
}
.thumb {
  width: 100%;
  display: block;
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
.pill.ok {
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.pill.mutedPill {
  border-color: #e5e7eb;
  background: #f8fafc;
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

.kpi {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
  font-weight: 900;
  text-align: center;
}
.kpi.good {
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.kpi.bad {
  border-color: #fecaca;
  background: #fef2f2;
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

/* legend */
.legend {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px;
  background: #fff;
  display: grid;
  gap: 6px;
}
.legendRow {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  opacity: 0.85;
}
.sw {
  width: 18px;
  height: 10px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}
.sw-sink {
  background: #fef2f2;
  border-color: #b91c1c;
}
.sw-stable {
  background: #f8fafc;
  border-color: #334155;
}
.sw-nodata {
  background: #f8fafc;
  border-color: #64748b;
}

/* bullets */
.bul {
  margin: 0;
  padding-inline-start: 18px;
}
.bul li {
  margin: 6px 0;
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

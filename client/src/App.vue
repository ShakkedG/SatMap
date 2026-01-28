<template>
  <div class="layout" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div>
          <div class="appTitle">SatMap</div>
          <div class="appSub">חיפוש Sentinel-1 + בדיקת בניינים לשקיעה (Prototype)</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>
      </div>

      <div class="tabs">
        <button class="tab" :class="{ on: mode === 'search' }" @click="mode = 'search'">חיפוש סצנות</button>
        <button class="tab" :class="{ on: mode === 'subsidence' }" @click="mode = 'subsidence'">בניינים שוקעים</button>
        <button class="tab" :class="{ on: mode === 'about' }" @click="mode = 'about'">איך זה עובד</button>
      </div>

      <!-- ================= SEARCH ================= -->
      <section v-if="mode === 'search'" class="section">
        <div class="banner info">
          <div class="bannerTitle">מה עושה מצב “חיפוש סצנות”?</div>
          <div class="bannerText">
            זה מצב שמחזיר <b>רשימת סצנות Sentinel-1</b> מה-ASF לפי אזור ותאריכים.
            <br />
            <b>זה לא מחשב שקיעה.</b> הוא רק עוזר להבין איזה תצפיות קיימות לאזור.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">1</div>
          <div class="stepBody">
            <div class="stepTitle">בחר אזור (AOI)</div>
            <div class="stepText">
              צייר מלבן/פוליגון על המפה. או הזן נקודת GovMap ולחץ “המר לנקודה”.
            </div>

            <div class="row grid2">
              <button class="btnGhost" @click="resetIsraelAOI">Reset לישראל</button>
              <button class="btnGhost" @click="clearAOI">נקה AOI</button>
            </div>

            <div class="row grid2">
              <div>
                <label>GovMap X</label>
                <input v-model="govX" placeholder="220000 או lon" />
              </div>
              <div>
                <label>GovMap Y</label>
                <input v-model="govY" placeholder="630000 או lat" />
              </div>
            </div>

            <div class="row grid2">
              <button class="btnGhost" @click="useGovmapPoint">המר לנקודה (WGS84)</button>
              <button class="btnGhost" @click="clearGovmapPoint">נקה נקודה</button>
            </div>

            <div class="mini" v-if="govPoint">
              נקודה: {{ govPoint.lat.toFixed(6) }}, {{ govPoint.lng.toFixed(6) }} (מקור {{ govPoint.crs }})
            </div>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">2</div>
          <div class="stepBody">
            <div class="stepTitle">בחר תאריכים וסינון</div>

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
              <div class="toggleLine">
                <label class="chk">
                  <input type="checkbox" v-model="showFootprints" @change="applyFootprintsVisibility" />
                  להציג Footprints
                </label>
              </div>
            </div>

            <div class="row actions">
              <button class="btnGhost" @click="downloadGeoJSON" :disabled="!features.length">הורד GeoJSON</button>
              <button class="btnGhost" @click="downloadCSV" :disabled="!features.length">הורד CSV</button>
            </div>

            <div class="mini">
              תוצאות: <b>{{ filtered.length }}</b> (מציג {{ shown.length }}).
            </div>

            <div class="list">
              <button
                class="card"
                v-for="r in shown"
                :key="r.key"
                :class="{ active: r.key === selectedKey }"
                @click="focusResult(r.key)"
                title="Zoom + הדגשה במפה"
              >
                <div class="mono line">
                  <span class="ell">{{ r.gid }}</span>
                  <span class="pill" v-if="r.flightDirection">{{ r.flightDirection }}</span>
                </div>
                <div class="mini line">
                  <span>{{ formatTime(r.time) }}</span>
                  <span class="muted" v-if="r.relativeOrbit"> | מסלול: {{ r.relativeOrbit }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= SUBSIDENCE ================= -->
      <section v-if="mode === 'subsidence'" class="section">
        <div class="banner warn">
          <div class="bannerTitle">מה עושה מצב “בניינים שוקעים”?</div>
          <div class="bannerText">
            המערכת עושה 3 שלבים:
            <br />
            <b>1)</b> מושכת פוליגונים של בניינים מ-OpenStreetMap (Overpass)
            <br />
            <b>2)</b> דוגמת “קצב שקיעה” לכל בניין דרך ה-API שלך (Cloudflare Worker)
            <br />
            <b>3)</b> מסמנת “שוקע” אם הקצב ≤ הסף שלך
            <br /><br />
            <b>חשוב:</b> זו עדיין <u>הערכה גסה</u> — במיוחד אם הנתונים שלך דלילים / לא InSAR אמיתי.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">1</div>
          <div class="stepBody">
            <div class="stepTitle">חיבור ל-API</div>

            <div class="row">
              <label>כתובת ה-API (Worker)</label>
              <input v-model="subsApiBase" />
              <div class="mini muted" style="margin-top:6px;">
                האתר קורא: <span class="mono">/subsidence?lat=..&lng=..&radius=..</span>
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

        <div class="step">
          <div class="stepNum">2</div>
          <div class="stepBody">
            <div class="stepTitle">הגדרות סריקה</div>

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
                <label>מינימום “אמינות”</label>
                <select v-model="subsConfidenceMode">
                  <option value="any">כל תוצאה (כולל רחוק)</option>
                  <option value="near">רק אם נקודה קרובה</option>
                </select>
              </div>
            </div>

            <div class="row grid2">
              <button class="btnGhost" @click="scanSubsidenceInRect" :disabled="subsBusy">
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
              אין נתון: <b>{{ subsStats.noData }}</b> |
              נפסלו (רחוק מדי): <b>{{ subsStats.tooFar }}</b>
            </div>

            <div class="mini muted" style="margin-top:8px;">
              <b>איך להשתמש:</b> צייר מלבן על המפה (במצב הזה אפשר לצייר רק מלבן).
              אחרי ציור, אפשר ללחוץ “סרוק את המלבן”.
            </div>
          </div>
        </div>

        <div class="step" v-if="subsBuildings.length">
          <div class="stepNum">3</div>
          <div class="stepBody">
            <div class="stepTitle">תוצאות</div>
            <div class="stepText">
              לחיצה על בניין תעשה Zoom ותפתח חלונית עם הסבר:
              קצב, מרחק לנקודת הנתונים הקרובה, והאם זה עבר את הסף.
            </div>

            <div class="list">
              <button class="card" v-for="(b, i) in subsBuildings" :key="i" @click="focusSubsBuilding(b)">
                <div class="mono line">
                  <span class="ell">{{ b.name }}</span>
                  <span class="pill danger">שוקע</span>
                </div>
                <div class="mini line">
                  <span>קצב: <b>{{ b.rate.toFixed(2) }}</b> mm/yr</span>
                  <span class="muted">מרחק: {{ fmtMeters(b.nearestMeters) }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div class="mini muted" v-if="lastClick" style="margin-top:10px;">
          לחיצה אחרונה: {{ lastClick.lat.toFixed(6) }}, {{ lastClick.lng.toFixed(6) }}
          | דגימה: <b v-if="subsMmPerYear != null">{{ subsMmPerYear.toFixed(2) }}</b><span v-else>—</span> mm/yr
          | תוצאה: <b>{{ subsResultText }}</b>
        </div>
      </section>

      <!-- ================= ABOUT ================= -->
      <section v-if="mode === 'about'" class="section">
        <div class="banner info">
          <div class="bannerTitle">למה כרגע זה עדיין לא “אתר שמיש” לשקיעה?</div>
          <div class="bannerText">
            כרגע המנגנון יודע “לצבוע בניינים” רק אם יש לך <b>מקור נתונים טוב</b> לשקיעה.
            אם הקובץ שלך מכיל מעט נקודות, או שהערך מגיע מנקודה רחוקה — זה לא אמין.
          </div>
        </div>

        <div class="step">
          <div class="stepNum">A</div>
          <div class="stepBody">
            <div class="stepTitle">מה עובד היום (כן)</div>
            <ul class="bul">
              <li>מושך בניינים מ-OSM (Overpass) בתוך מלבן שציירת</li>
              <li>קורא ל-API שלך ומקבל <span class="mono">mmPerYear</span> + <span class="mono">nearestMeters</span></li>
              <li>מציג “שוקע” אם עבר את הסף ומציג מרחק כדי להבין אמינות</li>
            </ul>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">B</div>
          <div class="stepBody">
            <div class="stepTitle">מה חסר כדי שזה יהיה אמיתי (לא)</div>
            <ul class="bul">
              <li><b>שכבת שקיעה אמיתית</b> (InSAR Velocity / mm/yr) שמכסה את ישראל בצורה צפופה</li>
              <li>API שמדגם <b>רשת/ראסטר</b> (לא “הנקודה הקרובה” בלבד) — רצוי לפי פיקסל/Tile</li>
              <li>מטא-דאטה: טווח שנים, שיטת עיבוד, סטיית תקן/איכות (quality)</li>
              <li>סינון רעשים: פסילת תוצאות כשאיכות נמוכה / קוהרנטיות נמוכה</li>
            </ul>
          </div>
        </div>

        <div class="step">
          <div class="stepNum">C</div>
          <div class="stepBody">
            <div class="stepTitle">איך להפוך את זה לאתר שמיש באמת</div>
            <div class="stepText" style="margin-bottom:8px;">
              הדרך הכי פרקטית: להחליף את קובץ הנקודות שלך לנתונים אמיתיים צפופים, ולהפוך את ה-API לדוגם ראסטר.
            </div>

            <ol class="bul">
              <li>
                <b>הפק נתוני שקיעה אמיתיים</b>:
                <div class="mini muted">
                  למשל: עיבוד InSAR לסנטינל-1 (Velocity mm/yr) על אזורים בישראל.
                  התוצאה המומלצת: GeoTIFF/COG (ראסטר) או Grid צפוף של נקודות.
                </div>
              </li>
              <li>
                <b>ארח את השכבה</b>:
                <div class="mini muted">
                  אפשר על Cloudflare R2 / GitHub Releases / כל אחסון סטטי.
                </div>
              </li>
              <li>
                <b>API דוגם פיקסל</b>:
                <div class="mini muted">
                  במקום “nearest point”, ה-API יקבל lat/lng ויחזיר את ערך הפיקסל (ועוד איכות).
                </div>
              </li>
              <li>
                <b>באתר</b>:
                <div class="mini muted">
                  מוסיפים: “איכות”, “מקור”, “שנים”, וחיווי ברור אם התוצאה לא אמינה.
                </div>
              </li>
            </ol>

            <div class="banner warn" style="margin-top:12px;">
              <div class="bannerTitle">כרגע מה הכי מגביל?</div>
              <div class="bannerText">
                אם אין לך שכבת mm/yr אמיתית — האתר לא יכול “למצוא שקיעה” באמת.
                הוא רק כלי תצוגה/חיבור: בניינים + דגימה מהמקור שאתה מספק.
              </div>
            </div>
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
import { computed, onMounted, ref, watch } from "vue";
import { govmapXYToWgs84, bufferPointToWktRect } from "./utils/govmapCrs.js";

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
const mode = ref("search"); // search | subsidence | about
const status = ref("—");
const busy = ref(false);

/** Search */
const start = ref(daysAgoISO(60));
const end = ref(todayISO());
const flightDirection = ref("");
const q = ref("");
const limit = ref(50);
const showFootprints = ref(true);

const features = ref([]);
const selectedKey = ref("");

/** GovMap */
const govX = ref("");
const govY = ref("");
const govPoint = ref(null);
let govMarker = null;

/** Subsidence settings */
const subsApiBase = ref("https://lucky-mouse-9360.shagolan28.workers.dev");
const subsRadiusM = ref(1200);
const subsThreshold = ref(-5);
const subsMaxBuildings = ref(250);
const subsConfidenceMode = ref("near"); // any | near

/** Subsidence runtime */
const apiOk = ref(false);
const apiTesting = ref(false);
const apiTestMsg = ref("");

const subsBusy = ref(false);
const subsBuildings = ref([]);
const lastClick = ref(null);
const subsMmPerYear = ref(null);

const subsProgress = ref({ stage: "", done: 0, total: 0 });
const subsProgressPercent = computed(() => {
  const t = subsProgress.value.total || 0;
  if (!t) return 0;
  return Math.max(0, Math.min(100, Math.round((subsProgress.value.done / t) * 100)));
});

const subsStats = ref({ totalChecked: 0, sinking: 0, noData: 0, tooFar: 0 });

const subsResultText = computed(() => {
  if (subsMmPerYear.value == null) return "אין נתון";
  return subsMmPerYear.value <= subsThreshold.value ? "שוקע" : "יציב/עולה";
});

/** Leaflet state */
let map = null;
let drawControl = null;

let drawn = null;
let footprintsGroup = null;
let subsAoiGroup = null;
let buildingsGroup = null;

let subsAoi = null;
let subsMarker = null;

const footprintLayers = new Map();

/** Abort controller for long scan */
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

/** ------------ GovMap ------------ */
function useGovmapPoint() {
  try {
    const p = govmapXYToWgs84(govX.value, govY.value);
    govPoint.value = p;

    if (govMarker) {
      govMarker.remove();
      govMarker = null;
    }
    govMarker = L.marker([p.lat, p.lng]).addTo(map);

    map.setView([p.lat, p.lng], Math.max(map.getZoom(), 15));
    status.value = `המרה הצליחה: ${p.lat.toFixed(6)}, ${p.lng.toFixed(6)} (מקור ${p.crs})`;
  } catch (e) {
    status.value = `שגיאה בהמרת GovMap: ${String(e)}`;
  }
}
function clearGovmapPoint() {
  govPoint.value = null;
  govX.value = "";
  govY.value = "";
  if (govMarker) {
    govMarker.remove();
    govMarker = null;
  }
}

/** ------------ API test ------------ */
async function testApi() {
  apiTesting.value = true;
  apiTestMsg.value = "";
  try {
    const base = subsApiBase.value.replace(/\/+$/, "");
    // health check
    const h = await fetch(`${base}/health`);
    if (!h.ok) throw new Error("health failed: " + h.status);
    const t = (await h.text()).trim();

    // sample check
    const s = await fetch(`${base}/subsidence?lat=31.78&lng=35.22&radius=${encodeURIComponent(String(subsRadiusM.value))}`);
    if (!s.ok) throw new Error("subsidence failed: " + s.status);
    const j = await s.json();

    apiOk.value = true;
    apiTestMsg.value = `בריאות: "${t}" | דגימה: mmPerYear=${j?.mmPerYear} | nearestMeters=${j?.nearestMeters}`;
    status.value = "API מחובר ועובד.";
  } catch (e) {
    apiOk.value = false;
    apiTestMsg.value = String(e);
    status.value = `בעיה ב-API: ${String(e)}`;
  } finally {
    apiTesting.value = false;
  }
}

/** ------------ Subsidence API call ------------ */
async function fetchSubsidenceSample(lat, lng) {
  const base = subsApiBase.value.replace(/\/+$/, "");
  const url = `${base}/subsidence?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}&radius=${encodeURIComponent(
    String(subsRadiusM.value)
  )}`;

  const r = await fetch(url, { signal: subsAbort?.signal });
  if (!r.ok) throw new Error("Subsidence API failed: " + r.status);
  const j = await r.json();

  const mm = Number(j?.mmPerYear);
  const nearest = Number(j?.nearestMeters);

  return {
    mmPerYear: Number.isFinite(mm) ? mm : null,
    nearestMeters: Number.isFinite(nearest) ? nearest : null,
  };
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

/** ------------ Clear subsidence ------------ */
function clearSubsidenceResults() {
  subsBuildings.value = [];
  subsStats.value = { totalChecked: 0, sinking: 0, noData: 0, tooFar: 0 };
  subsProgress.value = { stage: "", done: 0, total: 0 };
  if (buildingsGroup) buildingsGroup.clearLayers();
}
function clearSubsidenceAll() {
  stopSubsidenceScan();
  clearSubsidenceResults();
  if (subsAoiGroup) subsAoiGroup.clearLayers();
  subsAoi = null;

  if (subsMarker) {
    subsMarker.remove();
    subsMarker = null;
  }
  lastClick.value = null;
  subsMmPerYear.value = null;
}
function stopSubsidenceScan() {
  try {
    subsAbort?.abort?.();
  } catch {}
}

/** ------------ Draw control ------------ */
function rebuildDrawControl() {
  if (!map) return;

  patchLeafletDrawReadableArea();

  if (drawControl) {
    try {
      map.removeControl(drawControl);
    } catch {}
    drawControl = null;
  }

  const isSubs = mode.value === "subsidence";
  const aoiStyle = { color: "#111827", weight: 2, opacity: 0.9, fillOpacity: 0.06 };
  const subsStyle = { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.06 };

  drawControl = new L.Control.Draw({
    draw: isSubs
      ? {
          rectangle: { shapeOptions: subsStyle },
          polygon: false,
          polyline: false,
          circle: false,
          marker: false,
          circlemarker: false,
        }
      : {
          rectangle: { shapeOptions: aoiStyle },
          polygon: { allowIntersection: false, showArea: true, shapeOptions: aoiStyle },
          polyline: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
    edit: { featureGroup: isSubs ? subsAoiGroup : drawn },
  });

  map.addControl(drawControl);
}

/** ------------ initMap ------------ */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, zoomSnap: 0.25 }).setView([31.78, 35.22], 11);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19,
    maxZoom: 22,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const esri = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxNativeZoom: 19, maxZoom: 22, attribution: "Tiles &copy; Esri" }
  );

  L.control.layers({ "מפה (OSM)": osm, "לוויין (Esri)": esri }, {}, { position: "topleft" }).addTo(map);

  drawn = new L.FeatureGroup().addTo(map);
  footprintsGroup = new L.FeatureGroup().addTo(map);
  subsAoiGroup = new L.FeatureGroup().addTo(map);
  buildingsGroup = new L.FeatureGroup().addTo(map);

  resetIsraelAOI();
  rebuildDrawControl();

  map.on(L.Draw.Event.CREATED, async (e) => {
    if (mode.value === "subsidence") {
      subsAoiGroup.clearLayers();
      subsAoi = e.layer;
      subsAoiGroup.addLayer(subsAoi);

      // לא מריצים אוטומטית — שיהיה ברור למשתמש שהוא לוחץ “סרוק”
      status.value = "מלבן נבחר. לחץ “סרוק את המלבן”.";
    } else {
      drawn.clearLayers();
      drawn.addLayer(e.layer);
      status.value = "AOI נבחר. לחץ “חפש סצנות”.";
    }
  });

  map.on("click", async (e) => {
    if (mode.value !== "subsidence") return;

    const { lat, lng } = e.latlng;
    lastClick.value = { lat, lng };

    if (subsMarker) subsMarker.remove();
    subsMarker = L.marker([lat, lng]).addTo(map);

    try {
      const s = await fetchSubsidenceSample(lat, lng);
      subsMmPerYear.value = s.mmPerYear;
      status.value =
        s.mmPerYear == null
          ? `אין נתון קרוב לנקודה (nearest=${fmtMeters(s.nearestMeters)})`
          : `דגימה: ${s.mmPerYear.toFixed(2)} mm/yr | nearest=${fmtMeters(s.nearestMeters)}`;
    } catch (err) {
      subsMmPerYear.value = null;
      status.value = `שגיאה בדגימה: ${String(err)}`;
    }
  });
}

/** ------------ AOI search ------------ */
function resetIsraelAOI() {
  if (!drawn) return;
  drawn.clearLayers();
  const rect = L.rectangle([
    [29.45, 34.2],
    [33.4, 35.95],
  ]);
  drawn.addLayer(rect);
  if (map) map.fitBounds(rect.getBounds(), { padding: [20, 20], maxZoom: 11 });
}
function clearAOI() {
  if (!drawn) return;
  drawn.clearLayers();
}

/** ------------ WKT for ASF ------------ */
function layerToWkt(layer) {
  const arr = layer.getLatLngs();
  const ring = Array.isArray(arr[0]) ? arr[0] : arr;
  const pts = ring.map((p) => [p.lng, p.lat]);

  if (pts.length) {
    const [x0, y0] = pts[0];
    const [xn, yn] = pts[pts.length - 1];
    if (x0 !== xn || y0 !== yn) pts.push([x0, y0]);
  }

  const body = pts.map(([x, y]) => `${x} ${y}`).join(",");
  return `POLYGON((${body}))`;
}

/** ------------ Normalize ASF results ------------ */
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

/** ------------ Footprints ------------ */
function clearFootprints() {
  if (!footprintsGroup) return;
  footprintsGroup.clearLayers();
  footprintLayers.clear();
  selectedKey.value = "";
}
function applyFootprintsVisibility() {
  if (!map || !footprintsGroup) return;
  if (showFootprints.value) {
    if (!map.hasLayer(footprintsGroup)) footprintsGroup.addTo(map);
  } else {
    if (map.hasLayer(footprintsGroup)) map.removeLayer(footprintsGroup);
  }
}
function addFootprintsToMap(geojsonFeatures) {
  clearFootprints();

  const gj = L.geoJSON(
    { type: "FeatureCollection", features: geojsonFeatures },
    {
      style: () => ({ weight: 1, opacity: 0.6, fillOpacity: 0.0 }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        const gid = extractGranuleId(feature);
        const time = p.startTime || p.start || "";
        const key = `${gid}__${time || ""}`;

        footprintLayers.set(key, layer);
        layer.on("click", () => {
          setSelected(key);
          const html = `
            <div style="font-family: system-ui; font-size: 12px;">
              <div style="font-weight:700; margin-bottom:6px;">${gid}</div>
              <div>${time ? formatTime(time) : ""}</div>
              <div>${p.flightDirection ? "כיוון: " + p.flightDirection : ""}${p.relativeOrbit ? " | מסלול: " + p.relativeOrbit : ""}</div>
            </div>`;
          layer.bindPopup(html).openPopup();
        });
      },
    }
  );

  gj.eachLayer((l) => footprintsGroup.addLayer(l));
  applyFootprintsVisibility();

  if (footprintsGroup.getLayers().length) {
    try {
      const b = footprintsGroup.getBounds();
      if (b.isValid()) map.fitBounds(b, { padding: [24, 24], maxZoom: 12 });
    } catch {}
  }
}
function setSelected(key) {
  if (selectedKey.value && footprintLayers.has(selectedKey.value)) {
    footprintLayers.get(selectedKey.value).setStyle({ weight: 1, opacity: 0.6, fillOpacity: 0.0 });
  }
  selectedKey.value = key;
  if (footprintLayers.has(key)) {
    footprintLayers.get(key).setStyle({ weight: 4, opacity: 0.95, fillOpacity: 0.0 });
  }
}
function focusResult(key) {
  setSelected(key);
  const layer = footprintLayers.get(key);
  if (layer) {
    try {
      map.fitBounds(layer.getBounds(), { padding: [24, 24], maxZoom: 14 });
    } catch {}
  }
}

/** ------------ ASF search ------------ */
async function doSearch() {
  try {
    busy.value = true;
    features.value = [];
    clearFootprints();
    status.value = "מחפש…";

    const layer = drawn?.getLayers?.()[0];

    let wkt = "";
    if (layer) {
      wkt = layerToWkt(layer);
    } else if (govPoint.value) {
      wkt = bufferPointToWktRect(govPoint.value.lat, govPoint.value.lng, 300);
    } else {
      throw new Error("אין AOI על המפה וגם לא הוזנה נקודת GovMap");
    }

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

    addFootprintsToMap(feats.slice(0, limit.value));
    showFootprints.value = true;
    applyFootprintsVisibility();

    status.value = feats.length
      ? `נמצאו ${feats.length} סצנות. מציג על המפה ${Math.min(feats.length, limit.value)}.`
      : "אין תוצאות.";
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

async function scanSubsidenceInRect() {
  if (!subsAoi) {
    status.value = "אין מלבן. במצב בניינים שוקעים צייר מלבן על המפה.";
    return;
  }

  try {
    subsAbort?.abort?.();
    subsAbort = new AbortController();

    subsBusy.value = true;
    clearSubsidenceResults();

    subsProgress.value = { stage: "טוען בניינים (OSM)…", done: 0, total: 1 };
    status.value = "טוען בניינים (OSM)…";

    subsAoiGroup.clearLayers();
    subsAoiGroup.addLayer(subsAoi);

    const b = subsAoi.getBounds();
    const area = approxBboxAreaKm2(b);
    if (area > 25) throw new Error("המלבן גדול מדי. תצמצם כדי לא להפיל את Overpass.");

    const bbox = { south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() };
    const osm = await fetchBuildingsOSM(bbox);
    const gj = overpassToGeoJSON(osm);

    const all = gj.features || [];
    const list = all.slice(0, Math.max(50, Number(subsMaxBuildings.value) || 250));

    subsProgress.value = { stage: "בודק שקיעה לכל בניין…", done: 0, total: list.length };
    status.value = `נמצאו ${all.length} בניינים. בודק עד ${list.length}…`;

    let noData = 0;
    let tooFar = 0;
    const sinking = [];

    for (let i = 0; i < list.length; i++) {
      if (subsAbort.signal.aborted) throw new Error("בוטל");
      const f = list[i];
      const cc = featureCentroidLatLng(f);
      if (!cc) {
        subsProgress.value.done = i + 1;
        continue;
      }

      const s = await fetchSubsidenceSample(cc.lat, cc.lng);

      // אין נתון (או API מחזיר mmPerYear=null)
      if (s.mmPerYear == null) {
        noData++;
        subsProgress.value.done = i + 1;
        continue;
      }

      // אם רוצים "אמינות": נדרוש נקודה קרובה (nearestMeters != null)
      if (subsConfidenceMode.value === "near") {
        if (s.nearestMeters == null || s.nearestMeters > subsRadiusM.value) {
          tooFar++;
          subsProgress.value.done = i + 1;
          continue;
        }
      }

      if (s.mmPerYear <= subsThreshold.value) {
        sinking.push({ feature: f, centroid: cc, rate: s.mmPerYear, nearestMeters: s.nearestMeters });
      }

      subsProgress.value.done = i + 1;
      if ((i + 1) % 25 === 0) status.value = `בודק… ${i + 1}/${list.length}`;
    }

    buildingsGroup.clearLayers();

    const results = [];
    for (const item of sinking) {
      const tags = item.feature.properties || {};
      const name = buildingLabel(tags);

      const layer = L.geoJSON(item.feature, {
        style: { color: "#b91c1c", weight: 2, opacity: 0.95, fillOpacity: 0.18 },
      });

      const expl = `
        <div style="font-family:system-ui;font-size:12px;line-height:1.45;">
          <div style="font-weight:800;margin-bottom:6px;">${name}</div>
          <div><b>קצב:</b> ${item.rate.toFixed(2)} mm/yr</div>
          <div><b>מרחק לנקודת נתון:</b> ${fmtMeters(item.nearestMeters)}</div>
          <div style="margin-top:8px;">
            <div style="font-weight:700;margin-bottom:4px;">איך זה חושב?</div>
            <div>1) הבניין הגיע מ-OSM (Overpass)</div>
            <div>2) דגמנו שקיעה במרכז הבניין מ-API (Cloudflare Worker)</div>
            <div>3) סף שלך: <b>${subsThreshold.value}</b> mm/yr</div>
            <div style="margin-top:6px;opacity:.85;">
              הערה: תוצאה אמינה רק אם יש שכבת InSAR צפופה ואיכות טובה.
            </div>
          </div>
        </div>
      `;

      layer.on("click", () => {
        try {
          map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 19 });
        } catch {}
        layer.bindPopup(expl).openPopup();
      });

      layer.addTo(buildingsGroup);

      results.push({
        name,
        rate: item.rate,
        nearestMeters: item.nearestMeters,
        lat: item.centroid.lat,
        lng: item.centroid.lng,
        _layer: layer,
      });
    }

    subsBuildings.value = results.sort((a, b) => a.rate - b.rate);

    subsStats.value = {
      totalChecked: list.length,
      sinking: subsBuildings.value.length,
      noData,
      tooFar,
    };

    subsProgress.value = { stage: "", done: 0, total: 0 };

    status.value =
      `תוצאות: שוקעים=${subsBuildings.value.length} | אין נתון=${noData} | נפסלו(רחוק)=${tooFar} | ` +
      `סף=${subsThreshold.value} | רדיוס=${subsRadiusM.value}m`;

    if (subsBuildings.value.length) {
      try {
        map.fitBounds(buildingsGroup.getBounds(), { padding: [20, 20], maxZoom: 18 });
      } catch {}
    }
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
watch(mode, (m) => {
  rebuildDrawControl();

  if (m === "subsidence") {
    showFootprints.value = false;
    applyFootprintsVisibility();
    clearFootprints();
    clearSubsidenceAll();
    status.value = "מצב בניינים שוקעים: צייר מלבן, בדוק API, ואז סרוק.";
  } else if (m === "search") {
    clearSubsidenceAll();
    showFootprints.value = true;
    applyFootprintsVisibility();
    status.value = "מצב חיפוש: צייר AOI וחפש סצנות.";
  } else {
    status.value = "הסבר: למה זה עדיין Prototype ואיך הופכים את זה לשמיש.";
  }
});

/** ------------ mount ------------ */
onMounted(() => {
  initMap();
  applyFootprintsVisibility();
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
.card.active {
  border-color: #111827;
  box-shadow: 0 0 0 2px rgba(17, 24, 39, 0.08);
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

/* misc */
.mini {
  font-size: 12px;
  opacity: 0.85;
  line-height: 1.35;
}
.muted {
  opacity: 0.7;
}
.toggleLine {
  display: flex;
  align-items: end;
  justify-content: end;
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

<template>
  <div class="appRoot" dir="rtl">
    <!-- Loading -->
    <div v-if="!mapReady" id="loading">
      <div class="spinner"></div>
      <div class="loadingText">טוען מפה…</div>
      <div class="loadingHint" v-if="!govmapToken">
        חסר טוקן: <span class="mono">VITE_GOVMAP_TOKEN</span>
      </div>
    </div>

    <!-- Map -->
    <div id="map" class="map"></div>

    <!-- Top Always-Open Search Bar -->
    <div id="top-searchbar" ref="searchBarRef">
      <button id="addrBtn" type="button" @click="onSearchBtnClick">חפש</button>

      <input
        id="addrInput"
        v-model.trim="addrQuery"
        type="text"
        placeholder="לדוגמה: דיזנגוף 50 תל אביב"
        autocomplete="off"
        @keydown.enter.prevent="onSearchBtnClick"
        @keydown.esc="closeAddrResults"
        @input="onAddrInput"
      />

      <div id="addrResults" v-show="addrOpen">
        <div
          v-for="(it, idx) in addrResults"
          :key="idx"
          class="addr-item"
          @click="pickAddrResult(it)"
        >
          <div class="addr-title">{{ it.__title }}</div>
          <div v-if="it.__sub" class="addr-sub">{{ it.__sub }}</div>
        </div>

        <div v-if="addrOpen && !addrResults.length" class="addr-item">
          לא נמצאו תוצאות
        </div>
      </div>
    </div>

    <!-- Panel -->
    <aside id="info-panel" :class="{ collapsed: panelCollapsed }">
      <div id="panel-header">
        <h1>🛰️ SatMap – בניינים</h1>
        <p>
          GOVMAP שכבה: <strong>{{ govmapLayerId }}</strong><br />
          סטטוס: <strong>{{ status }}</strong>
        </p>

        <div id="header-actions">
          <button class="hbtn secondary" @click="aboutOpen = true">ℹ️ אודות</button>
          <button id="panelToggleBtn" class="hbtn secondary" @click="togglePanel">
            {{ panelCollapsed ? "➕ הגדל" : "➖ הקטן" }}
          </button>
        </div>
      </div>

      <div id="tabs">
        <div class="tab" :class="{ active: activeTab === 'single' }" @click="activeTab = 'single'">
          בניין
        </div>
        <div class="tab" :class="{ active: activeTab === 'how' }" @click="activeTab = 'how'">
          איך זה עובד
        </div>
        <div class="tab" :class="{ active: activeTab === 'debug' }" @click="activeTab = 'debug'">
          טיפים
        </div>
      </div>

      <div id="controls">
        <div class="mode-grid">
          <button class="mode-btn full primary active">🏢 שכבת בניינים</button>

          <button class="mode-btn active" title="סף שקיעה (mm/yr)">
            v סף
          </button>
          <button class="mode-btn" title="סף קוהרנס">
            coh סף
          </button>
          <button class="mode-btn full" disabled title="אין פעולות ריפרש/התמקדות">
            פעולות (בוטל)
          </button>
        </div>

        <div class="row2">
          <div>
            <label>סף “שוקע/חשוד” v (mm/yr)</label>
            <input type="number" v-model.number="rateThreshold" step="0.5" />
            <div class="hint">
              משפיע רק אם בשכבה יש <span class="mono">vel_mean</span>
            </div>
          </div>

          <div>
            <label>סף קוהרנס (0–1)</label>
            <input type="number" v-model.number="cohThreshold" step="0.05" min="0" max="1" />
            <div class="hint">
              משפיע רק אם בשכבה יש <span class="mono">coh_mean</span>
            </div>
          </div>
        </div>
      </div>

      <div id="info-content">
        <!-- TAB: single -->
        <div class="tab-content" :class="{ active: activeTab === 'single' }">
          <div id="info-title">בניין נבחר</div>

          <div v-if="!selectedProps" class="message message-info">
            לחץ על בניין במפה כדי לשלוף מאפיינים מהשכבה ב־GOVMAP.
          </div>

          <div v-else class="card">
            <div class="kpiRow">
              <div class="kpi">
                <div class="kpi-value mono">{{ selectedObjectId ?? "—" }}</div>
                <div class="kpi-label">OBJECTID</div>
              </div>
              <div class="kpi">
                <div class="kpi-value">{{ derived.status }}</div>
                <div class="kpi-label">סטטוס שקיעה</div>
              </div>
              <div class="kpi">
                <div class="kpi-value mono">{{ fmt(derived.coh_mean) }}</div>
                <div class="kpi-label">coh_mean</div>
              </div>
            </div>

            <div class="kvList">
              <div class="kv">
                <div class="k">v_mean (mm/yr)</div>
                <div class="v mono">{{ fmt(derived.vel_mean) }}</div>
              </div>

              <div class="kv">
                <div class="k">מס’ נקודות (אם קיים)</div>
                <div class="v mono">{{ fmtInt(derived.n_pts) }}</div>
              </div>

              <details class="details">
                <summary>הצג את כל השדות</summary>
                <pre class="pre">{{ JSON.stringify(selectedProps, null, 2) }}</pre>
              </details>
            </div>
          </div>
        </div>

        <!-- TAB: how -->
        <div class="tab-content" :class="{ active: activeTab === 'how' }">
          <div id="info-title">איך זה עובד</div>

          <div class="message message-info">
            האתר מציג שכבת <strong>בניינים</strong> מ־GOVMAP.
            בלחיצה על בניין מתבצע <span class="mono">identify</span> ומוצגים השדות.
          </div>

          <div class="message message-warn">
            “שקיעה/חשוד” מחושב רק אם בשכבה קיימים שדות כמו
            <span class="mono">vel_mean</span> (מהירות, mm/yr) ו־<span class="mono">coh_mean</span> (קוהרנס).
          </div>

          <div class="message message-info">
            חיפוש כתובת למעלה עובד עם <span class="mono">govmap.geocode</span>
            ומבצע <span class="mono">zoomToXY</span> לתוצאה שנבחרה.
          </div>
        </div>

        <!-- TAB: debug -->
        <div class="tab-content" :class="{ active: activeTab === 'debug' }">
          <div id="info-title">טיפים מהירים</div>

          <ul class="tips">
            <li>
              אם מופיע “חסר טוקן” – הוסף Secret בשם
              <span class="mono">VITE_GOVMAP_TOKEN</span>.
            </li>
            <li>
              אם “לא נמצא בניין” – תתקרב עוד / ודא שהשכבה {{ govmapLayerId }} זמינה.
            </li>
            <li>
              החיפוש לא תלוי בנתוני הבניינים – הוא עובד גם לפני בחירת בניין.
            </li>
          </ul>
        </div>
      </div>
    </aside>

    <!-- About modal -->
    <div class="modal" v-if="aboutOpen" aria-hidden="false">
      <div class="modalOverlay" @click="aboutOpen = false"></div>
      <div class="modalCard" role="dialog">
        <div class="modalHeader">
          <div class="modalHeaderTitle">ℹ️ אודות</div>
          <button class="modalClose" @click="aboutOpen = false">×</button>
        </div>
        <div class="modalBody">
          <p style="margin-top:0; font-weight:900">
            SatMap – תצוגת בניינים מ־GOVMAP + שליפת מאפיינים בלחיצה.
          </p>
          <ul style="margin:0; padding-right:18px; font-weight:900; color:#333; line-height:1.6">
            <li>חיפוש כתובת: <span class="mono">govmap.geocode</span></li>
            <li>שליפת בניין: <span class="mono">identifyByXYAndLayer</span></li>
            <li>חישוב “שקיעה”: לפי שדות <span class="mono">vel_mean/coh_mean</span> אם קיימים</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

// ===== GOVMAP CONFIG =====
const govmapLayerId = "225287";
const govmapToken = (import.meta.env.VITE_GOVMAP_TOKEN || "").trim();

// ===== UI STATE =====
const status = ref("מאתחל…");
const mapReady = ref(false);

const panelCollapsed = ref(false);
const activeTab = ref("single");
const aboutOpen = ref(false);

// thresholds
const rateThreshold = ref(-2.0);
const cohThreshold = ref(0.35);

// building selection
const selectedProps = ref(null);

// address search
const addrQuery = ref("");
const addrResults = ref([]);
const addrOpen = ref(false);
let addrReqId = 0;
let debounceTimer = null;
const searchBarRef = ref(null);

// govmap unsub
let unsubClick = null;

// ===== HELPERS =====
function fmt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(3);
}
function fmtInt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return Math.round(n).toLocaleString();
}
function togglePanel() {
  panelCollapsed.value = !panelCollapsed.value;
}

function fieldsToObject(fields) {
  const out = {};
  for (const f of fields || []) {
    const key = f?.fieldName ?? f?.FieldName ?? f?.name ?? f?.field;
    const val = f?.value ?? f?.Value ?? f?.fieldValue;
    if (key !== undefined) out[key] = val;
  }
  return out;
}
function findObjectIdField(props) {
  if (!props) return null;
  const keys = Object.keys(props);
  const lower = new Map(keys.map((k) => [k.toLowerCase(), k]));
  if (lower.has("objectid")) return lower.get("objectid");
  if (lower.has("oid")) return lower.get("oid");
  return null;
}
const selectedObjectId = computed(() => {
  const p = selectedProps.value || null;
  if (!p) return null;
  const oidKey = findObjectIdField(p);
  return oidKey ? p[oidKey] : (p.OBJECTID ?? p.objectid ?? null);
});

// ===== DERIVED SUBSIDENCE (if fields exist) =====
const derived = computed(() => {
  const p = selectedProps.value || {};

  const vRaw =
    p.vel_mean ?? p.VEL_MEAN ?? p.VELmean ?? p.VelMean ?? p.velocity_mean;
  const cRaw =
    p.coh_mean ?? p.COH_MEAN ?? p.COHmean ?? p.CohMean ?? p.coherence_mean;

  const nRaw =
    p.n_pts ?? p.N_PTS ?? p.NPTS ?? p.num_pts ?? p.points_n ?? p.points;

  const v = Number(vRaw);
  const c = Number(cRaw);
  const n = Number(nRaw);

  const hasV = Number.isFinite(v);
  const hasC = Number.isFinite(c);
  const hasN = Number.isFinite(n);

  let s = "אין נתוני InSAR בשכבה";
  if (hasV || hasC) {
    const cohOk = hasC ? c >= cohThreshold.value : true;
    if (!cohOk) s = "קוהרנס נמוך (לא אמין)";
    else if (hasV && v <= rateThreshold.value) s = "שוקע/חשוד";
    else s = "נראה תקין";
  }

  return {
    vel_mean: hasV ? v : null,
    coh_mean: hasC ? c : null,
    n_pts: hasN ? n : null,
    status: s,
  };
});

// ===== GOVMAP LOAD =====
function ensureGovMapScriptLoaded() {
  if (window.govmap) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://www.govmap.gov.il/govmap/api/govmap.api.js";
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("לא הצלחתי לטעון את GOVMAP API"));
    document.head.appendChild(s);
  });
}

async function selectOnMapByObjectId(objectId, oidField) {
  if (!window.govmap || objectId == null || !oidField) return;

  const layer = govmapLayerId;
  try {
    await window.govmap.selectFeaturesOnMap({
      layers: [layer],
      whereClause: {
        [layer]: `(${oidField} = ${Number(objectId)})`,
      },
      returnFields: {
        [layer]: [oidField],
      },
      selectOnMap: true,
      isZoomToExtent: false,
      continous: false,
    });
  } catch (_) {
    // no-op (avoid noisy logs)
  }
}

async function identifyAt(x, y) {
  if (!window.govmap) return;

  status.value = "מזהה…";
  try {
    const res = await window.govmap.identifyByXYAndLayer(x, y, [govmapLayerId]);
    const ent = res?.data?.[0]?.entities?.[0];

    if (!ent) {
      selectedProps.value = null;
      status.value = "לא נמצא בניין בנקודה";
      return;
    }

    const props = fieldsToObject(ent.fields);
    selectedProps.value = props;
    status.value = "נמצא בניין";

    const oidField = findObjectIdField(props);
    const oidVal = oidField ? props[oidField] : null;
    if (oidField && oidVal != null) await selectOnMapByObjectId(oidVal, oidField);
  } catch (_) {
    status.value = "שגיאה בזיהוי (בדוק טוקן/שכבה)";
  }
}

function bindGovMapClick() {
  const gm = window.govmap;
  if (!gm?.onEvent || !gm?.events) return;

  unsubClick = gm.onEvent(gm.events.CLICK).progress((e) => {
    const x = e?.mapPoint?.x;
    const y = e?.mapPoint?.y;
    if (typeof x === "number" && typeof y === "number") identifyAt(x, y);
  });
}

async function initGovMap() {
  await ensureGovMapScriptLoaded();

  if (!govmapToken) {
    status.value = "חסר טוקן GOVMAP (VITE_GOVMAP_TOKEN)";
    return;
  }

  status.value = "טוען מפה…";

  window.govmap.createMap("map", {
    token: govmapToken,
    layers: [govmapLayerId],
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    zoomButtons: true,
    background: 1,
    layersMode: 4,
    level: 7,
    onLoad: () => {
      mapReady.value = true;
      status.value = "מוכן – לחץ על בניין במפה";
      // פתיחה בישראל (בלי כפתור)
      try {
        window.govmap.zoomToXY?.({ x: 176000, y: 655000, level: 7, marker: false });
      } catch (_) {}
      bindGovMapClick();
    },
  });
}

// ===== Address search (govmap.geocode) =====
function parseGeocodeList(resp) {
  const list = resp?.data || resp?.Data || resp?.results || resp;
  if (Array.isArray(list)) return list;
  if (Array.isArray(list?.Result)) return list.Result;
  return [];
}

function extractXY(item) {
  const x = item?.X ?? item?.x ?? item?.CenterX ?? item?.centerX ?? item?.Lon ?? item?.lon;
  const y = item?.Y ?? item?.y ?? item?.CenterY ?? item?.centerY ?? item?.Lat ?? item?.lat;
  return { x: Number(x), y: Number(y) };
}

function closeAddrResults() {
  addrOpen.value = false;
}

function focusToGeocodeItem(item) {
  if (!mapReady.value) return;

  const { x, y } = extractXY(item);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    status.value = "תוצאה בלי קואורדינטות";
    return;
  }
  try {
    window.govmap.zoomToXY({ x, y, level: 10, marker: true });
  } catch (_) {}
}

function pickAddrResult(item) {
  focusToGeocodeItem(item);
  closeAddrResults();
  status.value = `התמקדתי לכתובת: ${item.__title || "תוצאה"}`;
}

function mapResultLabel(r, fallbackQ) {
  const candidates = [
    r?.SettlementName, r?.settlementName,
    r?.PlaceName, r?.placeName,
    r?.Name, r?.name,
    r?.ResultLabel, r?.resultLabel,
    r?.Address, r?.address,
    r?.Title, r?.title,
    r?.label,
  ]
    .map((x) => (x == null ? "" : String(x).trim()))
    .filter(Boolean);

  const title = candidates[0] || fallbackQ;
  const sub =
    String(r?.City || r?.city || r?.Region || r?.region || r?.Street || r?.street || r?.SubTitle || r?.subTitle || "").trim();

  return { __title: title, __sub: sub };
}

function runGeocode(q) {
  const query = String(q || "").trim();
  if (!query) return;

  if (!mapReady.value) {
    status.value = "המפה עדיין נטענת…";
    return;
  }

  const myId = ++addrReqId;
  addrOpen.value = true;
  addrResults.value = [];

  status.value = `מחפש כתובת: ${query}`;

  const payload = { keyword: query };
  if (window.govmap?.geocodeType?.AccuracyOnly) payload.type = window.govmap.geocodeType.AccuracyOnly;

  let res;
  try {
    res = window.govmap.geocode(payload);
  } catch (_) {
    status.value = "שגיאה בחיפוש כתובת";
    addrResults.value = [];
    return;
  }

  const onSuccess = (resp) => {
    if (myId !== addrReqId) return;
    const list = parseGeocodeList(resp).slice(0, 10);
    addrResults.value = list.map((r) => ({ ...r, ...mapResultLabel(r, query) }));
    status.value = addrResults.value.length ? "בחר תוצאה מהרשימה" : "לא נמצאו תוצאות";
  };

  const onFail = () => {
    if (myId !== addrReqId) return;
    status.value = "לא ניתן לבצע חיפוש";
    addrResults.value = [];
  };

  if (res && typeof res.then === "function") res.then(onSuccess).catch(onFail);
  else if (res && typeof res.done === "function") res.done(onSuccess).fail(onFail);
  else onFail();
}

function onAddrInput() {
  if (debounceTimer) clearTimeout(debounceTimer);
  const q = addrQuery.value.trim();
  if (q.length < 3) {
    addrOpen.value = false;
    addrResults.value = [];
    return;
  }
  debounceTimer = setTimeout(() => runGeocode(q), 350);
}

function onSearchBtnClick() {
  const q = addrQuery.value.trim();
  if (!q) return;

  // אם כבר יש תוצאות פתוחות – קפוץ לראשונה
  if (addrOpen.value && addrResults.value.length) {
    pickAddrResult(addrResults.value[0]);
    return;
  }
  runGeocode(q);
}

// ===== Mobile vh fix =====
function setMobileVh() {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty("--vh", `${vh}px`);
}

onMounted(() => {
  setMobileVh();
  window.addEventListener("resize", setMobileVh);
  if (window.visualViewport) window.visualViewport.addEventListener("resize", setMobileVh);

  // close dropdown on outside click
  document.addEventListener("click", (e) => {
    const root = searchBarRef.value;
    if (!root) return;
    if (addrOpen.value && !root.contains(e.target)) addrOpen.value = false;
  });

  initGovMap().catch(() => {
    status.value = "כשלון באתחול GOVMAP";
  });
});

onBeforeUnmount(() => {
  try { unsubClick?.unsubscribe?.(); } catch {}
  window.removeEventListener("resize", setMobileVh);
  if (window.visualViewport) window.visualViewport.removeEventListener("resize", setMobileVh);
});
</script>

<style>
* { box-sizing: border-box; }

:root {
  --bg: #f5f5f5;
  --blue1: #0b63ce;
  --blue2: #084eac;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  background: var(--bg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 15px;
}

.appRoot { height: 100vh; width: 100vw; position: relative; }

.map {
  position: absolute;
  inset: 0;
}

/* Loading */
#loading{
  position:absolute;
  top:50%;
  left:50%;
  transform:translate(-50%,-50%);
  background:#fff;
  padding:24px 28px;
  border-radius:16px;
  box-shadow:0 10px 30px rgba(0,0,0,0.22);
  z-index:10000;
  text-align:center;
}
.spinner{
  width:40px;
  height:40px;
  margin:0 auto 14px;
  border:4px solid #e7e7e7;
  border-top:4px solid var(--blue1);
  border-radius:50%;
  animation:spin 0.8s linear infinite;
}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
.loadingText{font-size:14px;color:#333;font-weight:1000}
.loadingHint{margin-top:10px;font-size:12.5px;color:#666;font-weight:900}

/* ===== Always-open top search bar ===== */
#top-searchbar{
  position: fixed;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: min(760px, calc(100vw - 24px));
  z-index: 30000;
  background: #fff;
  border-radius: 999px;
  padding: 8px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.16);
  border: 2px solid rgba(11, 99, 206, 0.35);
  display: flex;
  align-items: center;
  gap: 10px;
}
#addrInput{
  flex:1;
  border:2px solid #111;
  border-radius:999px;
  padding:10px 12px;
  font-weight:900;
  font-size:14px;
  outline:none;
  text-align:right;
  direction:rtl;
}
#addrBtn{
  padding:10px 14px;
  background: var(--blue1);
  color:#fff;
  border:none;
  border-radius:999px;
  cursor:pointer;
  font-weight:1000;
  font-size:14px;
  white-space:nowrap;
}
#addrBtn:active{ transform: translateY(1px); }

#addrResults{
  position:absolute;
  top: calc(100% + 10px);
  right: 0;
  left: 0;
  border:1px solid #e0e0e0;
  background:#fff;
  border-radius:16px;
  overflow:hidden;
  max-height:320px;
  overflow-y:auto;
  box-shadow:0 10px 22px rgba(0,0,0,0.10);
}
.addr-item{
  padding:10px 12px;
  cursor:pointer;
  font-size:14px;
  border-bottom:1px solid #f0f0f0;
  font-weight:900;
}
.addr-item:last-child{ border-bottom:none; }
.addr-item:hover{ background:#f5f9ff; }
.addr-title{ font-weight:1000; color:#111; }
.addr-sub{ font-size:12.5px; color:#666; margin-top:3px; font-weight:800; }

/* PANEL */
#info-panel{
  position: absolute;
  top: 15px;
  right: 30px;
  z-index: 25000;
  background: white;
  padding: 0;
  border-radius: 14px;
  width: 440px;
  max-height: calc(100vh - 30px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: height 0.2s ease, max-height 0.2s ease;
}

#panel-header{
  background: linear-gradient(135deg, var(--blue1) 0%, var(--blue2) 100%);
  color:#fff;
  padding:14px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.15);
  flex-shrink:0;
}
#panel-header h1{
  margin:0;
  font-size:17px;
  font-weight:1000;
  letter-spacing:-0.3px;
}
#panel-header p{
  margin:6px 0 0 0;
  font-size:13px;
  opacity:0.94;
  line-height:1.35;
  font-weight:900;
}
#header-actions{
  margin-top:10px;
  display:flex;
  gap:8px;
  align-items:center;
  flex-wrap:wrap;
}
.hbtn{
  padding:9px 12px;
  border-radius:12px;
  border:1px solid rgba(255,255,255,0.35);
  background: rgba(255,255,255,0.16);
  color:#fff;
  font-weight:1000;
  cursor:pointer;
  display:inline-flex;
  gap:8px;
  align-items:center;
  user-select:none;
  font-size:13px;
}
.hbtn:active{ transform: translateY(1px); }
.hbtn.secondary{
  background: rgba(0,0,0,0.12);
  border-color: rgba(255,255,255,0.22);
}

#tabs{
  display:flex;
  background:#fafafa;
  border-bottom:2px solid #e6e6e6;
  flex-shrink:0;
  overflow-x:auto;
}
.tab{
  flex:1;
  padding:11px 10px;
  text-align:center;
  cursor:pointer;
  border-bottom:3px solid transparent;
  transition:all 0.2s ease;
  font-size:13px;
  font-weight:1000;
  color:#666;
  user-select:none;
  white-space:nowrap;
  min-width:96px;
}
.tab:hover{ background:#f2f6ff; color:#2a4c8a; }
.tab.active{ background:#fff; border-bottom-color: var(--blue1); color: var(--blue1); }

#controls{
  padding:12px 14px;
  background:#fafafa;
  border-bottom:1px solid #e8e8e8;
  flex-shrink:0;
}
.mode-grid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:8px;
  margin-bottom:10px;
}
.mode-btn{
  padding:11px 10px;
  border-radius:12px;
  border:2px solid #e3e3e3;
  background:#fff;
  cursor:pointer;
  font-size:13px;
  font-weight:1000;
  color:#444;
  transition:all 0.15s ease;
  user-select:none;
  text-align:center;
  box-shadow:0 1px 0 rgba(0,0,0,0.02);
}
.mode-btn.active{
  background: var(--blue1);
  border-color: var(--blue1);
  color:#fff;
  box-shadow:0 8px 20px rgba(11,99,206,0.18);
}
.mode-btn.full{ grid-column: 1 / -1; }
.mode-btn.primary{
  font-size:14px;
  padding:13px 10px;
  border-width:3px;
}
.mode-btn:disabled{ opacity:0.55; cursor:not-allowed; }

.row2{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:12px;
}
label{ display:block; font-weight:1000; font-size:13px; color:#333; margin-bottom:6px; }
input{
  width:100%;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid #cfcfcf;
  font-size:14px;
  background:#fff;
  font-weight:900;
  outline:none;
}
.hint{ margin-top:6px; font-size:12px; color:#666; font-weight:900; }

#info-content{
  padding:14px;
  overflow-y:auto;
  flex:1;
  min-height:0;
  background:#fff;
}

.tab-content{ display:none; }
.tab-content.active{ display:block; }

#info-title{
  font-weight:1000;
  font-size:16px;
  margin-bottom:12px;
  color:#111;
  padding-bottom:8px;
  border-bottom:3px solid var(--blue1);
}

.message{
  padding:12px 14px;
  border-radius:12px;
  margin-bottom:10px;
  font-size:13.5px;
  border-right:4px solid;
  line-height:1.55;
  font-weight:900;
}
.message-info{ background:#e7f3ff; color:#063a73; border-right-color: var(--blue1); }
.message-warn{ background:#fff7e6; color:#6a3f00; border-right-color:#ffb300; }
.message-error{ background:#fff0f0; color:#b20000; border-right-color:#ff0000; }

.card{
  border:1px solid #e8e8e8;
  border-radius:16px;
  padding:12px;
  background:#fff;
  box-shadow:0 10px 22px rgba(0,0,0,0.06);
}
.kpiRow{
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap:8px;
  margin-bottom:10px;
}
.kpi{
  border:1px solid #eee;
  background:#fafafa;
  border-radius:14px;
  padding:10px;
  text-align:center;
}
.kpi-value{
  font-weight:1000;
  color: var(--blue1);
  font-size:14px;
  margin-bottom:4px;
}
.kpi-label{
  font-size:11px;
  font-weight:1000;
  color:#666;
  letter-spacing:0.2px;
}

.kvList{ display:grid; gap:8px; }
.kv{
  display:grid;
  grid-template-columns: 160px 1fr;
  gap:10px;
  align-items:baseline;
}
.k{ color:#666; font-size:12px; font-weight:1000; }
.v{ font-weight:1000; color:#111; }

.details{ margin-top:8px; }
.pre{
  margin:10px 0 0;
  padding:10px;
  border-radius:12px;
  background:#0b1020;
  color:#e5e7eb;
  border:1px solid rgba(0,0,0,0.12);
  overflow:auto;
  max-height:240px;
}
.mono{
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono","Courier New", monospace;
}

.tips{ margin:0; padding-right:18px; color:#333; font-weight:900; line-height:1.7; }

/* Collapse */
#info-panel.collapsed{
  max-height:74px;
  height:74px;
}
#info-panel.collapsed #tabs,
#info-panel.collapsed #controls,
#info-panel.collapsed #info-content{
  display:none;
}
#info-panel.collapsed #panel-header{
  padding:10px 12px;
}
#info-panel.collapsed #panel-header p{ display:none; }
#info-panel.collapsed #panel-header h1{ font-size:15px; }
#info-panel.collapsed #header-actions{
  margin-top:0;
  justify-content:flex-end;
}

/* Mobile bottom sheet */
@media (max-width: 768px){
  #top-searchbar{
    top:10px;
    width: calc(100vw - 20px);
  }

  #info-panel{
    position: fixed;
    left: 0;
    right: 0;
    top: auto;
    bottom: 0;

    width: 100%;
    height: calc(var(--vh, 1vh) * 55);
    max-height: calc(var(--vh, 1vh) * 55);
    border-radius: 20px 20px 0 0;
    overscroll-behavior: contain;
    touch-action: pan-y;
  }

  .row2{ grid-template-columns: 1fr; }

  .mode-grid{
    grid-template-columns: repeat(3, 1fr);
    gap:6px;
    margin-bottom:8px;
  }
  .mode-btn{ padding:9px 8px; font-size:12px; border-radius:12px; border-width:2px; }
  .mode-btn.full{ grid-column: auto; }
  .mode-btn.primary{ font-size:12.5px; padding:9px 8px; border-width:2px; }

  #info-content{
    padding:10px 10px 16px 10px;
    overflow-y:auto;
    -webkit-overflow-scrolling: touch;
  }
}

/* MODAL */
.modal{
  position: fixed;
  inset: 0;
  z-index: 40000;
}
.modalOverlay{
  position:absolute;
  inset:0;
  background: rgba(0,0,0,0.45);
}
.modalCard{
  position: relative;
  width: min(760px, calc(100vw - 26px));
  max-height: calc(100vh - 26px);
  margin: 13px auto;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 12px 34px rgba(0,0,0,0.25);
  overflow: hidden;
  display:flex;
  flex-direction:column;
}
.modalHeader{
  padding:14px 16px;
  border-bottom:1px solid rgba(255,255,255,0.25);
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  background: linear-gradient(135deg, var(--blue1) 0%, var(--blue2) 100%);
  color:#fff;
}
.modalHeaderTitle{ font-weight:1000; font-size:15px; }
.modalClose{
  border:none;
  background: rgba(255,255,255,0.18);
  color:#fff;
  width:42px;
  height:42px;
  border-radius:14px;
  cursor:pointer;
  font-size:20px;
  font-weight:1000;
}
.modalClose:active{ transform: translateY(1px); }
.modalBody{
  padding:16px;
  overflow:auto;
}
</style>

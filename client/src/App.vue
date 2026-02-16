<template>
  <div class="app" dir="rtl">
    <!-- TOP BAR (CrimeMap-like) -->
    <header class="topbar">
      <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>

      <div class="brand">
        <div class="title">SatMap</div>
        <div class="sub">GOVMAP – שכבת בניינים ({{ govmapLayerId }})</div>
      </div>

      <form class="search" @submit.prevent="searchAddress(true)">
        <input
          v-model.trim="addrQuery"
          class="searchInput"
          type="search"
          placeholder="חפש כתובת… (לדוגמה: עין גדי 32 אילת)"
          :disabled="!mapReady"
          autocomplete="off"
        />
        <button class="searchBtn" type="submit" :disabled="!mapReady || !addrQuery">
          חפש
        </button>
      </form>
    </header>

    <div class="body">
      <!-- SIDE PANEL -->
      <aside class="panel" :class="{ open: panelOpen }">
        <div class="panelSection">
          <div class="sectionTitle">סטטוס</div>
          <div class="statusRow">
            <span class="pill" :class="{ ok: mapReady, bad: !mapReady }">{{ mapReady ? 'מוכן' : 'טוען…' }}</span>
            <span class="statusText">{{ status }}</span>
          </div>
        </div>

        <div class="panelSection">
          <div class="sectionTitle">ספי איכות (אם קיימים שדות בשכבה)</div>
          <div class="grid2">
            <div>
              <label>סף “שוקע/חשוד” v (mm/yr)</label>
              <input type="number" v-model.number="rateThreshold" step="0.5" />
            </div>
            <div>
              <label>סף קוהרנס (0–1)</label>
              <input type="number" v-model.number="cohThreshold" step="0.05" min="0" max="1" />
            </div>
          </div>
          <div class="hint">
            משפיע רק אם יש בשכבה שדות כמו <span class="mono">vel_mean</span> / <span class="mono">coh_mean</span>.
          </div>
        </div>

        <div class="panelSection">
          <div class="sectionTitle">תוצאות חיפוש כתובת</div>

          <div v-if="searching" class="muted">מחפש…</div>
          <div v-else-if="addrResults.length === 0" class="muted">
            אין תוצאות כרגע. חפש למעלה.
          </div>

          <div class="results" v-else>
            <button
              v-for="(r, i) in addrResults"
              :key="i"
              class="resultBtn"
              @click="goToAddressResult(r)"
              :title="r.label"
            >
              <div class="rTitle">{{ r.label }}</div>
              <div class="rSub mono" v-if="Number.isFinite(r.x) && Number.isFinite(r.y)">
                X: {{ r.x.toFixed(2) }} · Y: {{ r.y.toFixed(2) }}
              </div>
              <div class="rSub" v-else>ללא קואורדינטות (בחר תוצאה אחרת)</div>
            </button>
          </div>
        </div>

        <div class="panelSection">
          <div class="sectionTitle">בניין נבחר</div>

          <div v-if="!selectedProps" class="muted">
            לחץ על בניין במפה או חפש כתובת כדי לזהות בניין.
          </div>

          <div v-else class="kvList">
            <div class="kv">
              <div class="k">OBJECTID</div>
              <div class="v mono">{{ pickedOidVal ?? '—' }}</div>
            </div>

            <div class="kv">
              <div class="k">סטטוס שקיעה</div>
              <div class="v">{{ derived.status }}</div>
            </div>

            <div class="kv">
              <div class="k">v_mean (mm/yr)</div>
              <div class="v mono">{{ fmt(derived.vel_mean) }}</div>
            </div>

            <div class="kv">
              <div class="k">coh_mean</div>
              <div class="v mono">{{ fmt(derived.coh_mean) }}</div>
            </div>

            <details class="details">
              <summary>כל השדות</summary>
              <pre class="pre">{{ JSON.stringify(selectedProps, null, 2) }}</pre>
            </details>
          </div>
        </div>

        <div class="panelSection">
          <div class="sectionTitle">טיפים</div>
          <ul class="tips">
            <li>אם מופיע “חסר טוקן” – ודא ש־<span class="mono">VITE_GOVMAP_TOKEN</span> מגיע בזמן build.</li>
            <li>אם אין בניין בלחיצה — התקרב עוד, או ודא שהשכבה דלוקה.</li>
          </ul>
        </div>
      </aside>

      <!-- MAP -->
      <main class="mapWrap">
        <div id="map" class="map"></div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

// ====== GOVMAP CONFIG ======
const govmapLayerId = '225287'
const govmapToken = (import.meta.env.VITE_GOVMAP_TOKEN || '').trim()

// ====== UI STATE ======
const panelOpen = ref(true)
const status = ref('מאתחל…')
const mapReady = ref(false)

const rateThreshold = ref(-2.0)
const cohThreshold = ref(0.35)

const selectedProps = ref(null)

// Address search
const addrQuery = ref('')
const searching = ref(false)
const addrResults = ref([]) // [{label,x,y,raw}]

let eventsBound = false
let searchTimer = null

function ensureGovMapScriptLoaded() {
  if (window.govmap) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = 'https://www.govmap.gov.il/govmap/api/govmap.api.js'
    s.defer = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('לא הצלחתי לטעון את GOVMAP API'))
    document.head.appendChild(s)
  })
}

// ---------- helpers ----------
function fmt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toFixed(3)
}

function fieldsToObject(fields) {
  const out = {}
  for (const f of fields || []) {
    const key = f?.fieldName ?? f?.name ?? f?.field
    const val = f?.value ?? f?.fieldValue
    if (key !== undefined) out[key] = val
  }
  return out
}

function getFiniteXYFromEvent(e) {
  const mp = e?.mapPoint || e?.data?.mapPoint || e?.point || null
  const xRaw = mp?.x ?? e?.x ?? null
  const yRaw = mp?.y ?? e?.y ?? null
  const x = typeof xRaw === 'string' ? Number.parseFloat(xRaw) : Number(xRaw)
  const y = typeof yRaw === 'string' ? Number.parseFloat(yRaw) : Number(yRaw)
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null
  return { x, y }
}

function pickObjectIdField(props) {
  if (!props) return null
  const keys = Object.keys(props)
  return keys.find((k) => String(k).toLowerCase() === 'objectid') || null
}

// ====== SUBSIDENCE DERIVATION ======
const derived = computed(() => {
  const p = selectedProps.value || {}

  const vRaw = p.vel_mean ?? p.VEL_MEAN ?? p.VELmean ?? p.VelMean ?? p.velocity_mean
  const cRaw = p.coh_mean ?? p.COH_MEAN ?? p.COHmean ?? p.CohMean ?? p.coherence_mean

  const v = Number(vRaw)
  const c = Number(cRaw)

  const hasV = Number.isFinite(v)
  const hasC = Number.isFinite(c)

  let s = 'אין נתוני InSAR בשכבה'
  if (hasV || hasC) {
    const cohOk = hasC ? c >= cohThreshold.value : true
    if (!cohOk) s = 'קוהרנס נמוך (לא אמין)'
    else if (hasV && v <= rateThreshold.value) s = 'שוקע/חשוד'
    else s = 'נראה תקין'
  }

  return {
    vel_mean: hasV ? v : null,
    coh_mean: hasC ? c : null,
    status: s,
  }
})

const pickedOidField = computed(() => pickObjectIdField(selectedProps.value))
const pickedOidVal = computed(() => {
  const f = pickedOidField.value
  return f ? selectedProps.value?.[f] : null
})

// ====== GOVMAP actions ======
function zoomTo(x, y, level = 9, marker = true) {
  if (!window.govmap) return
  if (!Number.isFinite(x) || !Number.isFinite(y)) return
  window.govmap.zoomToXY?.({ x, y, level, marker }) // :contentReference[oaicite:1]{index=1}
}

async function identifyAt(x, y) {
  if (!window.govmap) return
  if (!Number.isFinite(x) || !Number.isFinite(y)) return

  status.value = 'מזהה בניין…'

  try {
    const res = await window.govmap.identifyByXYAndLayer(x, y, [govmapLayerId])
    const ent = res?.data?.[0]?.entities?.[0]

    if (!ent) {
      selectedProps.value = null
      status.value = 'לא נמצא בניין בנקודה'
      return
    }

    const props = fieldsToObject(ent.fields)
    selectedProps.value = props
    status.value = 'נמצא בניין'
  } catch (e) {
    console.error(e)
    status.value = 'שגיאה בזיהוי (בדוק טוקן/שכבה)'
  }
}

function bindGovMapEvents() {
  const gm = window.govmap
  if (!gm?.onEvent || !gm?.events || eventsBound) return
  eventsBound = true

  // רק CLICK — אין יותר MOUSE_MOVE בכלל
  gm.onEvent(gm.events.CLICK).progress((e) => {
    const xy = getFiniteXYFromEvent(e)
    if (!xy) {
      status.value = 'לחיצה ללא קואורדינטות'
      return
    }
    identifyAt(xy.x, xy.y)
  })
}

// ====== ADDRESS SEARCH (govmap.geocode) ======
function normalizeGeocodeResponse(resp) {
  const r = resp?.data ?? resp ?? {}
  const resultCode = Number(r.ResultCode ?? r.resultCode ?? r.code ?? NaN)

  // נסה XY “ישיר”
  const xDirect = Number(r.X ?? r.x ?? r.Easting ?? r.easting)
  const yDirect = Number(r.Y ?? r.y ?? r.Northing ?? r.northing)

  // נסה רשימת תוצאות אפשריות
  const list =
    r.Results ??
    r.results ??
    r.Addresses ??
    r.addresses ??
    r.PossibleAddresses ??
    r.possibleAddresses ??
    r.data ??
    []

  const candidates = Array.isArray(list)
    ? list
        .map((it) => {
          const x = Number(it?.X ?? it?.x ?? it?.Easting ?? it?.easting)
          const y = Number(it?.Y ?? it?.y ?? it?.Northing ?? it?.northing)
          const label =
            it?.Address ??
            it?.address ??
            it?.Text ??
            it?.text ??
            it?.DisplayText ??
            it?.displayText ??
            it?.Name ??
            it?.name ??
            it?.value ??
            ''
          return {
            label: String(label || '').trim() || 'תוצאה',
            x: Number.isFinite(x) ? x : NaN,
            y: Number.isFinite(y) ? y : NaN,
            raw: it,
          }
        })
        .slice(0, 20)
    : []

  const direct = Number.isFinite(xDirect) && Number.isFinite(yDirect)
    ? [{ label: addrQuery.value || 'תוצאה מדויקת', x: xDirect, y: yDirect, raw: r }]
    : []

  // אם אין XY ישיר אבל יש candidates עם XY — נציג אותם.
  // אם יש XY ישיר — נציג אותו ראשון.
  const merged = [...direct, ...candidates].filter((v, i, a) => i === a.findIndex((t) => t.label === v.label && t.x === v.x && t.y === v.y))
  return { resultCode, merged }
}

async function searchAddress(enterPressed = false) {
  if (!window.govmap) return
  const q = addrQuery.value
  if (!q) {
    addrResults.value = []
    return
  }

  searching.value = true
  status.value = 'מחפש כתובת…'

  try {
    // AccuracyOnly אם לחצו Enter, אחרת FullResult (יותר “autocomplete”)
    const type = enterPressed ? window.govmap.geocodeType?.AccuracyOnly : window.govmap.geocodeType?.FullResult
    const resp = await window.govmap.geocode({ keyword: q, type }) // :contentReference[oaicite:2]{index=2}
    const { merged } = normalizeGeocodeResponse(resp)

    addrResults.value = merged
    status.value = merged.length ? 'בחר תוצאה מהרשימה' : 'לא נמצאו תוצאות'
  } catch (e) {
    console.error(e)
    status.value = 'שגיאה בחיפוש כתובת'
    addrResults.value = []
  } finally {
    searching.value = false
  }
}

function goToAddressResult(r) {
  if (!r) return
  if (Number.isFinite(r.x) && Number.isFinite(r.y)) {
    zoomTo(r.x, r.y, 9, true)
    // אחרי “קפיצה לכתובת” — ננסה לזהות בניין בנקודה
    identifyAt(r.x, r.y)
    status.value = 'התמקדתי לכתובת'
    // במובייל נוח לסגור פאנל
    if (window.innerWidth < 980) panelOpen.value = false
  } else {
    status.value = 'לתוצאה אין קואורדינטות'
  }
}

// Debounced autocomplete בזמן הקלדה
watch(addrQuery, (v) => {
  clearTimeout(searchTimer)
  if (!v || v.length < 3) {
    addrResults.value = []
    return
  }
  searchTimer = setTimeout(() => searchAddress(false), 300)
})

// ====== INIT ======
async function initGovMap() {
  await ensureGovMapScriptLoaded()

  if (!govmapToken) {
    status.value = 'חסר טוקן GOVMAP (VITE_GOVMAP_TOKEN)'
    return
  }

  status.value = 'טוען מפה…'

  window.govmap.createMap('map', {
    token: govmapToken,
    layers: [govmapLayerId],
    visibleLayers: [govmapLayerId],
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    zoomButtons: true,
    background: 1,
    layersMode: 4,
    level: 7,
    onLoad: () => {
      mapReady.value = true
      status.value = 'מוכן – חפש כתובת או לחץ על המפה'
      bindGovMapEvents()
      // התמקדות “ברירת מחדל” לישראל פעם אחת (בלי כפתור)
      zoomTo(176000, 655000, 7, false)
    },
  })
}

onMounted(() => {
  initGovMap().catch((e) => {
    console.error(e)
    status.value = 'כשלון באתחול GOVMAP'
  })
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  // ניקוי אירועים לפי ה-API :contentReference[oaicite:3]{index=3}
  try { window.govmap?.unbindEvent?.(window.govmap?.events?.CLICK) } catch {}
})
</script>

<style>
:root {
  --bg: #f3f4f6;
  --panel: #ffffff;
  --text: #0f172a;
  --muted: #6b7280;
  --line: rgba(15, 23, 42, 0.12);
  --shadow: 0 10px 30px rgba(0,0,0,0.10);
  --btn: #0f172a;
  --btnText: #ffffff;
}

* { box-sizing: border-box; }

html, body {
  height: 100%;
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}

.app { height: 100vh; display: grid; grid-template-rows: auto 1fr; }

.topbar {
  position: sticky; top: 0; z-index: 10;
  display: grid;
  grid-template-columns: auto 1fr 520px;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}

@media (max-width: 980px) {
  .topbar { grid-template-columns: auto 1fr; grid-template-rows: auto auto; }
  .search { grid-column: 1 / -1; }
}

.iconBtn {
  width: 40px; height: 40px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
  cursor: pointer;
  font-size: 18px;
}

.brand .title { font-weight: 900; letter-spacing: 0.2px; }
.brand .sub { font-size: 12px; color: var(--muted); margin-top: 2px; }

.search { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
.searchInput {
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--line);
  padding: 0 12px;
  outline: none;
  background: #fff;
}
.searchBtn {
  height: 40px;
  border-radius: 12px;
  border: 0;
  padding: 0 14px;
  background: var(--btn);
  color: var(--btnText);
  font-weight: 800;
  cursor: pointer;
}
.searchBtn:disabled { opacity: 0.55; cursor: not-allowed; }

.body { height: 100%; display: grid; grid-template-columns: 420px 1fr; }
@media (max-width: 980px) { .body { grid-template-columns: 1fr; } }

.panel {
  background: var(--panel);
  border-left: 1px solid var(--line);
  box-shadow: var(--shadow);
  overflow: auto;
  padding: 12px;
}

@media (max-width: 980px) {
  .panel {
    position: absolute;
    top: 62px; /* approx topbar height */
    bottom: 0;
    right: 0;
    width: min(92vw, 420px);
    transform: translateX(105%);
    transition: transform 180ms ease;
    z-index: 20;
  }
  .panel.open { transform: translateX(0); }
}

.panelSection {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fff;
}

.sectionTitle { font-weight: 900; margin-bottom: 10px; }

.statusRow { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.pill {
  display: inline-flex; align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
  font-weight: 900;
  font-size: 12px;
}
.pill.ok { background: #ecfdf5; border-color: rgba(16,185,129,0.35); }
.pill.bad { background: #fff7ed; border-color: rgba(249,115,22,0.35); }
.statusText { color: var(--muted); font-weight: 700; }

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
@media (max-width: 980px) { .grid2 { grid-template-columns: 1fr; } }

label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; font-weight: 800; }
input {
  width: 100%;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--line);
  padding: 0 10px;
  outline: none;
  background: #fff;
}

.hint { margin-top: 8px; color: var(--muted); font-size: 12px; }
.muted { color: var(--muted); }

.results { display: grid; gap: 8px; }
.resultBtn {
  text-align: right;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 14px;
  padding: 10px;
  cursor: pointer;
}
.resultBtn:hover { background: #f8fafc; }
.rTitle { font-weight: 900; }
.rSub { margin-top: 4px; color: var(--muted); font-size: 12px; }

.kvList { display: grid; gap: 8px; }
.kv { display: grid; grid-template-columns: 140px 1fr; gap: 10px; }
.kv .k { color: var(--muted); font-size: 12px; font-weight: 900; }
.kv .v { font-weight: 800; }

.details summary { cursor: pointer; font-weight: 900; color: var(--muted); }
.pre {
  margin: 10px 0 0;
  padding: 10px;
  border-radius: 12px;
  background: #0b10200f;
  border: 1px solid var(--line);
  overflow: auto;
  max-height: 240px;
}

.tips { margin: 0; padding-right: 18px; color: var(--muted); }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }

.mapWrap { position: relative; }
.map { position: absolute; inset: 0; }
</style>

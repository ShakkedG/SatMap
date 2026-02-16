<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">GOVMAP – שכבת בניינים ({{ govmapLayerId }})</div>
        </div>

        <div class="topBtns">
          <button class="btn ghost" @click="focusIsrael" :disabled="!mapReady">התמקד בישראל</button>
          <button class="btn" @click="reload">טען מחדש</button>
        </div>
      </div>

      <div class="box">
        <div class="row2">
          <div>
            <label>סף “שוקע/חשוד” v (mm/yr)</label>
            <input type="number" v-model.number="rateThreshold" step="0.5" />
            <div class="hint">ישפיע כשיהיו בשכבה שדות כמו <span class="mono">vel_mean</span> / <span class="mono">coh_mean</span></div>
          </div>

          <div>
            <label>סף קוהרנס (0–1)</label>
            <input type="number" v-model.number="cohThreshold" step="0.05" min="0" max="1" />
            <div class="hint">לזיהוי תצפיות אמינות יותר</div>
          </div>
        </div>
      </div>

      <div class="box">
        <div class="kpi">
          <div class="k">סטטוס</div>
          <div class="v">{{ status }}</div>
        </div>
        <div class="hint" v-if="lastXYText">{{ lastXYText }}</div>
      </div>

      <div class="box">
        <div class="sectionTitle">בניין נבחר</div>

        <div v-if="!selectedProps" class="empty">
          לחץ על בניין במפה כדי לשלוף את המאפיינים מהשכבה ב־GOVMAP.
        </div>

        <div v-else class="kvList">
          <div class="kv">
            <div class="k">OBJECTID</div>
            <div class="v mono">{{ pickedOidVal ?? '—' }}</div>
          </div>

          <div class="kv">
            <div class="k">סטטוס שקיעה (מהשדות)</div>
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
            <summary>הצג את כל השדות</summary>
            <pre class="pre">{{ JSON.stringify(selectedProps, null, 2) }}</pre>
          </details>
        </div>
      </div>

      <div class="box">
        <div class="sectionTitle">טיפים מהירים</div>
        <ul class="tips">
          <li>אם אתה רואה “חסר טוקן” – ודא שב־GitHub Actions אתה מעביר את <span class="mono">VITE_GOVMAP_TOKEN</span> כ־env בזמן ה־build (דוגמה למטה).</li>
          <li>ה־identify רגיש לזום; אם לא מוצא כלום נסה להתקרב/להתרחק קצת. :contentReference[oaicite:1]{index=1}</li>
        </ul>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map" class="map"></div>
      <div class="hud" v-if="hudText">{{ hudText }}</div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

// ====== GOVMAP CONFIG ======
const govmapLayerId = '225287'
const govmapToken = (import.meta.env.VITE_GOVMAP_TOKEN || '').trim()

// ====== UI STATE ======
const rateThreshold = ref(-2.0)
const cohThreshold = ref(0.35)

const status = ref('מאתחל…')
const hudText = ref('')
const lastXYText = ref('')
const selectedProps = ref(null)
const mapReady = ref(false)

let eventsBound = false

// ====== HELPERS ======
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

function throttle(fn, ms) {
  let last = 0
  let timer = null
  let queuedArgs = null
  return (...args) => {
    const now = Date.now()
    const remain = ms - (now - last)
    if (remain <= 0) {
      last = now
      fn(...args)
      return
    }
    queuedArgs = args
    clearTimeout(timer)
    timer = setTimeout(() => {
      last = Date.now()
      fn(...queuedArgs)
      queuedArgs = null
    }, remain)
  }
}

function reload() {
  location.reload()
}

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

// מחלץ XY “בטוח” מהאירוע (ומונע NaN/null שגורמים ל-crash)
function getFiniteXY(e) {
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
  const k = keys.find((kk) => String(kk).toLowerCase() === 'objectid')
  return k || null
}

// ====== SUBSIDENCE DERIVATION (אם יש שדות) ======
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

// ====== GOVMAP MAP ======
function focusIsrael() {
  if (!window.govmap) return
  window.govmap.zoomToXY?.({ x: 176000, y: 655000, level: 7, marker: false })
}

async function selectOnMapByObjectId(objectId, oidField) {
  if (!window.govmap) return
  const oid = Number(objectId)
  if (!Number.isFinite(oid) || !oidField) return

  try {
    await window.govmap.selectFeaturesOnMap({
      layers: [govmapLayerId],
      whereClause: {
        [govmapLayerId]: `${oidField} = ${oid}`,
      },
      returnFields: {
        [govmapLayerId]: [oidField],
      },
      selectOnMap: true,
      isZoomToExtent: false,
      continous: false,
    })
  } catch (e) {
    console.warn('selectFeaturesOnMap failed', e)
  }
}

async function identifyAt(x, y) {
  if (!window.govmap) return
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    status.value = 'קואורדינטות לא תקינות (התעלמתי כדי לא להפיל את האתר)'
    return
  }

  status.value = 'מזהה…'

  try {
    // govmap.identifyByXYAndLayer(x, y, layers) :contentReference[oaicite:2]{index=2}
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

    const oidField = pickObjectIdField(props)
    const oidVal = oidField ? props[oidField] : null
    if (oidField && oidVal !== null && oidVal !== undefined) {
      await selectOnMapByObjectId(oidVal, oidField)
    }
  } catch (e) {
    console.error(e)
    status.value = 'שגיאה בזיהוי (בדוק טוקן/שכבה)'
  }
}

function bindGovMapEvents() {
  const gm = window.govmap
  if (!gm?.onEvent || !gm?.events || eventsBound) return
  eventsBound = true

  gm.onEvent(gm.events.CLICK).progress((e) => {
    const xy = getFiniteXY(e)
    if (!xy) {
      status.value = 'לחיצה ללא קואורדינטות (התעלמתי)'
      return
    }
    lastXYText.value = `XY: ${xy.x.toFixed(2)}, ${xy.y.toFixed(2)}`
    identifyAt(xy.x, xy.y)
  })

  gm.onEvent(gm.events.MOUSE_MOVE).progress(
    throttle((e) => {
      const xy = getFiniteXY(e)
      if (!xy) {
        hudText.value = ''
        return
      }
      hudText.value = `X: ${xy.x.toFixed(2)}   Y: ${xy.y.toFixed(2)}`
    }, 120),
  )
}

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
    visibleLayers: [govmapLayerId], // חשוב כדי שהשכבה תהיה דלוקה :contentReference[oaicite:3]{index=3}
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    zoomButtons: true,
    background: 1,
    layersMode: 4,
    level: 7,
    onLoad: () => {
      mapReady.value = true
      status.value = 'מוכן – לחץ על בניין במפה'
      focusIsrael()
      bindGovMapEvents()
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
  // הסרה מסודרת לפי ה-API :contentReference[oaicite:4]{index=4}
  try { window.govmap?.unbindEvent?.(window.govmap?.events?.CLICK) } catch {}
  try { window.govmap?.unbindEvent?.(window.govmap?.events?.MOUSE_MOVE) } catch {}
})
</script>

<style>
:root {
  --bg: #0b1020;
  --panel: #0f172a;
  --panel2: #111c33;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --line: rgba(255, 255, 255, 0.08);
  --accent: #22c55e;
  --danger: #ef4444;
}

* { box-sizing: border-box; }

html, body {
  height: 100%;
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}

.layout {
  height: 100vh;
  display: grid;
  grid-template-columns: 420px 1fr;
}

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
}

.panel {
  background: linear-gradient(180deg, var(--panel), var(--panel2));
  border-left: 1px solid var(--line);
  padding: 14px;
  overflow: auto;
}

.top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.title { font-size: 22px; font-weight: 800; letter-spacing: 0.2px; }
.sub { font-size: 13px; color: var(--muted); margin-top: 2px; }
.topBtns { display: flex; gap: 8px; }

.btn {
  appearance: none;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
  border-radius: 10px;
  padding: 8px 10px;
  cursor: pointer;
  font-weight: 700;
}
.btn:hover { background: rgba(255, 255, 255, 0.09); }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn.ghost { background: transparent; }

.box {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.03);
}

.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 980px) { .row2 { grid-template-columns: 1fr; } }

label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }

input {
  width: 100%;
  border: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.2);
  color: var(--text);
  padding: 10px;
  border-radius: 10px;
  outline: none;
}

.hint { margin-top: 6px; font-size: 12px; color: var(--muted); }

.sectionTitle { font-weight: 800; margin-bottom: 10px; }
.empty { color: var(--muted); line-height: 1.4; }

.kpi { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.kpi .k { color: var(--muted); font-size: 12px; }
.kpi .v { font-weight: 800; }

.kvList { display: grid; gap: 8px; }

.kv {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 10px;
  align-items: baseline;
}

.kv .k { color: var(--muted); font-size: 12px; }
.kv .v { font-weight: 700; }

.details { margin-top: 6px; }

.pre {
  margin: 10px 0 0;
  padding: 10px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--line);
  overflow: auto;
  max-height: 240px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.tips { margin: 0; padding-right: 18px; color: var(--muted); }

.mapWrap { position: relative; }
.map { position: absolute; inset: 0; }

.hud {
  position: absolute;
  bottom: 14px;
  left: 14px;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--line);
  font-weight: 700;
}
</style>

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
      </div>

      <div class="box">
        <div class="sectionTitle">בניין נבחר</div>

        <div v-if="!selectedProps" class="empty">
          לחץ על בניין במפה כדי לשלוף את המאפיינים מהשכבה ב־GOVMAP.
        </div>

        <div v-else class="kvList">
          <div class="kv">
            <div class="k">OBJECTID</div>
            <div class="v mono">{{ selectedProps.OBJECTID ?? '—' }}</div>
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
          <li>אם אתה רואה “חסר טוקן” – שים את הטוקן ב־GitHub Secrets בשם <span class="mono">VITE_GOVMAP_TOKEN</span>.</li>
          <li>אם “לא נמצא בניין” – נסה להתקרב עוד, או ודא שהשכבה ({{ govmapLayerId }}) דולקת ב־GOVMAP.</li>
          <li>הקוד מסמן את הבניין במפה ע״י <span class="mono">OBJECTID</span> (אם קיים בשכבה).</li>
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
// שכבת המשתמש שהעלית ל־GOVMAP (מספר שכבה)
const govmapLayerId = '225287'

// מומלץ: להגדיר GitHub Secret בשם VITE_GOVMAP_TOKEN
// Settings -> Secrets and variables -> Actions -> New repository secret
const govmapToken = (import.meta.env.VITE_GOVMAP_TOKEN || '').trim()

// ====== UI STATE ======
const rateThreshold = ref(-2.0)
const cohThreshold = ref(0.35)

const status = ref('מאתחל…')
const hudText = ref('')
const selectedProps = ref(null)
const mapReady = ref(false)

let unsubClick = null
let unsubMove = null

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

// ====== GOVMAP MAP ======
function focusIsrael() {
  if (!window.govmap) return
  window.govmap.zoomToXY?.({ x: 176000, y: 655000, level: 7, marker: false })
}

async function selectOnMapByObjectId(objectId, oidField) {
  if (!window.govmap || objectId === null || objectId === undefined) return

  const layer = govmapLayerId
  if (!oidField) return

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
    })
  } catch (e) {
    console.warn('selectFeaturesOnMap failed', e)
  }
}

async function identifyAt(x, y) {
  if (!window.govmap) return

  status.value = 'מזהה…'

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

    const oidField = ('objectid' in props) ? 'objectid' : (('OBJECTID' in props) ? 'OBJECTID' : null)
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
  if (!gm?.onEvent || !gm?.events) return

  unsubClick = gm.onEvent(gm.events.CLICK).progress((e) => {
    const x = e?.mapPoint?.x
    const y = e?.mapPoint?.y
    if (typeof x === 'number' && typeof y === 'number') {
      identifyAt(x, y)
    }
  })

  unsubMove = gm.onEvent(gm.events.MOUSE_MOVE).progress(
    throttle((e) => {
      const x = e?.mapPoint?.x
      const y = e?.mapPoint?.y
      if (typeof x !== 'number' || typeof y !== 'number') return
      hudText.value = `X: ${x.toFixed(2)}   Y: ${y.toFixed(2)}`
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
  try { unsubClick?.unsubscribe?.() } catch {}
  try { unsubMove?.unsubscribe?.() } catch {}
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

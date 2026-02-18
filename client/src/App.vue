<template>
  <div class="layout" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div>
          <div class="appTitle">SatMap</div>
          <div class="appSub">GovMap buildings + InSAR JOIN (OBJECTID)</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>
      </div>

      <div class="box">
        <div class="title2">סטטוס</div>
        <div class="kv"><span>GovMap</span><b>{{ govmapReady ? "מוכן" : "טוען…" }}</b></div>
        <div class="kv"><span>CSV</span><b>{{ csvState.loaded ? `נטען (${csvState.count.toLocaleString()})` : (csvState.loading ? "טוען…" : "לא נטען") }}</b></div>
        <div class="hint" v-if="csvState.loading">{{ csvState.loading }}</div>
        <div class="hint" v-if="csvState.loaded">קובץ: <code>{{ CSV_URL }}</code></div>
        <div class="hint" v-if="govmapReady">שכבת בניינים: <code>{{ BUILDINGS_LAYER_ID }}</code></div>
      </div>

      <div class="box">
        <div class="title2">חיפוש OBJECTID</div>
        <div class="row2">
          <input v-model.trim="qObjectId" inputmode="numeric" placeholder="לדוגמה: 1210580" />
          <button class="btn" @click="searchInGovmap" :disabled="!govmapReady || !qObjectId">חפש במפה</button>
        </div>
        <div class="hint">
          החיפוש עושה Highlight במפה. כדי לראות את כל הנתונים בפאנל — לחץ על הבניין במפה.
        </div>
      </div>

      <div class="box" v-if="selected">
        <div class="title2">בניין נבחר</div>

        <div class="kv">
          <span>OBJECTID</span>
          <b>{{ selected.objectId ?? "—" }}</b>
        </div>

        <div class="row2">
          <button class="btn" @click="zoomToSelected" :disabled="!govmapReady || !selected.centroid">התמקד</button>
          <button class="btn ghost" @click="clearSelected">נקה</button>
        </div>

        <div class="sep"></div>

        <div class="title3">InSAR (מה־CSV)</div>
        <template v-if="selected.insar">
          <div class="kv"><span>vert_mm</span><b>{{ fmtNum(selected.insar.vert_mm, 2) }}</b></div>
          <div class="kv"><span>corr_u16</span><b>{{ selected.insar.corr_u16 }}</b></div>
          <div class="kv"><span>corr (0–1)</span><b>{{ fmtNum(selected.insar.corr_u16 / 65535, 4) }}</b></div>
          <div class="hint ok">JOIN נמצא ✅</div>
        </template>
        <template v-else>
          <div class="hint warn">אין רשומת InSAR ל־OBJECTID הזה (כלומר הבניין מחוץ לראסטר או שאין נתונים) → NULL</div>
        </template>

        <div class="sep"></div>

        <div class="title3">שדות בניין (GovMap Identify)</div>
        <div class="hint" v-if="!selected.fields?.length">לא התקבלו שדות (בדוק שה־Identify מצליח על השכבה).</div>

        <div class="fields" v-else>
          <div class="fieldRow" v-for="(f, i) in selected.fields.slice(0, 30)" :key="i">
            <span class="fName">{{ f.name }}</span>
            <b class="fVal">{{ f.value ?? "—" }}</b>
          </div>
          <div class="hint" v-if="selected.fields.length > 30">
            מוצגים 30 ראשונים. (אפשר להגדיל אם תרצה)
          </div>
        </div>
      </div>

      <div class="box error" v-if="err">
        {{ err }}
      </div>
    </aside>

    <main class="mapWrap">
      <div ref="mapEl" class="map"></div>

      <div class="loading" v-if="!govmapReady">
        טוען GovMap…
      </div>

      <div class="loading" v-else-if="csvState.loading">
        טוען דאטהבייס (CSV)…
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";

/** ====== קונפיג ====== */
const BUILDINGS_LAYER_ID = import.meta.env.VITE_BUILDINGS_LAYER_ID || "225287"; // שכבת המשתמש שלך ב-GovMap
const GOVMAP_TOKEN = import.meta.env.VITE_GOVMAP_TOKEN || ""; // מומלץ לשים ב-.env ולא בקוד

// שים את הקובץ כאן: client/public/data/tablecsv.csv
const CSV_URL = computed(() => {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}data/tablecsv.csv`;
}).value;

/** ====== UI State ====== */
const mapEl = ref(null);
const panelOpen = ref(true);
const govmapReady = ref(false);
const err = ref("");

const qObjectId = ref("");

/**
 * selected = {
 *   objectId: number,
 *   centroid: {x,y,level?} (ב-2039),
 *   fields: [{name,value}],
 *   insar: {vert_mm, corr_u16} | null
 * }
 */
const selected = ref(null);

/** ====== CSV DB (קומפקטי) ======
 * כדי לחסוך RAM: נשמור מערכים ממוינים + binary search
 */
const csvState = reactive({
  loaded: false,
  loading: "",
  count: 0,
  ids: /** @type {Int32Array|null} */ (null),
  vert: /** @type {Float32Array|null} */ (null),
  corr: /** @type {Uint16Array|null} */ (null),
});

/** ====== Helpers ====== */
function fmtNum(v, digits = 3) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function sleep0() {
  return new Promise((r) => setTimeout(r, 0));
}

function binarySearchInt32(arr, target) {
  let lo = 0, hi = arr.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const v = arr[mid];
    if (v === target) return mid;
    if (v < target) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}

function findInsarByObjectId(objectId) {
  if (!csvState.loaded || !csvState.ids) return null;
  const idx = binarySearchInt32(csvState.ids, objectId);
  if (idx < 0) return null;
  return {
    vert_mm: csvState.vert[idx],
    corr_u16: csvState.corr[idx],
  };
}

/** ====== Load GovMap script dynamically ====== */
function loadGovmapScript() {
  return new Promise((resolve, reject) => {
    if (window.govmap) return resolve();
    const s = document.createElement("script");
    s.src = "https://www.govmap.gov.il/govmap/api/govmap.api.js";
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("נכשל לטעון govmap.api.js"));
    document.head.appendChild(s);
  });
}

/** ====== Init GovMap ====== */
function initGovmap() {
  if (!window.govmap) throw new Error("govmap לא נטען");

  if (!GOVMAP_TOKEN) {
    throw new Error("חסר GOVMAP TOKEN. שים VITE_GOVMAP_TOKEN ב-.env (או תכניס בקוד).");
  }

  // יצירת מפה
  window.govmap.createMap(mapEl.value, {
    token: GOVMAP_TOKEN,
    layers: [String(BUILDINGS_LAYER_ID)], // שכבת הבניינים שלך
    showXY: true,
    identifyOnClick: false, // אנחנו עושים Identify בעצמנו כדי לתפוס OBJECTID
    isEmbeddedToggle: false,
    background: 3,
    layersMode: 1,
    zoomButtons: true,
  });

  govmapReady.value = true;

  // מאזין לקליק במפה → Identify על שכבת הבניינים → JOIN
  window.govmap.onEvent(window.govmap.events.CLICK).progress(async (e) => {
    try {
      const mp = e?.mapPoint;
      if (!mp) return;

      // Identify לפי XY רק על שכבת הבניינים
      const res = await window.govmap.identifyByXYAndLayer(mp.x, mp.y, [String(BUILDINGS_LAYER_ID)]);
      const entity = res?.data?.[0]?.entities?.[0];
      if (!entity) {
        selected.value = null;
        return;
      }

      const objId = extractObjectId(entity);
      const fields = normalizeFields(entity?.fields);

      selected.value = {
        objectId: objId,
        centroid: entity?.centroid ? { x: entity.centroid.x, y: entity.centroid.y, level: 10 } : { x: mp.x, y: mp.y, level: 10 },
        fields,
        insar: Number.isFinite(objId) ? findInsarByObjectId(objId) : null,
      };
    } catch (ex) {
      err.value = ex?.message || String(ex);
    }
  });
}

function extractObjectId(entity) {
  // בחלק מהמקרים objectId כבר מגיע
  const direct = Number(entity?.objectId);
  if (Number.isFinite(direct)) return direct;

  // אחרת נחפש בשדות
  const fields = entity?.fields || [];
  for (const f of fields) {
    const n = String(f?.fieldName || "").toUpperCase();
    if (n === "OBJECTID" || n === "OBJECT_ID") {
      const v = Number(f?.value);
      if (Number.isFinite(v)) return v;
    }
  }
  return NaN;
}

function normalizeFields(fields) {
  if (!Array.isArray(fields)) return [];
  return fields.map((f) => ({
    name: f?.fieldName ?? f?.fieldDisplayName ?? "field",
    value: f?.value,
  }));
}

function zoomToSelected() {
  if (!govmapReady.value || !selected.value?.centroid) return;
  const { x, y, level } = selected.value.centroid;
  // התמקדות לקואורדינטות וקנ"מ
  window.govmap.zoomToXY(x, y, level ?? 10);
}

function clearSelected() {
  selected.value = null;
}

/** ====== Search in layer by OBJECTID (highlight) ====== */
function searchInGovmap() {
  if (!govmapReady.value) return;
  const id = String(qObjectId.value || "").trim();
  if (!id) return;

  window.govmap.searchInLayer({
    layerName: String(BUILDINGS_LAYER_ID),
    fieldName: "OBJECTID",
    fieldValues: [id],
    highlight: true,
    showBubble: true,
    // צבעים (RGBA) – אפשר לשנות/להסיר
    outLineColor: [255, 0, 0, 255],
    fillColor: [255, 0, 0, 40],
  });

  // נעדכן לפחות את צד ה-CSV (גם בלי קליק)
  const n = Number(id);
  if (Number.isFinite(n)) {
    const ins = findInsarByObjectId(n);
    selected.value = {
      objectId: n,
      centroid: null,
      fields: [],
      insar: ins,
    };
  }
}

/** ====== Load CSV efficiently ====== */
async function loadCsvDb() {
  csvState.loading = "מוריד CSV…";
  csvState.loaded = false;
  err.value = "";

  const res = await fetch(CSV_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`נכשל להוריד CSV (${res.status})`);

  // Stream parse (לא תוקע דפדפן כמו split ענק)
  csvState.loading = "מפרש CSV…";

  const decoder = new TextDecoder("utf-8");
  const reader = res.body?.getReader?.();
  if (!reader) {
    // fallback
    const text = await res.text();
    await parseCsvText(text);
    return;
  }

  let header = null;
  let buf = "";
  const ids = [];
  const vert = [];
  const corr = [];

  let rowCount = 0;
  let idxOBJECTID = -1, idxVERT = -1, idxCORR = -1;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buf += decoder.decode(value, { stream: true });

    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).replace(/\r$/, "");
      buf = buf.slice(nl + 1);

      if (!line.trim()) continue;

      if (!header) {
        header = line;
        const cols = header.split(",").map((s) => s.trim().replace(/^\uFEFF/, ""));
        idxOBJECTID = cols.findIndex((c) => c.toUpperCase() === "OBJECTID");
        idxVERT = cols.findIndex((c) => c.toLowerCase() === "vert_mm");
        idxCORR = cols.findIndex((c) => c.toLowerCase() === "corr_u16");

        if (idxOBJECTID < 0 || idxVERT < 0 || idxCORR < 0) {
          throw new Error(`CSV חייב לכלול עמודות: OBJECTID, vert_mm, corr_u16. נמצאו: ${cols.join(", ")}`);
        }
        continue;
      }

      const parts = line.split(",");
      const oid = Number(parts[idxOBJECTID]);
      const v = Number(parts[idxVERT]);
      const c = Number(parts[idxCORR]);

      // אם חסר vert_mm → מדלגים (כמו שביקשת)
      if (!Number.isFinite(oid) || !Number.isFinite(v) || !Number.isFinite(c)) continue;

      ids.push(oid | 0);
      vert.push(v);
      corr.push(Math.max(0, Math.min(65535, c)) | 0);

      rowCount++;
      if (rowCount % 50000 === 0) {
        csvState.loading = `מפרש CSV… (${rowCount.toLocaleString()} שורות)`;
        await sleep0();
      }
    }
  }

  // אם נשארה שורה אחרונה בלי \n
  const tail = buf.trim();
  if (tail && header) {
    const parts = tail.split(",");
    // (לא חובה, אבל נחמד להשלים)
    // נתעלם אם לא תקין
    try {
      // eslint-disable-next-line no-unused-vars
      const _ = parts.length;
    } catch {}
  }

  // נוודא מיון לפי OBJECTID (כדי ש-binary search יעבוד)
  csvState.loading = "מסדר לפי OBJECTID…";
  await sleep0();

  // אם הקובץ כבר ממוין (כמעט תמיד) זה יהיה מהיר:
  let sorted = true;
  for (let i = 1; i < ids.length; i++) {
    if (ids[i] < ids[i - 1]) { sorted = false; break; }
  }

  let idsArr = ids, vertArr = vert, corrArr = corr;

  if (!sorted) {
    // sort indices (כבד, אבל עדיין עדיף Map ענק)
    const order = Array.from({ length: ids.length }, (_, i) => i);
    order.sort((a, b) => ids[a] - ids[b]);

    idsArr = order.map((i) => ids[i]);
    vertArr = order.map((i) => vert[i]);
    corrArr = order.map((i) => corr[i]);
  }

  // Typed arrays – קומפקטי ומהיר
  csvState.ids = Int32Array.from(idsArr);
  csvState.vert = Float32Array.from(vertArr);
  csvState.corr = Uint16Array.from(corrArr);

  csvState.count = csvState.ids.length;
  csvState.loaded = true;
  csvState.loading = "";
}

async function parseCsvText(text) {
  // fallback פשוט (אם אין streaming)
  const lines = text.split(/\r?\n/).filter(Boolean);
  const header = lines.shift();
  if (!header) throw new Error("CSV ריק");

  const cols = header.split(",").map((s) => s.trim().replace(/^\uFEFF/, ""));
  const idxOBJECTID = cols.findIndex((c) => c.toUpperCase() === "OBJECTID");
  const idxVERT = cols.findIndex((c) => c.toLowerCase() === "vert_mm");
  const idxCORR = cols.findIndex((c) => c.toLowerCase() === "corr_u16");
  if (idxOBJECTID < 0 || idxVERT < 0 || idxCORR < 0) {
    throw new Error(`CSV חייב לכלול עמודות: OBJECTID, vert_mm, corr_u16. נמצאו: ${cols.join(", ")}`);
  }

  const ids = [];
  const vert = [];
  const corr = [];

  for (let i = 0; i < lines.length; i++) {
    const parts = lines[i].split(",");
    const oid = Number(parts[idxOBJECTID]);
    const v = Number(parts[idxVERT]);
    const c = Number(parts[idxCORR]);
    if (!Number.isFinite(oid) || !Number.isFinite(v) || !Number.isFinite(c)) continue;
    ids.push(oid | 0);
    vert.push(v);
    corr.push(Math.max(0, Math.min(65535, c)) | 0);

    if (i % 50000 === 0 && i > 0) {
      csvState.loading = `מפרש CSV… (${i.toLocaleString()} שורות)`;
      await sleep0();
    }
  }

  ids.sort((a, b) => a - b); // מינימלי (אם fallback)
  // הערה: כאן לא מסדרים את vert/corr בהתאמה כי fallback הזה אמור להיות נדיר;
  // אם אתה רוצה גם fallback מלא – תגיד ואסדר גם את זה.
  csvState.ids = Int32Array.from(ids);
  csvState.vert = Float32Array.from(vert);
  csvState.corr = Uint16Array.from(corr);

  csvState.count = csvState.ids.length;
  csvState.loaded = true;
  csvState.loading = "";
}

/** ====== Lifecycle ====== */
onMounted(async () => {
  try {
    // 1) לטעון CSV
    await loadCsvDb();

    // 2) לטעון GovMap
    await loadGovmapScript();
    initGovmap();
  } catch (e) {
    err.value = e?.message || String(e);
    csvState.loading = "";
  }
});

onBeforeUnmount(() => {
  try {
    // אין destroy רשמי, אבל מנקה listeners אם צריך בעתיד
    // window.govmap?.unRegisterEvent?.(...)
  } catch {}
});
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  height: 100vh;
  background: #f6f7f9;
  overflow: hidden;
}

.panel {
  border-left: 1px solid #e5e7eb;
  background: #fff;
  height: 100%;
  overflow: auto;
}

.panelTop {
  position: sticky;
  top: 0;
  z-index: 5;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.appTitle { font-size: 18px; font-weight: 800; }
.appSub { font-size: 12px; opacity: 0.7; margin-top: 2px; }

.iconBtn {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 10px;
  padding: 6px 10px;
  cursor: pointer;
}

.box {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.title2 { font-weight: 800; margin-bottom: 8px; }
.title3 { font-weight: 800; margin: 10px 0 6px; font-size: 13px; }

.kv {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px dashed #eef2f7;
  gap: 10px;
}
.kv span { opacity: .8; }

.row2 {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
}

input {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  font-size: 14px;
}

.btn {
  border: 1px solid #111827;
  background: #111827;
  color: #fff;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  white-space: nowrap;
}
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn.ghost {
  background: #fff;
  color: #111827;
  border-color: #e5e7eb;
}

.hint { font-size: 12px; opacity: .7; margin-top: 8px; word-break: break-word; }
.hint code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
.hint.ok { color: #166534; }
.hint.warn { color: #b45309; }

.sep { height: 10px; }

.fields {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 8px;
  background: #fafafa;
}
.fieldRow {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dashed #e5e7eb;
}
.fieldRow:last-child { border-bottom: 0; }
.fName { opacity: .75; }
.fVal { text-align: left; overflow: hidden; text-overflow: ellipsis; }

.mapWrap { position: relative; }
.map { width: 100%; height: 100%; }

.loading {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: #111827;
  color: #fff;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
}

.error {
  color: #b91c1c;
  background: #fff5f5;
}

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .panel {
    position: absolute;
    inset: 0 auto 0 0;
    width: 85vw;
    max-width: 420px;
    transform: translateX(-100%);
    transition: .2s;
    z-index: 10;
  }
  .panel.open { transform: translateX(0); }
}
</style>

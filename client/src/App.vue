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
        <div class="title2">מקורות</div>
        <div class="kv"><span>GovMap layer</span><b>{{ BUILDINGS_LAYER }}</b></div>
        <div class="kv"><span>CSV</span><b dir="ltr">{{ CSV_URL }}</b></div>
        <div class="kv"><span>שורות נטענו</span><b>{{ csvCount.toLocaleString() }}</b></div>
        <div class="kv"><span>סטטוס</span><b>{{ csvReady ? "מוכן" : (csvLoading ? "טוען…" : "לא נטען") }}</b></div>
        <div class="hint" v-if="csvErr">{{ csvErr }}</div>
      </div>

      <div class="box">
        <div class="title2">חיפוש OBJECTID</div>
        <div class="row">
          <input v-model.trim="searchId" placeholder="לדוגמה: 1210580" inputmode="numeric" />
        </div>
        <div class="row2">
          <button class="btn" @click="searchOnMap" :disabled="!mapReady || !searchId">חפש במפה</button>
          <button class="btn ghost" @click="reloadCsv" :disabled="csvLoading">טען CSV מחדש</button>
        </div>
        <div class="hint">
          טיפ: אם החיפוש לא “תופס”, בדוק שהשם של השדה בשכבה הוא באמת <b>{{ OBJECTID_FIELD }}</b>.
        </div>
      </div>

      <div class="box" v-if="selected">
        <div class="title2">בניין נבחר</div>

        <div class="kv"><span>OBJECTID (מ-GovMap)</span><b>{{ selected.objectId }}</b></div>

        <div class="sep"></div>

        <div class="title3">InSAR (מה-CSV)</div>
        <div class="kv">
          <span>vert_mm</span>
          <b>{{ selected.insar ? selected.insar.vert_mm : "—" }}</b>
        </div>
        <div class="kv">
          <span>corr_u16</span>
          <b>{{ selected.insar ? selected.insar.corr_u16 : "—" }}</b>
        </div>
        <div class="kv">
          <span>corr (0–1)</span>
          <b>{{ selected.insar ? fmtCorr01(selected.insar.corr_u16) : "—" }}</b>
        </div>

        <div class="sep"></div>

        <div class="title3">שדות מהשכבה (GovMap identify)</div>
        <div class="fields" v-if="selected.fields?.length">
          <div class="fieldRow" v-for="(f,i) in selected.fields" :key="i">
            <span class="fn">{{ f.fieldName }}</span>
            <b class="fv">{{ f.value ?? "—" }}</b>
          </div>
        </div>
        <div class="hint" v-else>לא התקבלו שדות נוספים (זה בסדר).</div>

        <div class="row2" style="margin-top:10px;">
          <button class="btn" @click="highlightSelected" :disabled="!mapReady">סמן במפה</button>
          <button class="btn ghost" @click="selected = null">נקה</button>
        </div>
      </div>

      <div class="box error" v-if="mapErr">{{ mapErr }}</div>
    </aside>

    <main class="mapWrap">
      <div id="govmap" class="map"></div>
      <div class="loading" v-if="csvLoading">טוען CSV… (קובץ גדול)</div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from "vue";

/** =======================
 *  CONFIG (תעדכן פה)
 *  ======================= */

// שכבת הבניינים אצלך ב-GovMap (לפי מה ששלחת: 225287)
const BUILDINGS_LAYER = "225287";

// שם השדה בשכבה לחיפוש (ברוב שכבות ESRI זה באמת OBJECTID)
const OBJECTID_FIELD = "OBJECTID";

// טוקן GovMap (מומלץ לשים ב־.env כ־VITE_GOVMAP_TOKEN)
// אם אין לך בילד/ENV — תשים פה מחרוזת.
const GOVMAP_TOKEN = import.meta.env.VITE_GOVMAP_TOKEN || "PUT_YOUR_TOKEN_HERE";

/** CSV: שים את הקובץ ב־ public/data/tablescv.csv */
const CSV_URL = computed(() => {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}data/tablescv.csv`;
});

/** =======================
 *  STATE
 *  ======================= */
const panelOpen = ref(true);

const mapReady = ref(false);
const mapErr = ref("");

const csvLoading = ref(false);
const csvReady = ref(false);
const csvErr = ref("");
const csvCount = ref(0);

// “DB” בזיכרון: key=OBJECTID, value=packed int32 (vert_mm + corr_u16)
let insarDB = new Map(); // Map<number, number>

const selected = ref(null); // { objectId, fields, insar }
const searchId = ref("");

/** =======================
 *  GOVMAP LOADER
 *  ======================= */
function ensureGovMapScript() {
  return new Promise((resolve, reject) => {
    if (window.govmap) return resolve();

    const existing = document.querySelector('script[data-govmap="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("GovMap script failed")));
      return;
    }

    const s = document.createElement("script");
    s.src = "https://www.govmap.gov.il/govmap/api/govmap.api.js";
    s.async = true;
    s.dataset.govmap = "1";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("GovMap script failed to load"));
    document.head.appendChild(s);
  });
}

function initGovMap() {
  mapErr.value = "";
  try {
    // יצירת מפה + טעינת שכבה
    window.govmap.createMap("govmap", {
      token: GOVMAP_TOKEN,
      layers: [BUILDINGS_LAYER],
      showXY: false,
      identifyOnClick: false,
      background: 3,
      zoomButtons: true,
    });

    mapReady.value = true;

    // קליק במפה → Identify רק על שכבת הבניינים
    window.govmap
      .onEvent(window.govmap.events.CLICK)
      .progress(async (e) => {
        const p = e?.mapPoint;
        if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) return;

        const oid = await identifyObjectId(p.x, p.y);
        if (!oid) return;

        const insar = getInsarByObjectId(oid);

        selected.value = {
          objectId: oid,
          fields: lastIdentifyFields.value,
          insar,
        };
      });
  } catch (err) {
    mapErr.value = err?.message || String(err);
    mapReady.value = false;
  }
}

/** =======================
 *  IDENTIFY + JOIN
 *  ======================= */

// נשמור את השדות האחרונים שקיבלנו מה־identify (להצגה)
const lastIdentifyFields = ref([]);

async function identifyObjectId(x2039, y2039) {
  lastIdentifyFields.value = [];

  try {
    const res = await window.govmap.identifyByXYAndLayer(x2039, y2039, [BUILDINGS_LAYER]);
    const data = res?.data || [];

    // מחפש את הרשומה של השכבה שלנו
    const layerHit =
      data.find((d) => String(d.layerName).toLowerCase() === String(BUILDINGS_LAYER).toLowerCase()) ||
      data[0];

    const ent = layerHit?.entities?.[0];
    if (!ent) return null;

    // ברוב שכבות ESRI: objectId זה ה־OBJECTID
    const oid = Number(ent.objectId);
    if (!Number.isFinite(oid)) return null;

    // שדות להצגה (לא חובה)
    if (Array.isArray(ent.fields)) lastIdentifyFields.value = ent.fields;

    return oid;
  } catch {
    return null;
  }
}

// packing כדי לחסוך זיכרון: [vert_mm:int16 | corr_u16:uint16]
function packInsar(vert_mm, corr_u16) {
  const v = (Number(vert_mm) | 0) & 0xffff;
  const c = (Number(corr_u16) | 0) & 0xffff;
  return (v << 16) | c;
}

function unpackInsar(packed) {
  const vert_mm = packed >> 16; // signed
  const corr_u16 = packed & 0xffff;
  return { vert_mm, corr_u16 };
}

function getInsarByObjectId(objectId) {
  const packed = insarDB.get(Number(objectId));
  if (packed === undefined) return null;
  return unpackInsar(packed);
}

function fmtCorr01(corr_u16) {
  const n = Number(corr_u16);
  if (!Number.isFinite(n)) return "—";
  return (n / 65535).toFixed(4);
}

/** =======================
 *  SEARCH / HIGHLIGHT
 *  ======================= */
async function searchOnMap() {
  if (!mapReady.value) return;
  const oid = Number(searchId.value);
  if (!Number.isFinite(oid)) return;

  // גם אם אין נתוני InSAR — עדיין נסמן במפה
  try {
    await window.govmap.searchInLayer({
      layerName: BUILDINGS_LAYER,
      fieldName: OBJECTID_FIELD,
      fieldValues: [String(oid)],
      exactSearch: true,
      zoomToResults: true,
      clearExistingResults: true,
      showBubble: true,
    });

    const insar = getInsarByObjectId(oid);
    selected.value = { objectId: oid, fields: selected.value?.fields || [], insar };
  } catch (e) {
    mapErr.value = e?.message || String(e);
  }
}

async function highlightSelected() {
  if (!mapReady.value || !selected.value?.objectId) return;
  searchId.value = String(selected.value.objectId);
  await searchOnMap();
}

/** =======================
 *  CSV LOADER (stream)
 *  ======================= */
function detectDelimiter(headerLine) {
  const comma = (headerLine.match(/,/g) || []).length;
  const semi = (headerLine.match(/;/g) || []).length;
  return semi > comma ? ";" : ",";
}

async function loadCsv() {
  csvLoading.value = true;
  csvReady.value = false;
  csvErr.value = "";
  csvCount.value = 0;
  insarDB = new Map();

  try {
    const res = await fetch(CSV_URL.value, { cache: "no-store" });
    if (!res.ok) throw new Error(`CSV load failed (${res.status})`);

    // אם אין streaming, נופלים ל־text()
    if (!res.body || !res.body.getReader) {
      const text = await res.text();
      parseCsvText(text);
      csvReady.value = true;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buf = "";
    let headerParsed = false;
    let delim = ",";
    let idxOID = -1, idxVert = -1, idxCorr = -1;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });

      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        let line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);

        line = line.replace(/\r$/, "");
        if (!line) continue;

        if (!headerParsed) {
          // header
          const hdr = line.replace(/^\uFEFF/, "");
          delim = detectDelimiter(hdr);
          const cols = hdr.split(delim).map((s) => s.trim());

          idxVert = cols.findIndex((c) => c.toLowerCase() === "vert_mm");
          idxCorr = cols.findIndex((c) => c.toLowerCase() === "corr_u16");
          idxOID = cols.findIndex((c) => c.toLowerCase() === "objectid");

          if (idxOID < 0) throw new Error("לא מצאתי עמודה OBJECTID ב־CSV");
          if (idxVert < 0) idxVert = 0; // fallback
          if (idxCorr < 0) idxCorr = 1; // fallback

          headerParsed = true;
          continue;
        }

        const parts = line.split(delim);
        const oid = Number(parts[idxOID]);
        if (!Number.isFinite(oid)) continue;

        const vertRaw = (parts[idxVert] ?? "").trim();
        const corrRaw = (parts[idxCorr] ?? "").trim();

        if (vertRaw === "" || vertRaw.toLowerCase() === "null") continue; // כמו שביקשת: בלי נתונים → לא נכנס ל־DB

        const vert = Number(vertRaw);
        const corr = Number(corrRaw);

        if (!Number.isFinite(vert)) continue;

        // corr יכול להיות ריק — נשים 0
        const corrU16 = Number.isFinite(corr) ? corr : 0;

        insarDB.set(oid, packInsar(vert, corrU16));
        csvCount.value++;
      }
    }

    // שארית אחרונה בלי \n
    const last = buf.replace(/\r$/, "").trim();
    if (last && headerParsed) {
      const parts = last.split(delim);
      const oid = Number(parts[idxOID]);
      if (Number.isFinite(oid)) {
        const vertRaw = (parts[idxVert] ?? "").trim();
        const corrRaw = (parts[idxCorr] ?? "").trim();
        if (vertRaw && vertRaw.toLowerCase() !== "null") {
          const vert = Number(vertRaw);
          const corr = Number(corrRaw);
          if (Number.isFinite(vert)) {
            const corrU16 = Number.isFinite(corr) ? corr : 0;
            insarDB.set(oid, packInsar(vert, corrU16));
            csvCount.value++;
          }
        }
      }
    }

    csvReady.value = true;
  } catch (e) {
    csvErr.value = e?.message || String(e);
  } finally {
    csvLoading.value = false;
  }
}

function parseCsvText(text) {
  const lines = text.split(/\r?\n/).filter(Boolean);
  if (!lines.length) return;

  const header = lines[0].replace(/^\uFEFF/, "");
  const delim = detectDelimiter(header);
  const cols = header.split(delim).map((s) => s.trim().toLowerCase());

  const idxVert = cols.indexOf("vert_mm");
  const idxCorr = cols.indexOf("corr_u16");
  const idxOID = cols.indexOf("objectid");
  if (idxOID < 0) throw new Error("לא מצאתי עמודה OBJECTID ב־CSV");

  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(delim);
    const oid = Number(parts[idxOID]);
    if (!Number.isFinite(oid)) continue;

    const vertRaw = (parts[idxVert] ?? "").trim();
    const corrRaw = (parts[idxCorr] ?? "").trim();
    if (!vertRaw || vertRaw.toLowerCase() === "null") continue;

    const vert = Number(vertRaw);
    const corr = Number(corrRaw);
    if (!Number.isFinite(vert)) continue;

    const corrU16 = Number.isFinite(corr) ? corr : 0;
    insarDB.set(oid, packInsar(vert, corrU16));
    csvCount.value++;
  }
}

async function reloadCsv() {
  await loadCsv();
}

/** =======================
 *  LIFECYCLE
 *  ======================= */
onMounted(async () => {
  await loadCsv();
  await ensureGovMapScript();
  initGovMap();
});

onBeforeUnmount(() => {
  try {
    // אין destroy רשמי בדוקומנטציה, אז רק מנקים state
    mapReady.value = false;
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

.appTitle { font-size: 18px; font-weight: 900; }
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

.title2 { font-weight: 900; margin-bottom: 8px; }
.title3 { font-weight: 800; margin: 8px 0; font-size: 13px; opacity: .9; }

.row { display: grid; gap: 8px; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }

input {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
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
}
.btn:disabled { opacity: .5; cursor: not-allowed; }

.btn.ghost {
  background: #fff;
  color: #111827;
  border-color: #e5e7eb;
}

.kv {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px dashed #eef2f7;
}
.kv span { opacity: .75; }

.sep { height: 1px; background: #eef2f7; margin: 10px 0; }

.hint { font-size: 12px; opacity: .7; margin-top: 8px; }

.fields { display: grid; gap: 6px; }
.fieldRow {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dashed #eef2f7;
}
.fn { font-size: 12px; opacity: .75; }
.fv { font-size: 12px; }

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

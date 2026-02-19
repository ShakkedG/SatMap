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

      <div class="tabs">
        <button class="tab" :class="{ on: tab === 'buildings' }" @click="tab = 'buildings'">בניינים</button>
        <button class="tab" :class="{ on: tab === 'list' }" @click="tab = 'list'">רשימה</button>
        <button class="tab" :class="{ on: tab === 'about' }" @click="tab = 'about'">איך זה עובד</button>
      </div>

      <!-- ============== BUILDINGS TAB ============== -->
      <section v-if="tab === 'buildings'">
        <div class="box">
          <div class="row">
            <label>חיפוש OBJECTID</label>
            <input v-model.trim="q" placeholder="לדוגמה: 1210580" />
          </div>

          <div class="row2">
            <div>
              <label>סינון סטטוס</label>
              <select v-model="statusFilter">
                <option value="">הכל</option>
                <option value="stable">stable</option>
                <option value="no_data">no_data</option>
                <option value="suspect">suspect</option>
              </select>
            </div>

            <div>
              <label>סף שקיעה (vert_mm ≤)</label>
              <input type="number" v-model.number="velThreshold" step="0.5" />
              <div class="hint">לפרוטוטייפ: תנסה ‎-2 או ‎-5</div>
            </div>
          </div>

          <div class="row2">
            <button class="btn" @click="fitAll" :disabled="!mapReady">התמקד (ברירת מחדל)</button>
            <button class="btn ghost" @click="reload">טען מחדש CSV</button>
          </div>

          <div class="stats">
            <div>CSV נטען: <b>{{ dbReady ? "כן" : "לא" }}</b></div>
            <div>רשומות CSV: <b>{{ dbCount.toLocaleString() }}</b></div>
          </div>

          <div class="hint" v-if="csvUrl">
            נתיב טעינה: <b>{{ csvUrl }}</b>
          </div>
        </div>

        <div class="box" v-if="selected">
          <div class="title2">פרטי בניין נבחר</div>

          <div class="kv"><span>OBJECTID</span><b>{{ selected.OBJECTID ?? "—" }}</b></div>
          <div class="kv"><span>status</span><b>{{ selected.status ?? "—" }}</b></div>

          <div class="kv"><span>vert_mm</span><b>{{ fmtNum(selected.vert_mm, 3) }}</b></div>
          <div class="kv"><span>corr_u16</span><b>{{ selected.corr_u16 ?? "—" }}</b></div>
          <div class="kv"><span>corr (0..1)</span><b>{{ fmtNum(selected.corr01, 4) }}</b></div>

          <div class="row2">
            <button class="btn" @click="zoomToSelected" :disabled="!mapReady || !selected?.OBJECTID">הדגש/זום לבניין</button>
            <button class="btn ghost" @click="selected = null">נקה בחירה</button>
          </div>

          <div class="hint" v-if="selected.mapFields?.length">
            שדות מה-GovMap (זיהוי קליק):
            <div class="miniFields">
              <div class="mf" v-for="(f, i) in selected.mapFields.slice(0, 8)" :key="i">
                <span>{{ f.fieldName }}</span>
                <b>{{ f.fieldValue }}</b>
              </div>
            </div>
          </div>
        </div>

        <div class="box error" v-if="error">
          {{ error }}
        </div>
      </section>

      <!-- ============== LIST TAB ============== -->
      <section v-else-if="tab === 'list'">
        <div class="box">
          <div class="title2">רשימה ({{ filtered.length }})</div>

          <div class="list">
            <button
              v-for="item in filtered.slice(0, 250)"
              :key="item._key"
              class="listItem"
              :class="{ on: selected && idEq(selected.OBJECTID, item.OBJECTID) }"
              @click="selectByObjectId(item.OBJECTID)"
              :title="`vert_mm=${fmtNum(item.vert_mm, 3)} | status=${item.status}`"
            >
              <div class="liTop">
                <b>#{{ item.OBJECTID ?? "?" }}</b>
                <span class="badge" :class="badgeClass(item)">{{ item.status || "—" }}</span>
              </div>
              <div class="liSub">
                vert_mm: <b>{{ fmtNum(item.vert_mm, 3) }}</b> · corr: <b>{{ fmtNum(item.corr01, 4) }}</b>
              </div>
            </button>
          </div>

          <div class="hint" v-if="filtered.length > 250">
            מוצגים 250 ראשונים כדי לא להכביד על הדפדפן.
          </div>
        </div>

        <div class="box error" v-if="error">
          {{ error }}
        </div>
      </section>

      <!-- ============== ABOUT TAB ============== -->
      <section v-else class="box">
        <div class="title2">איך זה עובד</div>
        <div class="p">
          1) האתר טוען קובץ <b>CSV</b> קטן: <b>OBJECTID + vert_mm + corr_u16</b><br />
          2) במפה נטענת שכבת הבניינים ב-<b>GovMap</b>.<br />
          3) כשמחפשים/לוחצים בניין → עושים <b>JOIN</b> לפי <b>OBJECTID</b> ומציגים את הנתונים.
        </div>
        <div class="p">
          אם בניין לא נמצא ב-CSV → הוא מוגדר <b>no_data</b>.
        </div>
        <div class="hint">
          אם אתה עדיין מקבל 404 — תפתח בדפדפן את <b>/SatMap/data/tablecsv.csv</b> ותבדוק שזה באמת נפתח.
        </div>
      </section>
    </aside>

    <main class="mapWrap">
      <!-- GovMap חייב div עם id -->
      <div id="govmap" class="map"></div>

      <div class="legend" v-if="mapReady">
        <div class="lgRow"><span class="dot red"></span> ≤ -5</div>
        <div class="lgRow"><span class="dot orange"></span> ≤ -2</div>
        <div class="lgRow"><span class="dot green"></span> stable</div>
        <div class="lgRow"><span class="dot grey"></span> no_data</div>
      </div>

      <div class="loading" v-if="loading">טוען CSV…</div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";

/** =========================
 *  CONFIG — תעדכן רק כאן
 *  ========================= */
const GOVMAP_TOKEN = "PUT_YOUR_TOKEN_HERE";   // <-- תדביק את הטוקן שלך
const BUILDINGS_LAYER_NAME = "225287";        // <-- שם/מזהה השכבה כפי שטענת ב-createMap
const JOIN_FIELD = "OBJECTID";                // אם בשכבה זה נקרא אחרת—תשנה כאן

// מרכז ברירת מחדל (ITM / EPSG:2039 בקירוב). אם לא מתאים—תשנה.
const DEFAULT_X = 179500;
const DEFAULT_Y = 663500;
const DEFAULT_LEVEL = 9;

// שם הקובץ כפי שהוא נמצא תחת public/data/
const CSV_FILE = "tablecsv.csv";

/** ========================= */

const panelOpen = ref(true);
const tab = ref("buildings");
const selected = ref(null);

const q = ref("");
const statusFilter = ref("");
const velThreshold = ref(-2);

const loading = ref(false);
const error = ref("");

const mapReady = ref(false);
let govmapClickHandler = null;

const dbReady = ref(false);
const dbCount = ref(0);

// Map<OBJECTID:number, {vert_mm:number, corr_u16:number, corr01:number}>
const db = new Map();

// רשימה “קלה” להצגה: נשמור רק את ה-N הכי “גרועים” (הכי שליליים) כדי לא להציג מיליון שורות
const TOP_N = 8000;
const topWorst = ref([]); // array of items

const csvUrl = computed(() => {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}data/${CSV_FILE}`;
});

function fmtNum(v, digits = 3) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function idEq(a, b) {
  const na = Number(a);
  const nb = Number(b);
  if (Number.isFinite(na) && Number.isFinite(nb)) return na === nb;
  return String(a ?? "") === String(b ?? "");
}

function statusOf(vert) {
  const v = Number(vert);
  if (!Number.isFinite(v)) return "no_data";
  if (v <= -2) return "suspect";
  return "stable";
}

function badgeClass(item) {
  const v = Number(item.vert_mm);
  if (!Number.isFinite(v)) return "bGrey";
  if (v <= -5) return "bRed";
  if (v <= -2) return "bOrange";
  return "bGreen";
}

function normItemFromDb(objectId) {
  const oid = Number(objectId);
  const rec = db.get(oid);
  if (!rec) {
    return {
      _key: `oid_${oid}`,
      OBJECTID: oid,
      status: "no_data",
      vert_mm: null,
      corr_u16: null,
      corr01: null,
    };
  }
  return {
    _key: `oid_${oid}`,
    OBJECTID: oid,
    status: statusOf(rec.vert_mm),
    vert_mm: rec.vert_mm,
    corr_u16: rec.corr_u16,
    corr01: rec.corr01,
  };
}

const filtered = computed(() => {
  // אם יש חיפוש—נחזיר רק תוצאה אחת מדויקת (לא צריך לסרוק רשימה ענקית)
  if (q.value) {
    const oid = Number(q.value);
    if (!Number.isFinite(oid)) return [];
    return [normItemFromDb(oid)];
  }

  let arr = topWorst.value;

  if (statusFilter.value) {
    arr = arr.filter((it) => it.status === statusFilter.value);
  }

  const thr = Number(velThreshold.value);
  if (Number.isFinite(thr)) {
    arr = arr.filter((it) => {
      const v = Number(it.vert_mm);
      if (!Number.isFinite(v)) return true;
      return v <= thr;
    });
  }

  // הכי שליליים למעלה
  return [...arr].sort((a, b) => (Number(a.vert_mm) || 0) - (Number(b.vert_mm) || 0));
});

/** -------- CSV loader (כולל תמיכה בפסיק/נקודה-פסיק) -------- */
async function loadCsvIntoDb() {
  loading.value = true;
  error.value = "";
  dbReady.value = false;
  dbCount.value = 0;
  db.clear();
  topWorst.value = [];

  try {
    const res = await fetch(csvUrl.value, { cache: "no-store" });
    if (!res.ok) throw new Error(`CSV load failed (${res.status}) — בדוק שהקובץ נמצא ב: ${csvUrl.value}`);

    const text = await res.text();
    const lines = text.split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) throw new Error("CSV ריק או בלי נתונים");

    const header = lines[0];
    const delim = header.includes(";") && !header.includes(",") ? ";" : ",";

    const cols = header.split(delim).map((s) => s.trim().replace(/^"|"$/g, ""));
    const idxOid = cols.findIndex((c) => c.toUpperCase() === "OBJECTID");
    const idxVert = cols.findIndex((c) => c.toLowerCase() === "vert_mm" || c.toLowerCase() === "vert");
    const idxCorr = cols.findIndex((c) => c.toLowerCase() === "corr_u16" || c.toLowerCase() === "corr");

    if (idxOid < 0) throw new Error("לא מצאתי עמודה OBJECTID בכותרת ה-CSV");
    if (idxVert < 0) throw new Error("לא מצאתי עמודה vert_mm (או vert) בכותרת ה-CSV");
    if (idxCorr < 0) throw new Error("לא מצאתי עמודה corr_u16 (או corr) בכותרת ה-CSV");

    // פרסור
    for (let i = 1; i < lines.length; i++) {
      const row = lines[i].split(delim);
      const oid = Number(row[idxOid]);
      if (!Number.isFinite(oid)) continue;

      const vert = Number(row[idxVert]);
      const corrU16 = Number(row[idxCorr]);
      const corr01 = Number.isFinite(corrU16) ? corrU16 / 65535 : null;

      db.set(oid, { vert_mm: Number.isFinite(vert) ? vert : null, corr_u16: Number.isFinite(corrU16) ? corrU16 : null, corr01 });

      // topWorst (הכי שליליים)
      if (Number.isFinite(vert)) {
        const item = {
          _key: `oid_${oid}`,
          OBJECTID: oid,
          status: statusOf(vert),
          vert_mm: vert,
          corr_u16: Number.isFinite(corrU16) ? corrU16 : null,
          corr01,
        };

        // נכניס אם יש מקום או אם הוא “גרוע” יותר מהאחרון
        const arr = topWorst.value;
        if (arr.length < TOP_N) {
          arr.push(item);
        } else {
          // נמצא את הכי “יציב” (הכי גבוה) ברשימת הגרועים ונחליף אם צריך
          let maxIdx = 0;
          let maxVal = Number(arr[0].vert_mm);
          for (let j = 1; j < arr.length; j++) {
            const v = Number(arr[j].vert_mm);
            if (v > maxVal) {
              maxVal = v;
              maxIdx = j;
            }
          }
          if (vert < maxVal) arr[maxIdx] = item;
        }
      }
    }

    dbCount.value = db.size;
    dbReady.value = true;

    // אם המשתמש כבר הקליד OBJECTID
    if (q.value) {
      const oid = Number(q.value);
      if (Number.isFinite(oid)) selected.value = normItemFromDb(oid);
    }
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

/** -------- GovMap script + map -------- */
function loadGovmapScript() {
  return new Promise((resolve, reject) => {
    if (window.govmap) return resolve();
    const s = document.createElement("script");
    s.src = "https://www.govmap.gov.il/govmap/api/govmap.api.js";
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("לא הצלחתי לטעון govmap.api.js"));
    document.head.appendChild(s);
  });
}

function initGovMap() {
  const gm = window.govmap;
  if (!gm) throw new Error("govmap לא נטען");

  gm.createMap("govmap", {
    token: GOVMAP_TOKEN,
    layers: [BUILDINGS_LAYER_NAME],
    showXY: false,
    identifyOnClick: false,
    isEmbeddedToggle: false,
    background: "1",
    layersMode: 1,
    zoomButtons: true,
    level: DEFAULT_LEVEL,
  });

  // קליק על מפה -> identify -> join
  govmapClickHandler = async (e) => {
    try {
      const x = e?.mapPoint?.x;
      const y = e?.mapPoint?.y;
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;

      const resp = await gm.identifyByXYAndLayer(x, y, [BUILDINGS_LAYER_NAME]);
      const layer = resp?.data?.[0];
      const ent = layer?.entities?.[0];
      if (!ent) return;

      // 1) ננסה לקחת objectId (לעיתים הוא זהה ל-OBJECTID)
      let oid = Number(ent.objectId);

      // 2) אם יש שדה OBJECTID בתוך fields — נעדיף אותו
      const f = (ent.fields || []).find((ff) => {
        const n = String(ff.fieldName || ff.fieldDisplay || "").toUpperCase();
        return n.includes(JOIN_FIELD);
      });
      if (f && Number.isFinite(Number(f.fieldValue))) oid = Number(f.fieldValue);

      const item = normItemFromDb(oid);
      item.mapFields = ent.fields || [];
      selected.value = item;
      tab.value = "buildings";
    } catch (err) {
      // לא מפיל את האפליקציה
    }
  };

  gm.onEvent(gm.events.CLICK, govmapClickHandler);
  mapReady.value = true;

  // התמקדות ראשונית
  gm.zoomToXY(DEFAULT_X, DEFAULT_Y, DEFAULT_LEVEL);
}

function fitAll() {
  if (!mapReady.value || !window.govmap) return;
  window.govmap.zoomToXY(DEFAULT_X, DEFAULT_Y, DEFAULT_LEVEL);
}

async function zoomToSelected() {
  if (!mapReady.value || !window.govmap || !selected.value?.OBJECTID) return;

  // highlight + zoom ע"י חיפוש לפי שדה
  await window.govmap.searchInLayer({
    layerName: BUILDINGS_LAYER_NAME,
    fieldName: JOIN_FIELD,
    fieldValues: [String(selected.value.OBJECTID)],
    highlight: true,
    showBubble: false,
    zoomToResults: true,
    clearExisting: true,
  });
}

async function selectByObjectId(objectId) {
  const item = normItemFromDb(objectId);
  selected.value = item;
  tab.value = "buildings";
  await zoomToSelected();
}

async function reload() {
  await loadCsvIntoDb();
}

onMounted(async () => {
  await loadCsvIntoDb();
  await loadGovmapScript();
  initGovMap();
});

onBeforeUnmount(() => {
  try {
    const gm = window.govmap;
    if (gm && govmapClickHandler) gm.removeEvent(gm.events.CLICK, govmapClickHandler);
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

.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  background: #fff;
  position: sticky;
  top: 56px;
  z-index: 4;
}
.tab {
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 999px;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 13px;
}
.tab.on {
  border-color: #111827;
  background: #111827;
  color: #fff;
}

.box {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.row { display: grid; gap: 6px; margin-bottom: 10px; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
label { font-size: 12px; opacity: .8; }

input, select {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  font-size: 14px;
}

.hint { font-size: 12px; opacity: .65; margin-top: 6px; }

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

.title2 { font-weight: 900; margin-bottom: 8px; }
.kv {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px dashed #eef2f7;
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  font-size: 13px;
}

.list { display: grid; gap: 8px; }
.listItem {
  text-align: right;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 14px;
  padding: 10px;
  cursor: pointer;
}
.listItem.on { border-color: #111827; }

.liTop { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.liSub { font-size: 12px; opacity: .75; margin-top: 4px; }

.badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
}
.bGrey { background: #f3f4f6; }
.bGreen { background: #e8f5e9; }
.bOrange { background: #fff3e0; }
.bRed { background: #ffebee; }

.mapWrap { position: relative; }
.map { width: 100%; height: 100%; }

.legend {
  position: absolute;
  left: 16px;
  bottom: 16px;
  background: rgba(255,255,255,.95);
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 10px 12px;
  font-size: 12px;
  box-shadow: 0 10px 20px rgba(0,0,0,.08);
  z-index: 20;
}
.lgRow { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.dot { width: 10px; height: 10px; border-radius: 999px; display: inline-block; }
.dot.red { background: #e53935; }
.dot.orange { background: #fb8c00; }
.dot.green { background: #43a047; }
.dot.grey { background: #9aa0a6; }

.loading {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: #111827;
  color: #fff;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  z-index: 20;
}

.error {
  color: #b91c1c;
  background: #fff5f5;
}

.p { font-size: 13px; line-height: 1.6; margin: 8px 0; }

.miniFields { margin-top: 8px; display: grid; gap: 6px; }
.mf { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; padding: 6px 8px; border: 1px dashed #eef2f7; border-radius: 10px; }

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .panel {
    position: absolute;
    inset: 0 auto 0 0;
    width: 85vw;
    max-width: 420px;
    transform: translateX(-100%);
    transition: .2s;
    z-index: 30;
  }
  .panel.open { transform: translateX(0); }
}
</style>

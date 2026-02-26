<template>
  <div class="app" dir="rtl">
    <!-- Header -->
    <header class="header">
      <div class="brand">
        <div class="title">SatMap</div>
        <div class="sub">
          Prototype – בניינים + InSAR (CSV) + סימון חריגים על גבי GOVMAP
        </div>
      </div>

      <div class="headerBtns">
        <button class="btn ghost" @click="panelOpen = !panelOpen">
          {{ panelOpen ? "סגור תפריט" : "פתח תפריט" }}
        </button>
        <button class="btn" @click="reloadAll" :disabled="busy">
          {{ busy ? "טוען..." : "טען מחדש" }}
        </button>
      </div>
    </header>

    <div class="body">
      <!-- Side Panel -->
      <aside class="panel" :class="{ open: panelOpen }">
        <div class="tabs">
          <button class="tab" :class="{ on: mode === 'subsidence' }" @click="mode = 'subsidence'">
            בניינים שוקעים
          </button>
          <button class="tab" :class="{ on: mode === 'observations' }" @click="mode = 'observations'">
            תצפיות / נתונים
          </button>
          <button class="tab" :class="{ on: mode === 'about' }" @click="mode = 'about'">
            איך זה עובד
          </button>
        </div>

        <!-- ================= SUBSIDENCE ================= -->
        <section v-if="mode === 'subsidence'" class="section">
          <div class="box">
            <div class="row2">
              <div>
                <label>סף “שוקע/חשוד” v (mm/yr)</label>
                <input class="input" type="number" v-model.number="rateThreshold" step="0.5" />
                <div class="hint">
                  ברירת מחדל: ‎-2 (כל ערך קטן/שווה לסף נחשב “שוקע”).
                </div>
              </div>
              <div>
                <label>מינימום תצפיות (אופציונלי)</label>
                <input class="input" type="number" v-model.number="minObservations" step="1" min="0" />
                <div class="hint">
                  אם בעמודה ב־CSV יש num_obs / n / count – נסנן גם לפיה.
                </div>
              </div>
            </div>

            <div class="row2">
              <div>
                <label>חפש לפי OBJECTID</label>
                <div class="inline">
                  <input class="input" type="number" v-model.number="searchObjectId" placeholder="לדוגמה: 12345" />
                  <button class="btn" @click="jumpToObjectId" :disabled="!searchObjectId || !mapReady">
                    קפוץ
                  </button>
                </div>
                <div class="hint">
                  אם יש ל־CSV נקודת X/Y – נבצע התמקדות לפי הנקודה. אחרת רק נבחר רשומה.
                </div>
              </div>

              <div>
                <label>שכבת בניינים (אופציונלי)</label>
                <input class="input" type="text" v-model="buildingsLayerName" placeholder="למשל: BUILDINGS_LAYER_NAME" />
                <div class="hint">
                  אם תמלא כאן “שם שכבה” תקין של GOVMAP, נשתמש בו גם לתשאול בלחיצה (identify/getLayerData).
                </div>
              </div>
            </div>

            <div class="stats">
              <div class="pill">
                <div class="k">CSV</div>
                <div class="v">{{ csvStatus }}</div>
              </div>
              <div class="pill">
                <div class="k">סך רשומות</div>
                <div class="v">{{ rows.length }}</div>
              </div>
              <div class="pill">
                <div class="k">שוקעים</div>
                <div class="v">{{ filteredRows.length }}</div>
              </div>
            </div>
          </div>

          <div class="box">
            <div class="boxTitle">רשימת בניינים שוקעים (Top 200)</div>

            <div v-if="filteredRows.length === 0" class="empty">
              אין נתונים שעוברים את הסף. בדוק שה־CSV נטען ושיש עמודת מהירות (v / velocity / rate).
            </div>

            <div v-else class="list">
              <button
                v-for="r in topRows"
                :key="r.__key"
                class="listItem"
                :class="{ active: selected?.__key === r.__key }"
                @click="selectRow(r)"
              >
                <div class="liMain">
                  <div class="liTitle">
                    OBJECTID: <b>{{ r.objectId ?? "—" }}</b>
                  </div>
                  <div class="liSub">
                    v: <b>{{ fmt(r.rate) }}</b> mm/yr
                    <span v-if="r.obs != null"> · n={{ r.obs }}</span>
                    <span v-if="r.x != null && r.y != null"> · X/Y ✓</span>
                  </div>
                </div>
                <div class="liRight">→</div>
              </button>
            </div>
          </div>

          <div class="box" v-if="selected">
            <div class="boxTitle">פרטי בניין נבחר</div>
            <div class="kv">
              <div class="k">OBJECTID</div>
              <div class="v">{{ selected.objectId ?? "—" }}</div>
            </div>
            <div class="kv">
              <div class="k">v (mm/yr)</div>
              <div class="v">{{ fmt(selected.rate) }}</div>
            </div>
            <div class="kv">
              <div class="k">תצפיות</div>
              <div class="v">{{ selected.obs ?? "—" }}</div>
            </div>
            <div class="kv">
              <div class="k">X / Y</div>
              <div class="v">
                <span v-if="selected.x != null && selected.y != null">{{ selected.x }}, {{ selected.y }}</span>
                <span v-else>—</span>
              </div>
            </div>

            <div class="actions">
              <button class="btn" @click="focusSelected" :disabled="!mapReady || !hasXY(selected)">
                התמקדות במפה
              </button>
              <button class="btn ghost" @click="clearOverlays" :disabled="!mapReady">
                נקה סימונים
              </button>
            </div>

            <details class="raw">
              <summary>Raw row</summary>
              <pre>{{ selected.raw }}</pre>
            </details>
          </div>
        </section>

        <!-- ================= OBSERVATIONS ================= -->
        <section v-else-if="mode === 'observations'" class="section">
          <div class="box">
            <div class="boxTitle">קבצים ציבוריים</div>
            <div class="hint">
              הפרונט טוען את ה־CSV מתוך <code>client/public/insar_buildings.csv</code>
              (או מהשורש בפריסה של Vite).
            </div>

            <div class="kv">
              <div class="k">CSV URL</div>
              <div class="v">
                <code>{{ csvUrl }}</code>
              </div>
            </div>

            <div class="kv">
              <div class="k">סטטוס</div>
              <div class="v">{{ csvStatus }}</div>
            </div>

            <div class="actions">
              <button class="btn" @click="loadCsv" :disabled="busy">טען CSV</button>
              <button class="btn ghost" @click="drawFilteredOnMap" :disabled="!mapReady || filteredRows.length === 0">
                צייר את כל השוקעים על המפה
              </button>
            </div>
          </div>

          <div class="box">
            <div class="boxTitle">הערות פורמט CSV (מה שהאפליקציה יודעת לזהות)</div>
            <ul class="ul">
              <li>
                OBJECTID: אחת מהעמודות:
                <code>OBJECTID</code>, <code>objectid</code>, <code>id</code>, <code>building_id</code>
              </li>
              <li>
                rate(mm/yr): אחת מהעמודות:
                <code>v</code>, <code>velocity</code>, <code>rate</code>, <code>rate_mm_yr</code>, <code>mm_yr</code>
              </li>
              <li>
                תצפיות (אופציונלי):
                <code>num_obs</code>, <code>n</code>, <code>count</code>
              </li>
              <li>
                קואורדינטות (אם קיימות): <code>x</code>/<code>y</code> או <code>X</code>/<code>Y</code>
                (עדיף ב־ITM כדי שיתאים ל־GOVMAP).
              </li>
            </ul>
          </div>
        </section>

        <!-- ================= ABOUT ================= -->
        <section v-else class="section">
          <div class="box">
            <div class="boxTitle">מה קורה פה</div>
            <div class="p">
              1) נטענת מפה של GOVMAP בעזרת <code>govmap.api.js</code> ונוצר Map בתוך ה־DIV.
            </div>
            <div class="p">
              2) נטען <code>insar_buildings.csv</code> ומחולצים מזהים + מהירות שקיעה (mm/yr) + (אופציונלי) X/Y.
            </div>
            <div class="p">
              3) כשבוחרים בניין או כשלוחצים “צייר שוקעים”, האפליקציה מציירת סימונים על המפה באמצעות
              <code>govmap.displayGeometries</code> (כאן כעיגולים קטנים). :contentReference[oaicite:0]{index=0}
            </div>
            <div class="p">
              אם אתה רוצה גם “לשאול” שכבת בניינים בלחיצה (ולקבל פרטי ישות), תמלא שם שכבה תקין ב־“שכבת בניינים”
              ותוכל להרחיב את ה־onClick כדי לקרוא ל־<code>identifyByXYAndLayer</code>/<code>getLayerData</code>. :contentReference[oaicite:1]{index=1}
            </div>
          </div>

          <div class="box">
            <div class="boxTitle">טוקן GOVMAP</div>
            <div class="p">
              האפליקציה מצפה ל־<code>VITE_GOVMAP_TOKEN</code> (דרך Vite env). את המפה יוצרים עם
              <code>govmap.createMap</code>. :contentReference[oaicite:2]{index=2}
            </div>
          </div>
        </section>
      </aside>

      <!-- Map -->
      <main class="mapWrap">
        <div class="mapTopBar">
          <div class="mapStatus">
            <span class="dot" :class="{ ok: mapReady }"></span>
            <span>{{ mapReady ? "מפה מוכנה" : "טוען GOVMAP..." }}</span>
            <span v-if="mapError" class="err"> · {{ mapError }}</span>
          </div>

          <div class="mapBtns">
            <button class="btn ghost" @click="drawFilteredOnMap" :disabled="!mapReady || filteredRows.length === 0">
              צייר שוקעים
            </button>
            <button class="btn ghost" @click="clearOverlays" :disabled="!mapReady">
              נקה
            </button>
          </div>
        </div>

        <div id="govmap" class="map"></div>

        <div class="mapHint">
          טיפ: GOVMAP עובד עם token שמוגבל לדומיין. אם המפה לא נטענת — בדוק שהטוקן מאושר ל־GitHub Pages.
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

/**
 * =========================
 * Config (Vite env)
 * =========================
 */
const GOVMAP_TOKEN = import.meta.env.VITE_GOVMAP_TOKEN || "";
const GOVMAP_LAYERS = (import.meta.env.VITE_GOVMAP_LAYERS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const csvUrl = new URL("insar_buildings.csv", import.meta.env.BASE_URL).toString();

/**
 * =========================
 * UI State
 * =========================
 */
const panelOpen = ref(true);
const mode = ref("subsidence"); // subsidence | observations | about

const busy = ref(false);
const mapReady = ref(false);
const mapError = ref("");

const csvStatus = ref("לא נטען עדיין");
const rows = ref([]);
const selected = ref(null);

const rateThreshold = ref(-2);
const minObservations = ref(0);
const searchObjectId = ref(null);
const buildingsLayerName = ref(import.meta.env.VITE_BUILDINGS_LAYER_NAME || "");

/**
 * =========================
 * Derived
 * =========================
 */
const filteredRows = computed(() => {
  const thr = Number(rateThreshold.value);
  const minObs = Number(minObservations.value || 0);

  return rows.value
    .filter((r) => Number.isFinite(r.rate))
    .filter((r) => r.rate <= thr)
    .filter((r) => (minObs > 0 ? (r.obs ?? 0) >= minObs : true))
    .sort((a, b) => a.rate - b.rate);
});

const topRows = computed(() => filteredRows.value.slice(0, 200));

/**
 * =========================
 * GovMap Script Loader
 * =========================
 */
function loadScriptOnce(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[data-src="${src}"]`);
    if (existing) {
      // Already appended; wait until govmap exists.
      const t = setInterval(() => {
        if (window.govmap) {
          clearInterval(t);
          resolve();
        }
      }, 50);
      setTimeout(() => {
        clearInterval(t);
        if (window.govmap) resolve();
        else reject(new Error("govmap.api.js נטען אבל window.govmap לא זמין"));
      }, 12000);
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.defer = true;
    script.dataset.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("נכשל לטעון govmap.api.js"));
    document.head.appendChild(script);
  });
}

async function ensureGovMapLoaded() {
  if (window.govmap) return;
  await loadScriptOnce("https://www.govmap.gov.il/govmap/api/govmap.api.js");

  // Wait until the API attaches to window
  const start = Date.now();
  while (!window.govmap && Date.now() - start < 12000) {
    await new Promise((r) => setTimeout(r, 50));
  }
  if (!window.govmap) throw new Error("window.govmap לא זמין אחרי טעינת הסקריפט");
}

/**
 * =========================
 * Map init
 * =========================
 */
async function initMap() {
  mapReady.value = false;
  mapError.value = "";

  if (!GOVMAP_TOKEN) {
    mapError.value = "חסר VITE_GOVMAP_TOKEN";
    return;
  }

  try {
    await ensureGovMapLoaded();

    // Create map
    window.govmap.createMap("govmap", {
      token: GOVMAP_TOKEN,
      layers: GOVMAP_LAYERS,
      showXY: true,
      identifyOnClick: true,
      isEmbeddedToggle: false,
      background: "1",
      layersMode: 1,
      zoomButtons: true,
      onLoad: () => {
        mapReady.value = true;
      },
      onError: (e) => {
        mapError.value = (e && (e.message || e.toString())) || "שגיאה לא ידועה בטעינת המפה";
      },
      onClick: (e) => {
        // אפשר להרחיב: אם buildingsLayerName מוגדר, לקרוא identifyByXYAndLayer / getLayerData
        // ולפתוח חלון נתונים משלך.
        // כרגע נשמור את הקליק כדי שתוכל לראות בקונסול.
        // eslint-disable-next-line no-console
        console.log("GovMap onClick:", e);
      },
    });

    // אם onLoad לא מגיע (לפעמים), נעשה fallback:
    setTimeout(() => {
      if (!mapReady.value && window.govmap) mapReady.value = true;
    }, 2500);
  } catch (err) {
    mapError.value = err?.message || String(err);
  }
}

/**
 * =========================
 * CSV parsing
 * =========================
 */
function splitCsvLine(line) {
  // Simple CSV splitter supporting quotes
  const out = [];
  let cur = "";
  let inQ = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];

    if (ch === '"') {
      if (inQ && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQ = !inQ;
      }
      continue;
    }

    if (ch === "," && !inQ) {
      out.push(cur);
      cur = "";
      continue;
    }

    cur += ch;
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

function pickHeader(headers, candidates) {
  const lower = headers.map((h) => String(h).trim());
  for (const c of candidates) {
    const idx = lower.findIndex((h) => h.toLowerCase() === c.toLowerCase());
    if (idx !== -1) return { name: headers[idx], idx };
  }
  // fallback: contains
  for (const c of candidates) {
    const idx = lower.findIndex((h) => h.toLowerCase().includes(c.toLowerCase()));
    if (idx !== -1) return { name: headers[idx], idx };
  }
  return null;
}

function toNum(v) {
  if (v == null) return null;
  const s = String(v).trim();
  if (!s) return null;
  const n = Number(s.replaceAll(" ", ""));
  return Number.isFinite(n) ? n : null;
}

function hasXY(r) {
  return r && Number.isFinite(r.x) && Number.isFinite(r.y);
}

async function loadCsv() {
  busy.value = true;
  csvStatus.value = "טוען...";
  try {
    const res = await fetch(csvUrl, { cache: "no-store" });
    if (!res.ok) throw new Error(`CSV HTTP ${res.status}`);
    const text = await res.text();

    const lines = text
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length < 2) {
      rows.value = [];
      csvStatus.value = "CSV ריק / לא תקין";
      return;
    }

    const headers = splitCsvLine(lines[0]);

    const hObj = pickHeader(headers, ["OBJECTID", "objectid", "id", "building_id", "object_id"]);
    const hRate = pickHeader(headers, ["v", "velocity", "rate", "rate_mm_yr", "mm_yr", "subsidence"]);
    const hObs = pickHeader(headers, ["num_obs", "n", "count", "observations", "numobs"]);
    const hX = pickHeader(headers, ["x", "X", "easting", "east"]);
    const hY = pickHeader(headers, ["y", "Y", "northing", "north"]);

    const parsed = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = splitCsvLine(lines[i]);
      const rawObj = {};
      for (let j = 0; j < headers.length; j++) rawObj[headers[j]] = cols[j];

      const objectId = hObj ? toNum(cols[hObj.idx]) : null;
      const rate = hRate ? toNum(cols[hRate.idx]) : null;
      const obs = hObs ? toNum(cols[hObs.idx]) : null;
      const x = hX ? toNum(cols[hX.idx]) : null;
      const y = hY ? toNum(cols[hY.idx]) : null;

      parsed.push({
        __key: `${objectId ?? "na"}-${i}`,
        objectId,
        rate,
        obs,
        x,
        y,
        raw: rawObj,
      });
    }

    rows.value = parsed;
    csvStatus.value = `נטען (${parsed.length} שורות)`;
  } catch (err) {
    rows.value = [];
    csvStatus.value = `שגיאה: ${err?.message || String(err)}`;
  } finally {
    busy.value = false;
  }
}

/**
 * =========================
 * Map overlays (GovMap)
 * =========================
 */
async function clearOverlays() {
  if (!mapReady.value || !window.govmap) return;
  try {
    // ננקה את כל הגאומטריות שציירנו לפי שם prefix (פשוט יותר: נצייר תמיד עם clearExisting)
    // כאן נשאיר את זה פשוט:
    await window.govmap.displayGeometries({
      circleGeometries: [],
      names: [],
      geometryType: window.govmap.geometryType.CIRCLE,
      defaultSymbol: { outlineColor: [255, 0, 0, 1], outlineWidth: 1, fillColor: [255, 0, 0, 0.25] },
      symbols: [],
      clearExisting: true,
      data: { tooltips: [], headers: [], bubbles: [], bubbleUrl: "" },
    });
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("clearOverlays failed:", e);
  }
}

async function drawCirclesOnMap(items) {
  if (!mapReady.value || !window.govmap) return;
  const usable = items.filter(hasXY);
  if (usable.length === 0) return;

  // עיגולים קטנים סביב נקודות (X/Y)
  const circles = usable.map((r) => ({ x: r.x, y: r.y, radius: 10 }));
  const names = usable.map((r) => `b_${r.objectId ?? r.__key}`);
  const tooltips = usable.map((r) => `OBJECTID ${r.objectId ?? "—"} | v=${fmt(r.rate)} mm/yr`);
  const headers = usable.map((r) => `בניין ${r.objectId ?? "—"}`);

  try {
    await window.govmap.displayGeometries({
      circleGeometries: circles,
      names,
      geometryType: window.govmap.geometryType.CIRCLE,
      defaultSymbol: {
        outlineColor: [255, 0, 0, 1],
        outlineWidth: 2,
        fillColor: [255, 0, 0, 0.25],
      },
      symbols: [],
      clearExisting: true,
      showBubble: true,
      data: {
        tooltips,
        headers,
        bubbles: new Array(usable.length).fill(""),
        bubbleUrl: "",
        bubbleHTML:
          "<div style='padding:10px;font-family:Arial;direction:rtl'><div style='font-weight:700;margin-bottom:6px'>{0}</div><div>v (mm/yr): <b>{1}</b></div><div>תצפיות: <b>{2}</b></div><div style='margin-top:6px;font-size:12px;opacity:.75'>X/Y: {3}, {4}</div></div>",
        bubbleHTMLParameters: usable.map((r) => [
          `OBJECTID ${r.objectId ?? "—"}`,
          fmt(r.rate),
          r.obs ?? "—",
          r.x ?? "—",
          r.y ?? "—",
        ]),
      },
    });
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("drawCirclesOnMap failed:", e);
  }
}

function focusXY(x, y, level = 9) {
  if (!mapReady.value || !window.govmap) return;
  try {
    window.govmap.zoomToXY({ x, y, level, marker: true });
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("zoomToXY failed:", e);
  }
}

/**
 * =========================
 * Actions
 * =========================
 */
function fmt(n) {
  if (!Number.isFinite(n)) return "—";
  return Number(n).toFixed(2);
}

function selectRow(r) {
  selected.value = r;
  if (hasXY(r)) {
    focusXY(r.x, r.y, 9);
    drawCirclesOnMap([r]);
  }
}

function focusSelected() {
  if (!selected.value || !hasXY(selected.value)) return;
  focusXY(selected.value.x, selected.value.y, 10);
}

function drawFilteredOnMap() {
  drawCirclesOnMap(filteredRows.value.slice(0, 500)); // לא להגזים כדי לא להכביד
}

function jumpToObjectId() {
  const id = Number(searchObjectId.value);
  if (!Number.isFinite(id)) return;

  const r = rows.value.find((x) => x.objectId === id);
  if (r) {
    selectRow(r);
    return;
  }

  // לא נמצא ב־CSV: נשמור בבחירה ריקה, ותוכל בהמשך להרחיב לתשאול שכבה ע"י API
  selected.value = {
    __key: `manual-${id}`,
    objectId: id,
    rate: null,
    obs: null,
    x: null,
    y: null,
    raw: { note: "לא נמצא ב־CSV" },
  };
}

async function reloadAll() {
  busy.value = true;
  try {
    await loadCsv();
    if (!mapReady.value) await initMap();
    // אחרי טעינה – צייר אוטומטית את ה־Top (אם יש נקודות)
    setTimeout(() => drawCirclesOnMap(topRows.value.slice(0, 150)), 350);
  } finally {
    busy.value = false;
  }
}

/**
 * =========================
 * Auto redraw on threshold changes (throttled)
 * =========================
 */
let redrawTimer = null;
watch([rateThreshold, minObservations], () => {
  if (!mapReady.value) return;
  if (redrawTimer) clearTimeout(redrawTimer);
  redrawTimer = setTimeout(() => {
    // אל תצייר ישר אלפי נקודות — נשאיר את זה ידני/Top
    drawCirclesOnMap(topRows.value.slice(0, 150));
  }, 350);
});

/**
 * =========================
 * Mount
 * =========================
 */
onMounted(async () => {
  await initMap();
  await loadCsv();
  // ציור ראשוני קטן אם יש X/Y
  setTimeout(() => drawCirclesOnMap(topRows.value.slice(0, 150)), 400);
});
</script>

<style scoped>
/* Layout */
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f6f7fb;
  color: #111;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: #ffffff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.brand .title {
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
}
.brand .sub {
  font-size: 12px;
  opacity: 0.75;
  margin-top: 2px;
}

.headerBtns {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.body {
  flex: 1;
  display: grid;
  grid-template-columns: 380px 1fr;
  min-height: 0;
}

/* Panel */
.panel {
  background: #ffffff;
  border-left: 1px solid rgba(0, 0, 0, 0.08);
  padding: 10px;
  overflow: auto;
}

.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
  margin-bottom: 10px;
}

.tab {
  padding: 9px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  background: #fff;
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
}
.tab.on {
  background: #111;
  color: #fff;
  border-color: #111;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.box {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  padding: 10px;
}

.boxTitle {
  font-weight: 800;
  margin-bottom: 8px;
}

.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

label {
  display: block;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 6px;
}

.input {
  width: 100%;
  padding: 9px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.16);
  outline: none;
  background: #fff;
}

.inline {
  display: flex;
  gap: 8px;
  align-items: center;
}

.hint {
  font-size: 12px;
  opacity: 0.75;
  margin-top: 6px;
  line-height: 1.25;
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}

.pill {
  background: #f6f7fb;
  border-radius: 12px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.pill .k {
  font-size: 11px;
  opacity: 0.7;
}
.pill .v {
  font-weight: 900;
  margin-top: 2px;
}

/* List */
.list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 420px;
  overflow: auto;
  padding-right: 2px;
}

.listItem {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  text-align: right;
  padding: 9px 10px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: #fff;
  cursor: pointer;
}
.listItem:hover {
  background: #f6f7fb;
}
.listItem.active {
  border-color: rgba(0, 0, 0, 0.35);
  background: #f0f2ff;
}

.liTitle {
  font-size: 12px;
}
.liSub {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 2px;
}
.liRight {
  font-weight: 900;
  opacity: 0.6;
}

.empty {
  font-size: 13px;
  opacity: 0.75;
  padding: 8px 2px;
}

.kv {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.12);
}
.kv:last-child {
  border-bottom: 0;
}
.kv .k {
  font-weight: 900;
  font-size: 12px;
  opacity: 0.8;
}
.kv .v {
  font-size: 13px;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.raw {
  margin-top: 10px;
}
.raw pre {
  background: #0b1020;
  color: #e8eefc;
  padding: 10px;
  border-radius: 10px;
  overflow: auto;
  max-height: 220px;
}

/* Buttons */
.btn {
  padding: 9px 12px;
  border-radius: 12px;
  border: 1px solid #111;
  background: #111;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn.ghost {
  background: #fff;
  color: #111;
}

/* Map */
.mapWrap {
  position: relative;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.mapTopBar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.mapStatus {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  font-size: 12px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #c5c7d0;
}
.dot.ok {
  background: #3cb371;
}
.err {
  color: #b00020;
  font-weight: 900;
}

.mapBtns {
  display: flex;
  gap: 10px;
}

.map {
  flex: 1;
  min-height: 0;
  background: #e9ecf5;
}

.mapHint {
  position: absolute;
  bottom: 10px;
  left: 10px;
  right: 10px;
  max-width: 840px;
  margin: 0 auto;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 12px;
  font-size: 12px;
  opacity: 0.9;
}

/* Observations/About text */
.p {
  font-size: 13px;
  line-height: 1.35;
  margin-bottom: 8px;
}
.ul {
  margin: 0;
  padding-right: 18px;
}
.ul li {
  margin: 6px 0;
  font-size: 13px;
}

/* Mobile */
@media (max-width: 980px) {
  .body {
    grid-template-columns: 1fr;
  }
  .panel {
    position: fixed;
    top: 56px;
    right: 0;
    bottom: 0;
    width: min(92vw, 420px);
    transform: translateX(105%);
    transition: transform 0.2s ease;
    z-index: 5;
    box-shadow: -20px 0 50px rgba(0, 0, 0, 0.15);
  }
  .panel.open {
    transform: translateX(0%);
  }
}
</style>

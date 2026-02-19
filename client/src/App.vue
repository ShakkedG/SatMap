<template>
  <div class="app" dir="rtl">
    <!-- ===== Header (CrimesMap-ish) ===== -->
    <header class="topbar">
      <div class="brand">
        <div class="title">SatMap</div>
        <div class="subtitle">Buildings (GovMap) + CSV Join + חריגים</div>
      </div>

      <div class="top-actions">
        <button class="btn ghost" @click="panelOpen = !panelOpen" :title="panelOpen ? 'סגור פאנל' : 'פתח פאנל'">
          ☰
        </button>
        <button class="btn" @click="reloadCsv" :disabled="csvLoading">
          {{ csvLoading ? "טוען CSV…" : "רענן CSV" }}
        </button>
      </div>
    </header>

    <div class="body">
      <!-- ===== Left panel ===== -->
      <aside class="panel" :class="{ open: panelOpen }">
        <div class="tabs">
          <button class="tab" :class="{ on: tab === 'search' }" @click="tab = 'search'">חיפוש</button>
          <button class="tab" :class="{ on: tab === 'anoms' }" @click="tab = 'anoms'">חריגים</button>
          <button class="tab" :class="{ on: tab === 'selected' }" @click="tab = 'selected'">נבחר</button>
          <button class="tab" :class="{ on: tab === 'settings' }" @click="tab = 'settings'">הגדרות</button>
        </div>

        <!-- ===== SEARCH ===== -->
        <section v-if="tab === 'search'" class="card">
          <div class="cardTitle">חיפוש</div>

          <div class="row">
            <label class="lbl">חיפוש כתובת (GovMap geocode)</label>
            <input class="inp" v-model.trim="addressQuery" placeholder="לדוגמה: הרוקמים 26 חולון" />
          </div>
          <div class="row2">
            <button class="btn" @click="locateAddress" :disabled="!govReady || !addressQuery">אתר</button>
            <button class="btn ghost" @click="clearMarker" :disabled="!govReady">נקה סמן</button>
          </div>

          <div class="sep"></div>

          <div class="row">
            <label class="lbl">חיפוש לפי objectid</label>
            <input class="inp" v-model.trim="objectIdQuery" placeholder="למשל: 417568" inputmode="numeric" />
          </div>
          <div class="row2">
            <button class="btn" @click="findByObjectId" :disabled="!govReady || !objectIdQuery">מצא</button>
            <button class="btn ghost" @click="selectByClick = !selectByClick" :class="{ on: selectByClick }" :disabled="!govReady">
              {{ selectByClick ? "בחירה בלחיצה: פועל" : "בחירה בלחיצה: כבוי" }}
            </button>
          </div>

          <div class="sep"></div>

          <div class="row2">
            <button class="btn" @click="drawRectangleAndLoad" :disabled="!govReady">
              בחר אזור (מלבן) → טען חריגים
            </button>
            <button class="btn ghost" @click="refreshFromLastQuery" :disabled="!govReady || !lastQueryWkt">
              טען שוב
            </button>
          </div>

          <div class="row">
            <label class="lbl">Auto-refresh לפי זום/תזוזה</label>
            <label class="switch">
              <input type="checkbox" v-model="autoRefresh" />
              <span></span>
            </label>
          </div>

          <div class="info">
            <div class="k">סטטוס</div>
            <div class="v">
              <span v-if="!govReady">טוען GovMap…</span>
              <span v-else>GovMap מוכן</span>
              <span v-if="csvLoading"> · טוען CSV…</span>
              <span v-if="queryLoading"> · שואב בניינים…</span>
            </div>
          </div>

          <div class="info">
            <div class="k">CSV rows</div>
            <div class="v">{{ csvCount.toLocaleString() }}</div>
          </div>

          <div v-if="errorMsg" class="err">{{ errorMsg }}</div>
        </section>

        <!-- ===== ANOMS ===== -->
        <section v-if="tab === 'anoms'" class="card">
          <div class="cardTitle">חריגים</div>

          <div class="row">
            <label class="lbl">סף חריגה |rate|</label>
            <input class="inp" type="number" v-model.number="rateThreshold" step="0.5" />
          </div>

          <div class="row">
            <label class="lbl">חיפוש בתוך הרשימה</label>
            <input class="inp" v-model.trim="anomsFilter" placeholder="objectid…" />
          </div>

          <div class="muted" v-if="anomaliesFiltered.length === 0">
            אין חריגים לפי הסף/הפילטר כרגע.
          </div>

          <div class="list" v-else>
            <button
              v-for="b in anomaliesFiltered"
              :key="b.key"
              class="listItem"
              :class="{ on: selected?.objectId === b.objectId }"
              @click="selectBuilding(b)"
            >
              <div class="liTop">
                <div class="liId">objectid: {{ b.objectId }}</div>
                <div class="liRate">{{ fmtRate(b.csv?.rate) }}</div>
              </div>
              <div class="liSub">
                <span v-if="b.csv?.raw?.length">CSV: {{ b.csv.raw.join(", ") }}</span>
                <span v-else>אין נתון CSV</span>
              </div>
            </button>
          </div>

          <div class="row2" style="margin-top: 10px">
            <button class="btn ghost" @click="redrawOverlays" :disabled="!govReady">רענן הדגשות</button>
            <button class="btn ghost" @click="clearOverlays" :disabled="!govReady">נקה הדגשות</button>
          </div>
        </section>

        <!-- ===== SELECTED ===== -->
        <section v-if="tab === 'selected'" class="card">
          <div class="cardTitle">פרטי בניין</div>

          <div class="muted" v-if="!selected">
            בחר בניין (לחיצה על המפה / “מצא לפי objectid” / מהרשימה).
          </div>

          <template v-else>
            <div class="kv">
              <div class="k">objectid</div>
              <div class="v">{{ selected.objectId }}</div>

              <div class="k">Rate (CSV)</div>
              <div class="v">{{ fmtRate(selected.csv?.rate) }}</div>

              <div class="k">חריג?</div>
              <div class="v">{{ selected.isAnomaly ? "כן" : "לא" }}</div>

              <div class="k">שורת CSV</div>
              <div class="v mono">{{ selected.csv?.raw?.join(", ") || "לא נמצא ב־CSV" }}</div>
            </div>

            <div class="row2" style="margin-top: 10px">
              <button class="btn" @click="zoomToSelected" :disabled="!govReady">זום לבניין</button>
              <button class="btn ghost" @click="copyObjectId">העתק objectid</button>
            </div>
          </template>

          <div v-if="errorMsg" class="err" style="margin-top: 10px">{{ errorMsg }}</div>
        </section>

        <!-- ===== SETTINGS ===== -->
        <section v-if="tab === 'settings'" class="card">
          <div class="cardTitle">הגדרות</div>

          <div class="row">
            <label class="lbl">GovMap Token</label>
            <input class="inp" v-model="GOVMAP_TOKEN" />
          </div>

          <div class="row">
            <label class="lbl">שכבת בניינים (GovMap layer)</label>
            <input class="inp" v-model="BUILDINGS_LAYER" />
          </div>

          <div class="row">
            <label class="lbl">CSV URL</label>
            <input class="inp" v-model="CSV_PATH" />
          </div>

          <div class="sep"></div>

          <div class="muted small">
            <div>• GovMap CLICK event מחזיר mapPoint (x,y) ואנחנו עושים intersectFeatures בנקודה. :contentReference[oaicite:1]{index=1}</div>
            <div>• ה־JOIN נעשה לפי objectid (ObjectId בתשובה של GovMap).</div>
            <div>• CSV אצלך בלי כותרות → ברירת מחדל: עמודה 0 = objectid, עמודה אחרונה = rate.</div>
          </div>

          <div class="row2" style="margin-top: 10px">
            <button class="btn" @click="reinit" :disabled="!GOVMAP_TOKEN">הפעל מחדש מפה</button>
            <button class="btn ghost" @click="reloadCsv">טען CSV מחדש</button>
          </div>

          <div v-if="errorMsg" class="err" style="margin-top: 10px">{{ errorMsg }}</div>
        </section>
      </aside>

      <!-- ===== Map ===== -->
      <main class="mapWrap">
        <div id="map" class="map"></div>

        <div class="toast" v-if="toast">{{ toast }}</div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

/**
 * =========================
 * CONFIG (editable in UI too)
 * =========================
 */
const GOVMAP_TOKEN = ref("ede9a5fd-7c23-432f-8ffb-d85feffa3f3c");
const BUILDINGS_LAYER = ref("225287");

/**
 * CSV location:
 * file sits in: client/public/data/tablecsv.csv
 * so it should be served as: <BASE_URL>/data/tablecsv.csv
 */
const CSV_PATH = ref("data/tablecsv.csv");

/**
 * CSV format (based on your screenshot):
 *   objectid, <something>, rate
 * No header.
 * Defaults:
 *   id col = 0
 *   rate col = last
 */
const CSV_ID_COL = 0;
const CSV_RATE_COL = -1; // last column

/**
 * Highlight limits
 */
const MAX_DRAW_ANOMS = 800;
const MAX_DRAW_NORMALS = 400;

/**
 * =========================
 * STATE
 * =========================
 */
const panelOpen = ref(true);
const tab = ref("search");

const govReady = ref(false);
const csvLoading = ref(false);
const queryLoading = ref(false);
const errorMsg = ref("");

const toast = ref("");
let toastT = null;

const addressQuery = ref("");
const objectIdQuery = ref("");

const selectByClick = ref(true);
const autoRefresh = ref(false);

const rateThreshold = ref(2.0);
const anomsFilter = ref("");

const lastQueryWkt = ref("");

/**
 * CSV index: objectid(string) -> { rate:number|null, raw:string[] }
 */
const csvIndex = ref(new Map());
const csvCount = computed(() => csvIndex.value.size);

/**
 * Buildings in current query extent/rectangle:
 * { key, objectId, wkt, csv, isAnomaly }
 */
const buildings = ref([]);
const selected = ref(null);

/**
 * =========================
 * Helpers
 * =========================
 */
function setToast(msg, ms = 2200) {
  toast.value = msg;
  if (toastT) clearTimeout(toastT);
  toastT = setTimeout(() => (toast.value = ""), ms);
}

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmtRate(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  return `${v.toFixed(2)}`;
}

function baseUrlify(rel) {
  // Works in Vite / GitHub Pages when base is configured:
  // new URL(rel, import.meta.env.BASE_URL) -> absolute
  try {
    return new URL(rel, import.meta.env.BASE_URL).toString();
  } catch {
    // fallback: relative
    return rel;
  }
}

async function fetchTextSmart(urlCandidates) {
  let lastErr = null;
  for (const u of urlCandidates) {
    try {
      const res = await fetch(u, { cache: "no-store" });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return await res.text();
    } catch (e) {
      lastErr = new Error(`נכשל: ${u} (${e?.message || e})`);
    }
  }
  throw lastErr || new Error("fetch failed");
}

/**
 * =========================
 * CSV loader (real CSV)
 * =========================
 */
async function reloadCsv() {
  csvLoading.value = true;
  errorMsg.value = "";
  try {
    const rel = CSV_PATH.value.replace(/^\//, "");
    const urlA = baseUrlify(rel);
    // extra fallbacks for GH Pages confusion
    const urlB = "/" + rel;
    const urlC = `./${rel}`;

    const text = await fetchTextSmart([urlA, urlB, urlC]);

    const idx = new Map();

    // fast-ish parse for simple CSV (no quoted commas expected)
    const lines = text.split(/\r?\n/);

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const cols = line.split(",");
      if (cols.length < 2) continue;

      // header detection (if any letters in first line)
      if (i === 0 && /[A-Za-z\u0590-\u05FF]/.test(line)) {
        // has header -> skip for now (you can extend later)
        continue;
      }

      const id = String(cols[CSV_ID_COL] ?? "").trim();
      if (!id) continue;

      const rateColIndex = CSV_RATE_COL < 0 ? cols.length + CSV_RATE_COL : CSV_RATE_COL;
      const rate = toNum(cols[rateColIndex]);

      idx.set(id, { rate, raw: cols.map((c) => c.trim()) });
    }

    csvIndex.value = idx;
    setToast(`CSV נטען: ${idx.size.toLocaleString()} שורות`);

    // refresh joined buildings + redraw
    if (buildings.value.length) {
      buildings.value = buildings.value.map(applyCsvJoinAndAnom);
      await redrawOverlays();
    }
    if (selected.value) {
      selected.value = applyCsvJoinAndAnom(selected.value);
    }
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    csvLoading.value = false;
  }
}

/**
 * =========================
 * GovMap init
 * =========================
 */
function loadGovMapScript() {
  return new Promise((resolve, reject) => {
    if (window.govmap) return resolve();
    const id = "govmap-api-js";
    if (document.getElementById(id)) {
      const t = setInterval(() => {
        if (window.govmap) {
          clearInterval(t);
          resolve();
        }
      }, 50);
      setTimeout(() => {
        clearInterval(t);
        reject(new Error("GovMap script loaded but govmap object not found"));
      }, 8000);
      return;
    }

    const s = document.createElement("script");
    s.id = id;
    s.src = "https://www.govmap.gov.il/govmap/api/govmap.api.js";
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load govmap.api.js"));
    document.head.appendChild(s);
  });
}

async function initGovMap() {
  errorMsg.value = "";
  govReady.value = false;

  await loadGovMapScript();
  if (!GOVMAP_TOKEN.value) throw new Error("חסר GOVMAP_TOKEN");

  window.govmap.createMap("map", {
    token: GOVMAP_TOKEN.value,
    background: 3,
    // show the layer (as requested)
    layers: [BUILDINGS_LAYER.value],
    showXY: false,
    identifyOnClick: false, // אנחנו מנהלים קליקים לבד
    isEmbeddedToggle: false,
    layersMode: 1,
    zoomButtons: true,
    onLoad: () => {
      govReady.value = true;
      bindGovEvents();
      setToast("GovMap מוכן");
    },
    onError: (e) => {
      errorMsg.value = "שגיאת GovMap: " + (e?.message || JSON.stringify(e));
    },
  });
}

function bindGovEvents() {
  try {
    window.govmap.unbindEvent(window.govmap.events.CLICK);
    window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
  } catch (_) {}

  // Click on map -> pick building -> join CSV
  window.govmap.onEvent(window.govmap.events.CLICK).progress(async (e) => {
    if (!selectByClick.value) return;
    const p = e?.mapPoint;
    if (!p) return;
    await inspectBuildingAtPoint(p.x, p.y);
  });

  // Extent change -> auto refresh query
  window.govmap.onEvent(window.govmap.events.EXTENT_CHANGE).progress(async (e) => {
    if (!autoRefresh.value) return;
    const extent = e?.extent;
    const wkt = extentToWkt(extent);
    if (wkt) await loadBuildingsByWkt(wkt);
  });
}

async function reinit() {
  try {
    await initGovMap();
    await redrawOverlays();
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  }
}

onBeforeUnmount(() => {
  try {
    if (window.govmap?.unbindEvent) {
      window.govmap.unbindEvent(window.govmap.events.CLICK);
      window.govmap.unbindEvent(window.govmap.events.EXTENT_CHANGE);
    }
  } catch (_) {}
});

/**
 * =========================
 * GovMap querying
 * =========================
 */
function applyCsvJoinAndAnom(b) {
  const csv = csvIndex.value.get(String(b.objectId));
  const rate = csv?.rate;
  const isAnomaly = typeof rate === "number" && Number.isFinite(rate) && Math.abs(rate) >= Number(rateThreshold.value);

  return {
    ...b,
    csv: csv || null,
    isAnomaly: !!csv && isAnomaly,
  };
}

async function loadBuildingsByWkt(wkt) {
  if (!govReady.value || !wkt) return;

  queryLoading.value = true;
  errorMsg.value = "";
  lastQueryWkt.value = wkt;
  selected.value = null;

  try {
    const params = {
      layerName: BUILDINGS_LAYER.value,
      geometry: wkt,
      fields: [], // לא חייבים שדות בשביל objectid
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);
    const items = Array.isArray(resp?.data) ? resp.data : Array.isArray(resp) ? resp : [];

    const parsed = [];
    for (const it of items) {
      const objectId =
        it?.ObjectId ??
        it?.ObjectID ??
        it?.objectid ??
        it?.objectId ??
        it?.id ??
        null;

      if (objectId == null) continue;

      const shape =
        it?.Shape ??
        it?.shape ??
        it?.WKT ??
        it?.wkt ??
        it?.Geometry ??
        it?.geometry ??
        "";

      parsed.push(
        applyCsvJoinAndAnom({
          key: `${objectId}`,
          objectId: String(objectId),
          wkt: typeof shape === "string" ? shape : "",
          csv: null,
          isAnomaly: false,
        })
      );
    }

    buildings.value = parsed;
    await redrawOverlays();
    setToast(`נטענו ${parsed.length.toLocaleString()} בניינים באזור`);
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    queryLoading.value = false;
  }
}

async function inspectBuildingAtPoint(x, y) {
  if (!govReady.value) return;

  queryLoading.value = true;
  errorMsg.value = "";

  try {
    const wkt = `POINT(${x} ${y})`;

    const params = {
      layerName: BUILDINGS_LAYER.value,
      geometry: wkt,
      fields: [],
      getShapes: true,
    };

    const resp = await window.govmap.intersectFeatures(params);
    const items = Array.isArray(resp?.data) ? resp.data : Array.isArray(resp) ? resp : [];
    if (!items.length) {
      setToast("לא נמצא בניין בנקודה");
      return;
    }

    const it = items[0];
    const objectId =
      it?.ObjectId ??
      it?.ObjectID ??
      it?.objectid ??
      it?.objectId ??
      it?.id ??
      null;

    if (objectId == null) {
      throw new Error("לא התקבל objectid מה־GovMap");
    }

    const shape =
      it?.Shape ??
      it?.shape ??
      it?.WKT ??
      it?.wkt ??
      it?.Geometry ??
      it?.geometry ??
      "";

    const b = applyCsvJoinAndAnom({
      key: `${objectId}`,
      objectId: String(objectId),
      wkt: typeof shape === "string" ? shape : "",
      csv: null,
      isAnomaly: false,
    });

    selected.value = b;
    tab.value = "selected";
    await drawSelectedOverlay(b);

    // marker for feedback
    window.govmap.setMapMarker?.({ x, y });

    if (!b.csv) {
      setToast(`נבחר objectid=${b.objectId} (לא נמצא ב־CSV)`);
    } else {
      setToast(`נבחר objectid=${b.objectId} (CSV נמצא)`);
    }
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    queryLoading.value = false;
  }
}

/**
 * =========================
 * Draw overlays (highlight)
 * =========================
 */
async function clearOverlays() {
  if (!govReady.value) return;
  try {
    window.govmap.clearGeometriesByName(["anom", "norm", "sel"]);
  } catch (_) {}
}

async function redrawOverlays() {
  if (!govReady.value) return;

  await clearOverlays();

  const anoms = [];
  const normals = [];

  for (const b of buildings.value) {
    if (!b.wkt || !String(b.wkt).toUpperCase().includes("POLYGON")) continue;
    if (b.isAnomaly) anoms.push(b);
    else normals.push(b);
  }

  const anomToDraw = anoms.slice(0, MAX_DRAW_ANOMS);
  const normToDraw = normals.slice(0, MAX_DRAW_NORMALS);

  if (normToDraw.length) {
    await window.govmap.displayGeometries({
      wkts: normToDraw.map((b) => b.wkt),
      names: normToDraw.map(() => "norm"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [0, 90, 255, 0.8],
        outlineWidth: 1,
        fillColor: [0, 90, 255, 0.08],
      },
      clearExisting: false,
      clearExistings: false,
      showBubble: false,
      data: { tooltips: normToDraw.map((b) => `objectid: ${b.objectId}`) },
    });
  }

  if (anomToDraw.length) {
    await window.govmap.displayGeometries({
      wkts: anomToDraw.map((b) => b.wkt),
      names: anomToDraw.map(() => "anom"),
      geometryType: window.govmap.geometryType.POLYGON,
      defaultSymbol: {
        outlineColor: [255, 0, 0, 1],
        outlineWidth: 2,
        fillColor: [255, 0, 0, 0.28],
      },
      clearExisting: false,
      clearExistings: false,
      showBubble: false,
      data: {
        tooltips: anomToDraw.map((b) => `חריג • objectid:${b.objectId} • rate:${fmtRate(b.csv?.rate)}`),
      },
    });
  }

  if (selected.value) {
    await drawSelectedOverlay(selected.value);
  }
}

async function drawSelectedOverlay(b) {
  if (!govReady.value || !b?.wkt || !String(b.wkt).toUpperCase().includes("POLYGON")) return;
  try {
    window.govmap.clearGeometriesByName(["sel"]);
  } catch (_) {}

  await window.govmap.displayGeometries({
    wkts: [b.wkt],
    names: ["sel"],
    geometryType: window.govmap.geometryType.POLYGON,
    defaultSymbol: {
      outlineColor: [255, 215, 0, 1],
      outlineWidth: 3,
      fillColor: [255, 215, 0, 0.14],
    },
    clearExisting: false,
    clearExistings: false,
    showBubble: false,
    data: { tooltips: [`נבחר • objectid: ${b.objectId}`] },
  });
}

/**
 * =========================
 * UI actions
 * =========================
 */
async function drawRectangleAndLoad() {
  if (!govReady.value) return;
  errorMsg.value = "";

  try {
    const res = await window.govmap.draw(window.govmap.drawType.Rectangle);
    const wkt = res?.wkt;
    if (!wkt) throw new Error("לא התקבל WKT מהשרטוט");
    try {
      window.govmap.zoomToDrawing?.();
    } catch (_) {}
    await loadBuildingsByWkt(wkt);
    tab.value = "anoms";
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  } finally {
    try {
      window.govmap.setDefaultTool?.();
    } catch (_) {}
  }
}

async function refreshFromLastQuery() {
  if (!lastQueryWkt.value) return;
  await loadBuildingsByWkt(lastQueryWkt.value);
}

async function locateAddress() {
  if (!govReady.value || !addressQuery.value) return;
  errorMsg.value = "";

  try {
    const resp = await window.govmap.geocode({
      keyword: addressQuery.value,
      type: window.govmap.geocodeType.AccuracyOnly,
    });

    const x = resp?.X ?? resp?.x ?? resp?.data?.X ?? resp?.data?.x;
    const y = resp?.Y ?? resp?.y ?? resp?.data?.Y ?? resp?.data?.y;

    if (typeof x !== "number" || typeof y !== "number") {
      throw new Error("לא נמצאה תוצאה מדויקת. נסה לנסח כתובת אחרת/להוסיף מספר.");
    }

    window.govmap.zoomToXY({ x, y, level: 9 });
    window.govmap.setMapMarker?.({ x, y });
    setToast("מיקום נמצא");
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  }
}

function clearMarker() {
  try {
    window.govmap.clearMapMarker?.();
  } catch (_) {}
}

async function findByObjectId() {
  const id = String(objectIdQuery.value || "").trim();
  if (!id) return;

  // If we already have it in the loaded set, just select
  const hit = buildings.value.find((b) => String(b.objectId) === id);
  if (hit) {
    await selectBuilding(hit);
    return;
  }

  // Otherwise: we cannot query by objectid directly without whereClause unless you use searchInLayer.
  // So we just select from CSV if exists and tell user to click building or load rectangle around it.
  const csv = csvIndex.value.get(id);
  if (!csv) {
    setToast("לא נמצא objectid כזה ב־CSV");
  } else {
    setToast("נמצא ב־CSV — עכשיו לחץ על הבניין במפה כדי לבחור אותו");
  }
}

async function selectBuilding(b) {
  selected.value = b;
  tab.value = "selected";
  await drawSelectedOverlay(b);
}

function zoomToSelected() {
  if (!selected.value?.wkt || !String(selected.value.wkt).toUpperCase().includes("POLYGON")) return;
  const c = centroidFromPolygonWkt(selected.value.wkt);
  if (!c) return;
  window.govmap.zoomToXY?.({ x: c.x, y: c.y, level: 9 });
  window.govmap.setMapMarker?.({ x: c.x, y: c.y });
}

async function copyObjectId() {
  const id = selected.value?.objectId;
  if (!id) return;
  try {
    await navigator.clipboard.writeText(String(id));
    setToast("הועתק");
  } catch {
    setToast(String(id));
  }
}

/**
 * =========================
 * Geometry helpers
 * =========================
 */
function extentToWkt(ext) {
  const xmin = ext?.xmin ?? ext?.XMin ?? ext?.XMIN;
  const ymin = ext?.ymin ?? ext?.YMin ?? ext?.YMIN;
  const xmax = ext?.xmax ?? ext?.XMax ?? ext?.XMAX;
  const ymax = ext?.ymax ?? ext?.YMax ?? ext?.YMAX;
  if (![xmin, ymin, xmax, ymax].every((v) => typeof v === "number")) return "";
  return `POLYGON((${xmin} ${ymin}, ${xmax} ${ymin}, ${xmax} ${ymax}, ${xmin} ${ymax}, ${xmin} ${ymin}))`;
}

function centroidFromPolygonWkt(wkt) {
  if (!wkt || typeof wkt !== "string") return null;

  const m = wkt.match(/POLYGON\s*\(\(\s*([^)]+?)\s*\)\)/i);
  if (!m) return null;

  const coords = m[1]
    .split(",")
    .map((p) => p.trim().split(/\s+/).map(Number))
    .filter((xy) => xy.length >= 2 && Number.isFinite(xy[0]) && Number.isFinite(xy[1]))
    .map(([x, y]) => ({ x, y }));

  if (coords.length < 3) return null;

  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const p = coords[i];
    const q = coords[i + 1];
    const cross = p.x * q.y - q.x * p.y;
    a += cross;
    cx += (p.x + q.x) * cross;
    cy += (p.y + q.y) * cross;
  }
  a *= 0.5;
  if (Math.abs(a) < 1e-9) {
    const sx = coords.reduce((s, p) => s + p.x, 0);
    const sy = coords.reduce((s, p) => s + p.y, 0);
    return { x: sx / coords.length, y: sy / coords.length };
  }
  cx /= 6 * a;
  cy /= 6 * a;
  return { x: cx, y: cy };
}

/**
 * =========================
 * Derived lists
 * =========================
 */
const anomalies = computed(() =>
  buildings.value
    .filter((b) => b.isAnomaly)
    .sort((a, b) => Math.abs(b.csv?.rate ?? 0) - Math.abs(a.csv?.rate ?? 0))
);

const anomaliesFiltered = computed(() => {
  const f = anomsFilter.value.trim();
  const arr = anomalies.value.slice(0, 2500); // avoid huge DOM
  if (!f) return arr;
  return arr.filter((b) => String(b.objectId).includes(f));
});

/**
 * =========================
 * Watchers
 * =========================
 */
watch(rateThreshold, async () => {
  buildings.value = buildings.value.map(applyCsvJoinAndAnom);
  if (selected.value) selected.value = applyCsvJoinAndAnom(selected.value);
  await redrawOverlays();
});

/**
 * =========================
 * Mount
 * =========================
 */
onMounted(async () => {
  try {
    await initGovMap();
    await reloadCsv();
  } catch (e) {
    errorMsg.value = e?.message || String(e);
  }
});
</script>

<style scoped>
/* layout */
.app { height: 100vh; width: 100%; background: #f5f7fb; overflow: hidden; display: flex; flex-direction: column; }
.topbar {
  height: 58px;
  background: #0f172a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  gap: 12px;
}
.brand .title { font-weight: 900; letter-spacing: 0.2px; }
.brand .subtitle { font-size: 12px; opacity: 0.8; margin-top: 2px; }

.body { flex: 1; display: grid; grid-template-columns: 420px 1fr; min-height: 0; }

.panel { background: #fff; border-left: 1px solid #e7e9f2; padding: 12px; overflow: auto; }
.tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
.tab {
  border: 1px solid #e6e8f2;
  background: #f8fafc;
  padding: 10px 8px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 800;
}
.tab.on { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }

.card { border: 1px solid #eef0f7; border-radius: 16px; padding: 12px; background: #fbfbfe; margin-bottom: 12px; }
.cardTitle { font-weight: 900; margin-bottom: 10px; }

.row { display: grid; grid-template-columns: 1fr; gap: 8px; margin: 10px 0; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }

.lbl { font-size: 13px; color: #334155; font-weight: 700; }
.inp {
  width: 100%; padding: 10px 10px;
  border: 1px solid #e2e5f0; border-radius: 12px; outline: none; background: #fff;
}
.inp:focus { border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14,165,233,.15); }

.btn {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #0ea5e9;
  background: #0ea5e9;
  color: #fff;
  cursor: pointer;
  font-weight: 900;
}
.btn.ghost { background: #fff; color: #0ea5e9; }
.btn:disabled { opacity: .6; cursor: not-allowed; }
.btn.on { background: #16a34a; border-color: #16a34a; color: #fff; }

.top-actions { display: flex; gap: 8px; align-items: center; }

.sep { height: 1px; background: #eef0f7; margin: 12px 0; }

.info { display: flex; justify-content: space-between; align-items: baseline; padding: 8px 10px; border: 1px solid #eef0f7; border-radius: 12px; background: #fff; margin-top: 8px; }
.info .k { font-size: 12px; color: #64748b; }
.info .v { font-size: 13px; font-weight: 900; color: #0f172a; }

.err { margin-top: 10px; padding: 10px; border-radius: 12px; background: #fff1f1; border: 1px solid #ffd0d0; color: #b3261e; font-size: 13px; }
.muted { color: #64748b; font-size: 13px; }
.muted.small { font-size: 12px; line-height: 1.5; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }

.list { display: grid; gap: 8px; margin-top: 10px; }
.listItem {
  text-align: right;
  padding: 10px;
  border-radius: 14px;
  border: 1px solid #eef0f7;
  background: #fff;
  cursor: pointer;
}
.listItem.on { border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14,165,233,.15); }
.liTop { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.liId { font-weight: 900; color: #0f172a; }
.liRate { font-weight: 900; color: #b91c1c; }
.liSub { margin-top: 6px; font-size: 12px; color: #64748b; }

.kv { display: grid; grid-template-columns: 110px 1fr; gap: 8px 10px; }
.kv .k { font-size: 12px; color: #64748b; }
.kv .v { font-size: 13px; font-weight: 900; color: #0f172a; }

.mapWrap { position: relative; min-height: 0; }
.map { height: 100%; width: 100%; background: #dfe6f6; }

/* toast */
.toast {
  position: absolute;
  left: 12px;
  bottom: 12px;
  background: rgba(15, 23, 42, 0.92);
  color: #fff;
  padding: 10px 12px;
  border-radius: 14px;
  font-weight: 800;
  font-size: 13px;
}

/* toggle switch */
.switch { position: relative; width: 46px; height: 26px; display: inline-block; }
.switch input { display: none; }
.switch span { position: absolute; inset: 0; background: #d7dbea; border-radius: 999px; transition: .2s; }
.switch span::after {
  content: ""; position: absolute; top: 3px; right: 3px;
  width: 20px; height: 20px; background: #fff; border-radius: 999px;
  transition: .2s; box-shadow: 0 2px 8px rgba(0,0,0,.08);
}
.switch input:checked + span { background: #0ea5e9; }
.switch input:checked + span::after { transform: translateX(-20px); }

@media (max-width: 980px) {
  .body { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .panel { position: sticky; top: 0; z-index: 2; }
}
</style>

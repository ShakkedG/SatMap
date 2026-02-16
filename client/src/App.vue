<template>
  <div class="layout" dir="rtl">
    <aside class="panel" :class="{ open: panelOpen }">
      <div class="panelTop">
        <div>
          <div class="appTitle">SatMap</div>
          <div class="appSub">Buildings Joined (GeoJSON)</div>
        </div>
        <button class="iconBtn" @click="panelOpen = !panelOpen" title="פתח/סגור">☰</button>
      </div>

      <div class="box">
        <div class="row">
          <label>חיפוש OBJECTID</label>
          <input v-model.trim="q" placeholder="לדוגמה: 188" />
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
            <label>סף שקיעה (Vel_mean ≤)</label>
            <input type="number" v-model.number="velThreshold" step="0.5" />
            <div class="hint">לפרוטוטייפ: תנסה -2 או -5</div>
          </div>
        </div>

        <div class="row2">
          <button class="btn" @click="fitAll" :disabled="!mapReady || !geojson">התמקד על כל הבניינים</button>
          <button class="btn ghost" @click="reload">טען מחדש</button>
        </div>

        <div class="stats" v-if="geojson">
          <div>סה״כ: <b>{{ totalCount }}</b></div>
          <div>stable: <b>{{ counts.stable }}</b></div>
          <div>no_data: <b>{{ counts.no_data }}</b></div>
          <div>suspect: <b>{{ counts.suspect }}</b></div>
        </div>
      </div>

      <div class="box" v-if="selected">
        <div class="title2">פרטי בניין נבחר</div>
        <div class="kv"><span>OBJECTID</span><b>{{ selected.OBJECTID ?? "—" }}</b></div>
        <div class="kv"><span>status</span><b>{{ selected.status ?? "—" }}</b></div>
        <div class="kv"><span>Vel_mean</span><b>{{ fmtNum(selected.Vel_mean) }}</b></div>
        <div class="kv"><span>Vel_count</span><b>{{ selected.Vel_count ?? "—" }}</b></div>
        <div class="kv"><span>coer_mean</span><b>{{ fmtNum(selected.coer_mean) }}</b></div>

        <div class="row2">
          <button class="btn" @click="zoomToSelected" :disabled="!mapReady">זום לבניין</button>
          <button class="btn ghost" @click="selected = null">נקה בחירה</button>
        </div>
      </div>

      <div class="box">
        <div class="title2">רשימה ({{ filtered.length }})</div>
        <div class="list">
          <button
            v-for="item in filtered.slice(0, 250)"
            :key="item._key"
            class="listItem"
            :class="{ on: selected && selected.OBJECTID === item.OBJECTID }"
            @click="selectByObjectId(item.OBJECTID)"
            :title="`Vel_mean=${fmtNum(item.Vel_mean)} | status=${item.status}`"
          >
            <div class="liTop">
              <b>#{{ item.OBJECTID ?? "?" }}</b>
              <span class="badge" :class="badgeClass(item)">{{ item.status || "—" }}</span>
            </div>
            <div class="liSub">
              Vel_mean: <b>{{ fmtNum(item.Vel_mean) }}</b> · Vel_count: <b>{{ item.Vel_count ?? "—" }}</b>
            </div>
          </button>
        </div>
        <div class="hint" v-if="filtered.length > 250">
          מוצגים 250 ראשונים (כדי לא להכביד על הדפדפן).
        </div>
      </div>

      <div class="box error" v-if="error">
        {{ error }}
      </div>
    </aside>

    <main class="mapWrap">
      <div ref="mapEl" class="map"></div>

      <div class="loading" v-if="loading">
        טוען GeoJSON…
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const mapEl = ref(null);
const map = ref(null);
const mapReady = ref(false);

const geojson = ref(null);
const loading = ref(false);
const error = ref("");

const panelOpen = ref(true);
const selected = ref(null);

const q = ref("");
const statusFilter = ref("");
const velThreshold = ref(-2);

const GEOJSON_URL = computed(() => {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}data/buildings_joined.geojson`;
});

function fmtNum(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(3);
}

function normProps(f) {
  const p = f?.properties || {};
  return {
    _key: p.OBJECTID ?? Math.random().toString(36).slice(2),
    OBJECTID: p.OBJECTID,
    coer_mean: p.coer_mean,
    Vel_count: p.Vel_count,
    Vel_mean: p.Vel_mean,
    status: p.status,
  };
}

const allItems = computed(() => (geojson.value?.features || []).map(normProps));

const totalCount = computed(() => allItems.value.length);

const counts = computed(() => {
  const out = { stable: 0, no_data: 0, suspect: 0, other: 0 };
  for (const it of allItems.value) {
    if (it.status === "stable") out.stable++;
    else if (it.status === "no_data") out.no_data++;
    else if (it.status === "suspect") out.suspect++;
    else out.other++;
  }
  return out;
});

const filtered = computed(() => {
  let arr = allItems.value;

  if (q.value) {
    const qq = q.value.toLowerCase();
    arr = arr.filter((it) => String(it.OBJECTID ?? "").toLowerCase().includes(qq));
  }

  if (statusFilter.value) {
    arr = arr.filter((it) => it.status === statusFilter.value);
  }

  // “חשוד לשקיעה” לפי Vel_mean
  const thr = Number(velThreshold.value);
  if (Number.isFinite(thr)) {
    arr = arr.filter((it) => {
      const v = Number(it.Vel_mean);
      // אם אין נתון, לא מסננים אותו החוצה בכוח (תוכל לשנות אם בא לך)
      if (!Number.isFinite(v)) return true;
      return v <= thr || it.status === "no_data" || it.status === "stable";
    });
  }

  // ממיין: קודם מי שיש לו Vel_mean “חזק” (בערך מוחלט)
  return [...arr].sort((a, b) => Math.abs(Number(b.Vel_mean) || 0) - Math.abs(Number(a.Vel_mean) || 0));
});

function badgeClass(item) {
  const v = Number(item.Vel_mean);
  if (item.status === "no_data") return "bGrey";
  if (Number.isFinite(v) && v <= -5) return "bRed";
  if (Number.isFinite(v) && v <= -2) return "bOrange";
  return "bGreen";
}

async function loadGeoJSON() {
  loading.value = true;
  error.value = "";
  try {
    const res = await fetch(GEOJSON_URL.value, { cache: "no-store" });
    if (!res.ok) throw new Error(`נכשל לטעון GeoJSON (${res.status})`);
    const j = await res.json();
    if (!j || j.type !== "FeatureCollection") throw new Error("הקובץ לא נראה כמו FeatureCollection");
    geojson.value = j;
  } catch (e) {
    error.value = e?.message || String(e);
    geojson.value = null;
  } finally {
    loading.value = false;
  }
}

function initMap() {
  map.value = new maplibregl.Map({
    container: mapEl.value,
    style: "https://demotiles.maplibre.org/style.json",
    center: [34.8, 32.1],
    zoom: 8,
  });

  map.value.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-left");

  map.value.on("load", () => {
    mapReady.value = true;
    if (geojson.value) upsertGeojsonLayer();
  });

  map.value.on("click", "buildings-fill", (e) => {
    const f = e?.features?.[0];
    if (!f) return;
    selected.value = f.properties || null;
  });

  map.value.on("mouseenter", "buildings-fill", () => {
    map.value.getCanvas().style.cursor = "pointer";
  });
  map.value.on("mouseleave", "buildings-fill", () => {
    map.value.getCanvas().style.cursor = "";
  });
}

function upsertGeojsonLayer() {
  if (!mapReady.value || !map.value || !geojson.value) return;

  const m = map.value;

  // source
  if (m.getSource("buildings")) {
    m.getSource("buildings").setData(geojson.value);
  } else {
    m.addSource("buildings", { type: "geojson", data: geojson.value });
  }

  // layers
  if (!m.getLayer("buildings-fill")) {
    m.addLayer({
      id: "buildings-fill",
      type: "fill",
      source: "buildings",
      paint: {
        "fill-opacity": 0.55,
        "fill-color": [
          "case",
          ["==", ["get", "status"], "no_data"], "#9aa0a6",
          ["<=", ["to-number", ["get", "Vel_mean"]], -5], "#e53935",
          ["<=", ["to-number", ["get", "Vel_mean"]], -2], "#fb8c00",
          "#43a047"
        ],
      },
    });

    m.addLayer({
      id: "buildings-outline",
      type: "line",
      source: "buildings",
      paint: { "line-width": 1, "line-opacity": 0.8 },
    });
  }

  fitAll();
}

function walkCoords(coords, cb) {
  if (!Array.isArray(coords)) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    cb(coords[0], coords[1]);
    return;
  }
  for (const c of coords) walkCoords(c, cb);
}

function bboxFromFeature(f) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  walkCoords(f?.geometry?.coordinates, (x, y) => {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  });
  if (![minX, minY, maxX, maxY].every(Number.isFinite)) return null;
  return [[minX, minY], [maxX, maxY]];
}

function bboxFromGeojson(gj) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const f of gj?.features || []) {
    walkCoords(f?.geometry?.coordinates, (x, y) => {
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    });
  }
  if (![minX, minY, maxX, maxY].every(Number.isFinite)) return null;
  return [[minX, minY], [maxX, maxY]];
}

function fitAll() {
  if (!mapReady.value || !geojson.value) return;
  const bb = bboxFromGeojson(geojson.value);
  if (!bb) return;
  map.value.fitBounds(bb, { padding: 40, duration: 700 });
}

function zoomToSelected() {
  if (!mapReady.value || !selected.value || !geojson.value) return;
  // למצוא את הפיצ’ר המקורי כדי לקחת גיאומטריה
  const f = (geojson.value.features || []).find((x) => x?.properties?.OBJECTID === selected.value.OBJECTID);
  if (!f) return;
  const bb = bboxFromFeature(f);
  if (!bb) return;
  map.value.fitBounds(bb, { padding: 60, duration: 700 });
}

function selectByObjectId(objectId) {
  const f = (geojson.value?.features || []).find((x) => x?.properties?.OBJECTID === objectId);
  if (!f) return;
  selected.value = f.properties || null;
  zoomToSelected();
}

async function reload() {
  await loadGeoJSON();
  if (mapReady.value && geojson.value) upsertGeojsonLayer();
}

onMounted(async () => {
  await loadGeoJSON();
  initMap();
});

watch(geojson, () => {
  if (mapReady.value && geojson.value) upsertGeojsonLayer();
});

onBeforeUnmount(() => {
  try { map.value?.remove(); } catch {}
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

.row { display: grid; gap: 6px; margin-bottom: 10px; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
label { font-size: 12px; opacity: .8; }
input, select {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
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

.title2 { font-weight: 800; margin-bottom: 8px; }
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
  .panel { position: absolute; inset: 0 auto 0 0; width: 85vw; max-width: 420px; transform: translateX(-100%); transition: .2s; z-index: 10; }
  .panel.open { transform: translateX(0); }
}
</style>

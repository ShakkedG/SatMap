<template>
  <div class="layout" dir="rtl">
    <aside class="panel">
      <div class="top">
        <div>
          <div class="title">SatMap</div>
          <div class="sub">Prototype – בניינים + InSAR (P-SBAS CSV) + Δגובה</div>
        </div>
        <div class="topBtns">
          <button class="btn ghost" @click="fitToLayer" :disabled="!allBoundsValid">התמקד בשכבה</button>
          <button class="btn" @click="reload">טען מחדש</button>
        </div>
      </div>

      <div class="box">
        <div class="row2">
          <div>
            <label>סף “שוקע/חשוד” v (mm/yr)</label>
            <input type="number" v-model.number="rateThreshold" step="0.5" />
            <div class="hint">טיפ: התחל ב־-2 (מבוסס ספרות), ואז כוון לפי הנתונים שלך</div>
          </div>
          <div>
            <label>X שנים אחורה להשוואה</label>
            <input type="number" v-model.number="yearsBack" step="0.5" min="0.5" />
            <div class="hint">מומלץ: 3–5 שנים</div>
          </div>
        </div>

        <div class="row2">
          <div>
            <label>Buffer שיוך נקודות לבניין (מטר)</label>
            <input type="number" v-model.number="joinBufferM" step="0.5" min="0" />
            <div class="hint">ברירת מחדל 2m (נפוץ במחקרים בגלל דיוק מיקום נקודות InSAR)</div>
          </div>
          <div>
            <label>צבע “שוקעים” לפי</label>
            <select v-model="colorBy">
              <option value="status">סטטוס</option>
              <option value="rate">חומרה לפי v</option>
              <option value="delta">חומרה לפי Δh</option>
            </select>
          </div>
        </div>

        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="flipSign" />
            היפוך סימן (אם מרגיש שהשקיעה יוצאת “הפוך”)
          </label>
          <label class="chk">
            <input type="checkbox" v-model="assumeVerticalOnly" />
            הנחת תנועה אנכית בלבד (שימוש ב־cosU אם קיים)
          </label>
        </div>

        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showStable" @change="applyVisibility" />
            להציג יציב/עולה
          </label>
          <label class="chk">
            <input type="checkbox" v-model="showNoData" @change="applyVisibility" />
            להציג אין נתון
          </label>
        </div>

        <div class="row2">
          <label class="chk">
            <input type="checkbox" v-model="showInsarPoints" @change="renderInsarPointsLayer" :disabled="!insar.loaded" />
            להציג נקודות InSAR על המפה
          </label>
          <div class="hint" style="margin-top:10px">
            InSAR: <b>{{ insar.loaded ? `${insar.count} נקודות נטענו` : "לא נטען" }}</b>
            <span v-if="insar.msg" class="muted"> — {{ insar.msg }}</span>
          </div>
        </div>

        <div class="kpis">
          <div class="kpi"><div class="k">סה״כ בניינים</div><div class="v">{{ stats.total }}</div></div>
          <div class="kpi sink"><div class="k">שוקעים/חשודים</div><div class="v">{{ stats.sinking }}</div></div>
          <div class="kpi stable"><div class="k">יציב/עולה</div><div class="v">{{ stats.stable }}</div></div>
          <div class="kpi nodata"><div class="k">אין נתון</div><div class="v">{{ stats.noData }}</div></div>
        </div>

        <div class="mini muted" v-if="loadMsg">{{ loadMsg }}</div>
        <div class="mini err" v-if="loadErr">{{ loadErr }}</div>

        <div class="legend">
          <div class="legRow"><span class="sw sw-sink"></span> שוקע/חשוד (v ≤ {{ rateThreshold }})</div>
          <div class="legRow"><span class="sw sw-stable"></span> יציב/עולה</div>
          <div class="legRow"><span class="sw sw-nodata"></span> אין נתון (אין נקודות InSAR לבניין)</div>
        </div>
      </div>

      <details class="box" open>
        <summary class="sumTitle">מקרא נתונים – איך האתר משיג ומחשב כל דבר</summary>

        <div class="gloss">
          <div class="glRow">
            <div class="glKey">מקור הנתונים</div>
            <div class="glVal">
              קובץ נקודות InSAR: <span class="mono">data/insar_points.csv</span> (מומלץ P-SBAS).<br/>
              לכל נקודה יש Lat/Lon, Vel, Coer, Topo (ועוד).
              <div class="hint">אם הקובץ לא קיים/ריק → כל הבניינים יהיו “אין נתון”.</div>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">v (mm/yr)</div>
            <div class="glVal">
              מהירות תזוזה שנתית:
              <ul>
                <li>מה-CSV: <span class="mono">Vel</span> הוא <b>cm/year</b> → ממירים ל-mm/year: <span class="mono">v = Vel×10</span></li>
                <li>הערכים הם LOS. אם מסומן “אנכי בלבד”, מחלקים ב-<span class="mono">cosU</span> (אם קיים) בהנחה שהתנועה רק אנכית.</li>
                <li>לכל בניין לוקחים <b>מדיאן</b> של v מכל הנקודות בתוך/עד Buffer סביב הפוליגון.</li>
              </ul>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">Δh ב־X שנים (mm)</div>
            <div class="glVal">
              שינוי מצטבר:
              <div class="mono">Δh = v × X</div>
              <div class="hint">אם v שלילי → שקיעה (גובה קטן עם הזמן).</div>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">Topo / “גובה עכשיו” (m)</div>
            <div class="glVal">
              מה-CSV: <span class="mono">Topo</span> = גובה במטרים (מעל אליפסואיד).<br/>
              לבניין לוקחים <b>מדיאן</b> של Topo של הנקודות ששויכו אליו.
              <div class="hint">זה לא “גובה בניין”, אלא גובה הנקודות/הקרקע/היעד כפי שמוגדר בתוצר.</div>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">גובה לפני X שנים (m)</div>
            <div class="glVal">
              נגזר מהגובה ומהשינוי:
              <div class="mono">TopoPast = TopoNow - (Δh / 1000)</div>
            </div>
          </div>

          <div class="glRow">
            <div class="glKey">איכות/אמינות</div>
            <div class="glVal">
              מציגים:
              <ul>
                <li><b>#points</b> = כמה נקודות InSAR שויכו לבניין</li>
                <li><b>Coer</b> = Temporal Coherence (מדיאן) — גבוה יותר בדרך כלל אמין יותר</li>
              </ul>
            </div>
          </div>
        </div>
      </details>

      <div class="box" v-if="selected">
        <div class="selHeader">
          <div class="mini"><b>{{ selected.name }}</b></div>
          <button class="btn ghost small" @click="clearSelection">נקה בחירה</button>
        </div>

        <div class="selGrid">
          <div class="selCard">
            <div class="k">סטטוס</div>
            <div class="v" :class="{ danger: selected.status === 'sinking' }">{{ selected.statusLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">נקודות InSAR לבניין</div>
            <div class="v mono">{{ selected.psCountLabel }}</div>
            <div class="hint">Buffer: {{ joinBufferM }}m</div>
          </div>

          <div class="selCard">
            <div class="k">v (mm/yr)</div>
            <div class="v mono">{{ selected.rateLabel }}</div>
            <div class="hint" v-if="selected.rateMode">{{ selected.rateMode }}</div>
          </div>

          <div class="selCard">
            <div class="k">Coherence (מדיאן)</div>
            <div class="v mono">{{ selected.cohLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">Topo עכשיו (m)</div>
            <div class="v mono">{{ selected.topoNowLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">Topo לפני {{ yearsBack }} שנים (m)</div>
            <div class="v mono">{{ selected.topoPastLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">Δh ב־{{ yearsBack }} שנים (mm)</div>
            <div class="v mono">{{ selected.deltaLabel }}</div>
          </div>

          <div class="selCard">
            <div class="k">הערה</div>
            <div class="v" style="font-weight:700;font-size:12px;line-height:1.4">
              {{ selected.note }}
            </div>
          </div>
        </div>
      </div>
    </aside>

    <main class="mapWrap">
      <div id="map"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const buildingsUrl = `${import.meta.env.BASE_URL}data/tlvex.geojson`;
const insarCsvUrl  = `${import.meta.env.BASE_URL}data/insar_points.csv`;

/** UI */
const yearsBack = ref(3);
const rateThreshold = ref(-2); // mm/yr (שלילי = שקיעה)
const colorBy = ref("status");

const joinBufferM = ref(2);
const flipSign = ref(false);
const assumeVerticalOnly = ref(false);

const showStable = ref(true);
const showNoData = ref(false);
const showInsarPoints = ref(false);

const loadMsg = ref("");
const loadErr = ref("");

const stats = ref({ total: 0, sinking: 0, stable: 0, noData: 0 });
const selected = ref(null);

const insar = ref({ loaded: false, count: 0, msg: "", err: "" });

/** Leaflet */
let map = null;
let sinkingGroup = null;
let stableGroup = null;
let noDataGroup = null;
let insarPointsGroup = null;

let allBounds = null;
const allBoundsValid = ref(false);

/** InSAR in-memory */
let insarPoints = []; // {lat, lon, vel_cm_yr, vel_mm_yr, coher, topo_m, cosU}
let grid = null;
const GRID_DEG = 0.002; // ~200m (lat)

/** ===== Helpers ===== */
function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmt2(n) { return n == null ? "—" : Number(n).toFixed(2); }
function fmt3(n) { return n == null ? "—" : Number(n).toFixed(3); }
function fmtInt(n) { return n == null ? "—" : String(Math.round(n)); }

function median(arr) {
  const a = arr.filter(x => Number.isFinite(x)).slice().sort((x,y)=>x-y);
  if (!a.length) return null;
  const m = Math.floor(a.length/2);
  return a.length % 2 ? a[m] : (a[m-1] + a[m]) / 2;
}

/** CSV parsing (פשוט + מספיק לתוצרים סטנדרטיים) */
function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim().length);
  if (!lines.length) return { headers: [], rows: [] };

  const headers = splitCsvLine(lines[0]).map(s => s.trim());
  const rows = [];

  for (let i=1; i<lines.length; i++) {
    const cols = splitCsvLine(lines[i]);
    if (!cols.length) continue;
    const obj = {};
    for (let j=0; j<headers.length; j++) obj[headers[j]] = cols[j] ?? "";
    rows.push(obj);
  }
  return { headers, rows };
}

function splitCsvLine(line) {
  const out = [];
  let cur = "";
  let inQ = false;

  for (let i=0; i<line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQ && line[i+1] === '"') { cur += '"'; i++; }
      else inQ = !inQ;
      continue;
    }
    if (ch === "," && !inQ) { out.push(cur); cur = ""; continue; }
    cur += ch;
  }
  out.push(cur);
  return out;
}

function pickField(obj, candidates) {
  if (!obj) return "";
  for (const k of candidates) {
    if (Object.prototype.hasOwnProperty.call(obj, k)) return k;
  }
  // נסיון case-insensitive
  const keys = Object.keys(obj);
  const lowerMap = new Map(keys.map(k => [k.toLowerCase(), k]));
  for (const c of candidates) {
    const real = lowerMap.get(String(c).toLowerCase());
    if (real) return real;
  }
  return "";
}

/** Grid index for points */
function cellKey(lat, lon) {
  const y = Math.floor(lat / GRID_DEG);
  const x = Math.floor(lon / GRID_DEG);
  return `${y},${x}`;
}
function buildGrid(points) {
  const m = new Map();
  for (let i=0; i<points.length; i++) {
    const p = points[i];
    const k = cellKey(p.lat, p.lon);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(i);
  }
  return m;
}
function collectCandidatesByBbox(bbox) {
  if (!grid) return [];
  const [minLon, minLat, maxLon, maxLat] = bbox;

  const y0 = Math.floor(minLat / GRID_DEG);
  const y1 = Math.floor(maxLat / GRID_DEG);
  const x0 = Math.floor(minLon / GRID_DEG);
  const x1 = Math.floor(maxLon / GRID_DEG);

  const outIdx = [];
  for (let y=y0; y<=y1; y++) {
    for (let x=x0; x<=x1; x++) {
      const k = `${y},${x}`;
      const arr = grid.get(k);
      if (arr) outIdx.push(...arr);
    }
  }
  return outIdx;
}

/** Geometry utils */
function computeBbox(geom) {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;

  function visitCoord(c) {
    const lon = c[0], lat = c[1];
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
    if (lon < minLon) minLon = lon;
    if (lat < minLat) minLat = lat;
    if (lon > maxLon) maxLon = lon;
    if (lat > maxLat) maxLat = lat;
  }

  function walk(coords) {
    if (!coords) return;
    if (typeof coords[0] === "number") visitCoord(coords);
    else for (const cc of coords) walk(cc);
  }

  walk(geom?.coordinates);
  if (!Number.isFinite(minLon)) return null;
  return [minLon, minLat, maxLon, maxLat];
}

function bboxCenter(b) {
  return { lon: (b[0]+b[2])/2, lat: (b[1]+b[3])/2 };
}

function expandBboxMeters(b, meters, atLat) {
  const dLat = meters / 111320;
  const dLon = meters / (111320 * Math.cos((atLat*Math.PI)/180));
  return [b[0]-dLon, b[1]-dLat, b[2]+dLon, b[3]+dLat];
}

/** Point-in-polygon + distance-to-edges (במטרים) */
function projectToMeters(lat, lon, lat0, lon0) {
  const k = 111320;
  const x = (lon - lon0) * Math.cos((lat0*Math.PI)/180) * k;
  const y = (lat - lat0) * k;
  return { x, y };
}

function pointInRing(p, ring) {
  // ring: [{x,y},...]
  let inside = false;
  for (let i=0, j=ring.length-1; i<ring.length; j=i++) {
    const xi = ring[i].x, yi = ring[i].y;
    const xj = ring[j].x, yj = ring[j].y;
    const intersect = ((yi > p.y) !== (yj > p.y)) &&
      (p.x < (xj - xi) * (p.y - yi) / ((yj - yi) || 1e-12) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function distPointToSeg(p, a, b) {
  const vx = b.x - a.x, vy = b.y - a.y;
  const wx = p.x - a.x, wy = p.y - a.y;
  const c1 = vx*wx + vy*wy;
  if (c1 <= 0) return Math.hypot(p.x - a.x, p.y - a.y);
  const c2 = vx*vx + vy*vy;
  if (c2 <= c1) return Math.hypot(p.x - b.x, p.y - b.y);
  const t = c1 / (c2 || 1e-12);
  const px = a.x + t*vx, py = a.y + t*vy;
  return Math.hypot(p.x - px, p.y - py);
}

function minDistToRingEdges(p, ring) {
  let d = Infinity;
  for (let i=0; i<ring.length; i++) {
    const a = ring[i];
    const b = ring[(i+1) % ring.length];
    d = Math.min(d, distPointToSeg(p, a, b));
  }
  return d;
}

function geomRingsToMeters(geom, lat0, lon0) {
  // returns array of polygons; polygon = { outer:[{x,y}..], holes:[ring..] }
  const out = [];
  if (!geom) return out;

  const type = geom.type;
  const coords = geom.coordinates;

  function ringToM(ring) {
    return ring.map(c => projectToMeters(c[1], c[0], lat0, lon0));
  }

  if (type === "Polygon") {
    const outer = ringToM(coords[0] || []);
    const holes = (coords.slice(1) || []).map(ringToM);
    out.push({ outer, holes });
  } else if (type === "MultiPolygon") {
    for (const poly of coords) {
      const outer = ringToM(poly[0] || []);
      const holes = (poly.slice(1) || []).map(ringToM);
      out.push({ outer, holes });
    }
  }
  return out;
}

function pointInOrNearGeom(lat, lon, geom, bufferM) {
  const bb = computeBbox(geom);
  if (!bb) return false;
  const c = bboxCenter(bb);
  const p = projectToMeters(lat, lon, c.lat, c.lon);
  const polys = geomRingsToMeters(geom, c.lat, c.lon);

  for (const poly of polys) {
    if (!poly.outer.length) continue;

    const inOuter = pointInRing(p, poly.outer);
    if (inOuter) {
      // אם בתוך outer, צריך לוודא לא בתוך חור
      let inHole = false;
      for (const h of poly.holes) {
        if (h.length && pointInRing(p, h)) { inHole = true; break; }
      }
      if (!inHole) return true;
    }

    // לא בפנים: מרחק לשפה <= buffer
    if (bufferM > 0) {
      const dOuter = minDistToRingEdges(p, poly.outer);
      if (dOuter <= bufferM) return true;
    }
  }
  return false;
}

/** InSAR load */
async function loadInsarPoints() {
  insar.value = { loaded: false, count: 0, msg: "טוען InSAR…", err: "" };
  insarPoints = [];
  grid = null;

  try {
    const r = await fetch(insarCsvUrl, { cache: "no-store" });
    if (!r.ok) throw new Error(`insar_points.csv HTTP ${r.status}`);
    const text = await r.text();

    const { rows } = parseCsv(text);
    if (!rows.length) {
      insar.value = { loaded: false, count: 0, msg: "", err: "insar_points.csv ריק" };
      return;
    }

    // detect fields based on first row
    const sample = rows[0];
    const latF  = pickField(sample, ["Lat","lat","latitude"]);
    const lonF  = pickField(sample, ["Lon","lon","longitude","Long"]);
    const velF  = pickField(sample, ["Vel","vel","velocity","V"]);
    const cohF  = pickField(sample, ["Coer","coer","coh","coherence"]);
    const topoF = pickField(sample, ["Topo","topo","elev","height"]);
    const cosUF = pickField(sample, ["cosU","CosU","cosu"]);

    if (!latF || !lonF || !velF) {
      insar.value = { loaded: false, count: 0, msg: "", err: "לא מצאתי שדות חובה (Lat/Lon/Vel) בקובץ" };
      return;
    }

    for (const row of rows) {
      const lat = toNum(row[latF]);
      const lon = toNum(row[lonF]);
      const velCmYr = toNum(row[velF]);
      if (lat == null || lon == null || velCmYr == null) continue;

      const coher = cohF ? toNum(row[cohF]) : null;
      const topoM = topoF ? toNum(row[topoF]) : null;
      const cosU  = cosUF ? toNum(row[cosUF]) : null;

      const velMmYr = velCmYr * 10; // cm/yr -> mm/yr (P-SBAS)
      insarPoints.push({ lat, lon, vel_cm_yr: velCmYr, vel_mm_yr: velMmYr, coher, topo_m: topoM, cosU });
    }

    grid = buildGrid(insarPoints);
    insar.value = { loaded: true, count: insarPoints.length, msg: "OK", err: "" };
  } catch (e) {
    insar.value = { loaded: false, count: 0, msg: "", err: String(e) };
  }
}

/** Compute per building from InSAR points */
function computeBuildingInsar(geom) {
  if (!insar.value.loaded || !insarPoints.length) {
    return { psCount: 0, rateMmYr: null, coh: null, topoNowM: null, usedMode: "אין InSAR" };
  }

  const bb0 = computeBbox(geom);
  if (!bb0) return { psCount: 0, rateMmYr: null, coh: null, topoNowM: null, usedMode: "גאומטריה לא תקינה" };

  const c = bboxCenter(bb0);
  const bb = expandBboxMeters(bb0, Math.max(0, joinBufferM.value || 0), c.lat);

  const candIdx = collectCandidatesByBbox(bb);
  const velList = [];
  const velVertList = [];
  const cohList = [];
  const topoList = [];

  const buffer = Math.max(0, joinBufferM.value || 0);

  for (const idx of candIdx) {
    const p = insarPoints[idx];
    if (!p) continue;

    // bbox fast
    if (p.lon < bb[0] || p.lon > bb[2] || p.lat < bb[1] || p.lat > bb[3]) continue;

    // inside or near polygon
    if (!pointInOrNearGeom(p.lat, p.lon, geom, buffer)) continue;

    velList.push(p.vel_mm_yr);

    // vertical assumption if possible
    if (assumeVerticalOnly.value && p.cosU != null && Math.abs(p.cosU) > 0.05) {
      velVertList.push(p.vel_mm_yr / p.cosU);
    }

    if (p.coher != null) cohList.push(p.coher);
    if (p.topo_m != null) topoList.push(p.topo_m);
  }

  const psCount = velList.length;
  if (!psCount) return { psCount: 0, rateMmYr: null, coh: null, topoNowM: null, usedMode: "אין נקודות לבניין" };

  const vLosMed = median(velList);
  const vVertMed = velVertList.length ? median(velVertList) : null;

  let rate = (assumeVerticalOnly.value && vVertMed != null) ? vVertMed : vLosMed;
  let mode = (assumeVerticalOnly.value && vVertMed != null) ? "v אנכי (LOS/cosU, הנחה אנכית בלבד)" : "v LOS (כפי שהוא)";

  // flip sign if user wants
  if (flipSign.value && rate != null) rate = -rate;

  const coh = cohList.length ? median(cohList) : null;
  const topoNowM = topoList.length ? median(topoList) : null;

  return { psCount, rateMmYr: rate, coh, topoNowM, usedMode: mode };
}

function classify(rateMmYr) {
  if (rateMmYr == null) return "nodata";
  return rateMmYr <= rateThreshold.value ? "sinking" : "stable";
}

function statusLabel(status) {
  if (status === "sinking") return "שוקע/חשוד";
  if (status === "stable") return "יציב/עולה";
  return "אין נתון";
}

function styleFor(status, rateMmYr, deltaMm) {
  if (status === "nodata") {
    return {
      color: "#64748b", weight: 2, opacity: 0.85,
      fill: true, fillColor: "#cbd5e1", fillOpacity: 0.22, dashArray: "6 6",
    };
  }

  if (status === "stable") {
    return {
      color: "#0f172a", weight: 2, opacity: 0.85,
      fill: true, fillColor: "#60a5fa", fillOpacity: 0.22,
    };
  }

  // sinking severity
  let s = 0.55;
  if (colorBy.value === "rate" && rateMmYr != null && rateThreshold.value) {
    const ratio = Math.abs(rateMmYr / rateThreshold.value);
    s = Math.max(0.25, Math.min(1, (ratio - 1) / 2));
  } else if (colorBy.value === "delta" && deltaMm != null) {
    const dt = Math.abs(deltaMm);
    s = Math.max(0.25, Math.min(1, dt / 20)); // פרוטוטייפ: 20mm ומעלה -> חמור
  }

  const fillOpacity = 0.30 + s * 0.45;
  const weight = 2.2 + s * 1.4;
  const stroke = s >= 0.75 ? "#7f1d1d" : s >= 0.40 ? "#b91c1c" : "#dc2626";

  return {
    color: stroke, weight, opacity: 0.95,
    fill: true, fillColor: "#ef4444", fillOpacity,
  };
}

function pickName(props, idx) {
  return props?.name ?? props?.building_id ?? props?.id ?? `בניין ${idx + 1}`;
}

/** Hover highlight */
function applyHover(layer, baseStyle) {
  layer.on("mouseover", () => {
    try {
      layer.setStyle?.({
        weight: Math.max(3, (baseStyle?.weight ?? 2) + 1),
        opacity: 1,
        fillOpacity: Math.min(0.85, (baseStyle?.fillOpacity ?? 0.25) + 0.15),
      });
      layer.bringToFront?.();
    } catch {}
  });
  layer.on("mouseout", () => {
    try { layer.setStyle?.(baseStyle); } catch {}
  });
}

/** ===== Map ===== */
function initMap() {
  map = L.map("map", { zoomControl: true, maxZoom: 22, preferCanvas: true }).setView([32.08, 34.78], 12);

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxNativeZoom: 19, maxZoom: 22, attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const esri = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 22, attribution: "&copy; Esri" }
  );

  sinkingGroup = new L.FeatureGroup().addTo(map);
  stableGroup = new L.FeatureGroup();
  noDataGroup = new L.FeatureGroup();
  insarPointsGroup = new L.FeatureGroup();

  L.control.layers(
    { OSM: osm, "Satellite (Esri)": esri },
    {
      "שוקעים/חשודים": sinkingGroup,
      "יציב/עולה": stableGroup,
      "אין נתון": noDataGroup,
      "נקודות InSAR": insarPointsGroup,
    },
    { position: "topleft", collapsed: true }
  ).addTo(map);
}

function applyVisibility() {
  if (!map) return;

  if (!map.hasLayer(sinkingGroup)) sinkingGroup.addTo(map);

  if (showStable.value) {
    if (!map.hasLayer(stableGroup)) stableGroup.addTo(map);
  } else {
    if (map.hasLayer(stableGroup)) map.removeLayer(stableGroup);
  }

  if (showNoData.value) {
    if (!map.hasLayer(noDataGroup)) noDataGroup.addTo(map);
  } else {
    if (map.hasLayer(noDataGroup)) map.removeLayer(noDataGroup);
  }

  // נקודות InSAR נשלטות ע"י showInsarPoints
  if (showInsarPoints.value) {
    if (!map.hasLayer(insarPointsGroup)) insarPointsGroup.addTo(map);
  } else {
    if (map.hasLayer(insarPointsGroup)) map.removeLayer(insarPointsGroup);
  }
}

function clearSelection() { selected.value = null; }

function fitToLayer() {
  if (allBounds?.isValid?.()) {
    try { map.fitBounds(allBounds.pad(0.08)); } catch {}
  }
}

function renderInsarPointsLayer() {
  if (!insarPointsGroup) return;
  insarPointsGroup.clearLayers();

  if (!insar.value.loaded || !showInsarPoints.value) {
    applyVisibility();
    return;
  }

  // דגימה: לא לצייר מיליונים בפרוטוטייפ
  const maxDraw = 5000;
  const step = Math.max(1, Math.floor(insarPoints.length / maxDraw));

  for (let i=0; i<insarPoints.length; i += step) {
    const p = insarPoints[i];
    const v = p.vel_mm_yr;
    const signedV = flipSign.value ? -v : v;

    // צבע פשוט: שקיעה(שלילי) אדום, עליה/הפוך כחול
    const isSink = signedV <= rateThreshold.value;
    const fillColor = isSink ? "#ef4444" : "#3b82f6";
    const opacity = p.coher == null ? 0.45 : Math.max(0.25, Math.min(0.9, p.coher));

    const m = L.circleMarker([p.lat, p.lon], {
      radius: 3,
      color: "#111827",
      weight: 1,
      fillColor,
      fillOpacity: opacity,
      opacity: 0.8,
    });

    m.bindTooltip(
      `Vel: ${(v/10).toFixed(2)} cm/yr (${v.toFixed(1)} mm/yr) | Coer: ${p.coher == null ? "—" : p.coher.toFixed(2)} | Topo: ${p.topo_m == null ? "—" : p.topo_m.toFixed(1)} m`,
      { sticky: true, direction: "top", opacity: 0.95 }
    );

    m.addTo(insarPointsGroup);
  }

  applyVisibility();
}

/** ===== Load + render ===== */
async function loadAndRender() {
  loadErr.value = "";
  loadMsg.value = "טוען בניינים + InSAR…";
  clearSelection();

  sinkingGroup?.clearLayers?.();
  stableGroup?.clearLayers?.();
  noDataGroup?.clearLayers?.();
  insarPointsGroup?.clearLayers?.();

  allBounds = null;
  allBoundsValid.value = false;

  // 1) load InSAR (optional but strongly recommended)
  await loadInsarPoints();

  // 2) load buildings
  try {
    const r = await fetch(buildingsUrl, { cache: "no-store" });
    if (!r.ok) throw new Error("Buildings GeoJSON load failed: " + r.status);
    const gj = await r.json();

    const feats = Array.isArray(gj?.features) ? gj.features : [];
    let sinking = 0, stable = 0, noData = 0;

    for (let i=0; i<feats.length; i++) {
      const f = feats[i];
      const props = f?.properties || {};
      const geom = f?.geometry;

      const name = pickName(props, i);

      const bi = computeBuildingInsar(geom);
      const rate = bi.rateMmYr;

      const yrs = Math.max(0.25, toNum(yearsBack.value) ?? 3);
      const deltaMm = rate == null ? null : (rate * yrs);

      const st = classify(rate);
      if (st === "sinking") sinking++;
      else if (st === "stable") stable++;
      else noData++;

      const baseStyle = styleFor(st, rate, deltaMm);
      const layer = L.geoJSON(f, { style: baseStyle, interactive: true });

      // bounds
      try {
        const b = layer.getBounds();
        if (b?.isValid?.()) allBounds = allBounds ? allBounds.extend(b) : b;
      } catch {}

      applyHover(layer, baseStyle);

      const topoNow = bi.topoNowM;
      const topoPast = (topoNow == null || deltaMm == null) ? null : (topoNow - (deltaMm/1000));

      const tooltip = [
        `#pts: ${bi.psCount}`,
        `v: ${fmt2(rate)} mm/yr`,
        `Δh(${yrs.toFixed(1)}y): ${fmt2(deltaMm)} mm`,
        `Topo: ${topoNow == null ? "—" : topoNow.toFixed(1)} m`,
        `Coer: ${bi.coh == null ? "—" : bi.coh.toFixed(2)}`
      ].join(" | ");

      layer.bindTooltip(tooltip, { sticky: true, direction: "top", opacity: 0.95 });

      layer.on("click", () => {
        selected.value = {
          name,
          status: st,
          statusLabel: statusLabel(st),
          psCountLabel: String(bi.psCount),
          rateLabel: fmt2(rate),
          rateMode: bi.usedMode,
          cohLabel: bi.coh == null ? "—" : bi.coh.toFixed(2),
          topoNowLabel: topoNow == null ? "—" : topoNow.toFixed(2),
          topoPastLabel: topoPast == null ? "—" : topoPast.toFixed(2),
          deltaLabel: deltaMm == null ? "—" : deltaMm.toFixed(1),
          note:
            !insar.value.loaded ? "אין קובץ InSAR נטען. הוסף data/insar_points.csv כדי לקבל נתונים." :
            bi.psCount === 0 ? "אין נקודות InSAR ששויכו לבניין (נסה להגדיל Buffer או לבדוק כיסוי נקודות)." :
            `מבוסס מדיאן של ${bi.psCount} נק׳. אם Coer נמוך או מעט נקודות—קח בזהירות.`,
        };
      });

      if (st === "sinking") layer.addTo(sinkingGroup);
      else if (st === "stable") layer.addTo(stableGroup);
      else layer.addTo(noDataGroup);
    }

    stats.value = { total: feats.length, sinking, stable, noData };

    allBoundsValid.value = !!allBounds?.isValid?.();
    if (allBoundsValid.value) {
      try { map.fitBounds(allBounds.pad(0.08)); } catch {}
    }

    // points layer if requested
    renderInsarPointsLayer();

    applyVisibility();

    loadMsg.value = `נטענו ${feats.length} בניינים. InSAR: ${insar.value.loaded ? `${insar.value.count} נק׳` : "לא נטען"}`;
  } catch (e) {
    loadMsg.value = "";
    loadErr.value = String(e);
    stats.value = { total: 0, sinking: 0, stable: 0, noData: 0 };
  }
}

function reload() {
  loadAndRender();
}

watch([rateThreshold, yearsBack, joinBufferM, flipSign, assumeVerticalOnly, colorBy], () => {
  if (!map) return;
  loadAndRender();
});

onMounted(async () => {
  initMap();
  await loadAndRender();
});
</script>

<style>
.layout { display:grid; grid-template-columns: 460px 1fr; height:100vh; background:#f3f4f6; font-family:system-ui, Arial; }
.panel { background:#fff; border-left:1px solid #e5e7eb; padding:12px; overflow:auto; }
.mapWrap { position:relative; }
#map { width:100%; height:100vh; }

.top { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:10px; }
.topBtns { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.title { font-weight:900; font-size:18px; }
.sub { font-size:12px; opacity:0.72; margin-top:2px; }

.box { border:1px solid #e5e7eb; border-radius:16px; padding:10px; background:#fff; margin-bottom:10px; }
label { display:block; font-size:12px; opacity:0.85; margin-bottom:6px; }

input, select, .btn { width:100%; padding:10px; border-radius:12px; border:1px solid #e5e7eb; font-size:14px; background:#fff; }
select { cursor:pointer; }

.btn { cursor:pointer; background:#111827; color:#fff; border-color:#111827; font-weight:700; }
.btn.ghost { background:#fff; color:#111827; border-color:#e5e7eb; }
.btn.small { padding:8px 10px; font-size:12px; border-radius:10px; }
.btn:disabled { opacity:0.55; cursor:not-allowed; }

.row2 { display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:6px; }
.chk { display:flex; align-items:center; gap:8px; font-size:12px; opacity:0.9; margin-top:8px; }

.kpis { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:10px; }
.kpi { border:1px solid #e5e7eb; border-radius:12px; padding:10px; background:#f9fafb; }
.kpi .k { font-size:12px; opacity:0.7; }
.kpi .v { font-weight:900; font-size:18px; }
.kpi.sink { border-color:#fecaca; background:#fef2f2; }
.kpi.stable { border-color:#bfdbfe; background:#eff6ff; }
.kpi.nodata { border-color:#e2e8f0; background:#f8fafc; }

.legend { margin-top:10px; border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; display:grid; gap:6px; }
.legRow { display:flex; align-items:center; gap:10px; font-size:12px; opacity:0.92; }
.sw { width:18px; height:10px; border-radius:4px; border:1px solid #e5e7eb; }
.sw-sink { background:#fee2e2; border-color:#b91c1c; }
.sw-stable { background:#dbeafe; border-color:#1d4ed8; }
.sw-nodata { background:#e2e8f0; border-color:#64748b; }

.selHeader { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
.selGrid { display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px; }
.selCard { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#f9fafb; }
.selCard .k { font-size:12px; opacity:0.7; }
.selCard .v { font-weight:900; font-size:14px; margin-top:4px; }
.selCard .v.danger { color:#991b1b; }

.mini { font-size:12px; opacity:0.92; margin-top:8px; }
.muted { opacity:0.72; }
.err { color:#b91c1c; opacity:1; }
.hint { font-size:11px; opacity:0.7; margin-top:6px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

.sumTitle { cursor:pointer; font-weight:900; list-style:none; user-select:none; }
details > summary::-webkit-details-marker { display:none; }

.gloss { margin-top:10px; display:grid; gap:10px; }
.glRow { border:1px solid #e5e7eb; border-radius:14px; padding:10px; background:#fff; }
.glKey { font-weight:900; margin-bottom:6px; }
.glVal { font-size:12px; opacity:0.92; line-height:1.55; }
.glVal ul { margin:6px 18px 0 0; padding:0; }
.glVal li { margin:4px 0; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .panel { height: 54vh; border-left:none; border-bottom:1px solid #e5e7eb; }
  #map { height: 46vh; }
}
</style>

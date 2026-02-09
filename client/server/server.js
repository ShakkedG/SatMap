import express from "express";
import MBTiles from "@mapbox/mbtiles";
import fs from "fs";
import path from "path";

const app = express();
const PORT = process.env.PORT || 3000;

// איפה הקובץ ישב בשרת (מומלץ עם דיסק קבוע)
const MBTILES_PATH = process.env.MBTILES_PATH || "/var/data/buildings.mbtiles";

// אם תשים URL ציבורי (Release asset / R2 / S3) — השרת יוריד פעם אחת
const MBTILES_URL = process.env.MBTILES_URL || "";

// לרוב יצוא מ-QGIS → TMS. אם אתה לא רואה כלום אחר כך, תנסה TILE_SCHEME=xyz
const TILE_SCHEME = (process.env.TILE_SCHEME || "tms").toLowerCase();

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  next();
});

function isGzip(buf) {
  return buf && buf.length >= 2 && buf[0] === 0x1f && buf[1] === 0x8b;
}
function xyzToTmsY(z, y) {
  const n = 1 << z;
  return (n - 1) - y;
}

let mbtiles = null;
let lastError = null;
let loading = false;

function openMbtiles(filePath) {
  return new Promise((resolve, reject) => {
    new MBTiles(`${filePath}?mode=ro`, (err, mb) => {
      if (err) reject(err);
      else resolve(mb);
    });
  });
}

async function downloadMbtilesIfNeeded() {
  if (fs.existsSync(MBTILES_PATH)) return;

  if (!MBTILES_URL) return; // אין URL → פשוט נחכה לקובץ
  fs.mkdirSync(path.dirname(MBTILES_PATH), { recursive: true });

  const res = await fetch(MBTILES_URL, { redirect: "follow" });
  if (!res.ok) throw new Error(`Download failed: ${res.status} ${res.statusText}`);

  const file = fs.createWriteStream(MBTILES_PATH);
  await new Promise((resolve, reject) => {
    res.body.pipe(file);
    res.body.on("error", reject);
    file.on("finish", resolve);
    file.on("error", reject);
  });
}

async function ensureReady() {
  if (loading || mbtiles) return;
  loading = true;
  try {
    await downloadMbtilesIfNeeded();
    if (fs.existsSync(MBTILES_PATH)) {
      mbtiles = await openMbtiles(MBTILES_PATH);
      lastError = null;
      console.log("MBTiles ready:", MBTILES_PATH);
    }
  } catch (e) {
    lastError = String(e?.message || e);
    console.error("ensureReady error:", lastError);
  } finally {
    loading = false;
  }
}

// ננסה להיטען בהתחלה, ואז מדי דקה (כדי שברגע שהקובץ מוכן זה יתפוס)
ensureReady();
setInterval(ensureReady, 60_000);

app.get("/health", (req, res) => res.json({ ok: true }));

app.get("/status", (req, res) => {
  const exists = fs.existsSync(MBTILES_PATH);
  const size = exists ? fs.statSync(MBTILES_PATH).size : 0;
  res.json({
    ok: true,
    ready: !!mbtiles,
    loading,
    fileExists: exists,
    fileSizeBytes: size,
    tileScheme: TILE_SCHEME,
    hasUrl: !!MBTILES_URL,
    lastError
  });
});

// TileJSON שימושי ל-MapLibre
app.get("/tiles/buildings/tilejson.json", (req, res) => {
  const base = `${req.protocol}://${req.get("host")}`;
  res.json({
    tilejson: "2.2.0",
    name: "buildings",
    version: "1.0.0",
    scheme: "xyz",
    tiles: [`${base}/tiles/buildings/{z}/{x}/{y}.pbf`],
    minzoom: 7,
    maxzoom: 16
  });
});

app.get("/tiles/buildings/:z/:x/:y.pbf", async (req, res) => {
  if (!mbtiles) {
    await ensureReady();
    if (!mbtiles) return res.status(503).json({ error: "MBTiles not ready yet", hint: "Check /status" });
  }

  const z = Number(req.params.z);
  const x = Number(req.params.x);
  const y = Number(req.params.y);
  if (!Number.isFinite(z) || !Number.isFinite(x) || !Number.isFinite(y)) return res.status(400).end();

  const yy = (TILE_SCHEME === "xyz") ? y : xyzToTmsY(z, y);

  mbtiles.getTile(z, x, yy, (e, data) => {
    if (e || !data) return res.status(204).end();
    res.setHeader("Content-Type", "application/x-protobuf");
    if (isGzip(data)) res.setHeader("Content-Encoding", "gzip");
    res.setHeader("Cache-Control", "public, max-age=86400");
    res.end(data);
  });
});

app.listen(PORT, () => {
  console.log(`Tile server running on :${PORT}`);
});

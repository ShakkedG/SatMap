import express from "express";
import MBTiles from "@mapbox/mbtiles";
import fs from "fs";
import path from "path";

const app = express();
const PORT = process.env.PORT || 3000;

const MBTILES_PATH = process.env.MBTILES_PATH || "/var/data/buildings.mbtiles";
const MBTILES_URL = process.env.MBTILES_URL || "";
const TILE_SCHEME = (process.env.TILE_SCHEME || "tms").toLowerCase();

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  next();
});

app.get("/health", (req, res) => res.json({ ok: true }));

function isGzip(buf) {
  return buf && buf.length >= 2 && buf[0] === 0x1f && buf[1] === 0x8b;
}
function xyzToTmsY(z, y) {
  const n = 1 << z;
  return (n - 1) - y;
}

async function downloadIfNeeded() {
  if (fs.existsSync(MBTILES_PATH)) return;
  if (!MBTILES_URL) throw new Error("MBTILES_URL not set and MBTiles file not found");

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

function openMbtiles() {
  return new Promise((resolve, reject) => {
    new MBTiles(`${MBTILES_PATH}?mode=ro`, (err, mbtiles) => {
      if (err) reject(err);
      else resolve(mbtiles);
    });
  });
}

async function main() {
  await downloadIfNeeded();
  const mbtiles = await openMbtiles();

  app.get("/tiles/buildings/:z/:x/:y.pbf", (req, res) => {
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

  app.listen(PORT, () => console.log(`OK: http://localhost:${PORT}`));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

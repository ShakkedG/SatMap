import express from "express";
import MBTiles from "@mapbox/mbtiles";

const app = express();
const PORT = process.env.PORT || 3000;
const MBTILES_PATH = process.env.MBTILES_PATH || "./data/buildings.mbtiles";

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  next();
});

app.get("/health", (req, res) => res.json({ ok: true }));

function isGzip(buf) {
  return buf && buf.length >= 2 && buf[0] === 0x1f && buf[1] === 0x8b;
}

// MBTiles מאוחסן לרוב ב-TMS, והקליינט מבקש XYZ
function xyzToTmsY(z, y) {
  const n = 1 << z;
  return (n - 1) - y;
}

new MBTiles(`${MBTILES_PATH}?mode=ro`, (err, mbtiles) => {
  if (err) {
    console.error("Failed to open MBTiles:", err);
    process.exit(1);
  }

  // גם עם .pbf וגם בלי
  app.get("/tiles/buildings/:z/:x/:y", (req, res) => {
    const z = Number(req.params.z);
    const x = Number(req.params.x);
    const y = Number(req.params.y);

    if (!Number.isFinite(z) || !Number.isFinite(x) || !Number.isFinite(y)) {
      return res.status(400).send("Bad z/x/y");
    }

    const tmsY = xyzToTmsY(z, y);

    mbtiles.getTile(z, x, tmsY, (e, data) => {
      if (e || !data) return res.status(204).end();

      res.setHeader("Content-Type", "application/x-protobuf");
      if (isGzip(data)) res.setHeader("Content-Encoding", "gzip");
      res.setHeader("Cache-Control", "public, max-age=86400");
      res.end(data);
    });
  });

  app.get("/tiles/buildings/:z/:x/:y.pbf", (req, res) => {
    req.url = req.url.replace(/\.pbf$/, "");
    app._router.handle(req, res);
  });

  app.listen(PORT, () => {
    console.log(`Tile server on :${PORT}`);
    console.log(`MBTiles: ${MBTILES_PATH}`);
    console.log(`Endpoint: /tiles/buildings/{z}/{x}/{y}.pbf`);
  });
});

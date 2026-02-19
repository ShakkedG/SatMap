<!DOCTYPE html>
<html lang="he" dir="rtl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
    <title>SatMap – CrimesMap UI + חריגים</title>

    <style>
      * { box-sizing: border-box; }

      html, body {
        margin: 0; padding: 0; height: 100%;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        overflow: hidden;
        background: #f5f5f5;
        font-size: 15px;
      }

      #map { width: 100%; height: 100%; position: relative; }

      /* ================== GOVMAP: hide layer button / layer list (force layer always-on) ================== */
      /* try a lot of selectors because govmap UI classes may vary */
      #map [title*="שכבות"],
      #map [aria-label*="שכבות"],
      #map [data-tool*="layers"],
      #map .layers,
      #map .layer,
      #map .layer-list,
      #map .layerList,
      #map .esri-layer-list,
      #map .esri-layer-list__toggle,
      #map .esri-layer-list__container,
      #map .esri-ui .esri-component.esri-layer-list,
      #map .esri-ui-top-left .esri-component,
      #map .esri-ui-top-right .esri-component {
        /* NOTE: We still want zoom buttons sometimes; if this hides too much,
           remove the last two selectors and keep only the "layers" ones. */
      }

      /* safer: explicitly hide only elements that look like "layers" */
      #map [title*="שכבות"],
      #map [aria-label*="שכבות"],
      #map [data-tool*="layers"],
      #map .esri-layer-list,
      #map .esri-layer-list__toggle,
      #map .esri-layer-list__container {
        display: none !important;
      }

      /* ================== CrimesMap-like panel ================== */
      #panel {
        position: absolute;
        top: 14px;
        right: 18px;
        z-index: 9999;
        width: 460px;
        max-height: calc(100vh - 28px);
        border-radius: 16px;
        overflow: hidden;
        background: #fff;
        box-shadow: 0 12px 34px rgba(0,0,0,0.16);
        display: flex;
        flex-direction: column;
      }

      #panelHeader {
        padding: 14px 16px;
        color: #fff;
        background: linear-gradient(135deg, #0b63ce 0%, #084eac 100%);
        border-bottom: 1px solid rgba(255,255,255,0.18);
      }
      #panelHeader .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }
      #panelHeader .title {
        font-weight: 1000;
        font-size: 17px;
        letter-spacing: -0.3px;
        margin: 0;
      }
      #panelHeader .sub {
        margin-top: 6px;
        font-weight: 900;
        font-size: 13px;
        opacity: 0.95;
        line-height: 1.35;
      }

      .hdrBtn {
        border: 1px solid rgba(255,255,255,0.35);
        background: rgba(255,255,255,0.16);
        color: #fff;
        border-radius: 12px;
        padding: 9px 10px;
        font-weight: 1000;
        cursor: pointer;
        user-select: none;
        white-space: nowrap;
      }
      .hdrBtn:active { transform: translateY(1px); }

      #tabs {
        display: flex;
        background: #fafafa;
        border-bottom: 2px solid #e6e6e6;
      }
      .tab {
        flex: 1;
        text-align: center;
        padding: 11px 8px;
        cursor: pointer;
        user-select: none;
        font-weight: 1000;
        font-size: 13px;
        color: #666;
        border-bottom: 3px solid transparent;
        white-space: nowrap;
      }
      .tab:hover { background: #f2f6ff; color: #2a4c8a; }
      .tab.active { background: #fff; color: #0b63ce; border-bottom-color: #0b63ce; }

      #controls {
        padding: 12px 14px;
        background: #fafafa;
        border-bottom: 1px solid #e8e8e8;
      }

      .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .grid1 { display: grid; grid-template-columns: 1fr; gap: 8px; }

      .ctlLabel {
        font-weight: 1000;
        font-size: 12.5px;
        color: #333;
        margin-bottom: 6px;
      }
      .ctlRow {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .ctlInput {
        flex: 1;
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid #cfcfcf;
        font-weight: 900;
        outline: none;
      }
      .ctlInput.ltr { direction: ltr; text-align: left; }
      .ctlBtn {
        padding: 10px 12px;
        border-radius: 12px;
        border: 2px solid #e3e3e3;
        background: #fff;
        cursor: pointer;
        font-weight: 1000;
      }
      .ctlBtn.primary {
        background: #0b63ce;
        border-color: #0b63ce;
        color: #fff;
        box-shadow: 0 8px 20px rgba(11,99,206,0.18);
      }
      .ctlBtn:active { transform: translateY(1px); }

      .seg {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 10px;
      }
      .segBtn {
        flex: 1;
        min-width: 120px;
        padding: 11px 10px;
        border-radius: 12px;
        border: 2px solid #e3e3e3;
        background: #fff;
        cursor: pointer;
        font-weight: 1000;
        color: #444;
        text-align: center;
      }
      .segBtn.active {
        background: #0b63ce;
        border-color: #0b63ce;
        color: #fff;
        box-shadow: 0 8px 20px rgba(11,99,206,0.18);
      }

      #stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-top: 10px;
      }
      .stat {
        background: #fff;
        border: 1px solid #e7e7e7;
        border-radius: 14px;
        padding: 10px 10px;
        text-align: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
      }
      .statVal {
        font-weight: 1000;
        font-size: 18px;
        color: #0b63ce;
        direction: ltr;
        margin-bottom: 2px;
      }
      .statLbl {
        font-weight: 1000;
        font-size: 12px;
        color: #777;
      }

      #content {
        padding: 14px;
        overflow-y: auto;
        flex: 1;
        min-height: 0;
        background: #fff;
      }

      .msg {
        padding: 12px 14px;
        border-radius: 12px;
        margin-bottom: 10px;
        font-size: 13.5px;
        border-right: 4px solid;
        line-height: 1.55;
        font-weight: 900;
      }
      .info { background: #e7f3ff; color: #063a73; border-right-color: #0b63ce; }
      .warn { background: #fff7e6; color: #6a3f00; border-right-color: #ffb300; }
      .err  { background: #fff0f0; color: #b20000; border-right-color: #ff0000; }

      .bigNum {
        font-size: 24px;
        font-weight: 1000;
        color: #0b63ce;
        text-align: center;
        padding: 14px;
        background: linear-gradient(135deg, #e7f3ff 0%, #f3f8ff 100%);
        border-radius: 14px;
        border: 2px solid #b3d9ff;
        direction: ltr;
        margin-bottom: 10px;
      }

      .rankList {
        border: 1px solid #eee;
        border-radius: 16px;
        overflow: hidden;
        background: #fff;
        box-shadow: 0 10px 22px rgba(0,0,0,0.05);
      }
      .rankRow {
        display: grid;
        grid-template-columns: 44px 1fr auto;
        gap: 10px;
        align-items: center;
        padding: 11px 12px;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
        background: #fff;
      }
      .rankRow:nth-child(even) { background: #fafafa; }
      .rankRow:hover { background: #f5f9ff; }
      .rankNum {
        width: 34px; height: 34px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 1000;
        color: #063a73;
        background: #e7f3ff;
        border: 1px solid #b3d9ff;
      }
      .rankName {
        font-weight: 1000;
        color: #111;
        font-size: 13.5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        direction: ltr;
        text-align: left;
      }
      .rankVal {
        font-weight: 1000;
        color: #0b63ce;
        direction: ltr;
        font-size: 13.5px;
        min-width: 120px;
        text-align: left;
      }
      .rankMeta {
        padding: 0 12px 10px 12px;
        margin-top: -6px;
        border-bottom: 1px solid #f0f0f0;
        background: #fff;
        color: #666;
        font-weight: 900;
        font-size: 12px;
        direction: ltr;
        text-align: left;
      }

      .miniTag {
        display: inline-block;
        font-size: 12px;
        font-weight: 1000;
        padding: 5px 10px;
        border-radius: 999px;
        border: 1px solid #e0e0e0;
        background: #fafafa;
        color: #333;
        margin-left: 6px;
      }
      .tagBad { border-color:#ffb3b3; background:#fff0f0; color:#b20000; }
      .tagGood { border-color:#b7e3c6; background:#ecfff2; color:#0b6b2f; }
      .tagWarn { border-color:#ffcc80; background:#fff7e6; color:#6a3f00; }

      /* collapsed */
      #panel.collapsed { max-height: 74px; height: 74px; }
      #panel.collapsed #tabs,
      #panel.collapsed #controls,
      #panel.collapsed #content { display: none; }
      #panel.collapsed #panelHeader .sub { display: none; }

      /* mobile bottom sheet */
      @media (max-width: 768px) {
        #panel {
          position: fixed;
          left: 0; right: 0; top: auto; bottom: 0;
          width: 100%;
          height: calc(var(--vh, 1vh) * 58);
          max-height: calc(var(--vh, 1vh) * 58);
          border-radius: 20px 20px 0 0;
          right: 0;
        }
        #stats { display: none; }
      }

      /* loading */
      #loading {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%,-50%);
        z-index: 10000;
        background: #fff;
        border-radius: 16px;
        padding: 22px 26px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        text-align: center;
      }
      .spinner {
        width: 40px; height: 40px;
        margin: 0 auto 12px;
        border: 4px solid #e7e7e7;
        border-top: 4px solid #0b63ce;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
      @keyframes spin { from{transform:rotate(0)} to{transform:rotate(360deg)} }
    </style>

    <script>
      /* ===================== CONFIG ===================== */
      const TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";
      const BUILDINGS_LAYER = "225287";

      // CSV location (try several)
      const CSV_CANDIDATES = [
        "data/tablecsv.csv",
        "./data/tablecsv.csv",
        "public/data/tablecsv.csv",
        "./public/data/tablecsv.csv",
      ];

      // optional hints
      const CSV_ID_HINT = "";   // e.g. "objectid"
      const CSV_RATE_HINT = ""; // e.g. "v" / "rate" / "mm_yr"

      /* ===================== STATE ===================== */
      let mapInitialized = false;

      let rateThreshold = -10;       // mm/yr
      let onlyOutliersMode = true;   // מצב חריגים (מוצג כמו CrimesMap)

      let csvLoaded = false;
      let csvLoadError = null;
      let csvHeaders = [];
      let csvIdCol = null;
      let csvRateCol = null;
      let csvXCol = null;
      let csvYCol = null;

      const csvById = new Map();
      const buildingAgg = new Map(); // id -> { id, worstRate, rowsCount, anyXY, x, y }
      let outliersList = [];

      let selectedBuildingId = null;
      let selectedBuildingRows = null;

      let currentTab = "single"; // single | outliers | search | about

      // address search cache
      let lastGeocodeReqId = 0;
      let lastAddrItems = [];
      let lastGeocodeQuery = "";
      let searchTimeout = null;

      /* ===================== HELPERS ===================== */
      function setMobileVh() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty("--vh", `${vh}px`);
      }
      setMobileVh();
      window.addEventListener("resize", setMobileVh);
      if (window.visualViewport) window.visualViewport.addEventListener("resize", setMobileVh);

      function escapeHtml(s) {
        return String(s ?? "")
          .replace(/&/g, "&amp;").replace(/</g, "&lt;")
          .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      }

      function toFiniteNum(v) {
        if (v == null) return null;
        if (typeof v === "number") return Number.isFinite(v) ? v : null;
        let s = String(v).trim();
        if (!s) return null;
        s = s.replace(/\s+/g, "");
        if (s.includes(",") && s.includes(".")) s = s.replace(/,/g, "");
        else if (s.includes(",")) {
          if (/,(\d{3})$/.test(s)) s = s.replace(/,/g, "");
          else s = s.replace(/,/g, ".");
        }
        const n = Number(s);
        return Number.isFinite(n) ? n : null;
      }

      function normalizeFieldName(n) {
        return String(n ?? "")
          .trim()
          .replace(/\s+/g, " ")
          .replace(/[׳״"'`]/g, "")
          .replace(/[:;.,()\[\]{}<>!@#$%^&*+=?~\\|\/\-\u05be\u2010-\u2015]/g, "")
          .toLowerCase();
      }

      function fmt(n, digits = 2) {
        if (n == null) return "—";
        const x = Number(n);
        if (!Number.isFinite(x)) return "—";
        return x.toLocaleString(undefined, { maximumFractionDigits: digits });
      }

      function isOutlier(rate) {
        const r = Number(rate);
        if (!Number.isFinite(r)) return false;
        return r <= rateThreshold;
      }

      function parseCsvLine(line) {
        const out = [];
        let cur = "";
        let inQ = false;
        for (let i = 0; i < line.length; i++) {
          const ch = line[i];
          if (ch === '"') {
            if (inQ && line[i + 1] === '"') { cur += '"'; i++; }
            else inQ = !inQ;
            continue;
          }
          if (ch === "," && !inQ) { out.push(cur); cur = ""; continue; }
          cur += ch;
        }
        out.push(cur);
        return out;
      }

      function detectHasHeader(firstRow) {
        return firstRow.some((c) => /[A-Za-z\u0590-\u05FF]/.test(String(c || "")));
      }

      function pickIdCol(headers) {
        const norm = headers.map(normalizeFieldName);
        if (CSV_ID_HINT) {
          const idx = norm.indexOf(normalizeFieldName(CSV_ID_HINT));
          if (idx >= 0) return idx;
        }
        const candidates = ["objectid","objid","id","gid","fid","bldg_id","building_id","buildingid"];
        for (const c of candidates) {
          const idx = norm.indexOf(c);
          if (idx >= 0) return idx;
        }
        return 0;
      }

      function pickRateCol(headers) {
        const norm = headers.map(normalizeFieldName);
        if (CSV_RATE_HINT) {
          const idx = norm.indexOf(normalizeFieldName(CSV_RATE_HINT));
          if (idx >= 0) return idx;
        }
        const candidates = ["rate","v","vel","velocity","mmyr","mm_yr","mmperyear","subsidence","dz","deltaheight","dh"];
        for (const c of candidates) {
          const idx = norm.indexOf(c);
          if (idx >= 0) return idx;
        }
        for (let i = 0; i < norm.length; i++) {
          const n = norm[i];
          if (n.includes("mm") && (n.includes("yr") || n.includes("year"))) return i;
          if (n.includes("velo")) return i;
          if (n.includes("subsid")) return i;
          if (n === "v") return i;
        }
        return Math.max(0, headers.length - 1);
      }

      function pickXYCols(headers) {
        const norm = headers.map(normalizeFieldName);
        const xCandidates = ["x","itmx","easting","lon","longitude","centerx"];
        const yCandidates = ["y","itmy","northing","lat","latitude","centery"];
        let xCol = null, yCol = null;
        for (const c of xCandidates) { const idx = norm.indexOf(c); if (idx >= 0) { xCol = idx; break; } }
        for (const c of yCandidates) { const idx = norm.indexOf(c); if (idx >= 0) { yCol = idx; break; } }
        return { xCol, yCol };
      }

      function resolveCandidateUrls() {
        const base = new URL("./", location.href);
        const parts = location.pathname.split("/").filter(Boolean);
        const repoBase = parts.length >= 1 ? `/${parts[0]}/` : "/";
        const extra = [`${repoBase}data/tablecsv.csv`, `${repoBase}public/data/tablecsv.csv`];

        const urls = [];
        for (const p of CSV_CANDIDATES) urls.push(new URL(p, base).toString());
        for (const p of extra) urls.push(new URL(p, location.origin).toString());
        return Array.from(new Set(urls));
      }

      async function fetchFirstOk(urls) {
        let lastErr = null;
        for (const u of urls) {
          try {
            const res = await fetch(u, { cache: "no-store" });
            if (res.ok) return { url: u, text: await res.text() };
            lastErr = `HTTP ${res.status} (${u})`;
          } catch (e) {
            lastErr = String(e?.message || e);
          }
        }
        throw new Error(lastErr || "fetch failed");
      }

      function buildCsvIndexes(lines) {
        csvById.clear();
        buildingAgg.clear();
        outliersList = [];
        if (!lines.length) throw new Error("CSV ריק");

        const first = parseCsvLine(lines[0]);
        const hasHeader = detectHasHeader(first);

        csvHeaders = hasHeader
          ? first.map((h, i) => String(h || `col${i}`).trim() || `col${i}`)
          : first.map((_, i) => `col${i}`);

        csvIdCol = pickIdCol(csvHeaders);
        csvRateCol = pickRateCol(csvHeaders);

        const xy = pickXYCols(csvHeaders);
        csvXCol = xy.xCol;
        csvYCol = xy.yCol;

        const start = hasHeader ? 1 : 0;

        for (let i = start; i < lines.length; i++) {
          const line = lines[i];
          if (!line || !line.trim()) continue;
          const cols = parseCsvLine(line);
          while (cols.length < csvHeaders.length) cols.push("");

          const idRaw = cols[csvIdCol];
          if (idRaw == null || String(idRaw).trim() === "") continue;
          const id = String(idRaw).trim();

          const rate = toFiniteNum(cols[csvRateCol]);
          const x = csvXCol != null ? toFiniteNum(cols[csvXCol]) : null;
          const y = csvYCol != null ? toFiniteNum(cols[csvYCol]) : null;

          const row = { __cols: cols, __id: id, __rate: rate, __x: x, __y: y };
          const arr = csvById.get(id);
          if (arr) arr.push(row);
          else csvById.set(id, [row]);
        }

        for (const [id, rows] of csvById.entries()) {
          let worst = null;
          let anyXY = false;
          let bestX = null, bestY = null;

          for (const r of rows) {
            if (Number.isFinite(Number(r.__rate))) {
              if (worst == null || r.__rate < worst) worst = r.__rate;
            }
            if (r.__x != null && r.__y != null) {
              anyXY = true; bestX = r.__x; bestY = r.__y;
            }
          }

          buildingAgg.set(id, { id, worstRate: worst, rowsCount: rows.length, anyXY, x: bestX, y: bestY });
        }

        outliersList = Array.from(buildingAgg.values())
          .filter((a) => Number.isFinite(Number(a.worstRate)) && isOutlier(a.worstRate))
          .sort((a, b) => Number(a.worstRate) - Number(b.worstRate));
      }

      async function loadCsv() {
        csvLoaded = false;
        csvLoadError = null;
        try {
          const { url, text } = await fetchFirstOk(resolveCandidateUrls());
          buildCsvIndexes(text.split(/\r?\n/));
          csvLoaded = true;
          console.log("✅ CSV loaded:", url, {
            buildings: buildingAgg.size,
            outliers: outliersList.length,
            idCol: csvHeaders[csvIdCol],
            rateCol: csvHeaders[csvRateCol],
          });
        } catch (e) {
          csvLoadError = String(e?.message || e);
          console.error("❌ CSV load failed:", e);
        }
        refreshHeaderSub();
        updateStats();
        renderCurrentTab();
      }

      /* ===================== UI ===================== */
      function refreshHeaderSub() {
        const el = document.getElementById("panelSub");
        if (!el) return;

        const status = csvLoaded
          ? `CSV נטען • מזהה: <strong>${escapeHtml(csvHeaders?.[csvIdCol] ?? "col0")}</strong> • מדד: <strong>${escapeHtml(csvHeaders?.[csvRateCol] ?? "colN")}</strong>`
          : (csvLoadError
              ? `שגיאה בטעינת CSV • ${escapeHtml(csvLoadError)}`
              : `טוען CSV…`);

        const mode = onlyOutliersMode
          ? `מצב חריגים: <strong>פעיל</strong> (סף ${fmt(rateThreshold)}-)`
          : `מצב חריגים: <strong>כבוי</strong>`;

        el.innerHTML = `${status}<br>${mode}`;
      }

      function updateStats() {
        const a = document.getElementById("statAll");
        const o = document.getElementById("statOut");
        const s = document.getElementById("statSel");

        const totalBuildings = buildingAgg.size;
        const outCount = csvLoaded
          ? Array.from(buildingAgg.values()).filter((x) => Number.isFinite(Number(x.worstRate)) && isOutlier(x.worstRate)).length
          : 0;

        if (a) a.textContent = Number(totalBuildings).toLocaleString();
        if (o) o.textContent = Number(outCount).toLocaleString();
        if (s) s.textContent = selectedBuildingId ? String(selectedBuildingId) : "—";
      }

      function showMsg(type, html) {
        const c = document.getElementById("content");
        if (!c) return;
        c.innerHTML = `<div class="msg ${type}">${html}</div>`;
      }

      function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
        renderCurrentTab();
      }

      function renderCurrentTab() {
        if (currentTab === "single") renderSelectedBuilding();
        if (currentTab === "outliers") renderOutliers();
        if (currentTab === "search") renderSearch();
        if (currentTab === "about") renderAbout();
      }

      function togglePanel() {
        const p = document.getElementById("panel");
        if (!p) return;
        p.classList.toggle("collapsed");
      }

      function setOutliersMode(on) {
        onlyOutliersMode = !!on;
        document.getElementById("btnOutOn")?.classList.toggle("active", onlyOutliersMode);
        document.getElementById("btnOutOff")?.classList.toggle("active", !onlyOutliersMode);
        refreshHeaderSub();
        renderCurrentTab();
      }

      function applyThreshold() {
        const el = document.getElementById("thrInput");
        const v = toFiniteNum(el?.value);
        if (v == null) return;
        rateThreshold = v;
        refreshHeaderSub();
        updateStats();
        renderCurrentTab();
      }

      function setPreset(v) {
        rateThreshold = v;
        const el = document.getElementById("thrInput");
        if (el) el.value = String(v);
        refreshHeaderSub();
        updateStats();
        renderCurrentTab();
      }

      /* ===================== Selected building (CrimesMap style) ===================== */
      function renderSelectedBuilding() {
        if (!csvLoaded && csvLoadError) {
          showMsg("err", `לא הצלחתי לטעון CSV. ודא שיש קובץ <span style="direction:ltr;unicode-bidi:bidi-override;font-weight:1000;">data/tablecsv.csv</span><br>שגיאה: <span style="direction:ltr;unicode-bidi:bidi-override">${escapeHtml(csvLoadError)}</span>`);
          return;
        }
        if (!csvLoaded) {
          showMsg("info", "טוען CSV… (ברגע שנטען תוכל ללחוץ על בניין ולקבל נתונים)");
          return;
        }

        if (!selectedBuildingId) {
          showMsg("info", "לחץ על בניין במפה כדי להציג נתונים מה-CSV. לטאב חריגים – לחץ “חריגים”.");
          return;
        }

        const id = String(selectedBuildingId);
        const rows = csvById.get(id) || null;
        selectedBuildingRows = rows;

        const agg = buildingAgg.get(id) || null;
        const worst = agg?.worstRate;
        const hasRate = Number.isFinite(Number(worst));

        const tags = [];
        if (!rows) tags.push(`<span class="miniTag tagWarn">אין התאמה ב-CSV</span>`);
        else tags.push(`<span class="miniTag tagGood">נמצא ב-CSV (${Number(rows.length).toLocaleString()} שורות)</span>`);

        if (hasRate) {
          tags.push(isOutlier(worst)
            ? `<span class="miniTag tagBad">חריג (≤ ${fmt(rateThreshold)}-)</span>`
            : `<span class="miniTag tagGood">לא חריג</span>`);
        } else {
          tags.push(`<span class="miniTag tagWarn">אין ערך מדד</span>`);
        }

        // CrimesMap-like: when "outliers mode" ON, non-outlier shows minimal
        if (onlyOutliersMode && rows && hasRate && !isOutlier(worst)) {
          document.getElementById("content").innerHTML = `
            <div class="msg info">${tags.join(" ")}</div>
            <div class="msg info">מצב חריגים פעיל: הבניין הזה <strong>לא</strong> עומד בסף החריגים.<br>כדי לראות את כל הפרטים בכל מקרה – כבה מצב חריגים (למעלה).</div>
          `;
          return;
        }

        let html = `<div class="msg info"><strong>בניין #${escapeHtml(id)}</strong><br>${tags.join(" ")}</div>`;
        if (hasRate) html += `<div class="bigNum">${fmt(worst)} mm/yr</div>`;

        if (!rows) {
          html += `<div class="msg warn">מצאתי את הבניין ב-GovMap (OBJECTID=${escapeHtml(id)}), אבל לא מצאתי אותו ב-CSV. בדוק שהעמודה <strong>${escapeHtml(csvHeaders?.[csvIdCol] ?? "col0")}</strong> תואמת ל-OBJECTID.</div>`;
          document.getElementById("content").innerHTML = html;
          return;
        }

        // show a compact key/value preview like CrimesMap "details"
        const first = rows[0].__cols;
        const preferIdx = new Set([csvIdCol, csvRateCol, csvXCol, csvYCol].filter((x) => x != null));
        const kv = [];

        // preferred first
        for (const idx of preferIdx) {
          const k = csvHeaders[idx];
          const v = first[idx];
          kv.push([k, v]);
        }
        // then up to 10 more non-empty columns
        for (let i = 0; i < csvHeaders.length && kv.length < 14; i++) {
          if (preferIdx.has(i)) continue;
          const v = first[i];
          if (v == null || String(v).trim() === "") continue;
          kv.push([csvHeaders[i], v]);
        }

        html += `
          <div class="rankList" style="margin-top:10px;">
            <div class="rankMeta" style="padding-top:10px;border-bottom:none;">
              עמודה מזהה: <strong>${escapeHtml(csvHeaders?.[csvIdCol] ?? "col0")}</strong> •
              עמודת מדד: <strong>${escapeHtml(csvHeaders?.[csvRateCol] ?? "colN")}</strong> •
              שורות ל-ID: <strong>${Number(rows.length).toLocaleString()}</strong>
            </div>
            <div style="padding:10px 12px;">
              ${kv.map(([k,v]) => `
                <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px dashed #eee;">
                  <div style="min-width:155px;font-weight:1000;color:#333;">${escapeHtml(k)}</div>
                  <div style="flex:1;color:#111;direction:ltr;text-align:left;word-break:break-word;">${escapeHtml(v)}</div>
                </div>
              `).join("")}
            </div>
          </div>
        `;

        document.getElementById("content").innerHTML = html;
      }

      /* ===================== Outliers list (CrimesMap ranking style) ===================== */
      let outSort = "worst"; // worst | id | count
      let outOrder = "asc";  // asc = most negative first

      function renderOutliers() {
        if (!csvLoaded && csvLoadError) { renderSelectedBuilding(); return; }
        if (!csvLoaded) { showMsg("info", "טוען CSV…"); return; }

        let list = Array.from(buildingAgg.values())
          .filter((a) => Number.isFinite(Number(a.worstRate)) && isOutlier(a.worstRate));

        if (outSort === "worst") list.sort((a,b)=>Number(a.worstRate)-Number(b.worstRate));
        if (outSort === "id") list.sort((a,b)=>String(a.id).localeCompare(String(b.id)));
        if (outSort === "count") list.sort((a,b)=>(b.rowsCount||0)-(a.rowsCount||0));
        if (outOrder === "desc") list.reverse();

        const maxShow = 250;
        const shown = list.slice(0, maxShow);

        let html = `
          <div class="msg info">
            <strong>חריגים לפי סף:</strong> ${fmt(rateThreshold)}- mm/yr • נמצאו: <strong>${Number(list.length).toLocaleString()}</strong><br>
            לחץ על פריט כדי לפתוח אותו (כמו ברשימת דירוג של CrimesMap).
          </div>

          <div class="grid2" style="margin-bottom:10px;">
            <button class="ctlBtn ${outSort==='worst'?'primary':''}" onclick="outSort='worst';renderOutliers()">📉 לפי מדד</button>
            <button class="ctlBtn ${outSort==='id'?'primary':''}" onclick="outSort='id';renderOutliers()">🆔 לפי מזהה</button>
            <button class="ctlBtn ${outSort==='count'?'primary':''}" onclick="outSort='count';renderOutliers()">🧾 לפי שורות</button>
            <button class="ctlBtn ${outOrder==='asc'?'primary':''}" onclick="outOrder='asc';renderOutliers()">⬇️ חמור→קל</button>
          </div>

          <div class="ctlRow" style="margin-bottom:10px;">
            <input id="thrInput" class="ctlInput ltr" type="number" step="0.5" value="${escapeHtml(rateThreshold)}" />
            <button class="ctlBtn primary" onclick="applyThreshold()">החל</button>
            <button class="ctlBtn" onclick="setPreset(-2)">-2</button>
            <button class="ctlBtn" onclick="setPreset(-5)">-5</button>
            <button class="ctlBtn" onclick="setPreset(-10)">-10</button>
          </div>
        `;

        if (!list.length) {
          html += `<div class="msg warn">אין חריגים לפי הסף הנוכחי.</div>`;
          document.getElementById("content").innerHTML = html;
          updateStats();
          return;
        }

        html += `<div class="rankList">`;
        shown.forEach((r, idx) => {
          const val = `${fmt(r.worstRate)} mm/yr`;
          const meta = `rows=${Number(r.rowsCount).toLocaleString()}${r.anyXY ? " • XY✅" : ""}`;
          html += `
            <div class="rankRow" onclick="selectFromList('${escapeHtml(r.id)}')">
              <div class="rankNum">${idx + 1}</div>
              <div class="rankName">${escapeHtml(r.id)}</div>
              <div class="rankVal">${escapeHtml(val)}</div>
            </div>
            <div class="rankMeta">${escapeHtml(meta)}</div>
          `;
        });
        html += `</div>`;

        if (list.length > maxShow) {
          html += `<div class="msg info" style="margin-top:10px;">מוצגים ${maxShow} מתוך ${Number(list.length).toLocaleString()} (כדי לשמור על ביצועים).</div>`;
        }

        document.getElementById("content").innerHTML = html;
        updateStats();
      }

      function selectFromList(id) {
        selectedBuildingId = String(id);
        selectedBuildingRows = csvById.get(selectedBuildingId) || null;

        // if we have XY in csv, zoom there
        const agg = buildingAgg.get(selectedBuildingId);
        if (agg?.anyXY && agg?.x != null && agg?.y != null && mapInitialized) {
          try { govmap.zoomToXY({ x: agg.x, y: agg.y, level: 12, marker: true }); } catch (_) {}
        }

        updateStats();
        switchTab("single");
      }

      /* ===================== Search tab (address + ID) ===================== */
      function renderSearch() {
        if (!csvLoaded && csvLoadError) { renderSelectedBuilding(); return; }

        const addrBox = `
          <div class="ctlLabel">חיפוש כתובת (GovMap)</div>
          <div class="ctlRow">
            <input id="addrInput" class="ctlInput" placeholder="דיזנגוף 50 תל אביב" autocomplete="off" />
            <button class="ctlBtn primary" onclick="runGeocodeFromUI()">חפש</button>
          </div>
          <div id="addrResults" style="margin-top:10px;"></div>
        `;

        const idBox = `
          <div style="margin-top:12px;">
            <div class="ctlLabel">חיפוש לפי ID (מתוך ה-CSV)</div>
            <div class="ctlRow">
              <input id="idInput" class="ctlInput ltr" placeholder="417568" autocomplete="off" />
              <button class="ctlBtn primary" onclick="runIdSearch()">חפש</button>
            </div>
            <div id="idResults" style="margin-top:10px;"></div>
          </div>
        `;

        const msg = (!csvLoaded && !csvLoadError)
          ? `<div class="msg info">טוען CSV… (חיפוש ID יהיה זמין אחרי טעינה)</div>`
          : ``;

        document.getElementById("content").innerHTML = `${msg}${addrBox}${idBox}`;

        // enter key handlers
        const a = document.getElementById("addrInput");
        if (a) {
          a.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); runGeocodeFromUI(); }
          });
          a.addEventListener("input", () => {
            if (searchTimeout) clearTimeout(searchTimeout);
            const v = a.value.trim();
            if (v.length < 3) { document.getElementById("addrResults").innerHTML = ""; return; }
            searchTimeout = setTimeout(() => runGeocode(v), 350);
          });
        }

        const i = document.getElementById("idInput");
        if (i) {
          i.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); runIdSearch(); }
          });
        }
      }

      function runIdSearch() {
        const box = document.getElementById("idResults");
        const inp = document.getElementById("idInput");
        if (!box || !inp) return;

        if (!csvLoaded) {
          box.innerHTML = `<div class="msg warn">ה-CSV עדיין לא נטען.</div>`;
          return;
        }

        const q = String(inp.value || "").trim();
        if (!q) return;

        if (csvById.has(q)) {
          box.innerHTML = `<div class="msg info">נמצא ID מדויק. פותח…</div>`;
          selectFromList(q);
          return;
        }

        const hits = [];
        const limit = 50;
        for (const id of buildingAgg.keys()) {
          if (String(id).includes(q)) hits.push(String(id));
          if (hits.length >= limit) break;
        }

        if (!hits.length) {
          box.innerHTML = `<div class="msg warn">לא נמצאו תוצאות עבור <strong>${escapeHtml(q)}</strong>.</div>`;
          return;
        }

        box.innerHTML = `
          <div class="msg info">נמצאו ${Number(hits.length).toLocaleString()} תוצאות (עד ${limit}). לחץ לפתיחה:</div>
          <div class="rankList">
            ${hits.map((id, idx) => {
              const agg = buildingAgg.get(id);
              const w = agg?.worstRate;
              const val = Number.isFinite(Number(w)) ? `${fmt(w)} mm/yr` : "—";
              const tag = Number.isFinite(Number(w))
                ? (isOutlier(w) ? `<span class="miniTag tagBad">חריג</span>` : `<span class="miniTag tagGood">לא חריג</span>`)
                : `<span class="miniTag tagWarn">אין מדד</span>`;
              return `
                <div class="rankRow" onclick="selectFromList('${escapeHtml(id)}')">
                  <div class="rankNum">${idx + 1}</div>
                  <div class="rankName">${escapeHtml(id)}</div>
                  <div class="rankVal">${escapeHtml(val)}</div>
                </div>
                <div class="rankMeta">${tag} rows=${Number(agg?.rowsCount || 0).toLocaleString()}</div>
              `;
            }).join("")}
          </div>
        `;
      }

      /* ===================== About ===================== */
      function renderAbout() {
        const idName = csvHeaders?.[csvIdCol] ?? "col0";
        const rateName = csvHeaders?.[csvRateCol] ?? "colN";
        document.getElementById("content").innerHTML = `
          <div class="msg info">
            <strong>מה קורה כאן?</strong><br>
            1) המפה נטענת מ-GovMap עם שכבת בניינים <span style="direction:ltr;unicode-bidi:bidi-override;font-weight:1000;">${escapeHtml(BUILDINGS_LAYER)}</span>.<br>
            2) נטען CSV מ-<span style="direction:ltr;unicode-bidi:bidi-override;font-weight:1000;">data/tablecsv.csv</span> ונעשה אינדוקס לפי ID.<br>
            3) בלחיצה על בניין: נשלף <strong>OBJECTID</strong> (לרוב <code style="direction:ltr;font-weight:1000;">objectid</code>) ומוצגים נתוני ה-CSV.<br><br>
            <strong>מצב חריגים:</strong> מציג/מדגיש רק IDs עם ערך מדד ≤ סף (שלילי). “אין נתון” לא נחשב חריג.
          </div>
          <div class="msg info">
            <strong>זיהוי עמודות:</strong><br>
            עמודת ID ב-CSV: <strong>${escapeHtml(idName)}</strong><br>
            עמודת מדד: <strong>${escapeHtml(rateName)}</strong>
          </div>
          <div class="msg info">
            <strong>הערה חשובה לפי הבקשה שלך:</strong><br>
            כפתור השכבות הוסתר, ובקוד יש “אכיפה” שהשכבה תמיד דלוקה.
          </div>
        `;
      }

      /* ===================== GOVMAP: force layer always-on + hide layers UI ===================== */
      function hideLayersUIHard() {
        const mapEl = document.getElementById("map");
        if (!mapEl) return;

        const hideIfLooksLikeLayers = (el) => {
          const t = (el.getAttribute?.("title") || "") + " " + (el.getAttribute?.("aria-label") || "");
          const c = (el.className || "");
          const s = (t + " " + c).toLowerCase();
          if (s.includes("שכבות") || s.includes("layers") || s.includes("layer-list") || s.includes("layerlist")) {
            el.style.display = "none";
          }
        };

        // initial sweep
        mapEl.querySelectorAll("*").forEach(hideIfLooksLikeLayers);

        // observe DOM changes (govmap sometimes injects UI later)
        const obs = new MutationObserver((muts) => {
          for (const m of muts) {
            m.addedNodes?.forEach((n) => {
              if (n && n.nodeType === 1) {
                hideIfLooksLikeLayers(n);
                n.querySelectorAll?.("*")?.forEach?.(hideIfLooksLikeLayers);
              }
            });
          }
        });
        obs.observe(mapEl, { childList: true, subtree: true });
      }

      function forceBuildingsLayerOn() {
        const target = [BUILDINGS_LAYER];

        // try multiple method names (govmap versions differ)
        try { if (typeof govmap.setVisibleLayers === "function") govmap.setVisibleLayers(target); } catch (_) {}
        try { if (typeof govmap.setVisibleLayers === "function") govmap.setVisibleLayers({ layers: target }); } catch (_) {}
        try { if (typeof govmap.showLayer === "function") govmap.showLayer(BUILDINGS_LAYER); } catch (_) {}
        try { if (typeof govmap.setLayerVisibility === "function") govmap.setLayerVisibility(BUILDINGS_LAYER, true); } catch (_) {}
        try { if (typeof govmap.setLayersVisibility === "function") govmap.setLayersVisibility(target, true); } catch (_) {}
      }

      /* ===================== GOVMAP click -> building ID ===================== */
      function fieldsToObject(fields) {
        if (!Array.isArray(fields)) return fields;
        const obj = {};
        for (const f of fields) {
          const k = f?.FieldName ?? f?.fieldName ?? f?.name;
          if (k != null) obj[k] = f?.Value ?? f?.value;
        }
        return obj;
      }

      function getFieldFromAttrs(attrsRaw, candidates) {
        const attrsObj = fieldsToObject(attrsRaw) || attrsRaw;
        if (!attrsObj || typeof attrsObj !== "object") return null;

        // direct
        for (const c of candidates || []) {
          if (attrsObj[c] != null && String(attrsObj[c]).trim() !== "") return attrsObj[c];
        }

        // normalized
        const normMap = {};
        for (const k in attrsObj) normMap[normalizeFieldName(k)] = attrsObj[k];

        for (const c of (candidates || [])) {
          const n = normalizeFieldName(c);
          if (normMap[n] != null && String(normMap[n]).trim() !== "") return normMap[n];
        }
        return null;
      }

      function normalizeMapPoint(input) {
        const mp = input?.mapPoint ?? input?.Point ?? input ?? null;
        if (!mp) return null;
        const x = mp.x ?? mp.X;
        const y = mp.y ?? mp.Y;
        const nx = Number(x), ny = Number(y);
        if (!Number.isFinite(nx) || !Number.isFinite(ny)) return null;
        return { x: nx, y: ny };
      }

      function extractBuildingIdFromGovmapItem(item) {
        const attrs = item?.Fields || item?.Attributes || item;
        const candidates = ["objectid","OBJECTID","ObjectId","ObjectID","oid","OID","id","ID","building_id","BUILDING_ID"];
        const v = getFieldFromAttrs(attrs, candidates);
        if (v == null) return null;
        const s = String(v).trim();
        return s ? s : null;
      }

      async function onMapClick(e) {
        if (!mapInitialized) return;
        const pt = normalizeMapPoint(e);
        if (!pt) return;

        try {
          const resp = await govmap.getLayerData({
            LayerName: BUILDINGS_LAYER,
            Point: { x: pt.x, y: pt.y, X: pt.x, Y: pt.y },
            Radius: 30,
          });

          const items = resp?.data || resp?.Data || [];
          if (!items.length) return;

          const id = extractBuildingIdFromGovmapItem(items[0]);
          if (!id) return;

          selectedBuildingId = String(id);
          selectedBuildingRows = csvById.get(selectedBuildingId) || null;
          updateStats();

          // optional: zoom to XY from CSV if exists
          const agg = buildingAgg.get(selectedBuildingId);
          if (agg?.anyXY && agg?.x != null && agg?.y != null) {
            try { govmap.zoomToXY({ x: agg.x, y: agg.y, level: 12, marker: true }); } catch (_) {}
          }

          if (currentTab !== "single") switchTab("single");
          else renderSelectedBuilding();
        } catch (err) {
          console.error("click error:", err);
        }
      }

      /* ===================== Address geocode (inside panel) ===================== */
      function parseGeocodeList(resp) {
        const list = resp?.data || resp?.Data || resp?.results || resp;
        if (Array.isArray(list)) return list;
        if (Array.isArray(list?.Result)) return list.Result;
        return [];
      }

      function extractXY(item) {
        const x = item?.X ?? item?.x ?? item?.CenterX ?? item?.centerX ?? item?.Lon ?? item?.lon;
        const y = item?.Y ?? item?.y ?? item?.CenterY ?? item?.centerY ?? item?.Lat ?? item?.lat;
        return { x: Number(x), y: Number(y) };
      }

      function runGeocodeFromUI() {
        const inp = document.getElementById("addrInput");
        const q = String(inp?.value || "").trim();
        if (!q) return;
        runGeocode(q);
      }

      function renderAddrResults(items, query) {
        const box = document.getElementById("addrResults");
        if (!box) return;

        if (!items || !items.length) {
          box.innerHTML = `<div class="msg warn">לא נמצאו תוצאות עבור <strong>${escapeHtml(query)}</strong>.</div>`;
          return;
        }

        box.innerHTML = `
          <div class="msg info">תוצאות כתובת (עד 10): לחץ להתמקדות</div>
          <div class="rankList">
            ${items.map((it, idx) => `
              <div class="rankRow" onclick="focusToGeocodeIdx(${idx})">
                <div class="rankNum">${idx + 1}</div>
                <div style="font-weight:1000;color:#111;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(it.__title || query)}</div>
                <div class="rankVal" style="min-width:80px;">📍</div>
              </div>
              <div class="rankMeta">${escapeHtml(it.__sub || "")}</div>
            `).join("")}
          </div>
        `;
      }

      function runGeocode(query) {
        const q = String(query || "").trim();
        if (!q) return;

        lastGeocodeQuery = q;
        const box = document.getElementById("addrResults");
        if (box) box.innerHTML = `<div class="msg info">מחפש כתובת…</div>`;

        if (!mapInitialized) {
          if (box) box.innerHTML = `<div class="msg warn">המפה עדיין נטענת.</div>`;
          return;
        }

        const myId = ++lastGeocodeReqId;
        lastAddrItems = [];

        let payload = { keyword: q };
        if (govmap.geocodeType?.AccuracyOnly) payload.type = govmap.geocodeType.AccuracyOnly;

        let res;
        try { res = govmap.geocode(payload); }
        catch (e) {
          if (box) box.innerHTML = `<div class="msg err">שגיאה בחיפוש כתובת.</div>`;
          return;
        }

        const onSuccess = (resp) => {
          if (myId !== lastGeocodeReqId) return;
          const list = parseGeocodeList(resp).slice(0, 10);

          const mapped = list.map((r) => {
            const candidates = [
              r?.SettlementName, r?.PlaceName, r?.Name, r?.ResultLabel, r?.Address, r?.Title, r?.label
            ].map((x) => (x == null ? "" : String(x).trim())).filter(Boolean);

            const title = candidates.find(Boolean) || q;
            const sub = String(r?.City || r?.Region || r?.Street || r?.SubTitle || "").trim();
            return { ...r, __title: title, __sub: sub };
          });

          lastAddrItems = mapped;
          renderAddrResults(mapped, q);
        };

        const onFail = () => {
          if (myId !== lastGeocodeReqId) return;
          if (box) box.innerHTML = `<div class="msg err">לא ניתן לבצע חיפוש עבור <strong>${escapeHtml(q)}</strong>.</div>`;
        };

        if (res && typeof res.then === "function") res.then(onSuccess).catch(onFail);
        else if (res && typeof res.done === "function") res.done(onSuccess).fail(onFail);
        else onFail();
      }

      window.focusToGeocodeIdx = function (idx) {
        const it = lastAddrItems[idx];
        if (!it) return;
        const { x, y } = extractXY(it);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return;
        try { govmap.zoomToXY({ x, y, level: 10, marker: true }); } catch (_) {}
      };

      /* ===================== INIT GOVMAP ===================== */
      function initGovMap() {
        loadCsv(); // in parallel

        govmap.createMap("map", {
          token: TOKEN,
          layers: [BUILDINGS_LAYER],
          layersMode: 4,
          background: 3,
          zoomButtons: true,

          // try disabling layer UI (if supported by this govmap version)
          layersButton: false,
          layerList: false,
          showLayerList: false,
          identifyOnClick: false,

          visibleLayers: [BUILDINGS_LAYER],

          onLoad: () => {
            mapInitialized = true;

            // hard hide layers button/panel + force layer always on
            hideLayersUIHard();
            forceBuildingsLayerOn();
            setInterval(forceBuildingsLayerOn, 2000);

            // map click
            try {
              govmap.onEvent(govmap.events.CLICK).progress((e) => {
                const pt = normalizeMapPoint(e);
                onMapClick(pt ? { mapPoint: pt } : e);
              });
            } catch (_) {}

            // stop loading
            const l = document.getElementById("loading");
            if (l) l.style.display = "none";

            refreshHeaderSub();
            updateStats();
            renderCurrentTab();
          },
        });
      }

      /* ===================== expose minimal handlers ===================== */
      window.switchTab = switchTab;
      window.togglePanel = togglePanel;
      window.setOutliersMode = setOutliersMode;
      window.applyThreshold = applyThreshold;
      window.setPreset = setPreset;
      window.selectFromList = selectFromList;
      window.runIdSearch = runIdSearch;
      window.runGeocodeFromUI = runGeocodeFromUI;
      window.initGovMap = initGovMap;
    </script>

    <!-- GOVMAP API -->
    <script src="https://www.govmap.gov.il/govmap/api/govmap.api.js" defer onload="initGovMap()"></script>
  </head>

  <body>
    <div id="loading">
      <div class="spinner"></div>
      <div style="font-weight:1000;color:#333;">טוען מפה…</div>
    </div>

    <div id="map"></div>

    <aside id="panel">
      <div id="panelHeader">
        <div class="row">
          <div>
            <div class="title">SatMap</div>
          </div>
          <div style="display:flex;gap:8px;">
            <button class="hdrBtn" onclick="togglePanel()">☰</button>
          </div>
        </div>
        <div id="panelSub" class="sub">טוען CSV…</div>
      </div>

      <div id="tabs">
        <div class="tab active" data-tab="single" onclick="switchTab('single')">בניין</div>
        <div class="tab" data-tab="outliers" onclick="switchTab('outliers')">חריגים</div>
        <div class="tab" data-tab="search" onclick="switchTab('search')">חיפוש</div>
        <div class="tab" data-tab="about" onclick="switchTab('about')">הסבר</div>
      </div>

      <div id="controls">
        <div class="ctlLabel">מצב</div>
        <div class="seg">
          <button id="btnOutOn" class="segBtn active" onclick="setOutliersMode(true)">🚨 חריגים</button>
          <button id="btnOutOff" class="segBtn" onclick="setOutliersMode(false)">📋 הכל</button>
        </div>

        <div id="stats">
          <div class="stat">
            <div class="statVal" id="statAll">-</div>
            <div class="statLbl">סה״כ IDs</div>
          </div>
          <div class="stat">
            <div class="statVal" id="statOut">-</div>
            <div class="statLbl">חריגים</div>
          </div>
          <div class="stat">
            <div class="statVal" id="statSel">-</div>
            <div class="statLbl">נבחר</div>
          </div>
        </div>
      </div>

      <div id="content"></div>
    </aside>
  </body>
</html>

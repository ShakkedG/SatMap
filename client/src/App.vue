<!DOCTYPE html>
<html lang="he" dir="rtl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>SatMap – בניינים שוקעים (חריגים) | GovMap</title>

    <style>
      * { box-sizing: border-box; }

      html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        overflow: hidden;
        background: #f5f5f5;
        font-size: 15px;
      }

      #map { width: 100%; height: 100%; position: relative; }

      /* hide ESRI widgets if appear */
      .esri-layer-list, .esri-legend { display: none !important; }

      /* ===== Always-open top search bar (copied style) ===== */
      #top-searchbar {
        position: fixed;
        top: 12px;
        left: 50%;
        transform: translateX(-50%);
        width: min(760px, calc(100vw - 24px));
        z-index: 30000;

        background: #fff;
        border-radius: 999px;
        padding: 8px;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.16);
        border: 2px solid rgba(11, 99, 206, 0.35);
        display: flex;
        align-items: center;
        gap: 10px;
      }
      #addrInput {
        flex: 1;
        border: 2px solid #111;
        border-radius: 999px;
        padding: 10px 12px;
        font-weight: 900;
        font-size: 14px;
        outline: none;
        text-align: right;
        direction: rtl;
      }
      #addrBtn {
        padding: 10px 14px;
        background: #0b63ce;
        color: #fff;
        border: none;
        border-radius: 999px;
        cursor: pointer;
        font-weight: 1000;
        font-size: 14px;
        white-space: nowrap;
      }
      #addrBtn:active { transform: translateY(1px); }

      #addrResults {
        position: absolute;
        top: calc(100% + 10px);
        right: 0;
        left: 0;
        display: none;
        border: 1px solid #e0e0e0;
        background: #fff;
        border-radius: 16px;
        overflow: hidden;
        max-height: 320px;
        overflow-y: auto;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.1);
      }
      .addr-item {
        padding: 10px 12px;
        cursor: pointer;
        font-size: 14px;
        border-bottom: 1px solid #f0f0f0;
        font-weight: 900;
      }
      .addr-item:last-child { border-bottom: none; }
      .addr-item:hover { background: #f5f9ff; }
      .addr-sub { font-size: 12.5px; color: #666; margin-top: 3px; font-weight: 800; }

      @media (max-width: 768px) {
        #top-searchbar {
          top: 10px;
          left: 50%;
          transform: translateX(-50%);
          width: calc(100vw - 20px);
        }
      }

      /* PANEL */
      #info-panel {
        position: absolute;
        top: 15px;
        right: 30px;
        z-index: 9999;
        background: white;
        padding: 0;
        border-radius: 14px;
        width: 440px;
        max-height: calc(100vh - 30px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        font-size: 14px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: height 0.2s ease, max-height 0.2s ease;
      }

      #panel-header {
        background: linear-gradient(135deg, #0b63ce 0%, #084eac 100%);
        color: white;
        padding: 14px 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15);
        flex-shrink: 0;
      }
      #panel-header h1 { margin: 0; font-size: 17px; font-weight: 1000; letter-spacing: -0.3px; }
      #panel-header p { margin: 6px 0 0 0; font-size: 13px; opacity: 0.94; line-height: 1.35; font-weight: 900; }

      #header-actions {
        margin-top: 10px;
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
      }
      .hbtn {
        padding: 9px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.35);
        background: rgba(255, 255, 255, 0.16);
        color: #fff;
        font-weight: 1000;
        cursor: pointer;
        display: inline-flex;
        gap: 8px;
        align-items: center;
        user-select: none;
        font-size: 13px;
      }
      .hbtn:active { transform: translateY(1px); }
      .hbtn.secondary { background: rgba(0, 0, 0, 0.12); border-color: rgba(255, 255, 255, 0.22); }

      #tabs {
        display: flex;
        background: #fafafa;
        border-bottom: 2px solid #e6e6e6;
        flex-shrink: 0;
        overflow-x: auto;
      }
      .tab {
        flex: 1;
        padding: 11px 10px;
        text-align: center;
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
        font-size: 13px;
        font-weight: 1000;
        color: #666;
        user-select: none;
        white-space: nowrap;
        min-width: 96px;
      }
      .tab:hover { background: #f2f6ff; color: #2a4c8a; }
      .tab.active { background: white; border-bottom-color: #0b63ce; color: #0b63ce; }

      #controls {
        padding: 12px 14px;
        background: #fafafa;
        border-bottom: 1px solid #e8e8e8;
        flex-shrink: 0;
      }

      .controls-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        align-items: end;
      }
      .ctl label {
        font-weight: 1000;
        font-size: 13px;
        color: #333;
        display: block;
        margin-bottom: 6px;
      }
      .ctl input {
        width: 100%;
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid #cfcfcf;
        font-size: 14px;
        background: white;
        font-weight: 1000;
        outline: none;
      }

      .btn-wide {
        grid-column: 1 / -1;
        padding: 12px;
        border-radius: 14px;
        border: none;
        font-size: 14px;
        font-weight: 1000;
        cursor: pointer;
        box-shadow: 0 10px 24px rgba(11, 99, 206, 0.18);
        background: #0b63ce;
        color: #fff;
      }
      .btn-wide:active { transform: translateY(1px); }
      .btn-wide.danger {
        background: #c62828;
        box-shadow: 0 10px 24px rgba(198, 40, 40, 0.18);
      }
      .btn-wide.gray {
        background: #455a64;
        box-shadow: 0 10px 24px rgba(69, 90, 100, 0.18);
      }

      #info-content {
        padding: 14px;
        overflow-y: auto;
        flex: 1;
        min-height: 0;
        background: white;
      }

      .tab-content { display: none; }
      .tab-content.active { display: block; }

      .message {
        padding: 12px 14px;
        border-radius: 12px;
        margin-bottom: 10px;
        font-size: 13.5px;
        border-right: 4px solid;
        line-height: 1.55;
        font-weight: 900;
      }
      .message-info { background: #e7f3ff; color: #063a73; border-right-color: #0b63ce; }
      .message-warn { background: #fff7e6; color: #6a3f00; border-right-color: #ffb300; }
      .message-error { background: #fff0f0; color: #b20000; border-right-color: #ff0000; }

      .kpi-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 10px;
      }
      .kpi {
        border: 1px solid #eee;
        background: #fafafa;
        border-radius: 14px;
        padding: 10px;
        text-align: center;
      }
      .kpi .v {
        font-weight: 1000;
        font-size: 16px;
        margin-bottom: 4px;
      }
      .kpi .l {
        font-weight: 1000;
        color: #666;
        font-size: 11px;
        letter-spacing: 0.2px;
      }
      .v.ok { color: #0b63ce; }
      .v.bad { color: #c62828; }
      .v.na { color: #666; }

      .outlier-list {
        border: 1px solid #eee;
        border-radius: 16px;
        overflow: hidden;
        background: #fff;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.05);
      }
      .outlier-row {
        display: grid;
        grid-template-columns: 56px 1fr auto;
        gap: 10px;
        align-items: center;
        padding: 11px 12px;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
        background: #fff;
      }
      .outlier-row:nth-child(even) { background: #fafafa; }
      .outlier-row:hover { background: #fff3f3; }
      .pill {
        width: 44px; height: 34px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 1000;
        border: 1px solid #ffd0d0;
        background: #fff0f0;
        color: #b20000;
        direction: ltr;
      }
      .outlier-id { font-weight: 1000; color: #111; direction: ltr; text-align: left; }
      .outlier-rate { font-weight: 1000; color: #c62828; direction: ltr; text-align: left; min-width: 110px; }
      .outlier-rate small { display:block; font-weight: 900; color:#666; font-size:11px; margin-top:2px; }

      /* Loading */
      #loading {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 24px 28px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
        z-index: 10000;
        text-align: center;
      }
      .spinner {
        width: 40px;
        height: 40px;
        margin: 0 auto 14px;
        border: 4px solid #e7e7e7;
        border-top: 4px solid #0b63ce;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      /* Collapse behavior */
      #info-panel.collapsed { max-height: 74px; height: 74px; }
      #info-panel.collapsed #tabs,
      #info-panel.collapsed #controls,
      #info-panel.collapsed #info-content { display: none; }
      #info-panel.collapsed #panel-header { padding: 10px 12px; }
      #info-panel.collapsed #panel-header p { display: none; }
      #info-panel.collapsed #panel-header h1 { font-size: 15px; }
      #info-panel.collapsed #header-actions { margin-top: 0; justify-content: flex-end; }
      #info-panel.collapsed #panelToggleBtn { display: inline-flex; }

      /* Mobile bottom sheet */
      @media (max-width: 768px) {
        #info-panel {
          position: fixed;
          left: 0; right: 0;
          top: auto; bottom: 0;
          width: 100%;
          height: calc(var(--vh, 1vh) * 55);
          max-height: calc(var(--vh, 1vh) * 55);
          border-radius: 20px 20px 0 0;
          overscroll-behavior: contain;
          touch-action: pan-y;
        }
        #panel-header { padding: 10px 12px; }
        #panel-header h1 { font-size: 15px; }
        #panel-header p { margin-top: 4px; font-size: 12px; line-height: 1.25; }
        #header-actions { margin-top: 8px; }
        #header-actions .hbtn { padding: 8px 10px; font-size: 12px; border-radius: 12px; }
        #tabs .tab { padding: 9px 8px; font-size: 12px; min-width: 78px; }
        #controls { padding: 8px 10px; }
        #info-content {
          padding: 10px 10px 16px 10px;
          overflow-y: auto;
          -webkit-overflow-scrolling: touch;
          overscroll-behavior: contain;
          touch-action: pan-y;
        }
      }
    </style>

    <script>
      // ===================== CONFIG =====================
      const TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";
      const BUILDINGS_LAYER = "225287";

      // עדכן לשם הקובץ אצלך:
      const INSAR_CSV_URL = "insar_buildings.csv";

      // מצב חריגים: חריג = rate <= threshold (למשל -2 mm/yr)
      let threshold = -2.0;
      let highlightOutliersOnMapEnabled = false;

      // ===================== STATE =====================
      let mapInitialized = false;

      // Insar DB: objectid(string) -> row
      const insarById = new Map(); // { id, rate, extra1, extra2 }
      let insarLoaded = false;
      let insarLoadError = null;

      // detected field name on govmap layer for objectid (OBJECTID vs objectid)
      let objectIdFieldName = null;

      // selection
      let selectedObjectId = null;
      let selectedAttrs = null;

      // outliers cache
      let outliersSorted = []; // [{id, rate, row}]
      const OUTLIERS_MAX_HIGHLIGHT = 50;

      // Address search state
      let lastGeocodeReqId = 0;
      let lastAddrItems = [];
      let lastGeocodeQuery = "";
      let searchTimeout = null;

      // ===================== HELPERS =====================
      function escapeHtml(s) {
        return String(s ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
      }

      function fmtNum(n, digits = 1) {
        const x = Number(n);
        if (!Number.isFinite(x)) return "—";
        return x.toLocaleString(undefined, { maximumFractionDigits: digits });
      }

      function toFiniteNum(v) {
        if (v == null) return null;
        if (typeof v === "string") {
          let s = v.trim();
          if (!s) return null;
          // comma/dot handling
          if (s.includes(",") && s.includes(".")) s = s.replace(/,/g, "");
          else if (s.includes(",") && !s.includes(".")) s = s.replace(/,/g, ".");
          const n = Number(s);
          return Number.isFinite(n) ? n : null;
        }
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
      }

      function setMobileVh() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty("--vh", `${vh}px`);
      }
      setMobileVh();
      window.addEventListener("resize", setMobileVh);
      if (window.visualViewport) window.visualViewport.addEventListener("resize", setMobileVh);

      function showMessage(type, html) {
        const box = document.getElementById("single-body");
        if (!box) return;
        box.innerHTML = `<div class="message message-${type}">${html}</div>`;
      }

      function switchTab(tabName) {
        document.querySelectorAll(".tab").forEach((t) => {
          t.classList.toggle("active", t.dataset.tab === tabName);
        });
        document.querySelectorAll(".tab-content").forEach((c) => {
          c.classList.toggle("active", c.id === `tab-${tabName}`);
        });

        if (tabName === "single") renderSelected();
        if (tabName === "outliers") renderOutliers();
        if (tabName === "about") renderAbout();
      }

      function togglePanel() {
        const panel = document.getElementById("info-panel");
        if (!panel) return;
        panel.classList.toggle("collapsed");
        const btn = document.getElementById("panelToggleBtn");
        if (btn) {
          const collapsed = panel.classList.contains("collapsed");
          btn.textContent = collapsed ? "➕ הגדל" : "➖ הקטן";
        }
      }

      // ===================== CSV LOAD & OUTLIERS =====================
      function guessColumns(headers) {
        const norm = (s) => String(s || "").trim().toLowerCase().replace(/\s+/g, "");
        const hs = (headers || []).map(norm);

        const pick = (cands) => {
          for (const c of cands) {
            const i = hs.indexOf(norm(c));
            if (i >= 0) return i;
          }
          // partial match
          for (let i = 0; i < hs.length; i++) {
            for (const c of cands) if (hs[i].includes(norm(c))) return i;
          }
          return -1;
        };

        const idIdx = pick(["objectid", "OBJECTID", "id", "buildingid", "bldg_id", "bldgid"]);
        const rateIdx = pick(["rate", "velocity", "v", "mm/yr", "mmyr", "subsidence", "sink", "delta", "dh"]);

        return { idIdx, rateIdx };
      }

      function parseCsvText(text) {
        const lines = String(text || "")
          .replace(/\r/g, "")
          .split("\n")
          .map((l) => l.trim())
          .filter((l) => l && !l.startsWith("#"));

        if (!lines.length) return { ok: false, err: "הקובץ ריק" };

        const split = (line) => {
          // simple CSV split (no quotes handling because your file is numeric/simple)
          // supports comma or semicolon
          const delim = line.includes(";") && !line.includes(",") ? ";" : ",";
          return line.split(delim).map((x) => x.trim());
        };

        const first = split(lines[0]);
        const hasHeader = first.some((c) => /[a-zA-Zא-ת]/.test(c));
        let headers = null;
        let start = 0;

        if (hasHeader) {
          headers = first;
          start = 1;
        }

        const colGuess = headers ? guessColumns(headers) : { idIdx: 0, rateIdx: -1 };

        // fallback rules if no header / couldn't detect rate:
        // - if 2 cols: [id, rate]
        // - if >=3 cols: [id, last] as rate
        let rowsParsed = 0;

        for (let i = start; i < lines.length; i++) {
          const cols = split(lines[i]);
          if (cols.length < 2) continue;

          const idIdx = colGuess.idIdx >= 0 ? colGuess.idIdx : 0;
          let rateIdx = colGuess.rateIdx;

          if (rateIdx < 0) {
            if (cols.length === 2) rateIdx = 1;
            else rateIdx = cols.length - 1;
          }

          const id = cols[idIdx];
          const rate = toFiniteNum(cols[rateIdx]);

          if (!id) continue;
          if (rate == null) {
            // "אין נתונים" -> לא חריג
            insarById.set(String(id).trim(), { id: String(id).trim(), rate: null, cols });
            rowsParsed++;
            continue;
          }

          insarById.set(String(id).trim(), { id: String(id).trim(), rate, cols });
          rowsParsed++;
        }

        return { ok: true, rows: rowsParsed, hasHeader, headers };
      }

      async function loadInsarCsv() {
        insarLoaded = false;
        insarLoadError = null;
        insarById.clear();

        try {
          const res = await fetch(INSAR_CSV_URL, { cache: "no-store" });
          if (!res.ok) throw new Error(`fetch failed (${res.status})`);
          const text = await res.text();
          const parsed = parseCsvText(text);
          if (!parsed.ok) throw new Error(parsed.err || "CSV parse error");

          insarLoaded = true;
          recomputeOutliers();
          renderSelected();
          renderOutliers();

          console.log("✅ InSAR CSV loaded:", insarById.size, "rows");
        } catch (e) {
          insarLoadError = e;
          console.error("❌ Failed loading InSAR CSV:", e);
          renderSelected();
          renderOutliers();
        }
      }

      function recomputeOutliers() {
        const t = Number(threshold);
        const tmp = [];

        for (const [id, row] of insarById.entries()) {
          const r = row?.rate;
          if (!Number.isFinite(r)) continue; // אין נתונים -> לא חריג
          if (r <= t) tmp.push({ id, rate: r, row });
        }

        tmp.sort((a, b) => (a.rate - b.rate)); // הכי שלילי ראשון (הכי חריג)
        outliersSorted = tmp;
      }

      // ===================== GOVMAP DATA (click identify) =====================
      function fieldsToObject(fields) {
        if (!Array.isArray(fields)) return fields;
        const obj = {};
        for (const f of fields) if (f?.FieldName) obj[f.FieldName] = f.Value;
        return obj;
      }

      function detectObjectIdField(attrsObj) {
        if (!attrsObj || typeof attrsObj !== "object") return null;
        const keys = Object.keys(attrsObj);
        const found = keys.find((k) => String(k).toLowerCase() === "objectid");
        return found || null;
      }

      function getObjectIdFromAttrs(attrsObj) {
        if (!attrsObj || typeof attrsObj !== "object") return null;
        // try common keys
        const candidates = ["objectid", "OBJECTID", "ObjectID"];
        for (const c of candidates) {
          if (attrsObj[c] != null && String(attrsObj[c]).trim() !== "") return String(attrsObj[c]).trim();
        }
        // fallback: scan
        for (const k of Object.keys(attrsObj)) {
          if (String(k).toLowerCase() === "objectid") return String(attrsObj[k]).trim();
        }
        return null;
      }

      function normalizeMapPoint(input) {
        const mp = input?.mapPoint ?? input?.Point ?? input ?? null;
        if (!mp) return null;
        const x = mp.x ?? mp.X ?? mp.lon ?? mp.Lon ?? mp.centerX ?? mp.CenterX;
        const y = mp.y ?? mp.Y ?? mp.lat ?? mp.Lat ?? mp.centerY ?? mp.CenterY;
        const nx = Number(x);
        const ny = Number(y);
        if (!Number.isFinite(nx) || !Number.isFinite(ny)) return null;
        return { x: nx, y: ny };
      }

      async function onMapClick(e) {
        if (!mapInitialized) return;
        const pt = normalizeMapPoint(e);
        if (!pt) return;

        try {
          // This is the same call style you already used successfully
          const resp = await govmap.getLayerData({
            LayerName: BUILDINGS_LAYER,
            Point: { x: pt.x, y: pt.y, X: pt.x, Y: pt.y },
            Radius: 80,
          });

          const items = resp?.data || resp?.Data || [];
          if (!items.length) {
            selectedObjectId = null;
            selectedAttrs = null;
            renderSelected();
            showMessage("info", "לא נמצא בניין באזור הלחיצה.");
            return;
          }

          const first = items[0];
          const attrsRaw = first.Fields || first.Attributes || first;
          const attrsObj = fieldsToObject(attrsRaw) || attrsRaw || {};

          // detect objectid field name once
          const detected = detectObjectIdField(attrsObj);
          if (detected) objectIdFieldName = detected;

          const oid = getObjectIdFromAttrs(attrsObj);
          if (!oid) {
            selectedObjectId = null;
            selectedAttrs = attrsObj;
            renderSelected();
            showMessage(
              "error",
              `זוהה בניין אבל לא נמצא שדה OBJECTID.<br/>שדות: <span style="direction:ltr;unicode-bidi:bidi-override">${escapeHtml(Object.keys(attrsObj).join(" | "))}</span>`
            );
            return;
          }

          selectedObjectId = String(oid);
          selectedAttrs = attrsObj;

          // visually highlight the selected building (blue) without turning layers UI on
          await highlightSelectionByIds([selectedObjectId], true);

          renderSelected();
        } catch (error) {
          console.error("❌ Error in onMapClick:", error);
          selectedObjectId = null;
          selectedAttrs = null;
          renderSelected();
          showMessage("error", `אירעה שגיאה: ${escapeHtml(error?.message || "שגיאה לא מוגדרת")}`);
        }
      }

      // ===================== MAP HIGHLIGHT (Outliers / Selected) =====================
      function buildWhereIn(field, ids) {
        const safe = (ids || []).map((x) => Number(String(x).trim())).filter((n) => Number.isFinite(n));
        if (!safe.length) return "(1=0)";
        return `(${field} IN (${safe.join(",")}))`;
      }

      async function selectFeatures(whereClause, zoom) {
        const params = {
          continous: false,
          filterLayer: false,
          isZoomToExtent: !!zoom,
          layers: [BUILDINGS_LAYER],
          returnFields: { [BUILDINGS_LAYER]: ["objectid"] },
          selectOnMap: true,
          whereClause: { [BUILDINGS_LAYER]: whereClause },
        };
        return govmap.selectFeaturesOnMap(params);
      }

      async function highlightSelectionByIds(ids, zoom) {
        if (!mapInitialized || !govmap.selectFeaturesOnMap) return;

        const fieldCandidates = [];
        if (objectIdFieldName) fieldCandidates.push(objectIdFieldName);
        fieldCandidates.push("objectid", "OBJECTID");

        const list = (ids || []).slice(0, OUTLIERS_MAX_HIGHLIGHT);
        if (!list.length) return;

        let lastErr = null;
        for (const f of fieldCandidates) {
          try {
            const where = buildWhereIn(f, list);
            await selectFeatures(where, zoom);
            return;
          } catch (e) {
            lastErr = e;
          }
        }

        console.warn("highlightSelectionByIds failed:", lastErr);
      }

      async function clearSelection() {
        if (!mapInitialized || !govmap.selectFeaturesOnMap) return;
        try {
          await selectFeatures("(1=0)", false);
        } catch (_) {
          try { govmap.returnToDefaultTool && govmap.returnToDefaultTool(); } catch (_) {}
        }
        try { govmap.closeBubble && govmap.closeBubble(); } catch (_) {}
      }

      async function applyOutliersHighlightIfNeeded() {
        if (!highlightOutliersOnMapEnabled) return;
        if (!mapInitialized) return;

        const ids = outliersSorted.slice(0, OUTLIERS_MAX_HIGHLIGHT).map((o) => o.id);
        if (!ids.length) {
          await clearSelection();
          return;
        }

        // select outliers (no zoom) - highlights on map
        await highlightSelectionByIds(ids, false);
      }

      // ===================== UI RENDER =====================
      function renderSelected() {
        const box = document.getElementById("single-body");
        if (!box) return;

        if (insarLoadError) {
          box.innerHTML = `<div class="message message-error">
            לא הצלחתי לטעון את קובץ ה־CSV של InSAR.<br/>
            בדוק שהקובץ <strong style="direction:ltr;unicode-bidi:bidi-override">${escapeHtml(INSAR_CSV_URL)}</strong> נמצא באותו תיקייה של index.html ב־GitHub Pages.
          </div>`;
          return;
        }

        if (!insarLoaded) {
          box.innerHTML = `<div class="message message-info">טוען נתוני InSAR…</div>`;
          return;
        }

        if (!selectedObjectId) {
          box.innerHTML = `<div class="message message-info">
            לחץ על בניין במפה כדי לראות נתונים.<br/>
            טיפ: השתמש בחיפוש כתובת למעלה כדי להתמקד ואז לחץ על הבניין.
          </div>`;
          return;
        }

        const row = insarById.get(String(selectedObjectId));
        const rate = row?.rate;

        const isOutlier = Number.isFinite(rate) && rate <= Number(threshold);

        const rateText = Number.isFinite(rate) ? `${fmtNum(rate, 1)} mm/yr` : "אין נתונים";
        const rateClass = Number.isFinite(rate) ? (isOutlier ? "bad" : "ok") : "na";

        const statusMsg = Number.isFinite(rate)
          ? (isOutlier
              ? `<div class="message message-warn"><strong>חריג:</strong> קצב שקיעה נמוך מהסף (${fmtNum(threshold, 1)} mm/yr).</div>`
              : `<div class="message message-info">הבניין לא חריג לפי הסף הנוכחי (${fmtNum(threshold, 1)} mm/yr).</div>`)
          : `<div class="message message-info">אין התאמה ב־CSV לבניין הזה, לכן הוא <strong>לא</strong> נספר כחריג.</div>`;

        const extraFields = selectedAttrs ? Object.keys(selectedAttrs).slice(0, 6) : [];

        box.innerHTML = `
          <div class="kpi-row">
            <div class="kpi">
              <div class="v ${rateClass}">${escapeHtml(rateText)}</div>
              <div class="l">קצב (מה־CSV)</div>
            </div>
            <div class="kpi">
              <div class="v ok" style="direction:ltr;text-align:center;">${escapeHtml(String(selectedObjectId))}</div>
              <div class="l">OBJECTID</div>
            </div>
            <div class="kpi">
              <div class="v ${isOutlier ? "bad" : "ok"}">${isOutlier ? "כן" : "לא"}</div>
              <div class="l">חריג לפי סף</div>
            </div>
          </div>

          ${statusMsg}

          <button class="btn-wide gray" onclick="zoomToSelected()">🎯 התמקדות לבניין</button>
          <button class="btn-wide ${highlightOutliersOnMapEnabled ? "danger" : "danger"}" onclick="toggleOutliersHighlight()">
            ${highlightOutliersOnMapEnabled ? "🟥 הדגשת חריגים: פעיל (כבה)" : "🟥 הדגש חריגים על המפה (טופ 50)"}
          </button>

          ${selectedAttrs ? `
            <div class="message message-info">
              שדות לדוגמה מהשכבה (לבדיקה):<br/>
              <span style="direction:ltr;unicode-bidi:bidi-override">${escapeHtml(extraFields.join(" | "))}${selectedAttrs && Object.keys(selectedAttrs).length > 6 ? " | …" : ""}</span>
            </div>
          ` : ""}
        `;
      }

      function renderOutliers() {
        const box = document.getElementById("outliers-body");
        if (!box) return;

        if (insarLoadError) {
          box.innerHTML = `<div class="message message-error">
            אין נתוני חריגים כי ה־CSV לא נטען.
          </div>`;
          return;
        }
        if (!insarLoaded) {
          box.innerHTML = `<div class="message message-info">טוען נתוני InSAR…</div>`;
          return;
        }

        const count = outliersSorted.length;

        let html = `
          <div class="message message-info">
            סף חריגים: <strong style="direction:ltr;unicode-bidi:bidi-override">${fmtNum(threshold, 1)} mm/yr</strong><br/>
            חריגים (עם נתונים בלבד): <strong>${count.toLocaleString()}</strong><br/>
            מודגשים על המפה: <strong>טופ ${OUTLIERS_MAX_HIGHLIGHT}</strong> (אם הדגשה פעילה)
          </div>

          <button class="btn-wide ${highlightOutliersOnMapEnabled ? "danger" : "danger"}" onclick="toggleOutliersHighlight()">
            ${highlightOutliersOnMapEnabled ? "🟥 הדגשת חריגים: פעיל (כבה)" : "🟥 הדגש חריגים על המפה (טופ 50)"}
          </button>
        `;

        if (!count) {
          html += `<div class="message message-warn">לא נמצאו חריגים לפי הסף הנוכחי.</div>`;
          box.innerHTML = html;
          return;
        }

        const top = outliersSorted.slice(0, 200); // רשימה ל־UI (עד 200)

        html += `<div class="outlier-list">`;
        top.forEach((o, idx) => {
          html += `
            <div class="outlier-row" onclick="selectOutlier('${escapeHtml(o.id)}')">
              <div class="pill">${idx + 1}</div>
              <div class="outlier-id">${escapeHtml(o.id)}</div>
              <div class="outlier-rate">
                ${fmtNum(o.rate, 1)} mm/yr
                <small>לחץ כדי להתמקד ולהדגיש</small>
              </div>
            </div>
          `;
        });
        html += `</div>`;

        box.innerHTML = html;
      }

      function renderAbout() {
        const box = document.getElementById("about-body");
        if (!box) return;

        box.innerHTML = `
          <div class="message message-info">
            <strong>איך זה עובד (בקצרה)</strong><br/>
            1) שכבת הבניינים תמיד דלוקה ב־GovMap.<br/>
            2) הנתונים (CSV) נטענים מהאתר שלך (GitHub Pages / localhost).<br/>
            3) “חריג” = ערך קצב (mm/yr) קטן/שווה לסף שהגדרת (למשל -2).<br/>
            4) “אין נתונים” (אין שורה ב־CSV / ערך לא מספרי) – <strong>לא</strong> נחשב חריג ולא מודגש.
          </div>

          <div class="message message-warn">
            <strong>מה צריך בריפו:</strong><br/>
            - index.html (הקובץ הזה)<br/>
            - <span style="direction:ltr;unicode-bidi:bidi-override"><strong>${escapeHtml(INSAR_CSV_URL)}</strong></span> (CSV InSAR)
          </div>
        `;
      }

      // ===================== UI ACTIONS =====================
      async function zoomToSelected() {
        if (!selectedObjectId) return;
        await highlightSelectionByIds([selectedObjectId], true);
      }

      async function selectOutlier(id) {
        selectedObjectId = String(id);
        selectedAttrs = null; // לא חובה
        await highlightSelectionByIds([selectedObjectId], true);
        switchTab("single");
      }

      async function toggleOutliersHighlight() {
        highlightOutliersOnMapEnabled = !highlightOutliersOnMapEnabled;
        await applyOutliersHighlightIfNeeded();
        renderSelected();
        renderOutliers();
      }

      function onThresholdChanged(v) {
        const n = toFiniteNum(v);
        if (n == null) return;
        threshold = n;
        recomputeOutliers();
        renderSelected();
        renderOutliers();
        // לא מדגיש אוטומטית כדי לא “לקפוץ”/להעמיס – רק אם המשתמש הפעיל הדגשה
        applyOutliersHighlightIfNeeded();
      }

      // ===================== ADDRESS SEARCH (same behavior/style) =====================
      function getAddrEls() {
        const root = document.getElementById("top-searchbar");
        if (!root) return { root: null, input: null, btn: null, box: null };
        return {
          root,
          input: root.querySelector("#addrInput"),
          btn: root.querySelector("#addrBtn"),
          box: root.querySelector("#addrResults"),
        };
      }

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

      function isBadTitle(t) {
        const s = String(t ?? "").trim();
        if (!s) return true;
        const low = s.toLowerCase();
        return (s === "תוצאה" || low === "result" || low === "results" || low === "unknown");
      }

      function setAddrLoading(msg) {
        const { box } = getAddrEls();
        if (!box) return;
        box.style.display = "block";
        box.innerHTML = `<div class="addr-item">${escapeHtml(msg || "מחפש…")}</div>`;
      }

      function renderAddrResults(items) {
        const { box } = getAddrEls();
        if (!box) return;

        lastAddrItems = items || [];

        if (!items || !items.length) {
          box.style.display = "block";
          box.innerHTML = `<div class="addr-item">לא נמצאו תוצאות</div>`;
          return;
        }

        box.style.display = "block";
        box.innerHTML = items.map((it, idx) => {
          const title = escapeHtml(it.__title || lastGeocodeQuery || "תוצאה");
          const sub = escapeHtml(it.__sub || "");
          return `
            <div class="addr-item" data-idx="${idx}">
              <div style="font-weight:1000; color:#111;">${title}</div>
              ${sub ? `<div class="addr-sub">${sub}</div>` : ""}
            </div>
          `;
        }).join("");

        box.querySelectorAll(".addr-item").forEach((el) => {
          el.addEventListener("click", () => {
            const idx = Number(el.dataset.idx);
            const picked = lastAddrItems[idx];
            if (picked) focusToGeocodeItem(picked);
            box.style.display = "none";
          });
        });
      }

      function focusToGeocodeItem(item) {
        if (!mapInitialized) return;
        const { x, y } = extractXY(item);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return;

        try { govmap.zoomToXY({ x, y, level: 10, marker: true }); } catch (_) {}

        const label = !isBadTitle(item.__title) ? item.__title : (lastGeocodeQuery || "תוצאה");
        const box = document.getElementById("single-body");
        if (box && !selectedObjectId) {
          showMessage("info", `התמקדתי לכתובת: <strong>${escapeHtml(label)}</strong><br/>עכשיו לחץ על הבניין כדי לראות נתונים.`);
        }
      }

      function runGeocode(query) {
        const q = String(query || "").trim();
        if (!q) return;

        lastGeocodeQuery = q;

        if (!mapInitialized) return;

        const myId = ++lastGeocodeReqId;
        setAddrLoading("מחפש כתובת…");

        const payload = { keyword: q };
        if (govmap.geocodeType?.AccuracyOnly) payload.type = govmap.geocodeType.AccuracyOnly;

        let res;
        try { res = govmap.geocode(payload); }
        catch (_) {
          renderAddrResults([]);
          return;
        }

        const onSuccess = (resp) => {
          if (myId !== lastGeocodeReqId) return;

          const list = parseGeocodeList(resp);
          if (!list || !list.length) {
            renderAddrResults([]);
            return;
          }

          const mapped = list.slice(0, 10).map((r) => {
            const candidates = [
              r?.SettlementName, r?.settlementName,
              r?.PlaceName, r?.placeName,
              r?.Name, r?.name,
              r?.ResultLabel, r?.resultLabel,
              r?.Address, r?.address,
              r?.Title, r?.title,
              r?.label,
            ].map((x) => (x == null ? "" : String(x).trim())).filter(Boolean);

            let title = candidates.find((t) => !isBadTitle(t)) || q;
            let sub = r?.City || r?.city || r?.Region || r?.region || r?.Street || r?.street || r?.SubTitle || r?.subTitle || "";
            sub = String(sub || "").trim();
            return { ...r, __title: title, __sub: sub };
          });

          renderAddrResults(mapped);
        };

        const onFail = () => {
          if (myId !== lastGeocodeReqId) return;
          renderAddrResults([]);
        };

        if (res && typeof res.then === "function") res.then(onSuccess).catch(onFail);
        else if (res && typeof res.done === "function") res.done(onSuccess).fail(onFail);
        else onFail();
      }

      function initAddressSearchUI() {
        const { input, btn, box } = getAddrEls();
        if (!input || !btn || !box) return;

        btn.addEventListener("click", () => {
          const q = String(input.value || "").trim();
          if (!q) return;

          const sameQuery = String(lastGeocodeQuery || "").trim() === q;
          if (sameQuery && Array.isArray(lastAddrItems) && lastAddrItems.length) {
            const exact = lastAddrItems.find((it) => String(it?.__title || "").trim() === q) || lastAddrItems[0];
            focusToGeocodeItem(exact);
            box.style.display = "none";
            return;
          }
          runGeocode(q);
        });

        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") { e.preventDefault(); btn.click(); }
          if (e.key === "Escape") box.style.display = "none";
        });

        input.addEventListener("input", () => {
          if (searchTimeout) clearTimeout(searchTimeout);
          const v = input.value.trim();
          if (v.length < 3) {
            box.style.display = "none";
            return;
          }
          searchTimeout = setTimeout(() => runGeocode(v), 350);
        });

        document.addEventListener("click", (e) => {
          if (!box.contains(e.target) && e.target !== input && e.target !== btn) {
            box.style.display = "none";
          }
        });
      }

      // ===================== GOVMAP INIT =====================
      function initGovMap() {
        // Load CSV immediately (even before map load is OK)
        loadInsarCsv();

        // init UI controls
        const th = document.getElementById("thresholdInput");
        if (th) {
          th.value = String(threshold);
          th.addEventListener("change", (e) => onThresholdChanged(e.target.value));
          th.addEventListener("input", (e) => onThresholdChanged(e.target.value));
        }

        const toggleBtn = document.getElementById("panelToggleBtn");
        if (toggleBtn) toggleBtn.addEventListener("click", togglePanel);

        // Create map: layersMode 4 => hides layers button
        govmap.createMap("map", {
          token: TOKEN,
          layers: [BUILDINGS_LAYER],
          visibleLayers: [BUILDINGS_LAYER],
          layersMode: 4,          // ✅ אין כפתור שכבות
          background: 3,
          zoomButtons: true,
          identifyOnClick: false,
          isEmbeddedToggle: false,
          onLoad: () => {
            mapInitialized = true;

            try {
              govmap.onEvent(govmap.events.CLICK).progress((e) => {
                const pt = normalizeMapPoint(e);
                if (!pt) return;
                onMapClick({ mapPoint: pt, __fromGovmap: true });
              });
            } catch (_) {}

            initAddressSearchUI();

            const l = document.getElementById("loading");
            if (l) l.style.display = "none";

            // default tab
            switchTab("single");
            renderAbout();

            console.log("✅ Map initialized");
          },
        });
      }

      // Expose for inline onclick
      window.initGovMap = initGovMap;
      window.switchTab = switchTab;
      window.togglePanel = togglePanel;
      window.toggleOutliersHighlight = toggleOutliersHighlight;
      window.zoomToSelected = zoomToSelected;
      window.selectOutlier = selectOutlier;
    </script>

    <script src="https://www.govmap.gov.il/govmap/api/govmap.api.js" defer onload="initGovMap()"></script>
  </head>

  <body>
    <div id="loading">
      <div class="spinner"></div>
      <div style="font-size: 14px; color: #333; font-weight: 1000">טוען מפה…</div>
    </div>

    <div id="map"></div>

    <!-- Top Always-Open Search Bar (CrimesMap style) -->
    <div id="top-searchbar">
      <button id="addrBtn" type="button">חפש</button>
      <input id="addrInput" type="text" placeholder="לדוגמה: דיזנגוף 50 תל אביב" autocomplete="off" />
      <div id="addrResults"></div>
    </div>

    <div id="info-panel">
      <div id="panel-header">
        <h1>🏢 SatMap – בניינים שוקעים</h1>
        <p>
          שכבה: <strong>בניינים</strong> • חריג = <strong>rate ≤ סף</strong><br />
          “אין נתונים” לא נחשב חריג ולא מודגש
        </p>

        <div id="header-actions">
          <button class="hbtn secondary" onclick="switchTab('about')">ℹ️ אודות</button>
          <button id="panelToggleBtn" class="hbtn secondary" title="כיווץ/הרחבה">➖ הקטן</button>
        </div>
      </div>

      <div id="tabs">
        <div class="tab active" data-tab="single" onclick="switchTab('single')">נבחר</div>
        <div class="tab" data-tab="outliers" onclick="switchTab('outliers')">חריגים</div>
        <div class="tab" data-tab="about" onclick="switchTab('about')">הסבר</div>
      </div>

      <div id="controls">
        <div class="controls-grid">
          <div class="ctl">
            <label>סף חריגים (mm/yr)</label>
            <input id="thresholdInput" type="number" step="0.5" />
          </div>
          <div class="ctl">
            <label>הערה</label>
            <div style="padding:10px 12px;border:1px solid #e7e7e7;border-radius:12px;background:#fff;font-weight:900;font-size:13px;color:#333">
              לדוגמה: -2 מסמן שקיעה חשודה
            </div>
          </div>
        </div>
      </div>

      <div id="info-content">
        <div class="tab-content active" id="tab-single">
          <div id="single-body"></div>
        </div>

        <div class="tab-content" id="tab-outliers">
          <div id="outliers-body"></div>
        </div>

        <div class="tab-content" id="tab-about">
          <div id="about-body"></div>
        </div>
      </div>
    </div>
  </body>
</html>

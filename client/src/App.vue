<!DOCTYPE html>
<html lang="he" dir="rtl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>SatMap – Buildings + CSV (Outliers)</title>

    <style>
      * {
        box-sizing: border-box;
      }

      html,
      body {
        margin: 0;
        padding: 0;
        height: 100%;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        overflow: hidden;
        background: #f5f5f5;
        font-size: 15px;
      }

      #map {
        width: 100%;
        height: 100%;
        position: relative;
      }

      /* hide ESRI widgets if appear */
      .esri-layer-list,
      .esri-legend {
        display: none !important;
      }

      /* ===== Top Always-Open Search Bar (CrimesMap-like) ===== */
      #top-searchbar {
        position: fixed;
        top: 12px;
        left: 50%;
        transform: translateX(-50%);
        width: min(980px, calc(100vw - 24px));
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

      .pillBtn {
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
      .pillBtn.secondary {
        background: #084eac;
      }
      .pillBtn:active {
        transform: translateY(1px);
      }

      .pillInput {
        flex: 1;
        border: 2px solid #111;
        border-radius: 999px;
        padding: 10px 12px;
        font-weight: 900;
        font-size: 14px;
        outline: none;
        text-align: right;
        direction: rtl;
        min-width: 160px;
      }
      .pillInput.ltr {
        direction: ltr;
        text-align: left;
      }

      #addrResults,
      #idResults {
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

      .dropSectionTitle {
        padding: 10px 12px;
        background: #f6f6f6;
        font-weight: 1000;
        color: #333;
        border-bottom: 1px solid #eee;
      }

      .addr-item {
        padding: 10px 12px;
        cursor: pointer;
        font-size: 14px;
        border-bottom: 1px solid #f0f0f0;
        font-weight: 900;
      }
      .addr-item:last-child {
        border-bottom: none;
      }
      .addr-item:hover {
        background: #f5f9ff;
      }
      .addr-sub {
        font-size: 12.5px;
        color: #666;
        margin-top: 3px;
        font-weight: 800;
      }

      @media (max-width: 768px) {
        #top-searchbar {
          top: 10px;
          width: calc(100vw - 20px);
          flex-wrap: wrap;
          border-radius: 18px;
        }
        .pillInput {
          flex: 1 1 100%;
          min-width: 0;
        }
        .pillBtn {
          flex: 1 1 auto;
        }
      }

      /* ===== Loading ===== */
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
        0% {
          transform: rotate(0deg);
        }
        100% {
          transform: rotate(360deg);
        }
      }

      /* ===== PANEL (CrimesMap-like) ===== */
      #info-panel {
        position: absolute;
        top: 15px;
        right: 30px;
        z-index: 9999;
        background: white;
        padding: 0;
        border-radius: 14px;
        width: 460px;
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
      #panel-header h1 {
        margin: 0;
        font-size: 17px;
        font-weight: 1000;
        letter-spacing: -0.3px;
      }
      #panel-header p {
        margin: 6px 0 0 0;
        font-size: 13px;
        opacity: 0.94;
        line-height: 1.35;
        font-weight: 900;
      }

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
      .hbtn:active {
        transform: translateY(1px);
      }
      .hbtn.secondary {
        background: rgba(0, 0, 0, 0.12);
        border-color: rgba(255, 255, 255, 0.22);
      }

      #tabs {
        display: flex;
        gap: 0;
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
      .tab:hover {
        background: #f2f6ff;
        color: #2a4c8a;
      }
      .tab.active {
        background: white;
        border-bottom-color: #0b63ce;
        color: #0b63ce;
      }

      #controls {
        padding: 12px 14px;
        background: #fafafa;
        border-bottom: 1px solid #e8e8e8;
        flex-shrink: 0;
      }

      .mode-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 10px;
      }
      .mode-btn {
        padding: 11px 10px;
        border-radius: 12px;
        border: 2px solid #e3e3e3;
        background: white;
        cursor: pointer;
        font-size: 13px;
        font-weight: 1000;
        color: #444;
        transition: all 0.15s ease;
        user-select: none;
        text-align: center;
        box-shadow: 0 1px 0 rgba(0, 0, 0, 0.02);
      }
      .mode-btn:hover {
        border-color: #0b63ce;
        color: #0b63ce;
      }
      .mode-btn.active {
        background: #0b63ce;
        border-color: #0b63ce;
        color: white;
        box-shadow: 0 8px 20px rgba(11, 99, 206, 0.18);
      }
      .mode-btn.disabled {
        opacity: 0.55;
        cursor: not-allowed !important;
        border-color: #ddd !important;
        color: #666 !important;
        background: #fff !important;
        pointer-events: none;
        box-shadow: none;
      }
      .mode-btn.full {
        grid-column: 1 / -1;
      }
      .mode-btn.primary {
        font-size: 14px;
        padding: 13px 10px;
        border-width: 3px;
      }

      #quick-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
      }
      .stat-card {
        background: white;
        padding: 12px;
        border-radius: 14px;
        text-align: center;
        border: 1px solid #e7e7e7;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
      }
      .stat-value {
        font-size: 18px;
        font-weight: 1000;
        color: #0b63ce;
        margin-bottom: 3px;
        direction: ltr;
      }
      .stat-label {
        font-size: 12px;
        color: #777;
        font-weight: 1000;
        letter-spacing: 0.2px;
      }

      #info-content {
        padding: 14px;
        overflow-y: auto;
        flex: 1;
        min-height: 0;
        background: white;
      }

      .tab-content {
        display: none;
      }
      .tab-content.active {
        display: block;
      }

      #info-title {
        font-weight: 1000;
        font-size: 16px;
        margin-bottom: 12px;
        color: #111;
        padding-bottom: 8px;
        border-bottom: 3px solid #0b63ce;
      }
      #info-body {
        line-height: 1.6;
        color: #444;
      }

      .message {
        padding: 12px 14px;
        border-radius: 12px;
        margin-bottom: 10px;
        font-size: 13.5px;
        border-right: 4px solid;
        line-height: 1.55;
        font-weight: 900;
      }
      .message-info {
        background: #e7f3ff;
        color: #063a73;
        border-right-color: #0b63ce;
      }
      .message-warn {
        background: #fff7e6;
        color: #6a3f00;
        border-right-color: #ffb300;
      }
      .message-error {
        background: #fff0f0;
        color: #b20000;
        border-right-color: #ff0000;
      }

      .total-summary {
        font-size: 24px;
        font-weight: 1000;
        color: #0b63ce;
        margin: 12px 0 10px 0;
        text-align: center;
        padding: 14px;
        background: linear-gradient(135deg, #e7f3ff 0%, #f3f8ff 100%);
        border-radius: 14px;
        border: 2px solid #b3d9ff;
        direction: ltr;
      }

      .badgeRow {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        margin-bottom: 12px;
      }
      .badge {
        font-size: 12px;
        font-weight: 1000;
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid #e0e0e0;
        background: #fafafa;
        color: #333;
      }
      .badge-warn {
        border-color: #ffcc80;
        background: #fff7e6;
        color: #6a3f00;
      }
      .badge-good {
        border-color: #b7e3c6;
        background: #ecfff2;
        color: #0b6b2f;
      }
      .badge-bad {
        border-color: #ffb3b3;
        background: #fff0f0;
        color: #b20000;
      }

      /* Outliers list (CrimesMap-like rankings list) */
      .rank-controls {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
        margin-bottom: 10px;
      }
      .rank-ctl-btn {
        padding: 9px 10px;
        border-radius: 12px;
        border: 2px solid #e3e3e3;
        background: #fff;
        cursor: pointer;
        font-weight: 1000;
        font-size: 13px;
        color: #333;
      }
      .rank-ctl-btn.active {
        background: #0b63ce;
        border-color: #0b63ce;
        color: #fff;
        box-shadow: 0 8px 20px rgba(11, 99, 206, 0.18);
      }
      .rank-filter {
        flex: 1;
        min-width: 170px;
        padding: 9px 10px;
        border-radius: 12px;
        border: 1px solid #cfcfcf;
        font-weight: 900;
        font-size: 13px;
        outline: none;
      }

      .rank-list {
        border: 1px solid #eee;
        border-radius: 16px;
        overflow: hidden;
        background: #fff;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.05);
      }
      .rank-row {
        display: grid;
        grid-template-columns: 42px 1fr auto;
        gap: 10px;
        align-items: center;
        padding: 11px 12px;
        border-bottom: 1px solid #f0f0f0;
        background: #fff;
        cursor: pointer;
      }
      .rank-row:hover {
        background: #f5f9ff;
      }
      .rank-row:nth-child(even) {
        background: #fafafa;
      }
      .rank-num {
        width: 34px;
        height: 34px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 1000;
        color: #063a73;
        background: #e7f3ff;
        border: 1px solid #b3d9ff;
      }
      .rank-name {
        font-weight: 1000;
        color: #111;
        font-size: 13.5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        direction: ltr;
        text-align: left;
      }
      .rank-value {
        font-weight: 1000;
        color: #0b63ce;
        direction: ltr;
        font-size: 13.5px;
        min-width: 110px;
        text-align: left;
      }
      .rank-extra {
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

      /* Collapse */
      #info-panel.collapsed {
        max-height: 74px;
        height: 74px;
      }
      #info-panel.collapsed #tabs,
      #info-panel.collapsed #controls,
      #info-panel.collapsed #info-content {
        display: none;
      }
      #info-panel.collapsed #panel-header {
        padding: 10px 12px;
      }
      #info-panel.collapsed #panel-header p {
        display: none;
      }
      #info-panel.collapsed #panel-header h1 {
        font-size: 15px;
      }
      #info-panel.collapsed #header-actions {
        margin-top: 0;
        justify-content: flex-end;
      }
      #info-panel.collapsed #panelToggleBtn {
        display: inline-flex;
      }

      /* Mobile bottom sheet */
      @media (max-width: 768px) {
        #quick-stats {
          display: none !important;
        }
        #info-panel {
          position: fixed;
          left: 0;
          right: 0;
          top: auto;
          bottom: 0;

          width: 100%;
          height: calc(var(--vh, 1vh) * 55);
          max-height: calc(var(--vh, 1vh) * 55);

          border-radius: 20px 20px 0 0;
          overscroll-behavior: contain;
          touch-action: pan-y;
          right: 0;
        }
        #panel-header {
          padding: 10px 12px;
        }
        #panel-header h1 {
          font-size: 15px;
        }
        #panel-header p {
          margin-top: 4px;
          font-size: 12px;
          line-height: 1.25;
        }
        #header-actions {
          margin-top: 8px;
        }
        #header-actions .hbtn {
          padding: 8px 10px;
          font-size: 12px;
          border-radius: 12px;
        }
        #tabs .tab {
          padding: 9px 8px;
          font-size: 12px;
          min-width: 78px;
        }
        #controls {
          padding: 8px 10px;
        }
        .mode-grid {
          grid-template-columns: repeat(3, 1fr);
          gap: 6px;
          margin-bottom: 8px;
        }
        .mode-btn {
          padding: 9px 8px;
          font-size: 12px;
          border-radius: 12px;
          border-width: 2px;
        }
        .mode-btn.full {
          grid-column: auto;
        }
        .mode-btn.primary {
          font-size: 12.5px;
          padding: 9px 8px;
          border-width: 2px;
        }
        #info-content {
          padding: 10px 10px 16px 10px;
          overflow-y: auto;
          -webkit-overflow-scrolling: touch;
          overscroll-behavior: contain;
          touch-action: pan-y;
        }
        #info-panel.collapsed {
          height: calc(var(--vh, 1vh) * 45);
          max-height: none;
        }
        #info-panel.collapsed #tabs,
        #info-panel.collapsed #controls {
          display: none !important;
        }
        #info-panel.collapsed #info-content {
          display: block !important;
        }
      }

      /* Modal */
      .modal {
        display: none;
        position: fixed;
        inset: 0;
        z-index: 20000;
      }
      .modalOverlay {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
      }
      .modalCard {
        position: relative;
        width: min(760px, calc(100vw - 26px));
        max-height: calc(100vh - 26px);
        margin: 13px auto;
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 12px 34px rgba(0, 0, 0, 0.25);
        overflow: hidden;
        display: flex;
        flex-direction: column;
      }
      .modalHeader {
        padding: 14px 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.25);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        background: linear-gradient(135deg, #0b63ce 0%, #084eac 100%);
        color: #fff;
      }
      .modalHeaderTitle {
        font-weight: 1000;
        font-size: 15px;
      }
      .modalClose {
        border: none;
        background: rgba(255, 255, 255, 0.18);
        color: #fff;
        width: 42px;
        height: 42px;
        border-radius: 14px;
        cursor: pointer;
        font-size: 20px;
        font-weight: 1000;
      }
      .modalClose:active {
        transform: translateY(1px);
      }
      .modalBody {
        padding: 16px;
        overflow: auto;
      }
      code.inline {
        background: #f5f5f5;
        border: 1px solid #eee;
        padding: 2px 6px;
        border-radius: 8px;
        font-weight: 900;
        direction: ltr;
        display: inline-block;
      }
    </style>

    <script>
      // ===================== CONFIG =====================
      const TOKEN = "ede9a5fd-7c23-432f-8ffb-d85feffa3f3c";

      // GovMap buildings layer
      const BUILDINGS_LAYER = "225287";

      // CSV location (we try several paths until one works)
      const CSV_CANDIDATES = [
        "data/tablecsv.csv",
        "./data/tablecsv.csv",
        "public/data/tablecsv.csv",
        "./public/data/tablecsv.csv",
        "client/public/data/tablecsv.csv",
        "./client/public/data/tablecsv.csv",
      ];

      // Optional hint: if you KNOW the ID column name in the CSV, set it here (leave "" for auto-detect)
      const CSV_ID_HINT = ""; // e.g. "objectid" / "OBJECTID" / "BLDG_ID"

      // Optional hint: if you KNOW the rate column name in the CSV, set it here (leave "" for auto-detect)
      const CSV_RATE_HINT = ""; // e.g. "rate" / "v" / "mm_yr" / "velocity"

      // Rate threshold (outlier = value <= threshold, usually negative means subsidence)
      let rateThreshold = -10; // mm/yr (default)
      let onlyOutliersMode = true; // "מצב חריגים" – emphasis

      // ===================== STATE =====================
      let mapInitialized = false;

      // CSV data
      let csvLoaded = false;
      let csvLoadError = null;

      let csvHeaders = [];
      let csvHasHeader = true;

      let csvIdCol = null;   // index
      let csvRateCol = null; // index
      let csvXCol = null;    // index (optional)
      let csvYCol = null;    // index (optional)

      // Map: buildingId -> rows[]
      const csvById = new Map();

      // Building aggregated stats: buildingId -> { id, worstRate, rowsCount, anyXY, x, y }
      const buildingAgg = new Map();
      let outliersList = []; // [{id, worstRate, rowsCount, x,y}]

      // Selection
      let selectedBuildingId = null;
      let selectedBuildingRows = null; // rows[]
      let selectedGovmapPoint = null;  // {x,y}

      // Search dropdown
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

      function toFiniteNum(v) {
        if (v == null) return null;
        if (typeof v === "number") return Number.isFinite(v) ? v : null;

        let s = String(v).trim();
        if (!s) return null;

        // remove spaces
        s = s.replace(/\s+/g, "");

        // handle comma/decimal
        if (s.includes(",") && s.includes(".")) {
          s = s.replace(/,/g, "");
        } else if (s.includes(",")) {
          // if looks like thousands separator -> remove, else treat as decimal
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
        const wanted = (candidates || []).map(normalizeFieldName);

        if (Array.isArray(attrsRaw)) {
          for (const f of attrsRaw) {
            const fn = normalizeFieldName(f?.FieldName ?? f?.fieldName ?? f?.name);
            if (!fn) continue;

            if (wanted.includes(fn)) return f?.Value ?? f?.value;

            for (const w of wanted) {
              if (fn.includes(w)) return f?.Value ?? f?.value;
            }
          }
        }

        const attrsObj = fieldsToObject(attrsRaw) || attrsRaw;
        if (!attrsObj || typeof attrsObj !== "object") return null;

        // Direct keys
        for (const c of candidates || []) {
          if (attrsObj[c] != null && String(attrsObj[c]).trim() !== "") return attrsObj[c];
        }

        // Normalized map
        const normMap = {};
        for (const k in attrsObj) normMap[normalizeFieldName(k)] = attrsObj[k];

        for (const w of wanted) {
          if (normMap[w] != null && String(normMap[w]).trim() !== "") return normMap[w];
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

      function showInfo(title, body, type = "info") {
        const t = document.getElementById("info-title");
        const b = document.getElementById("info-body");
        if (!t || !b) return;
        t.textContent = title;
        b.innerHTML = `<div class="message message-${type}">${body}</div>`;
      }

      function setMobileVh() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty("--vh", `${vh}px`);
      }
      setMobileVh();
      window.addEventListener("resize", setMobileVh);
      if (window.visualViewport) window.visualViewport.addEventListener("resize", setMobileVh);

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

      function updateStats() {
        const elTotal = document.getElementById("stat-total");
        const elOut = document.getElementById("stat-outliers");
        const elSel = document.getElementById("stat-selected");

        const totalBuildings = buildingAgg.size;
        const outCount = outliersList.length;
        const sel = selectedBuildingId ? String(selectedBuildingId) : "—";

        if (elTotal) elTotal.textContent = Number(totalBuildings).toLocaleString();
        if (elOut) elOut.textContent = Number(outCount).toLocaleString();
        if (elSel) elSel.textContent = sel;
      }

      function setPanelSubtitle() {
        const p = document.querySelector("#panel-header p");
        if (!p) return;

        const status = csvLoaded
          ? `CSV נטען • מזהה: <strong>${escapeHtml(csvHeaders?.[csvIdCol] ?? "col0")}</strong> • מדד: <strong>${escapeHtml(csvHeaders?.[csvRateCol] ?? "colN")}</strong>`
          : csvLoadError
            ? `שגיאה בטעינת CSV • ${escapeHtml(csvLoadError)}`
            : `טוען CSV…`;

        const mode = onlyOutliersMode
          ? `מצב חריגים: <strong>פעיל</strong> (סף ${fmt(rateThreshold)}-)`
          : `מצב חריגים: <strong>כבוי</strong>`;

        p.innerHTML = `${status}<br>${mode}`;
      }

      // ===================== UI: TABS =====================
      let currentTab = "single"; // single | outliers | search | about

      function switchTab(tabName) {
        currentTab = tabName;

        document.querySelectorAll(".tab").forEach((tab) => {
          tab.classList.toggle("active", tab.dataset.tab === tabName);
        });
        document.querySelectorAll(".tab-content").forEach((content) => {
          content.classList.toggle("active", content.id === `tab-${tabName}`);
        });

        if (tabName === "single") {
          if (!selectedBuildingId) {
            showInfo(
              "בניינים (GovMap) + CSV",
              "לחץ על בניין במפה כדי לקבל את הנתונים שלו מקובץ ה-CSV.",
              "info",
            );
          } else {
            renderSelectedBuilding();
          }
        }

        if (tabName === "outliers") renderOutliers();
        if (tabName === "search") renderSearchTab();
        if (tabName === "about") renderAbout();
      }

      // ===================== PANEL: COLLAPSE =====================
      function togglePanel() {
        const panel = document.getElementById("info-panel");
        if (!panel) return;
        panel.classList.toggle("collapsed");

        const btn = document.getElementById("panelToggleBtn");
        if (btn) {
          const collapsed = panel.classList.contains("collapsed");
          btn.textContent = collapsed ? "➕ הגדל" : "➖ הקטן";
          btn.title = collapsed ? "הגדל" : "הקטן/הגדל";
        }
      }

      // ===================== CSV LOADING =====================
      function resolveCandidateUrls() {
        const base = new URL("./", location.href);
        const repoBase = (() => {
          // If hosted under /<repo>/..., try using that as base prefix
          // Example: https://user.github.io/SatMap/ -> prefix "/SatMap/"
          const parts = location.pathname.split("/").filter(Boolean);
          if (parts.length >= 1) return `/${parts[0]}/`;
          return "/";
        })();

        const extra = [
          `${repoBase}data/tablecsv.csv`,
          `${repoBase}public/data/tablecsv.csv`,
        ];

        const urls = [];
        for (const p of CSV_CANDIDATES) urls.push(new URL(p, base).toString());
        for (const p of extra) urls.push(new URL(p, location.origin).toString());

        // Dedup
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

      // Minimal CSV parser (handles quotes)
      function parseCsvLine(line) {
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
        return out;
      }

      function detectHasHeader(firstRow) {
        // If any cell contains Hebrew/English letters -> header
        return firstRow.some((c) => /[A-Za-z\u0590-\u05FF]/.test(String(c || "")));
      }

      function pickIdCol(headers) {
        const norm = headers.map(normalizeFieldName);

        // If user forced a hint
        if (CSV_ID_HINT) {
          const h = normalizeFieldName(CSV_ID_HINT);
          const idx = norm.indexOf(h);
          if (idx >= 0) return idx;
        }

        const candidates = [
          "objectid",
          "objid",
          "id",
          "gid",
          "fid",
          "bldg_id",
          "blgd_id",
          "building_id",
          "buildingid",
          "bldgid",
          "b_id",
        ];
        for (const c of candidates) {
          const idx = norm.indexOf(c);
          if (idx >= 0) return idx;
        }

        // fallback: first column
        return 0;
      }

      function pickRateCol(headers) {
        const norm = headers.map(normalizeFieldName);

        if (CSV_RATE_HINT) {
          const h = normalizeFieldName(CSV_RATE_HINT);
          const idx = norm.indexOf(h);
          if (idx >= 0) return idx;
        }

        // strong candidates
        const candidates = [
          "rate",
          "v",
          "vel",
          "velocity",
          "mmyr",
          "mm_yr",
          "mmperyear",
          "subsidence",
          "sink",
          "dh",
          "delta",
          "delta_h",
          "deltaheight",
          "dz",
        ];
        for (const c of candidates) {
          const idx = norm.indexOf(c);
          if (idx >= 0) return idx;
        }

        // try contains
        for (let i = 0; i < norm.length; i++) {
          const n = norm[i];
          if (n.includes("mm") && (n.includes("yr") || n.includes("year"))) return i;
          if (n.includes("velo")) return i;
          if (n.includes("subsid")) return i;
          if (n === "v") return i;
        }

        // fallback: last column
        return Math.max(0, headers.length - 1);
      }

      function pickXYCols(headers) {
        const norm = headers.map(normalizeFieldName);

        const xCandidates = ["x", "itmx", "easting", "east", "lon", "longitude", "centerx"];
        const yCandidates = ["y", "itmy", "northing", "north", "lat", "latitude", "centery"];

        let xCol = null, yCol = null;

        for (const c of xCandidates) {
          const idx = norm.indexOf(c);
          if (idx >= 0) { xCol = idx; break; }
        }
        for (const c of yCandidates) {
          const idx = norm.indexOf(c);
          if (idx >= 0) { yCol = idx; break; }
        }

        return { xCol, yCol };
      }

      function buildCsvIndexes(lines) {
        csvById.clear();
        buildingAgg.clear();
        outliersList = [];

        if (!lines.length) throw new Error("CSV ריק");

        // Parse first row
        const first = parseCsvLine(lines[0]);

        csvHasHeader = detectHasHeader(first);

        if (csvHasHeader) {
          csvHeaders = first.map((h, i) => String(h || `col${i}`).trim() || `col${i}`);
        } else {
          csvHeaders = first.map((_, i) => `col${i}`);
        }

        // Decide columns
        csvIdCol = pickIdCol(csvHeaders);
        csvRateCol = pickRateCol(csvHeaders);

        const xy = pickXYCols(csvHeaders);
        csvXCol = xy.xCol;
        csvYCol = xy.yCol;

        // Iterate rows
        const start = csvHasHeader ? 1 : 0;
        for (let i = start; i < lines.length; i++) {
          const line = lines[i];
          if (!line || !line.trim()) continue;

          const cols = parseCsvLine(line);

          // pad if shorter
          while (cols.length < csvHeaders.length) cols.push("");

          const idRaw = cols[csvIdCol];
          if (idRaw == null || String(idRaw).trim() === "") continue;

          const id = String(idRaw).trim(); // keep as string to avoid 64bit issues

          const rateRaw = cols[csvRateCol];
          const rate = toFiniteNum(rateRaw);

          const x = csvXCol != null ? toFiniteNum(cols[csvXCol]) : null;
          const y = csvYCol != null ? toFiniteNum(cols[csvYCol]) : null;

          // store full row as array + also object for rendering
          const row = { __cols: cols, __id: id, __rate: rate, __x: x, __y: y };

          const arr = csvById.get(id);
          if (arr) arr.push(row);
          else csvById.set(id, [row]);
        }

        // Aggregate per building
        for (const [id, rows] of csvById.entries()) {
          let worst = null;
          let anyXY = false;
          let bestX = null, bestY = null;

          for (const r of rows) {
            if (Number.isFinite(Number(r.__rate))) {
              if (worst == null || r.__rate < worst) worst = r.__rate; // more negative = "worse"
            }
            if (r.__x != null && r.__y != null) {
              anyXY = true;
              bestX = r.__x;
              bestY = r.__y;
            }
          }

          const agg = {
            id,
            worstRate: worst,
            rowsCount: rows.length,
            anyXY,
            x: bestX,
            y: bestY,
          };
          buildingAgg.set(id, agg);
        }

        // Build outliers list (exclude "no data" from being outlier)
        outliersList = Array.from(buildingAgg.values())
          .filter((a) => Number.isFinite(Number(a.worstRate)) && isOutlier(a.worstRate))
          .sort((a, b) => Number(a.worstRate) - Number(b.worstRate)); // most negative first
      }

      async function loadCsv() {
        csvLoaded = false;
        csvLoadError = null;

        try {
          const urls = resolveCandidateUrls();
          const { url, text } = await fetchFirstOk(urls);

          // Split lines safely
          const rawLines = text.split(/\r?\n/);

          buildCsvIndexes(rawLines);

          csvLoaded = true;
          setPanelSubtitle();
          updateStats();

          // Update UI sections if already open
          if (currentTab === "outliers") renderOutliers();
          if (currentTab === "search") renderSearchTab();
          if (currentTab === "single" && !selectedBuildingId) {
            showInfo(
              "CSV נטען ✅",
              `נטענו <strong>${Number(buildingAgg.size).toLocaleString()}</strong> מזהי בניינים מה-CSV.<br>
               חריגים לפי סף ${fmt(rateThreshold)}-: <strong>${Number(outliersList.length).toLocaleString()}</strong>`,
              "info",
            );
          }

          console.log("✅ CSV loaded from:", url, {
            rows: rawLines.length,
            buildings: buildingAgg.size,
            outliers: outliersList.length,
            idCol: csvHeaders[csvIdCol],
            rateCol: csvHeaders[csvRateCol],
            xCol: csvXCol != null ? csvHeaders[csvXCol] : null,
            yCol: csvYCol != null ? csvHeaders[csvYCol] : null,
          });
        } catch (e) {
          csvLoadError = String(e?.message || e);
          setPanelSubtitle();
          updateStats();
          showInfo(
            "שגיאה בטעינת CSV",
            `לא הצלחתי לטעון את <code class="inline">tablecsv.csv</code>.<br>
             ודא שהוא נמצא ביחס ל-<code class="inline">index.html</code> בנתיב <code class="inline">data/tablecsv.csv</code> (ללא / בתחילה).<br><br>
             שגיאה: <span style="direction:ltr;unicode-bidi:bidi-override">${escapeHtml(csvLoadError)}</span>`,
            "error",
          );
          console.error("❌ CSV load failed:", e);
        }
      }

      // ===================== BUILDING: RENDER =====================
      function renderSelectedBuilding() {
        const title = document.getElementById("info-title");
        const body = document.getElementById("info-body");
        if (!title || !body) return;

        if (!selectedBuildingId) {
          showInfo(
            "בניינים (GovMap) + CSV",
            "לחץ על בניין במפה כדי לקבל את הנתונים שלו מקובץ ה-CSV.",
            "info",
          );
          return;
        }

        const id = String(selectedBuildingId);

        const rows = csvById.get(id) || null;
        selectedBuildingRows = rows;

        const agg = buildingAgg.get(id) || null;

        title.textContent = `בניין #${id}`;

        // Build badges
        const badges = [];
        if (!csvLoaded) badges.push(`<span class="badge badge-warn">CSV עדיין לא נטען</span>`);
        else if (!rows) badges.push(`<span class="badge badge-warn">אין התאמה ב-CSV</span>`);
        else badges.push(`<span class="badge badge-good">נמצא ב-CSV (${Number(rows.length).toLocaleString()} שורות)</span>`);

        const worst = agg?.worstRate;
        const hasRate = Number.isFinite(Number(worst));
        if (hasRate) {
          if (isOutlier(worst)) badges.push(`<span class="badge badge-bad">חריג (≤ ${fmt(rateThreshold)}-)</span>`);
          else badges.push(`<span class="badge badge-good">לא חריג</span>`);
        } else {
          badges.push(`<span class="badge badge-warn">אין ערך מדד בשורה/ות</span>`);
        }

        // Emphasis in outliers mode: if not outlier, keep it minimal
        if (onlyOutliersMode && csvLoaded && rows && hasRate && !isOutlier(worst)) {
          body.innerHTML = `
            <div class="badgeRow">${badges.join("")}</div>
            <div class="message message-info">
              מצב חריגים פעיל: הבניין הזה <strong>לא</strong> עומד בסף החריגים.<br>
              אם אתה רוצה לראות את כל הפרטים בכל מקרה – כבה "מצב חריגים".
            </div>
          `;
          return;
        }

        let html = `<div class="badgeRow">${badges.join("")}</div>`;

        if (hasRate) {
          html += `<div class="total-summary">${fmt(worst)} mm/yr</div>`;
        } else {
          html += `<div class="message message-warn">אין ערך מספרי בעמודת המדד (<strong>${escapeHtml(csvHeaders?.[csvRateCol] ?? "?" )}</strong>).</div>`;
        }

        if (!rows) {
          html += `
            <div class="message message-warn">
              מצאתי את הבניין ב-GovMap (OBJECTID=${escapeHtml(id)}), אבל לא מצאתי אותו ב-CSV.<br>
              בדוק שהעמודה <strong>${escapeHtml(csvHeaders?.[csvIdCol] ?? "col0")}</strong> ב-CSV תואמת ל-OBJECTID ש-GovMap מחזיר.
            </div>
          `;
          body.innerHTML = html;
          return;
        }

        // Render a small “preview table” of first row
        const first = rows[0].__cols;

        // Build key/value list with a few best columns:
        const kv = [];
        const prefer = [
          csvHeaders[csvIdCol],
          csvHeaders[csvRateCol],
          csvXCol != null ? csvHeaders[csvXCol] : null,
          csvYCol != null ? csvHeaders[csvYCol] : null,
        ].filter(Boolean);

        // Put preferred columns first
        const used = new Set();
        for (const name of prefer) {
          const idx = csvHeaders.indexOf(name);
          if (idx >= 0) {
            used.add(idx);
            kv.push([name, first[idx]]);
          }
        }

        // Add up to 10 more columns (not the whole CSV row)
        for (let i = 0; i < csvHeaders.length && kv.length < 14; i++) {
          if (used.has(i)) continue;
          const v = first[i];
          if (v == null || String(v).trim() === "") continue;
          kv.push([csvHeaders[i], v]);
        }

        html += `
          <div class="message message-info">
            עמודה מזהה ב-CSV: <strong>${escapeHtml(csvHeaders?.[csvIdCol] ?? "col0")}</strong> •
            עמודת מדד: <strong>${escapeHtml(csvHeaders?.[csvRateCol] ?? "colN")}</strong> •
            שורות ל-ID: <strong>${Number(rows.length).toLocaleString()}</strong>
          </div>
        `;

        html += `<div style="border:1px solid #eee;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 10px 22px rgba(0,0,0,.05);">`;
        html += `<div style="padding:10px 12px;background:#fafafa;border-bottom:1px solid #eee;font-weight:1000;color:#111;">פרטים (דוגמה מהשורה הראשונה)</div>`;
        html += `<div style="padding:10px 12px;">`;
        html += kv
          .map(
            ([k, v]) => `
              <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px dashed #eee;">
                <div style="min-width:150px;font-weight:1000;color:#333;">${escapeHtml(k)}</div>
                <div style="flex:1;color:#111;direction:ltr;text-align:left;word-break:break-word;">${escapeHtml(v)}</div>
              </div>
            `,
          )
          .join("");
        html += `</div></div>`;

        // If multiple rows, show a hint
        if (rows.length > 1) {
          html += `
            <div class="message message-info" style="margin-top:10px;">
              ל-ID הזה יש <strong>${Number(rows.length).toLocaleString()}</strong> שורות ב-CSV.<br>
              מוצג כאן ערך החריגות לפי <strong>הערך הנמוך ביותר</strong> בעמודת המדד.
            </div>
          `;
        }

        body.innerHTML = html;
      }

      // ===================== OUTLIERS TAB =====================
      let outSort = "worst"; // worst | id | count
      let outOrder = "asc";  // asc = most negative first

      function setOutSort(v) {
        outSort = v;
        renderOutliers();
      }
      function setOutOrder(v) {
        outOrder = v;
        renderOutliers();
      }

      function renderOutliers() {
        const container = document.getElementById("outliers-content");
        if (!container) return;

        if (!csvLoaded) {
          container.innerHTML = `<div class="message message-warn">ה-CSV עדיין לא נטען, לכן אין רשימת חריגים.</div>`;
          return;
        }

        // Recompute outliers according to current threshold
        outliersList = Array.from(buildingAgg.values())
          .filter((a) => Number.isFinite(Number(a.worstRate)) && isOutlier(a.worstRate))
          .sort((a, b) => Number(a.worstRate) - Number(b.worstRate));

        // Sort option
        let rows = [...outliersList];
        if (outSort === "id") rows.sort((a, b) => String(a.id).localeCompare(String(b.id)));
        if (outSort === "count") rows.sort((a, b) => (b.rowsCount || 0) - (a.rowsCount || 0));
        if (outSort === "worst") rows.sort((a, b) => Number(a.worstRate) - Number(b.worstRate));

        if (outOrder === "desc") rows.reverse();

        const orderLabel =
          outOrder === "asc"
            ? "מהכי חמור (שלילי) להכי פחות"
            : "מהכי פחות חמור להכי חמור";
        const sortLabel =
          outSort === "worst" ? "מדד" : outSort === "id" ? "מזהה" : "מספר שורות";

        let html = `
          <div class="rank-controls">
            <button class="rank-ctl-btn ${outSort === "worst" ? "active" : ""}" onclick="setOutSort('worst')">📉 לפי מדד</button>
            <button class="rank-ctl-btn ${outSort === "id" ? "active" : ""}" onclick="setOutSort('id')">🆔 לפי מזהה</button>
            <button class="rank-ctl-btn ${outSort === "count" ? "active" : ""}" onclick="setOutSort('count')">🧾 לפי כמות שורות</button>
            <button class="rank-ctl-btn ${outOrder === "asc" ? "active" : ""}" onclick="setOutOrder('asc')">⬇️ חמור→קל</button>
            <button class="rank-ctl-btn ${outOrder === "desc" ? "active" : ""}" onclick="setOutOrder('desc')">⬆️ קל→חמור</button>
          </div>

          <div class="message message-info" style="margin-bottom:10px;">
            סף חריגים: <strong>${fmt(rateThreshold)}-</strong> mm/yr • חריגים נמצאו: <strong>${Number(rows.length).toLocaleString()}</strong><br>
            מיון: <strong>${escapeHtml(sortLabel)}</strong> • סדר: <strong>${escapeHtml(orderLabel)}</strong><br>
            טיפ: לחץ על שורה כדי לפתוח את פרטי הבניין (בכרטיס "בניין") ולנסות להתמקד אליו.
          </div>

          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
            <div style="font-weight:1000;">סף:</div>
            <input id="thrInput" type="number" step="0.5" value="${escapeHtml(rateThreshold)}"
                   style="padding:10px 12px;border-radius:12px;border:1px solid #cfcfcf;font-weight:1000;width:140px;direction:ltr;text-align:left;">
            <button class="rank-ctl-btn" onclick="applyThreshold()">החל</button>
            <button class="rank-ctl-btn" onclick="setPreset(-2)">-2</button>
            <button class="rank-ctl-btn" onclick="setPreset(-5)">-5</button>
            <button class="rank-ctl-btn" onclick="setPreset(-10)">-10</button>
            <button class="rank-ctl-btn" onclick="setPreset(-20)">-20</button>
          </div>
        `;

        if (!rows.length) {
          html += `<div class="message message-warn">אין חריגים לפי הסף הנוכחי.</div>`;
          container.innerHTML = html;
          updateStats();
          setPanelSubtitle();
          return;
        }

        html += `<div class="rank-list">`;

        const maxShow = 200; // keep UI responsive
        const shown = rows.slice(0, maxShow);

        shown.forEach((r, idx) => {
          const valueText = `${fmt(r.worstRate)} mm/yr`;
          const extra = `rows=${Number(r.rowsCount).toLocaleString()}${r.anyXY ? " • XY✅" : ""}`;

          html += `
            <div class="rank-row" onclick="selectBuildingFromList('${escapeHtml(r.id)}')">
              <div class="rank-num">${idx + 1}</div>
              <div class="rank-name">${escapeHtml(r.id)}</div>
              <div class="rank-value">${escapeHtml(valueText)}</div>
            </div>
            <div class="rank-extra">${escapeHtml(extra)}</div>
          `;
        });

        if (rows.length > maxShow) {
          html += `
            <div class="message message-info" style="margin:12px;">
              מוצגים ${Number(maxShow).toLocaleString()} מתוך ${Number(rows.length).toLocaleString()} חריגים (כדי לשמור על ביצועים).
            </div>
          `;
        }

        html += `</div>`;

        container.innerHTML = html;
        updateStats();
        setPanelSubtitle();
      }

      function applyThreshold() {
        const el = document.getElementById("thrInput");
        if (!el) return;
        const v = toFiniteNum(el.value);
        if (v == null) return;

        rateThreshold = v;
        renderOutliers();
        setPanelSubtitle();
        updateStats();

        // refresh single view if selected
        if (selectedBuildingId && currentTab === "single") renderSelectedBuilding();
      }
      function setPreset(v) {
        rateThreshold = v;
        const el = document.getElementById("thrInput");
        if (el) el.value = String(v);
        renderOutliers();
        setPanelSubtitle();
        updateStats();
        if (selectedBuildingId && currentTab === "single") renderSelectedBuilding();
      }

      function selectBuildingFromList(id) {
        selectedBuildingId = String(id);
        selectedBuildingRows = csvById.get(selectedBuildingId) || null;

        // If we have XY in agg, zoom there (nice “highlight”)
        const agg = buildingAgg.get(selectedBuildingId);
        if (agg?.anyXY && agg?.x != null && agg?.y != null && mapInitialized) {
          try {
            govmap.zoomToXY({ x: agg.x, y: agg.y, level: 12, marker: true });
          } catch (_) {}
        }

        updateStats();
        switchTab("single");
      }

      // ===================== SEARCH TAB =====================
      function renderSearchTab() {
        const container = document.getElementById("search-content");
        if (!container) return;

        if (!csvLoaded) {
          container.innerHTML = `<div class="message message-warn">ה-CSV עדיין לא נטען, לכן חיפוש לפי ID לא זמין.</div>`;
          return;
        }

        container.innerHTML = `
          <div class="message message-info">
            חיפוש לפי מזהה בניין (ID) מתוך ה-CSV. אפשר גם להשתמש בשורת החיפוש העליונה.
          </div>

          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
            <input id="searchIdInput" class="rank-filter" placeholder="הקלד ID… (למשל 417568)" style="direction:ltr;text-align:left;" />
            <button class="rank-ctl-btn" onclick="runIdSearch()">חפש</button>
          </div>

          <div id="search-results"></div>
        `;

        const inp = document.getElementById("searchIdInput");
        if (inp) {
          inp.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              runIdSearch();
            }
          });
        }
      }

      function runIdSearch() {
        const inp = document.getElementById("searchIdInput");
        const box = document.getElementById("search-results");
        if (!inp || !box) return;

        const q = String(inp.value || "").trim();
        if (!q) return;

        // exact match first
        if (csvById.has(q)) {
          box.innerHTML = `
            <div class="message message-info">נמצא התאמה מדויקת ל-ID <strong>${escapeHtml(q)}</strong>. פותח פרטים…</div>
          `;
          selectBuildingFromList(q);
          return;
        }

        // prefix contains
        const items = [];
        const limit = 50;
        for (const id of buildingAgg.keys()) {
          if (String(id).includes(q)) items.push(String(id));
          if (items.length >= limit) break;
        }

        if (!items.length) {
          box.innerHTML = `<div class="message message-warn">לא נמצאו תוצאות עבור <strong>${escapeHtml(q)}</strong>.</div>`;
          return;
        }

        box.innerHTML = `
          <div class="message message-info">נמצאו ${Number(items.length).toLocaleString()} תוצאות (מציג עד ${limit}). לחץ לפתיחה:</div>
          <div class="rank-list">
            ${items
              .map((id, idx) => {
                const agg = buildingAgg.get(id);
                const w = agg?.worstRate;
                const badge = Number.isFinite(Number(w))
                  ? isOutlier(w)
                    ? `<span class="badge badge-bad" style="margin-left:8px;">חריג</span>`
                    : `<span class="badge badge-good" style="margin-left:8px;">לא חריג</span>`
                  : `<span class="badge badge-warn" style="margin-left:8px;">אין מדד</span>`;
                const val = Number.isFinite(Number(w)) ? `${fmt(w)} mm/yr` : "—";
                return `
                  <div class="rank-row" onclick="selectBuildingFromList('${escapeHtml(id)}')">
                    <div class="rank-num">${idx + 1}</div>
                    <div class="rank-name">${escapeHtml(id)}</div>
                    <div class="rank-value">${escapeHtml(val)}</div>
                  </div>
                  <div class="rank-extra">${badge} rows=${Number(agg?.rowsCount || 0).toLocaleString()}</div>
                `;
              })
              .join("")}
          </div>
        `;
      }

      // ===================== ABOUT TAB =====================
      function renderAbout() {
        const container = document.getElementById("about-content");
        if (!container) return;

        const idName = csvHeaders?.[csvIdCol] ?? "col0";
        const rateName = csvHeaders?.[csvRateCol] ?? "colN";

        container.innerHTML = `
          <div class="message message-info">
            <strong>מה האתר עושה?</strong><br>
            1) טוען שכבת בניינים מ-GovMap (<code class="inline">${escapeHtml(BUILDINGS_LAYER)}</code>).<br>
            2) טוען קובץ CSV בשם <code class="inline">tablecsv.csv</code> ומבצע אינדוקס לפי מזהה בניין.<br>
            3) בלחיצה על בניין – מציג את הנתונים מה-CSV עבור אותו ID.<br><br>
            <strong>מצב חריגים</strong> מדגיש רק בניינים עם ערך מדד ≤ סף (שלילי).<br>
            חשוב: "אין נתונים" לא נחשב חריג (רק ערך מספרי).
          </div>

          <div class="message message-info">
            <strong>חיבורים חשובים:</strong><br>
            • GovMap מחזיר לרוב את המזהה בשדה <code class="inline">objectid</code> (כמו שראית).<br>
            • ב-CSV צריך שהעמודה <strong>${escapeHtml(idName)}</strong> תתאים ל-OBJECTID הזה.<br>
            • עמודת המדד הנוכחית מזוהה כ-<strong>${escapeHtml(rateName)}</strong>.
          </div>

          <div class="message message-info">
            <strong>מיקום ה-CSV:</strong><br>
            מומלץ לשים את הקובץ בנתיב יחסי: <code class="inline">data/tablecsv.csv</code> ליד ה-index.html (או בתוך dist).<br>
            ב-GitHub Pages: אל תתחיל את הנתיב עם <code class="inline">/</code>.
          </div>
        `;
      }

      // ===================== GOVMAP: CLICK -> BUILDING ID =====================
      function extractBuildingIdFromGovmapItem(item) {
        const attrs = item?.Fields || item?.Attributes || item;
        // The key fix: prefer objectid
        const candidates = [
          "objectid",
          "OBJECTID",
          "ObjectId",
          "ObjectID",
          "oid",
          "OID",
          "id",
          "ID",
          "bldg_id",
          "BLDG_ID",
          "blgd_id",
          "BLGD_ID",
          "building_id",
          "BUILDING_ID",
        ];
        const v = getFieldFromAttrs(attrs, candidates);
        if (v == null) return null;
        const s = String(v).trim();
        return s ? s : null;
      }

      async function onMapClick(e) {
        if (!mapInitialized) return;

        const pt = normalizeMapPoint(e);
        if (!pt) {
          showInfo("רגע", "לא התקבלה נקודת מפה תקינה (X/Y).", "warn");
          return;
        }

        selectedGovmapPoint = pt;

        try {
          const resp = await govmap.getLayerData({
            LayerName: BUILDINGS_LAYER,
            Point: { x: pt.x, y: pt.y, X: pt.x, Y: pt.y },
            Radius: 30,
          });

          const items = resp?.data || resp?.Data || [];
          if (!items.length) {
            showInfo("לא נמצא", "אין בניין באזור הזה.", "info");
            return;
          }

          const id = extractBuildingIdFromGovmapItem(items[0]);
          if (!id) {
            // This is the exact place your old UI got stuck. Now we show fields to debug.
            const attrsObj = fieldsToObject(items[0]?.Fields || items[0]?.Attributes) || {};
            const keys = Object.keys(attrsObj);
            showInfo(
              "מצאתי בניין אבל חסר ID",
              `מצאתי בניין, אבל לא הצלחתי לחלץ מזהה.<br>
               שדות שחזרו: <span style="direction:ltr;unicode-bidi:bidi-override">${escapeHtml(keys.join(" | "))}</span><br>
               טיפ: לרוב המזהה הוא <code class="inline">objectid</code>.`,
              "error",
            );
            return;
          }

          selectedBuildingId = String(id);
          selectedBuildingRows = csvById.get(selectedBuildingId) || null;
          updateStats();

          // If we have coordinates in CSV for this ID, we can “highlight” by zoom marker (optional)
          const agg = buildingAgg.get(selectedBuildingId);
          if (agg?.anyXY && agg?.x != null && agg?.y != null) {
            try {
              govmap.zoomToXY({ x: agg.x, y: agg.y, level: 12, marker: true });
            } catch (_) {}
          }

          // Update single tab view
          if (currentTab !== "single") switchTab("single");
          else renderSelectedBuilding();
        } catch (error) {
          console.error("❌ Error in onMapClick:", error);
          showInfo(
            "שגיאה",
            `אירעה שגיאה: ${escapeHtml(error?.message || "שגיאה לא מוגדרת")}`,
            "error",
          );
        }
      }

      // ===================== ADDRESS SEARCH (GovMap geocode) =====================
      function parseGeocodeList(resp) {
        const list = resp?.data || resp?.Data || resp?.results || resp;
        if (Array.isArray(list)) return list;
        if (Array.isArray(list?.Result)) return list.Result;
        return [];
      }

      function extractXY(item) {
        const x =
          item?.X ?? item?.x ?? item?.CenterX ?? item?.centerX ?? item?.Lon ?? item?.lon;
        const y =
          item?.Y ?? item?.y ?? item?.CenterY ?? item?.centerY ?? item?.Lat ?? item?.lat;
        return { x: Number(x), y: Number(y) };
      }

      function isBadTitle(t) {
        const s = String(t ?? "").trim();
        if (!s) return true;
        const low = s.toLowerCase();
        return s === "תוצאה" || low === "result" || low === "results" || low === "unknown";
      }

      function getTopBarEls() {
        const root = document.getElementById("top-searchbar");
        if (!root) return {};
        return {
          addrInput: root.querySelector("#addrInput"),
          addrBtn: root.querySelector("#addrBtn"),
          addrResults: document.getElementById("addrResults"),
          idInput: root.querySelector("#idInput"),
          idBtn: root.querySelector("#idBtn"),
          idResults: document.getElementById("idResults"),
          toggleOutliersBtn: root.querySelector("#toggleOutliersBtn"),
        };
      }

      function setAddrLoading(msg) {
        const { addrResults } = getTopBarEls();
        if (!addrResults) return;
        addrResults.style.display = "block";
        addrResults.innerHTML = `<div class="addr-item">${escapeHtml(msg || "מחפש…")}</div>`;
      }

      function renderAddrResults(items) {
        const { addrResults } = getTopBarEls();
        if (!addrResults) return;

        lastAddrItems = items || [];

        if (!items || !items.length) {
          addrResults.style.display = "block";
          addrResults.innerHTML = `<div class="addr-item">לא נמצאו תוצאות</div>`;
          return;
        }

        addrResults.style.display = "block";
        addrResults.innerHTML =
          `<div class="dropSectionTitle">תוצאות חיפוש כתובת</div>` +
          items
            .map((it, idx) => {
              const title = escapeHtml(it.__title || lastGeocodeQuery || "תוצאה");
              const sub = escapeHtml(it.__sub || "");
              return `
                <div class="addr-item" data-idx="${idx}">
                  <div style="font-weight:1000; color:#111;">${title}</div>
                  ${sub ? `<div class="addr-sub">${sub}</div>` : ""}
                </div>
              `;
            })
            .join("");

        addrResults.querySelectorAll(".addr-item[data-idx]").forEach((el) => {
          el.addEventListener("click", () => {
            const idx = Number(el.dataset.idx);
            const picked = lastAddrItems[idx];
            if (picked) focusToGeocodeItem(picked);
            addrResults.style.display = "none";
          });
        });
      }

      function focusToGeocodeItem(item) {
        if (!mapInitialized) return;

        const { x, y } = extractXY(item);
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
          showInfo("שגיאה", "התקבלה תוצאה בלי קואורדינטות X/Y", "error");
          return;
        }

        try {
          govmap.zoomToXY({ x, y, level: 10, marker: true });
        } catch (_) {}

        const label = !isBadTitle(item.__title) ? item.__title : lastGeocodeQuery || "תוצאה";
        showInfo("כתובת", `התמקדתי לכתובת: <strong>${escapeHtml(label)}</strong>`, "info");
      }

      function runGeocode(query) {
        const q = String(query || "").trim();
        if (!q) return;

        lastGeocodeQuery = q;

        if (!mapInitialized) {
          showInfo("רגע", "המפה עדיין נטענת, נסה שוב בעוד רגע.", "warn");
          return;
        }

        const myId = ++lastGeocodeReqId;

        showInfo("חיפוש כתובת", `מחפש: <strong>${escapeHtml(q)}</strong>`, "info");
        setAddrLoading("מחפש כתובת…");

        const payload = { keyword: q };
        if (govmap.geocodeType?.AccuracyOnly) payload.type = govmap.geocodeType.AccuracyOnly;

        let res;
        try {
          res = govmap.geocode(payload);
        } catch (e) {
          showInfo("חיפוש כתובת", `שגיאה בחיפוש עבור: <strong>${escapeHtml(q)}</strong>`, "error");
          renderAddrResults([]);
          return;
        }

        const onSuccess = (resp) => {
          if (myId !== lastGeocodeReqId) return;

          const list = parseGeocodeList(resp);
          if (!list || !list.length) {
            showInfo("חיפוש כתובת", `לא נמצאו תוצאות עבור: <strong>${escapeHtml(q)}</strong>`, "warn");
            renderAddrResults([]);
            return;
          }

          const mapped = list.slice(0, 10).map((r) => {
            const candidates = [
              r?.SettlementName,
              r?.settlementName,
              r?.PlaceName,
              r?.placeName,
              r?.Name,
              r?.name,
              r?.ResultLabel,
              r?.resultLabel,
              r?.Address,
              r?.address,
              r?.Title,
              r?.title,
              r?.label,
            ]
              .map((x) => (x == null ? "" : String(x).trim()))
              .filter(Boolean);

            let title = candidates.find((t) => !isBadTitle(t)) || q;
            let sub =
              r?.City ||
              r?.city ||
              r?.Region ||
              r?.region ||
              r?.Street ||
              r?.street ||
              r?.SubTitle ||
              r?.subTitle ||
              "";
            sub = String(sub || "").trim();
            return { ...r, __title: title, __sub: sub };
          });

          renderAddrResults(mapped);
        };

        const onFail = () => {
          if (myId !== lastGeocodeReqId) return;
          showInfo("חיפוש כתובת", `לא ניתן לבצע חיפוש עבור: <strong>${escapeHtml(q)}</strong>`, "error");
          renderAddrResults([]);
        };

        if (res && typeof res.then === "function") res.then(onSuccess).catch(onFail);
        else if (res && typeof res.done === "function") res.done(onSuccess).fail(onFail);
        else onFail();
      }

      // ===================== TOP BAR: ID SEARCH DROPDOWN =====================
      function renderIdDropdown(items, q) {
        const { idResults } = getTopBarEls();
        if (!idResults) return;

        if (!items || !items.length) {
          idResults.style.display = "block";
          idResults.innerHTML = `
            <div class="dropSectionTitle">חיפוש ID</div>
            <div class="addr-item">לא נמצאו תוצאות עבור "${escapeHtml(q)}"</div>
          `;
          return;
        }

        idResults.style.display = "block";
        idResults.innerHTML =
          `<div class="dropSectionTitle">תוצאות ID (עד 20)</div>` +
          items
            .map((id) => {
              const agg = buildingAgg.get(id);
              const w = agg?.worstRate;
              const val = Number.isFinite(Number(w)) ? `${fmt(w)} mm/yr` : "—";
              const tag =
                Number.isFinite(Number(w))
                  ? isOutlier(w)
                    ? `<span class="badge badge-bad" style="margin-right:8px;">חריג</span>`
                    : `<span class="badge badge-good" style="margin-right:8px;">לא חריג</span>`
                  : `<span class="badge badge-warn" style="margin-right:8px;">אין מדד</span>`;

              return `
                <div class="addr-item" data-id="${escapeHtml(id)}" style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                  <div style="direction:ltr;text-align:left;font-weight:1000;color:#111;">${escapeHtml(id)}</div>
                  <div style="display:flex;align-items:center;gap:10px;direction:ltr;">
                    ${tag}
                    <span style="font-weight:1000;color:#0b63ce;">${escapeHtml(val)}</span>
                  </div>
                </div>
              `;
            })
            .join("");

        idResults.querySelectorAll(".addr-item[data-id]").forEach((el) => {
          el.addEventListener("click", () => {
            const id = el.getAttribute("data-id");
            if (id) selectBuildingFromList(id);
            idResults.style.display = "none";
          });
        });
      }

      function runTopIdSearch(q) {
        if (!csvLoaded) {
          showInfo("חיפוש ID", "ה-CSV עדיין לא נטען.", "warn");
          return;
        }
        const query = String(q || "").trim();
        if (!query) return;

        if (csvById.has(query)) {
          selectBuildingFromList(query);
          return;
        }

        const hits = [];
        for (const id of buildingAgg.keys()) {
          if (String(id).includes(query)) hits.push(String(id));
          if (hits.length >= 20) break;
        }
        renderIdDropdown(hits, query);
      }

      // ===================== INIT UI =====================
      function initTopBar() {
        const { addrInput, addrBtn, addrResults, idInput, idBtn, idResults, toggleOutliersBtn } = getTopBarEls();
        if (!addrInput || !addrBtn || !idInput || !idBtn) return;

        // Address
        addrBtn.addEventListener("click", () => {
          const q = String(addrInput.value || "").trim();
          if (!q) return;

          // If same query + cached list, jump to first
          const sameQuery = String(lastGeocodeQuery || "").trim() === q;
          if (sameQuery && Array.isArray(lastAddrItems) && lastAddrItems.length) {
            const exact =
              lastAddrItems.find((it) => String(it?.__title || "").trim() === q) || lastAddrItems[0];
            focusToGeocodeItem(exact);
            if (addrResults) addrResults.style.display = "none";
            return;
          }

          runGeocode(q);
        });

        addrInput.addEventListener("keydown", (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            addrBtn.click();
          }
          if (e.key === "Escape" && addrResults) addrResults.style.display = "none";
        });

        addrInput.addEventListener("input", () => {
          if (searchTimeout) clearTimeout(searchTimeout);
          const v = addrInput.value.trim();
          if (v.length < 3) {
            if (addrResults) addrResults.style.display = "none";
            return;
          }
          searchTimeout = setTimeout(() => runGeocode(v), 350);
        });

        // ID
        idBtn.addEventListener("click", () => runTopIdSearch(idInput.value));
        idInput.addEventListener("keydown", (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            idBtn.click();
          }
          if (e.key === "Escape" && idResults) idResults.style.display = "none";
        });
        idInput.addEventListener("input", () => {
          const v = idInput.value.trim();
          if (!v) {
            if (idResults) idResults.style.display = "none";
            return;
          }
          // quick suggestions
          runTopIdSearch(v);
        });

        // Toggle outliers mode
        if (toggleOutliersBtn) {
          toggleOutliersBtn.addEventListener("click", () => {
            onlyOutliersMode = !onlyOutliersMode;
            toggleOutliersBtn.textContent = onlyOutliersMode ? "🚨 חריגים: פעיל" : "🚨 חריגים: כבוי";
            toggleOutliersBtn.classList.toggle("secondary", !onlyOutliersMode);
            setPanelSubtitle();

            // refresh current view
            if (currentTab === "single") renderSelectedBuilding();
            if (currentTab === "outliers") renderOutliers();
          });
        }

        // click outside to close dropdowns
        document.addEventListener("click", (e) => {
          if (addrResults && !addrResults.contains(e.target) && e.target !== addrInput && e.target !== addrBtn) {
            addrResults.style.display = "none";
          }
          if (idResults && !idResults.contains(e.target) && e.target !== idInput && e.target !== idBtn) {
            idResults.style.display = "none";
          }
        });
      }

      // ===================== MODAL =====================
      let lastFocusedElement = null;
      function openModal(id, focusElId = null) {
        const m = document.getElementById(id);
        if (!m) return;
        lastFocusedElement = document.activeElement;
        m.style.display = "block";
        m.setAttribute("aria-hidden", "false");
        document.documentElement.style.overflow = "hidden";
        document.body.style.overflow = "hidden";

        const focusEl =
          (focusElId && document.getElementById(focusElId)) ||
          m.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (focusEl) setTimeout(() => focusEl.focus(), 0);
      }
      function closeModal(id) {
        const m = document.getElementById(id);
        if (!m) return;

        if (m.contains(document.activeElement) && lastFocusedElement && typeof lastFocusedElement.focus === "function") {
          lastFocusedElement.focus();
        }

        m.setAttribute("aria-hidden", "true");
        m.style.display = "none";
        document.documentElement.style.overflow = "";
        document.body.style.overflow = "";
      }

      function initModals() {
        const aboutBtn = document.getElementById("aboutBtn");
        const aboutClose = document.getElementById("aboutCloseBtn");
        const aboutOverlay = document.getElementById("aboutOverlay");

        if (aboutBtn) aboutBtn.addEventListener("click", () => openModal("aboutModal", "aboutCloseBtn"));
        if (aboutClose) aboutClose.addEventListener("click", () => closeModal("aboutModal"));
        if (aboutOverlay) aboutOverlay.addEventListener("click", () => closeModal("aboutModal"));

        document.addEventListener("keydown", (e) => {
          if (e.key === "Escape") {
            closeModal("aboutModal");
            const { addrResults, idResults } = getTopBarEls();
            if (addrResults) addrResults.style.display = "none";
            if (idResults) idResults.style.display = "none";
          }
        });
      }

      // ===================== GOVMAP INIT =====================
      function initGovMap() {
        // Start loading CSV immediately (in parallel)
        loadCsv().finally(() => {
          setPanelSubtitle();
          updateStats();
        });

        // Init panel defaults
        setPanelSubtitle();
        updateStats();

        govmap.createMap("map", {
          token: TOKEN,
          layers: [BUILDINGS_LAYER],
          layersMode: 4,
          background: 3,
          zoomButtons: true,
          identifyOnClick: false,
          visibleLayers: [BUILDINGS_LAYER],
          onLoad: () => {
            mapInitialized = true;

            initModals();
            initTopBar();

            const toggleBtn = document.getElementById("panelToggleBtn");
            if (toggleBtn) toggleBtn.addEventListener("click", togglePanel);
            if (toggleBtn) toggleBtn.textContent = "➖ הקטן";

            try {
              govmap.onEvent(govmap.events.CLICK).progress((e) => {
                const pt = normalizeMapPoint(e);
                onMapClick(pt ? { mapPoint: pt, __fromGovmap: true } : e);
              });
            } catch (_) {}

            const l = document.getElementById("loading");
            if (l) l.style.display = "none";

            showInfo(
              "SatMap – בניינים + CSV",
              `שכבה: <strong>${escapeHtml(BUILDINGS_LAYER)}</strong><br>
               לחץ על בניין כדי לקבל נתונים מה-CSV. עבור "חריגים" – פתח את הטאב חריגים.`,
              "info",
            );

            setPanelSubtitle();
            updateStats();
            console.log("✅ Map initialized successfully");
          },
        });
      }

      // Expose functions for inline handlers
      window.switchTab = switchTab;
      window.togglePanel = togglePanel;
      window.applyThreshold = applyThreshold;
      window.setPreset = setPreset;
      window.selectBuildingFromList = selectBuildingFromList;
      window.setOutSort = setOutSort;
      window.setOutOrder = setOutOrder;
      window.renderOutliers = renderOutliers;
      window.runIdSearch = runIdSearch;
      window.initGovMap = initGovMap;
    </script>

    <!-- GOVMAP API -->
    <script
      src="https://www.govmap.gov.il/govmap/api/govmap.api.js"
      defer
      onload="initGovMap()"
    ></script>
  </head>

  <body>
    <div id="loading">
      <div class="spinner"></div>
      <div style="font-size: 14px; color: #333; font-weight: 1000">טוען מפה...</div>
    </div>

    <div id="map"></div>

    <!-- Top Always-Open Search Bar -->
    <div id="top-searchbar">
      <button id="addrBtn" class="pillBtn" type="button">חפש כתובת</button>
      <input id="addrInput" class="pillInput" type="text" placeholder="לדוגמה: דיזנגוף 50 תל אביב" autocomplete="off" />
      <button id="idBtn" class="pillBtn secondary" type="button">חפש ID</button>
      <input id="idInput" class="pillInput ltr" type="text" placeholder="417568" autocomplete="off" />
      <button id="toggleOutliersBtn" class="pillBtn" type="button">🚨 חריגים: פעיל</button>

      <div id="addrResults"></div>
      <div id="idResults"></div>
    </div>

    <div id="info-panel">
      <div id="panel-header">
        <h1>🛰️ SatMap – Buildings + CSV</h1>
        <p>טוען CSV…<br>מצב חריגים: <strong>פעיל</strong></p>

        <div id="header-actions">
          <button id="aboutBtn" class="hbtn secondary">ℹ️ אודות</button>
          <button id="panelToggleBtn" class="hbtn secondary" title="כיווץ/הרחבה">➖ הקטן</button>
        </div>
      </div>

      <div id="tabs">
        <div class="tab active" data-tab="single" onclick="switchTab('single')">בניין</div>
        <div class="tab" data-tab="outliers" onclick="switchTab('outliers')">חריגים</div>
        <div class="tab" data-tab="search" onclick="switchTab('search')">חיפוש</div>
        <div class="tab" data-tab="about" onclick="switchTab('about')">הסבר</div>
      </div>

      <div id="controls">
        <div class="mode-grid">
          <button class="mode-btn full primary active" onclick="switchTab('single')">🏢 קליק על בניין → נתוני CSV</button>
          <button class="mode-btn" onclick="switchTab('outliers')">🚨 מצב חריגים</button>
          <button class="mode-btn" onclick="switchTab('search')">🔎 חיפוש ID</button>
          <button class="mode-btn full" onclick="switchTab('about')">ℹ️ איך זה עובד</button>
        </div>

        <div id="quick-stats">
          <div class="stat-card">
            <div class="stat-value" id="stat-total">-</div>
            <div class="stat-label">סה"כ IDs ב-CSV</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="stat-outliers">-</div>
            <div class="stat-label">חריגים לפי סף</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="stat-selected">-</div>
            <div class="stat-label">נבחר</div>
          </div>
        </div>
      </div>

      <div id="info-content">
        <div class="tab-content active" id="tab-single">
          <div id="info-title">טוען נתונים...</div>
          <div id="info-body"></div>
        </div>

        <div class="tab-content" id="tab-outliers">
          <div id="outliers-content">
            <div class="message message-info">טוען חריגים…</div>
          </div>
        </div>

        <div class="tab-content" id="tab-search">
          <div id="search-content">
            <div class="message message-info">טוען חיפוש…</div>
          </div>
        </div>

        <div class="tab-content" id="tab-about">
          <div id="about-content">
            <div class="message message-info">טוען הסבר…</div>
          </div>
        </div>
      </div>
    </div>

    <!-- About Modal (optional – keeps CrimesMap feel) -->
    <div id="aboutModal" class="modal" aria-hidden="true">
      <div id="aboutOverlay" class="modalOverlay"></div>
      <div class="modalCard" role="dialog">
        <div class="modalHeader">
          <div class="modalHeaderTitle">ℹ️ אודות + מקורות</div>
          <button id="aboutCloseBtn" class="modalClose">×</button>
        </div>
        <div class="modalBody">
          <p style="margin-top: 0; font-weight: 900">
            SatMap – אתר בדיקה לבניינים חריגים לפי נתוני CSV (למשל InSAR/Velocity) בשילוב שכבת בניינים של GovMap.
          </p>
          <ul style="margin: 0; padding-right: 18px; font-weight: 900; color: #333; line-height: 1.6">
            <li><strong>שכבת בניינים:</strong> GovMap Layer <code class="inline">225287</code> (visibleLayers).</li>
            <li><strong>CSV:</strong> נטען מהנתיב היחסי <code class="inline">data/tablecsv.csv</code> (עם ניסיונות fallback).</li>
            <li><strong>מזהה:</strong> בלחיצה – GovMap מחזיר לרוב <code class="inline">objectid</code>, והאתר מחפש אותו ב-CSV.</li>
            <li><strong>חריגים:</strong> רק ערך מספרי שמקיים ≤ סף (שלילי) נחשב חריג; “אין נתונים” לא חריג.</li>
          </ul>
        </div>
      </div>
    </div>
  </body>
</html>

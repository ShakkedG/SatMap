// אם בעתיד יהיה לך XYZ tiles לשקיעה, תשים כאן URL template, למשל:
// const SUBSIDENCE_XYZ_URL = "./tiles/subsidence/{z}/{x}/{y}.png";
const SUBSIDENCE_XYZ_URL = null;

const map = L.map("map").setView([31.78, 35.22], 8);

const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 20,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const esriSat = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 20, attribution: "Tiles &copy; Esri" }
);

let subsidenceLayer = null;
if (SUBSIDENCE_XYZ_URL) {
  subsidenceLayer = L.tileLayer(SUBSIDENCE_XYZ_URL, { maxZoom: 20, opacity: 0.75 }).addTo(map);
}

L.control.layers(
  { "מפה רגילה (OSM)": osm, "לווין (Esri)": esriSat },
  subsidenceLayer ? { "שקיעה (XYZ)": subsidenceLayer } : {},
  { collapsed: true }
).addTo(map);

const resultEl = document.getElementById("result");
const thresholdEl = document.getElementById("threshold");
const copyBtn = document.getElementById("copyBtn");

let lastClick = null;
let marker = null;

copyBtn.addEventListener("click", async () => {
  if (!lastClick) return;
  const text = `${lastClick.lat.toFixed(6)}, ${lastClick.lng.toFixed(6)}`;
  try {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = "הועתק ✅";
    setTimeout(() => (copyBtn.textContent = "העתק קואורדינטות"), 1200);
  } catch {
    alert(text);
  }
});

// כרגע אין נתון אמיתי — בשלב הבא נחבר דגימת Raster/Points
async function getSubsidenceAt(lat, lng) {
  return null; // mm/yr
}

function statusFromValue(mmPerYear, threshold) {
  if (mmPerYear == null) return "אין נתון";
  return mmPerYear <= threshold ? "שוקע" : "יציב/עולה";
}

map.on("click", async (e) => {
  const { lat, lng } = e.latlng;
  lastClick = { lat, lng };
  copyBtn.disabled = false;

  if (marker) marker.remove();
  marker = L.marker([lat, lng]).addTo(map);

  resultEl.classList.remove("muted");
  resultEl.textContent = "טוען...";

  const threshold = Number(thresholdEl.value || -5);
  const mmPerYear = await getSubsidenceAt(lat, lng);
  const status = statusFromValue(mmPerYear, threshold);

  resultEl.textContent =
    `📍 נקודה: ${lat.toFixed(6)}, ${lng.toFixed(6)}\n` +
    `🎯 סף: ${threshold} mm/yr\n` +
    `📉 מהירות שקיעה: ${mmPerYear == null ? "N/A" : `${mmPerYear} mm/yr`}\n` +
    `✅ סטטוס: ${status}\n`;
});

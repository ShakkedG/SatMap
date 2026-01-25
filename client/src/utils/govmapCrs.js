import proj4 from "proj4";

// EPSG:2039 (Israel 1993 / ITM) – הגדרה מוכנה ל-Proj4js :contentReference[oaicite:3]{index=3}
proj4.defs(
  "EPSG:2039",
  "+proj=tmerc +lat_0=31.7343936111111 +lon_0=35.2045169444444 +k=1.0000067 +x_0=219529.584 +y_0=626907.39 +ellps=GRS80 +towgs84=23.772,17.49,17.859,-0.3132,-1.85274,1.67299,-5.4262 +units=m +no_defs +type=crs"
);

// GovMap: לפעמים X/Y זה ITM, לפעמים זה WGS84, ולפעמים (GPS) זה WebMercator (3857) :contentReference[oaicite:4]{index=4}
export function govmapXYToWgs84(x, y) {
  const X = Number(x);
  const Y = Number(y);
  if (!Number.isFinite(X) || !Number.isFinite(Y)) {
    throw new Error("קואורדינטות לא תקינות");
  }

  // אם זה כבר WGS84 לפי הטווחים של GovMap (X=lon, Y=lat)
  if (X >= 4 && X <= 36 && Y >= 29.4 && Y <= 33.4) {
    return { lat: Y, lng: X, crs: "EPSG:4326" };
  }

  // אם זה ITM / רשת ישראל החדשה לפי הטווחים של GovMap
  if (X >= 100000 && X <= 300000 && Y >= 370000 && Y <= 810000) {
    const [lng, lat] = proj4("EPSG:2039", "EPSG:4326", [X, Y]); // proj4 מחזיר [lon,lat]
    return { lat, lng, crs: "EPSG:2039" };
  }

  // אחרת נניח שזה WebMercator (EPSG:3857) כמו GPS של GovMap :contentReference[oaicite:5]{index=5}
  return webMercatorToWgs84(X, Y);
}

function webMercatorToWgs84(x, y) {
  const R = 6378137;
  const lng = (x / R) * (180 / Math.PI);
  const lat = (2 * Math.atan(Math.exp(y / R)) - Math.PI / 2) * (180 / Math.PI);
  return { lat, lng, crs: "EPSG:3857" };
}

// נוח לבנות AOI קטן סביב נקודה (למשל 200–500 מטר) בשביל חיפוש לוויין
export function bufferPointToWktRect(lat, lng, radiusMeters = 300) {
  const dLat = radiusMeters / 111320;
  const dLng = radiusMeters / (111320 * Math.cos((lat * Math.PI) / 180));

  const minLat = lat - dLat;
  const maxLat = lat + dLat;
  const minLng = lng - dLng;
  const maxLng = lng + dLng;

  // POLYGON((lng lat, ...)) – lon קודם
  return `POLYGON((${minLng} ${minLat},${maxLng} ${minLat},${maxLng} ${maxLat},${minLng} ${maxLat},${minLng} ${minLat}))`;
}

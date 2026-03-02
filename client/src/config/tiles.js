export const TILES_BASE_URL = "https://satmap-tiles.onrender.com";

// Vector tiles (מהשרת שלך)
export const BUILDINGS_TILES_TEMPLATE =
  `${TILES_BASE_URL}/tiles/buildings/{z}/{x}/{y}.pbf`;

// Fallback GeoJSON (אצלך כבר יש data/…)
export const BUILDINGS_GEOJSON_URL = "/data/buildings_joined.geojson";

// client/src/analysis/anomalies.js

// Robust slope (Theil–Sen) for monthly trend.
// Input: points = [{ t: ms, y: mm }, ...]
// Returns: slope_mm_per_day
export function theilSenSlope(points) {
  const n = points.length;
  if (n < 2) return 0;

  const slopes = [];
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const dt = (points[j].t - points[i].t) / (1000 * 60 * 60 * 24); // days
      if (dt === 0) continue;
      slopes.push((points[j].y - points[i].y) / dt);
    }
  }
  if (!slopes.length) return 0;
  slopes.sort((a, b) => a - b);
  return slopes[Math.floor(slopes.length / 2)];
}

// Median Absolute Deviation (robust std proxy)
export function mad(values) {
  if (!values.length) return 0;
  const med = median(values);
  const abs = values.map((v) => Math.abs(v - med));
  return median(abs);
}

export function median(values) {
  if (!values.length) return 0;
  const a = [...values].sort((x, y) => x - y);
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

// Compute per-point trend (mm/month) + anomaly score (relative to neighbors)
export function computeTrendAndScore(points, opts = {}) {
  const {
    neighborRadiusM = 2000, // 2 km
    minObs = 10,
    scoreThreshold = 5,
  } = opts;

  // compute trend
  const enriched = points
    .map((p) => {
      const series = (p.series || [])
        .map((s) => ({ t: new Date(s.date).getTime(), y: Number(s.mm) }))
        .filter((s) => Number.isFinite(s.t) && Number.isFinite(s.y))
        .sort((a, b) => a.t - b.t);

      if (series.length < minObs) {
        return { ...p, trend_mm_month: 0, ok: false };
      }
      const slope_mm_day = theilSenSlope(series);
      return { ...p, trend_mm_month: slope_mm_day * 30.4375, ok: true };
    })
    .filter((p) => p.ok);

  // neighbor-relative score: v_local = v - median(v neighbors)
  const trends = enriched.map((p) => p.trend_mm_month);
  const globalMAD = mad(trends) || 1e-9;

  const scored = enriched.map((p) => {
    const neigh = enriched
      .filter((q) => q !== p && haversineM(p.lat, p.lng, q.lat, q.lng) <= neighborRadiusM)
      .map((q) => q.trend_mm_month);

    const localMed = neigh.length ? median(neigh) : median(trends);
    const vLocal = p.trend_mm_month - localMed;
    const denom = (neigh.length ? mad(neigh) : globalMAD) || 1e-9;
    const score = Math.abs(vLocal) / denom;

    return { ...p, vLocal, score, isAnomaly: score >= scoreThreshold };
  });

  return scored;
}

// Simple clustering by grid (fast, no deps)
// Groups anomalies into clusters, returns GeoJSON points clusters
export function clusterAnomaliesGrid(scoredPoints, opts = {}) {
  const { cellMeters = 1000, minPoints = 6 } = opts;
  const anomalies = scoredPoints.filter((p) => p.isAnomaly);

  // approximate meters->degrees (good enough for Israel scale)
  const degLat = cellMeters / 111320;
  const clusters = new Map();

  for (const p of anomalies) {
    const key = `${Math.floor(p.lat / degLat)}:${Math.floor(p.lng / degLat)}`;
    if (!clusters.has(key)) clusters.set(key, []);
    clusters.get(key).push(p);
  }

  // build cluster features
  const features = [];
  for (const [key, pts] of clusters.entries()) {
    if (pts.length < minPoints) continue;
    const lat = pts.reduce((a, x) => a + x.lat, 0) / pts.length;
    const lng = pts.reduce((a, x) => a + x.lng, 0) / pts.length;
    const maxScore = Math.max(...pts.map((p) => p.score));
    const meanTrend = pts.reduce((a, x) => a + x.trend_mm_month, 0) / pts.length;

    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lng, lat] },
      properties: {
        count: pts.length,
        maxScore,
        meanTrend_mm_month: meanTrend,
        key,
      },
    });
  }

  return { type: "FeatureCollection", features };
}

function haversineM(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

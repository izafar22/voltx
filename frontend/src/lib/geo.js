export const validCoordinates = (lat, lng) =>
  typeof lat === "number" && Number.isFinite(lat) && Math.abs(lat) <= 90 &&
  typeof lng === "number" && Number.isFinite(lng) && Math.abs(lng) <= 180;

export function calculateDistanceKm(lat1, lng1, lat2, lng2) {
  if (!validCoordinates(lat1, lng1) || !validCoordinates(lat2, lng2)) return null;
  const rad = (degrees) => degrees * Math.PI / 180;
  const a = Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lng2 - lng1) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, a))));
}

export function formatDistance(km) {
  if (typeof km !== "number" || !Number.isFinite(km) || km < 0) return null;
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

// Rectangular discovery-map extent, including India's island regions.
export const INDIA_BOUNDS = [[6.5, 68.0], [37.5, 97.5]];

export function isWithinIndiaBounds(lat, lng) {
  return validCoordinates(lat, lng) &&
    lat >= INDIA_BOUNDS[0][0] && lat <= INDIA_BOUNDS[1][0] &&
    lng >= INDIA_BOUNDS[0][1] && lng <= INDIA_BOUNDS[1][1];
}

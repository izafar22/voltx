import { calculateDistanceKm } from "./geo";

export function getStatusGroup(status) {
  switch (typeof status === "string" ? status.trim().toLowerCase() : "") {
    case "available": return "available";
    case "charging": case "preparing": case "finishing": return "in-use";
    case "fault": return "fault";
    default: return "offline";
  }
}
export const getStatusClass = (status) => `station-status--${getStatusGroup(status)}`;
export const isAvailable = (status) => getStatusGroup(status) === "available";

export function findNearestAvailable(stations, location) {
  if (!location) return null;
  return stations.reduce((nearest, station) => {
    if (!isAvailable(station.status)) return nearest;
    const distanceKm = calculateDistanceKm(location.latitude, location.longitude, station.lat, station.lng);
    return distanceKm !== null && (!nearest || distanceKm < nearest.distanceKm)
      ? { station, distanceKm } : nearest;
  }, null);
}

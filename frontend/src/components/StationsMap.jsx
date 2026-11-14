import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { inr } from "../lib/api";
import { calculateDistanceKm, formatDistance, validCoordinates, INDIA_BOUNDS, isWithinIndiaBounds } from "../lib/geo";
import { getStatusGroup, getStatusClass, isAvailable, findNearestAvailable } from "../lib/stationStatus";
import { mapConfig } from "../config/mapConfig";
import "./StationsMap.css";

const icons = Object.fromEntries(["available", "in-use", "fault", "offline"].map((group) => [group, L.divIcon({
  className: `station-beacon station-status--${group}`,
  html: '<span class="station-beacon__ring" aria-hidden="true"></span><span class="station-beacon__led" aria-hidden="true"></span>',
  iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -16],
})]));
const customerIcon = L.divIcon({
  className: "customer-location", html: '<span aria-hidden="true"></span>',
  iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12],
});
const locationMessages = {
  loading: "Finding your location…",
  denied: "Location access is off",
  unavailable: "Unable to determine your location",
  timeout: "Location request timed out",
  unsupported: "Location is not supported by this browser",
};

// Viewport positioning is independent of station data. A future moveend observer
// can read map.getBounds() (north/south/east/west) without changing this behavior.
function InitialMapPosition({ location }) {
  const map = useMap();
  const positioned = useRef(false);
  useEffect(() => {
    if (positioned.current || !location ||
        !isWithinIndiaBounds(location.latitude, location.longitude)) return;
    positioned.current = true;
    map.setView([location.latitude, location.longitude], 13, { animate: false });
  }, [map, location]);
  return null;
}

function openNavigation({ lat, lng }) {
  if (!validCoordinates(lat, lng)) return;
  window.open(
    `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`,
    "_blank",
    "noopener,noreferrer"
  );
}

export const StationsMap = ({ stations = [], onNearbyCount }) => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [locationRequest, setLocationRequest] = useState(0);
  const [location, setLocation] = useState(null);
  const [locationState, setLocationState] = useState("loading");
  useEffect(() => {
    let active = true;
    setLocationState("loading");
    const fail = (error) => {
      if (active) setLocationState(({ 1: "denied", 2: "unavailable", 3: "timeout" })[error?.code] || "unavailable");
    };
    if (!navigator.geolocation) setLocationState("unsupported");
    else {
      try {
        navigator.geolocation.getCurrentPosition(({ coords }) => {
          if (!active) return;
          if (!validCoordinates(coords.latitude, coords.longitude)) { fail(); return; }
          setLocation({ latitude: coords.latitude, longitude: coords.longitude, accuracy: coords.accuracy });
          setLocationState("ready");
        }, fail, { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 });
      } catch { fail(); }
    }
    return () => { active = false; };
  }, [locationRequest]);
  const points = useMemo(() => stations.filter((s) => validCoordinates(s.lat, s.lng)), [stations]);
  const nearest = useMemo(() => findNearestAvailable(points, location), [points, location]);
  useEffect(() => {
    onNearbyCount?.(location ? points.filter((station) => {
      const distance = calculateDistanceKm(location.latitude, location.longitude, station.lat, station.lng);
      return isAvailable(station.status) && distance !== null && distance <= 10;
    }).length : null);
  }, [points, location, onNearbyCount]);

  return (
    <div className="stations-map relative z-0 isolate h-full w-full overflow-hidden rounded-xl" data-testid="stations-map">
      <MapContainer center={mapConfig.defaultCenter} zoom={mapConfig.defaultZoom} maxBounds={INDIA_BOUNDS} maxBoundsViscosity={1.0} minZoom={4} scrollWheelZoom className="h-full w-full">
        <TileLayer url={theme === "dark" ? mapConfig.darkUrl : mapConfig.lightUrl} attribution={mapConfig.attribution} />
        <InitialMapPosition location={location} />
        {points.map((s) => {
          const distance = location && formatDistance(calculateDistanceKm(location.latitude, location.longitude, s.lat, s.lng));
          return <Marker key={s.charger_id} position={[s.lat, s.lng]} icon={icons[getStatusGroup(s.status)]} title={`${s.name} — ${s.status || "Unknown"}`} alt={`${s.name} — ${s.status || "Unknown"}`}>
            <Popup>
              <div className="station-popup">
                <strong className="station-popup__name">{s.name}</strong>
                <div className="station-popup__id">{s.charger_id}</div>
                <div className="station-popup__location">{s.location}</div>
                <div className={`station-popup__status ${getStatusClass(s.status)}`}>{s.status || "Unknown"}</div>
                {distance && <div className="station-popup__distance">{distance} away <span>(straight-line)</span></div>}
                <div className="station-popup__specs">
                  {s.price_per_kwh != null && <span>{inr(s.price_per_kwh)}/kWh</span>}
                  {s.max_power_kw != null && <span>{s.max_power_kw} kW</span>}
                  {s.connector && <span>{s.connector}</span>}
                </div>
                <button className="station-popup__action" data-testid={`map-view-${s.charger_id}`} onClick={() => navigate(`/app/charger/${s.charger_id}`)}>
                  View charger
                </button>
                {validCoordinates(s.lat, s.lng) && <button
                  type="button"
                  className="station-popup__action station-popup__navigate"
                  data-testid={`map-navigate-${s.charger_id}`}
                  aria-label="Navigate (opens Google Maps in a new tab)"
                  onClick={() => openNavigation(s)}>
                  Navigate
                </button>}
              </div>
            </Popup>
          </Marker>;
        })}
        {location && <>
          {Number.isFinite(location.accuracy) && location.accuracy > 0 && <Circle center={[location.latitude, location.longitude]} radius={location.accuracy} interactive={false} pathOptions={{ color: "#2563eb", weight: 1, fillOpacity: 0.08 }} />}
          <Marker position={[location.latitude, location.longitude]} icon={customerIcon} title="You are here" alt="Your location"><Popup>You are here</Popup></Marker>
        </>}
      </MapContainer>
      {(locationState !== "ready" || nearest) && <div className="map-overlay map-summary" role="status" aria-live="polite">
        {locationState !== "ready" ? <>
          <span>{locationMessages[locationState]}</span>
          {locationState !== "loading" && locationState !== "unsupported" && <button type="button" onClick={() => setLocationRequest((value) => value + 1)} className="map-location-retry">
            {locationState === "denied" ? "Enable location" : "Try location again"}
          </button>}
          {locationState === "denied" && <span>Allow location in your browser’s site settings, then retry.</span>}
        </> : <><strong>Nearest available</strong><button className="map-nearest-link" onClick={() => navigate(`/app/charger/${nearest.station.charger_id}`)}>{nearest.station.name}</button><span>{formatDistance(nearest.distanceKm)} away</span></>}
      </div>}
      <div className="map-overlay map-legend" aria-label="Charger status legend">
        {[["available", "Available"], ["in-use", "In use"], ["fault", "Fault"], ["offline", "Offline"]].map(([group, label]) => <span className="map-legend__item" key={group}><i className={`station-beacon station-status--${group}`} aria-hidden="true"><span className="station-beacon__ring" /><span className="station-beacon__led" /></i>{label}</span>)}
      </div>
    </div>
  );
};

import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useNavigate } from "react-router-dom";
import { useTheme } from "@/context/ThemeContext";
import { inr } from "@/lib/api";

const COLORS = { Available: "#16A34A", Charging: "#F59E0B", Preparing: "#F59E0B", Finishing: "#F59E0B", Offline: "#71717A", Fault: "#FF3B30" };

const makeIcon = (status) => {
  const color = COLORS[status] || "#71717A";
  const pulse = status === "Charging" || status === "Available";
  return L.divIcon({
    className: "",
    html: `<div style="position:relative;display:flex;align-items:center;justify-content:center">
      ${pulse ? `<span style="position:absolute;width:26px;height:26px;border-radius:9999px;background:${color};opacity:0.25"></span>` : ""}
      <span style="width:16px;height:16px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></span>
    </div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -12],
  });
};

export const StationsMap = ({ stations = [] }) => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const pts = stations.filter((s) => s.lat != null && s.lng != null);
  const center = pts.length ? [pts.reduce((a, s) => a + s.lat, 0) / pts.length, pts.reduce((a, s) => a + s.lng, 0) / pts.length] : [20.59, 78.96];
  const tile = theme === "dark"
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

  return (
    <div className="relative z-0 isolate h-full w-full overflow-hidden rounded-xl" data-testid="stations-map">
      <MapContainer center={center} zoom={5} scrollWheelZoom className="h-full w-full" style={{ background: "transparent" }}>
        <TileLayer key={theme} url={tile} attribution='&copy; OpenStreetMap &copy; CARTO' />
        {pts.map((s) => (
          <Marker key={s.charger_id} position={[s.lat, s.lng]} icon={makeIcon(s.status)}>
            <Popup>
              <div style={{ minWidth: 180 }}>
                <div style={{ fontWeight: 700, fontSize: 14 }}>{s.name}</div>
                <div style={{ fontSize: 12, color: "#666", fontFamily: "monospace" }}>{s.charger_id} · {s.location}</div>
                <div style={{ display: "flex", gap: 8, marginTop: 6, fontSize: 12 }}>
                  <span style={{ color: COLORS[s.status], fontWeight: 600 }}>{s.status}</span>
                  <span>· {inr(s.price_per_kwh)}/kWh</span>
                  <span>· {s.max_power_kw}kW</span>
                </div>
                <button
                  data-testid={`map-view-${s.charger_id}`}
                  onClick={() => navigate(`/app/charger/${s.charger_id}`)}
                  style={{ marginTop: 8, width: "100%", padding: "6px 10px", borderRadius: 8, border: "none", background: s.status === "Available" ? "#16A34A" : "#333", color: "#fff", cursor: "pointer", fontWeight: 600 }}>
                  {s.status === "Available" ? "Start charging" : "View charger"}
                </button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

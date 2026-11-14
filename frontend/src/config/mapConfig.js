// CRA embeds REACT_APP_* values in the public bundle. Never put secrets here.
const defaultTileUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const attribution = process.env.REACT_APP_MAP_ATTRIBUTION || process.env.REACT_APP_MAP_TILE_ATTRIBUTION ||
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
export const mapConfig = {
  lightUrl: process.env.REACT_APP_MAP_TILE_URL || defaultTileUrl,
  darkUrl: process.env.REACT_APP_MAP_TILE_DARK_URL || process.env.REACT_APP_MAP_TILE_URL || defaultTileUrl,
  attribution,
  defaultCenter: [22.9734, 78.6569],
  defaultZoom: 5,
};

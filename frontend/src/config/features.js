// Frontend release switches, not authorization controls. Backend permissions still apply.
// Enable charging first, then the desired entry points for a future release.
export const FEATURES = {
  repair: true,
  charging: false,
  qrCharging: false,
  stationDiscovery: false,
  stationMap: false,
  wallet: false, // Currently funds charging only; repair estimates do not use it.
};

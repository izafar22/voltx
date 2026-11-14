const KEY = "rushx.repair-destination";
export function rememberRepairDestination(path) {
  if (path === "/repairs" || path === "/repairs/new") {
    try {
      sessionStorage.setItem(KEY, path);
    } catch {
      /* Storage may be disabled. */
    }
  }
}
export function readRepairDestination(fallback) {
  try {
    const path = sessionStorage.getItem(KEY);
    return path === "/repairs" || path === "/repairs/new" ? path : fallback;
  } catch {
    return fallback;
  }
}

export function takeRepairDestination(fallback) {
  const destination = readRepairDestination(fallback);
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* Storage may be disabled. */
  }
  return destination;
}

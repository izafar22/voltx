const key = "rushx.auth.returnTo";
export function safeDestination(value) {
  if (typeof value !== "string" || /[\\\s\x00-\x1f]/.test(value)) return null;
  return /^\/(?:app(?:\/[A-Za-z0-9_-]+)*|repairs(?:\/[A-Za-z0-9_-]+)?|owner|admin)(?:[?#].*)?$/.test(
    value,
  )
    ? value
    : null;
}
export function intendedDestination(state) {
  return (
    safeDestination(state?.from) || safeDestination(sessionStorage.getItem(key))
  );
}
export function rememberDestination(value) {
  const path = safeDestination(value);
  if (path) sessionStorage.setItem(key, path);
  else sessionStorage.removeItem(key);
}
export function clearDestination() {
  sessionStorage.removeItem(key);
}

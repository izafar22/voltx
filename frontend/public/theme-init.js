/* Read-only pre-paint bootstrap. ThemeContext owns subsequent state and persistence. */
(function () {
  var preference;
  try {
    preference = window.localStorage.getItem("rushx-theme");
  } catch (_) {}
  var theme =
    preference === "light" || preference === "dark"
      ? preference
      : window.matchMedia &&
          window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
})();

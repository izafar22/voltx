import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useState,
} from "react";

const ThemeContext = createContext();
const validTheme = (value) => value === "light" || value === "dark";
const systemTheme = () =>
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
const preferredTheme = () => {
  try {
    const stored = localStorage.getItem("rushx-theme");
    if (validTheme(stored)) return stored;
  } catch {
    /* Private browsing can disable storage. */
  }
  return systemTheme();
};
// Storybook controls this same provider; the app uses its persisted default.
export const ThemeProvider = ({
  children,
  theme: controlledTheme,
  onThemeChange,
}) => {
  const [preference, setPreference] = useState(preferredTheme);
  const theme = validTheme(controlledTheme) ? controlledTheme : preference;
  const setTheme = (value) => {
    if (!validTheme(value)) return;
    setPreference(value);
    onThemeChange?.(value);
  };
  useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
    try {
      localStorage.setItem("rushx-theme", theme);
    } catch {
      /* Theme still works without persistence. */
    }
  }, [theme]);
  useEffect(() => {
    const sync = (event) => {
      if (event.key === "rushx-theme")
        setPreference(
          validTheme(event.newValue) ? event.newValue : systemTheme(),
        );
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        toggle: () => setTheme(theme === "dark" ? "light" : "dark"),
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};
export const useTheme = () => useContext(ThemeContext);

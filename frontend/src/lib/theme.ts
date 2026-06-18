// Light/dark theme: persisted in localStorage, honors prefers-color-scheme on first load.

export type Theme = "light" | "dark";

const KEY = "openfpa-theme";

export function getStoredTheme(): Theme | null {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : null;
}

export function resolveInitialTheme(): Theme {
  const stored = getStoredTheme();
  if (stored) return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(KEY, theme);
  applyTheme(theme);
}

/** Call once before render to avoid a flash of the wrong theme. */
export function initTheme(): Theme {
  const theme = resolveInitialTheme();
  applyTheme(theme);
  return theme;
}

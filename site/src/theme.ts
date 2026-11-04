export const THEME_STORAGE_KEY = "paper-theme";

export type PaperTheme = "light" | "dark";

export function isPaperTheme(value: string | null): value is PaperTheme {
  return value === "light" || value === "dark";
}

export function themeFromDocument(): PaperTheme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function applyTheme(theme: PaperTheme, persist: boolean): void {
  document.documentElement.dataset.theme = theme;
  if (!persist) {
    return;
  }
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // A blocked storage API still leaves the choice on the document for this visit.
  }
}

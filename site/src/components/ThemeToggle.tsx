import { useEffect, useState } from "react";
import { applyTheme, isPaperTheme, themeFromDocument, THEME_STORAGE_KEY, type PaperTheme } from "../theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<PaperTheme>(() => themeFromDocument());

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(THEME_STORAGE_KEY);
    } catch {
      stored = null;
    }
    if (isPaperTheme(stored)) {
      return;
    }

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const next: PaperTheme = media.matches ? "dark" : "light";
      applyTheme(next, false);
      setTheme(next);
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const nextTheme: PaperTheme = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-pressed={theme === "dark"}
      onClick={() => {
        applyTheme(nextTheme, true);
        setTheme(nextTheme);
      }}
    >
      {theme === "dark" ? "Use light paper" : "Use dark paper"}
    </button>
  );
}

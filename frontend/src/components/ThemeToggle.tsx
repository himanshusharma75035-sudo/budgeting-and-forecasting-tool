import { Moon, Sun } from "lucide-react";
import { useState } from "react";

import { resolveInitialTheme, setTheme, type Theme } from "../lib/theme";
import { Button } from "./ui/button";

export function ThemeToggle() {
  const [theme, setThemeState] = useState<Theme>(() => resolveInitialTheme());

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      title="Toggle theme"
    >
      {theme === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}

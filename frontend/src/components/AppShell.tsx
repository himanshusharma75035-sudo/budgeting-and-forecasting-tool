import { X } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "../lib/utils";
import { CommandPalette } from "./CommandPalette";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

const COLLAPSE_KEY = "openfpa-sidebar-collapsed";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem(COLLAPSE_KEY) === "1",
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function toggleSidebar() {
    if (window.matchMedia("(min-width: 768px)").matches) {
      setCollapsed((c) => !c);
    } else {
      setMobileOpen(true);
    }
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* desktop sidebar */}
      <aside
        className={cn(
          "hidden shrink-0 border-r border-border bg-sidebar transition-[width] duration-200 md:block",
          collapsed ? "w-16" : "w-64",
        )}
      >
        <Sidebar collapsed={collapsed} />
      </aside>

      {/* mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-border bg-sidebar">
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute right-2 top-2 inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
              aria-label="Close menu"
            >
              <X className="size-4" />
            </button>
            <Sidebar collapsed={false} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      {/* main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onToggleSidebar={toggleSidebar} onOpenPalette={() => setPaletteOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1440px] p-6 md:p-8">{children}</div>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}

import { PanelLeft, Search } from "lucide-react";
import { useLocation } from "react-router-dom";

import { Select } from "./ui/select";
import { ThemeToggle } from "./ThemeToggle";
import { navItems } from "./navItems";

function useCrumb(): string {
  const { pathname } = useLocation();
  const item = navItems.find((i) => i.to === pathname);
  return item?.label ?? "Overview";
}

export function TopBar({
  onToggleSidebar,
  onOpenPalette,
}: {
  onToggleSidebar: () => void;
  onOpenPalette: () => void;
}) {
  const crumb = useCrumb();
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-card/95 px-4 backdrop-blur">
      <button
        onClick={onToggleSidebar}
        className="inline-flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        aria-label="Toggle sidebar"
      >
        <PanelLeft className="size-4" />
      </button>

      <nav aria-label="Breadcrumb" className="hidden items-center gap-2 text-sm sm:flex">
        <span className="text-muted-foreground">OpenFP&A</span>
        <span className="text-muted-foreground">/</span>
        <span className="font-medium" aria-current="page">
          {crumb}
        </span>
      </nav>

      <button
        onClick={onOpenPalette}
        className="ml-2 hidden h-9 w-64 items-center gap-2 rounded-md border border-border bg-background px-3 text-sm text-muted-foreground hover:bg-muted md:flex"
      >
        <Search className="size-4" />
        <span className="flex-1 text-left">Search…</span>
        <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">⌘K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-2">
        <div className="hidden w-28 sm:block">
          <Select defaultValue="FY26" aria-label="Fiscal year">
            <option value="FY26">FY 2026</option>
            <option value="FY25">FY 2025</option>
          </Select>
        </div>
        <div className="hidden w-32 sm:block">
          <Select defaultValue="ACTUAL" aria-label="Scenario">
            <option value="ACTUAL">Actuals</option>
            <option value="BUDGET">Budget</option>
            <option value="FORECAST">Forecast</option>
          </Select>
        </div>
        <ThemeToggle />
        <div
          className="flex size-8 items-center justify-center rounded-full bg-muted text-xs font-medium"
          title="Local user"
        >
          HS
        </div>
      </div>
    </header>
  );
}

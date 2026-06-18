import { Activity } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "../lib/utils";
import { navGroups, navItems } from "./navItems";

export function Sidebar({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      {/* brand / workspace */}
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-4">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Activity className="size-4" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold leading-tight">OpenFP&A</div>
            <div className="truncate text-xs text-muted-foreground">Demo workspace</div>
          </div>
        )}
      </div>

      {/* nav groups */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {navGroups.map((group) => {
          const items = navItems.filter((i) => i.group === group);
          if (items.length === 0) return null;
          return (
            <div key={group} className="mb-4">
              {!collapsed && (
                <div className="px-3 pb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {group}
                </div>
              )}
              <ul className="space-y-0.5">
                {items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === "/"}
                      onClick={onNavigate}
                      title={collapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        cn(
                          "relative flex h-9 items-center gap-3 rounded-md px-3 text-sm text-sidebar-foreground transition-colors hover:bg-muted hover:text-foreground",
                          collapsed && "justify-center px-0",
                          isActive &&
                            "bg-accent font-medium text-accent-foreground before:absolute before:left-0 before:h-5 before:w-[2px] before:rounded-full before:bg-primary",
                        )
                      }
                    >
                      <item.icon className="size-4 shrink-0" />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
          Local · SQLite
        </div>
      )}
    </div>
  );
}

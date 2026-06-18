import { Command } from "cmdk";
import { Moon } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { resolveInitialTheme, setTheme } from "../lib/theme";
import { navItems } from "./navItems";

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const navigate = useNavigate();

  function run(action: () => void) {
    action();
    onOpenChange(false);
  }

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label="Command menu"
      className="fixed left-1/2 top-[20%] z-50 w-full max-w-[640px] -translate-x-1/2 overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-lg"
      overlayClassName="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
    >
      <Command.Input
        placeholder="Search pages and actions…"
        className="h-12 w-full border-b border-border bg-transparent px-4 text-sm outline-none placeholder:text-muted-foreground"
      />
      <Command.List className="max-h-80 overflow-y-auto p-2">
        <Command.Empty className="py-8 text-center text-sm text-muted-foreground">
          No results found.
        </Command.Empty>
        <Command.Group
          heading="Navigate"
          className="px-1 py-1 text-xs font-medium text-muted-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pb-1"
        >
          {navItems.map((item) => (
            <Command.Item
              key={item.to}
              value={`Go to ${item.label}`}
              onSelect={() => run(() => navigate(item.to))}
              className="flex h-9 cursor-pointer items-center gap-3 rounded-md px-2 text-sm text-foreground data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
            >
              <item.icon className="size-4" />
              {item.label}
            </Command.Item>
          ))}
        </Command.Group>
        <Command.Group
          heading="Actions"
          className="px-1 py-1 text-xs font-medium text-muted-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pb-1"
        >
          <Command.Item
            value="Toggle theme dark light"
            onSelect={() =>
              run(() => setTheme(resolveInitialTheme() === "dark" ? "light" : "dark"))
            }
            className="flex h-9 cursor-pointer items-center gap-3 rounded-md px-2 text-sm text-foreground data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
          >
            <Moon className="size-4" />
            Toggle theme
          </Command.Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}

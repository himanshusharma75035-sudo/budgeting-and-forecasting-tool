import type { TooltipContentProps } from "recharts";

import { fmtCurrency } from "../../lib/format";

/** Themed tooltip; hides transparent helper series (band bases). */
export function FinanceTooltip({ active, payload, label }: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload || payload.length === 0) return null;
  const rows = payload.filter(
    (p) => p.value != null && p.color !== "transparent" && !String(p.dataKey).startsWith("_"),
  );
  if (rows.length === 0) return null;
  return (
    <div className="rounded-md border border-border bg-popover p-3 text-sm shadow-md">
      {label != null && <div className="mb-1 font-medium text-popover-foreground">{label}</div>}
      <div className="flex flex-col gap-1">
        {rows.map((p, i) => (
          <div key={i} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span
                className="inline-block size-2 rounded-full"
                style={{ background: p.color ?? "var(--chart-1)" }}
              />
              {p.name}
            </span>
            <span className="tabular font-medium text-popover-foreground">
              {typeof p.value === "number" ? fmtCurrency(p.value) : String(p.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

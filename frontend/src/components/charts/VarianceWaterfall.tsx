import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
  XAxis,
  YAxis,
} from "recharts";

import { fmtCurrency, fmtCurrencyCompact, fmtDeltaCompact } from "../../lib/format";

export type WaterfallType = "total" | "favorable" | "unfavorable";

export interface WaterfallRow {
  name: string;
  type: WaterfallType;
  _base: number;
  value: number;
  signed: number;
}

export interface BridgeStep {
  label: string;
  delta: number;
}

/** Build IBCS waterfall rows: start total -> +/- contributions -> end total. */
export function buildBridgeRows(
  start: number,
  steps: BridgeStep[],
  end: number,
  startLabel = "Budget",
  endLabel = "Actual",
): WaterfallRow[] {
  const rows: WaterfallRow[] = [
    { name: startLabel, type: "total", _base: 0, value: start, signed: start },
  ];
  let running = start;
  for (const s of steps) {
    const next = running + s.delta;
    rows.push({
      name: s.label,
      type: s.delta >= 0 ? "favorable" : "unfavorable",
      _base: Math.min(running, next),
      value: Math.abs(s.delta),
      signed: s.delta,
    });
    running = next;
  }
  rows.push({ name: endLabel, type: "total", _base: 0, value: end, signed: end });
  return rows;
}

// Short axis labels so the category names don't collide.
const SHORT: Record<string, string> = {
  "Revenue from operations": "Revenue",
  "Other income": "Other inc.",
  "Cost of materials consumed": "Materials",
  "Purchases of stock-in-trade": "Purchases",
  "Changes in inventories": "Inventory",
  "Employee benefits expense": "Employee",
  "Other expenses": "Other exp.",
  "Finance costs": "Finance",
  "Depreciation & amortization": "Deprec.",
  "Tax expense": "Tax",
  Budget: "Budget",
  Actual: "Actual",
};
const short = (name: string): string => SHORT[name] ?? (name.length > 11 ? `${name.slice(0, 10)}…` : name);

function WaterfallTooltip({ active, payload }: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0]?.payload as WaterfallRow | undefined;
  if (!row) return null;
  const isTotal = row.type === "total";
  return (
    <div className="rounded-md border border-border bg-popover p-3 text-sm shadow-md">
      <div className="mb-1 font-medium text-popover-foreground">{row.name}</div>
      <div className="flex items-center justify-between gap-6">
        <span className="text-muted-foreground">{isTotal ? "Total" : "Contribution"}</span>
        <span
          className={`tabular font-medium ${
            isTotal ? "text-popover-foreground" : row.signed >= 0 ? "text-pos" : "text-neg"
          }`}
        >
          {isTotal ? fmtCurrency(row.signed) : fmtDeltaCompact(row.signed)}
        </span>
      </div>
    </div>
  );
}

export interface VarianceWaterfallProps {
  rows: WaterfallRow[];
  colorblind?: boolean;
}

export function VarianceWaterfall({ rows, colorblind = false }: VarianceWaterfallProps) {
  const posColor = colorblind ? "var(--chart-3)" : "var(--pos)";
  const negColor = colorblind ? "var(--chart-4)" : "var(--neg)";
  const fillFor = (t: WaterfallType): string =>
    t === "total" ? "var(--chart-ink)" : t === "favorable" ? posColor : negColor;

  const data = rows.map((r) => ({
    ...r,
    labelText: r.type === "total" ? fmtCurrencyCompact(r.value) : fmtDeltaCompact(r.signed),
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} barCategoryGap="18%" margin={{ top: 24, right: 12, bottom: 8, left: 8 }}>
        <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />
        <XAxis
          dataKey="name"
          tickFormatter={short}
          axisLine={false}
          tickLine={false}
          interval={0}
          angle={-35}
          textAnchor="end"
          height={64}
          tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
        />
        <YAxis
          axisLine={false}
          tickLine={false}
          width={60}
          tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
          tickFormatter={(v: number) => fmtCurrencyCompact(v)}
        />
        <Tooltip content={<WaterfallTooltip />} cursor={{ fill: "var(--muted)", opacity: 0.4 }} />
        <ReferenceLine y={0} stroke="var(--chart-axis)" />
        <Bar dataKey="_base" stackId="w" fill="transparent" isAnimationActive={false} legendType="none" />
        <Bar dataKey="value" stackId="w" radius={[2, 2, 0, 0]} isAnimationActive={false} maxBarSize={64}>
          {rows.map((r, i) => (
            <Cell key={i} fill={fillFor(r.type)} />
          ))}
          <LabelList dataKey="labelText" position="top" fill="var(--chart-axis)" fontSize={11} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

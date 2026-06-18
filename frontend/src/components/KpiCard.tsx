import { ArrowDown, ArrowUp } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

import { fmtPctSigned } from "../lib/format";
import { cn } from "../lib/utils";
import { Card } from "./ui/card";

export interface KpiCardProps {
  label: string;
  value: string;
  /** signed percentage delta (e.g. 4.2 or -3.1) */
  deltaPct?: number | null;
  /** comparison basis caption, e.g. "vs Budget" */
  basis?: string;
  /** higher-is-better? expense KPIs set false so a positive delta reads as negative */
  higherIsBetter?: boolean;
  sparkline?: number[];
}

export function KpiCard({
  label,
  value,
  deltaPct,
  basis,
  higherIsBetter = true,
  sparkline,
}: KpiCardProps) {
  const hasDelta = deltaPct != null && !Number.isNaN(deltaPct);
  const favorable = hasDelta ? (higherIsBetter ? deltaPct! >= 0 : deltaPct! <= 0) : true;
  const tone = favorable ? "var(--pos)" : "var(--neg)";
  const Arrow = hasDelta && deltaPct! < 0 ? ArrowDown : ArrowUp;

  return (
    <Card className="flex flex-col gap-3 p-5">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="flex items-end justify-between gap-2">
        <span className="text-3xl font-semibold tracking-tight tabular">{value}</span>
        {sparkline && sparkline.length > 1 && (
          <div className="h-8 w-20 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sparkline.map((v, i) => ({ i, v }))}>
                <Area
                  dataKey="v"
                  stroke={tone}
                  strokeWidth={1.5}
                  fill={tone}
                  fillOpacity={0.12}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      {hasDelta && (
        <div className="flex items-center gap-1.5 text-sm">
          <span
            className={cn(
              "inline-flex items-center gap-0.5 font-medium tabular",
              favorable ? "text-pos" : "text-neg",
            )}
          >
            <Arrow className="size-3.5" />
            {fmtPctSigned(deltaPct)}
          </span>
          {basis && <span className="text-muted-foreground">{basis}</span>}
        </div>
      )}
    </Card>
  );
}

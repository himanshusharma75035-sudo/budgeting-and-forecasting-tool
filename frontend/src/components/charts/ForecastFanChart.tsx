import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fmtCurrencyCompact } from "../../lib/format";
import { FinanceTooltip } from "./FinanceTooltip";

export interface ForecastFanChartProps {
  history: number[];
  point: number[];
  lower: Record<string | number, number[]>;
  upper: Record<string | number, number[]>;
  historyLabels?: string[];
  forecastLabels?: string[];
}

type Row = Record<string, number | string | undefined>;

function arr(rec: Record<string | number, number[]>, lvl: number): number[] {
  return rec[lvl] ?? rec[String(lvl)] ?? [];
}

export function ForecastFanChart({
  history,
  point,
  lower,
  upper,
  historyLabels,
  forecastLabels,
}: ForecastFanChartProps) {
  // Levels actually present in the response (both bounds), ascending.
  const levels = Object.keys(upper)
    .map(Number)
    .filter((l) => arr(lower, l).length > 0 && arr(upper, l).length > 0)
    .sort((a, b) => a - b);
  const outer = levels.at(-1);
  const inner = levels.length > 1 ? levels[0] : undefined;

  const rows: Row[] = history.map((v, i) => ({
    t: historyLabels?.[i] ?? `P${i + 1}`,
    history: v,
  }));

  const boundary = rows[rows.length - 1];
  if (boundary) {
    boundary.forecast = boundary.history;
    boundary._loOuter = boundary.history as number;
    boundary.bandOuter = 0;
    boundary._loInner = boundary.history as number;
    boundary.bandInner = 0;
  }

  point.forEach((p, k) => {
    const row: Row = { t: forecastLabels?.[k] ?? `+${k + 1}`, forecast: p };
    if (outer != null) {
      const lo = arr(lower, outer)[k];
      const hi = arr(upper, outer)[k];
      if (lo != null && hi != null) {
        row._loOuter = lo;
        row.bandOuter = hi - lo;
      }
    }
    if (inner != null) {
      const lo = arr(lower, inner)[k];
      const hi = arr(upper, inner)[k];
      if (lo != null && hi != null) {
        row._loInner = lo;
        row.bandInner = hi - lo;
      }
    }
    rows.push(row);
  });

  const todayLabel = boundary?.t as string | undefined;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />
        <XAxis
          dataKey="t"
          axisLine={false}
          tickLine={false}
          tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
          minTickGap={24}
        />
        <YAxis
          axisLine={false}
          tickLine={false}
          width={56}
          tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
          tickFormatter={(v: number) => fmtCurrencyCompact(v)}
        />
        <Tooltip content={<FinanceTooltip />} />

        {outer != null && (
          <>
            <Area dataKey="_loOuter" stackId="bo" stroke="none" fill="transparent" isAnimationActive={false} activeDot={false} legendType="none" />
            <Area
              name={`${outer}% interval`}
              dataKey="bandOuter"
              stackId="bo"
              stroke="none"
              fill="var(--chart-1)"
              fillOpacity={0.12}
              isAnimationActive={false}
              activeDot={false}
            />
          </>
        )}
        {inner != null && (
          <>
            <Area dataKey="_loInner" stackId="bi" stroke="none" fill="transparent" isAnimationActive={false} activeDot={false} legendType="none" />
            <Area
              name={`${inner}% interval`}
              dataKey="bandInner"
              stackId="bi"
              stroke="none"
              fill="var(--chart-1)"
              fillOpacity={0.24}
              isAnimationActive={false}
              activeDot={false}
            />
          </>
        )}

        <Line name="Actual" dataKey="history" stroke="var(--chart-ink)" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line
          name="Forecast"
          dataKey="forecast"
          stroke="var(--chart-1)"
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={false}
          isAnimationActive={false}
        />

        {todayLabel && (
          <ReferenceLine
            x={todayLabel}
            stroke="var(--chart-axis)"
            strokeDasharray="3 3"
            label={{ value: "Forecast →", position: "insideTopRight", fill: "var(--chart-axis)", fontSize: 12 }}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

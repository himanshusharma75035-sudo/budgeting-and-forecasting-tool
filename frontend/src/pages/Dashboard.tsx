import { useQuery } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartCard } from "../components/ChartCard";
import { FinanceTooltip } from "../components/charts/FinanceTooltip";
import { EmptyState } from "../components/EmptyState";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { apiGet } from "../lib/api";
import { fmtCurrencyCompact } from "../lib/format";
import type { AccountOut, EntryOut } from "../lib/types";

const REVENUE_TYPES = new Set(["REVENUE", "OTHER_INCOME"]);
const COST_TYPES = new Set(["COGS", "OPEX", "OTHER_EXPENSE"]);

interface MonthAgg {
  period: string;
  revenue: number;
  cost: number;
  net: number;
}

function aggregate(entries: EntryOut[], typeByCode: Map<string, string>): MonthAgg[] {
  const byPeriod = new Map<string, { revenue: number; cost: number }>();
  for (const e of entries) {
    const t = typeByCode.get(e.account_code);
    if (!t) continue;
    const slot = byPeriod.get(e.period) ?? { revenue: 0, cost: 0 };
    if (REVENUE_TYPES.has(t)) slot.revenue += e.amount;
    else if (COST_TYPES.has(t)) slot.cost += e.amount;
    byPeriod.set(e.period, slot);
  }
  return [...byPeriod.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period, v]) => ({ period, revenue: v.revenue, cost: v.cost, net: v.revenue - v.cost }));
}

function pctChange(curr: number, prev: number): number | null {
  if (prev === 0) return null;
  return ((curr - prev) / Math.abs(prev)) * 100;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const accountsQ = useQuery({
    queryKey: ["accounts"],
    queryFn: () => apiGet<AccountOut[]>("/accounts"),
  });
  const entriesQ = useQuery({
    queryKey: ["entries", "ACTUAL"],
    queryFn: () => apiGet<EntryOut[]>("/entries?scenario=ACTUAL"),
  });

  const loading = accountsQ.isLoading || entriesQ.isLoading;
  const typeByCode = new Map((accountsQ.data ?? []).map((a) => [a.account_code, a.account_type]));
  const series = entriesQ.data ? aggregate(entriesQ.data, typeByCode) : [];
  const last = series.at(-1);
  const prev = series.at(-2);

  const header = (
    <PageHeader
      title="Dashboard"
      subtitle="Company financial overview"
      caption="Source: local workspace · Actuals"
      actions={
        <Button onClick={() => navigate("/import")}>
          <Upload /> Import data
        </Button>
      }
    />
  );

  if (loading) {
    return (
      <>
        {header}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80" />
        </div>
      </>
    );
  }

  if (!last) {
    return (
      <>
        {header}
        <Card className="p-6">
          <EmptyState
            icon={Upload}
            title="No data yet"
            description="Seed the demo workspace or import a CSV/Excel file to populate the dashboard."
            action={<Button onClick={() => navigate("/import")}>Import data</Button>}
          />
        </Card>
      </>
    );
  }

  const revSpark = series.map((s) => s.revenue);
  const costSpark = series.map((s) => s.cost);
  const netSpark = series.map((s) => s.net);

  return (
    <>
      {header}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Revenue (latest)"
          value={fmtCurrencyCompact(last.revenue)}
          deltaPct={prev ? pctChange(last.revenue, prev.revenue) : null}
          basis="vs prior month"
          sparkline={revSpark}
        />
        <KpiCard
          label="Operating costs"
          value={fmtCurrencyCompact(last.cost)}
          deltaPct={prev ? pctChange(last.cost, prev.cost) : null}
          basis="vs prior month"
          higherIsBetter={false}
          sparkline={costSpark}
        />
        <KpiCard
          label="Net income"
          value={fmtCurrencyCompact(last.net)}
          deltaPct={prev ? pctChange(last.net, prev.net) : null}
          basis="vs prior month"
          sparkline={netSpark}
        />
        <KpiCard
          label="Accounts"
          value={String(accountsQ.data?.length ?? 0)}
          basis="chart of accounts"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ChartCard
          title="Revenue, cost & net trend"
          className="lg:col-span-2"
          aside={
            <Legend
              items={[
                ["Revenue", "var(--chart-1)"],
                ["Cost", "var(--chart-prior)"],
                ["Net", "var(--chart-2)"],
              ]}
            />
          }
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />
              <XAxis
                dataKey="period"
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
              <Line
                name="Revenue"
                dataKey="revenue"
                stroke="var(--chart-1)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                name="Cost"
                dataKey="cost"
                stroke="var(--chart-prior)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                name="Net"
                dataKey="net"
                stroke="var(--chart-2)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Net income by month">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={series} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />
              <XAxis
                dataKey="period"
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
              <Tooltip content={<FinanceTooltip />} cursor={{ fill: "var(--muted)", opacity: 0.4 }} />
              <Bar name="Net" dataKey="net" radius={[2, 2, 0, 0]} isAnimationActive={false}>
                {series.map((s, i) => (
                  <Cell key={i} fill={s.net >= 0 ? "var(--pos)" : "var(--neg)"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </>
  );
}

function Legend({ items }: { items: [string, string][] }) {
  return (
    <>
      {items.map(([label, color]) => (
        <span key={label} className="flex items-center gap-1.5">
          <span className="inline-block size-2 rounded-full" style={{ background: color }} />
          {label}
        </span>
      ))}
    </>
  );
}

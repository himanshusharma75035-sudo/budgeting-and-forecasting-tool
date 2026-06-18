import { useQuery } from "@tanstack/react-query";
import { GitCompareArrows } from "lucide-react";
import { useState } from "react";

import { ChartCard } from "../components/ChartCard";
import { buildBridgeRows, VarianceWaterfall } from "../components/charts/VarianceWaterfall";
import { EmptyState } from "../components/EmptyState";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { apiPost } from "../lib/api";
import { fmtCurrency, fmtCurrencyCompact, fmtPctSigned } from "../lib/format";
import type { BridgeOut, VarianceComputeRequest, VarianceRowOut } from "../lib/types";
import { cn } from "../lib/utils";

const SCENARIOS = ["ACTUAL", "BUDGET", "FORECAST"];

function statusClass(status: string): string {
  if (status === "FAVORABLE") return "text-pos";
  if (status === "UNFAVORABLE") return "text-neg";
  return "text-muted-foreground";
}

export default function Variance() {
  const [base, setBase] = useState("ACTUAL");
  const [compare, setCompare] = useState("BUDGET");
  const [colorblind, setColorblind] = useState(false);

  const req: VarianceComputeRequest = { base_scenario: base, compare_scenario: compare };

  const rowsQ = useQuery({
    queryKey: ["variance", base, compare],
    queryFn: () => apiPost<VarianceRowOut[]>("/variance/compute", req),
  });
  const bridgeQ = useQuery({
    queryKey: ["variance-bridge", base, compare],
    queryFn: () => apiPost<BridgeOut>("/variance/bridge", req),
  });

  const rows = (rowsQ.data ?? [])
    .slice()
    .sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance));

  const bridge = bridgeQ.data;
  const waterfall = bridge ? buildBridgeRows(bridge.start, bridge.steps, bridge.end) : [];
  const net = bridge ? bridge.end - bridge.start : 0;
  const favCount = rows.filter((r) => r.status === "FAVORABLE").length;
  const unfavCount = rows.filter((r) => r.status === "UNFAVORABLE").length;

  const isLoading = rowsQ.isLoading || bridgeQ.isLoading;

  return (
    <>
      <PageHeader
        title="Variance Analysis"
        subtitle="Budget vs actual with a contribution bridge"
        actions={
          <div className="flex items-center gap-2">
            <div className="w-32">
              <Select value={base} onChange={(e) => setBase(e.target.value)} aria-label="Base scenario">
                {SCENARIOS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </div>
            <span className="text-sm text-muted-foreground">vs</span>
            <div className="w-32">
              <Select
                value={compare}
                onChange={(e) => setCompare(e.target.value)}
                aria-label="Compare scenario"
              >
                {SCENARIOS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        }
      />

      {isLoading && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
          <Skeleton className="mt-6 h-80" />
        </>
      )}

      {!isLoading && rows.length === 0 && (
        <Card className="p-6">
          <EmptyState
            icon={GitCompareArrows}
            title="Nothing to compare yet"
            description={`No overlapping ${base} and ${compare} data. Generate a budget or import data, then compare.`}
          />
        </Card>
      )}

      {!isLoading && rows.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <KpiCard
              label="Net variance"
              value={fmtCurrencyCompact(net)}
              basis={`${base} vs ${compare}`}
            />
            <KpiCard label="Favorable lines" value={String(favCount)} basis="count" />
            <KpiCard label="Unfavorable lines" value={String(unfavCount)} basis="count" higherIsBetter={false} />
          </div>

          {waterfall.length > 0 && (
            <ChartCard
              title="Contribution bridge"
              className="mt-6"
              height={340}
              aside={
                <button
                  className="rounded border border-border px-2 py-0.5 hover:bg-muted"
                  onClick={() => setColorblind((c) => !c)}
                >
                  {colorblind ? "Standard colors" : "Colorblind-safe"}
                </button>
              }
            >
              <VarianceWaterfall rows={waterfall} colorblind={colorblind} />
            </ChartCard>
          )}

          <Card className="mt-6">
            <Table>
              <THead>
                <TR>
                  <TH className="sticky left-0 bg-card">Account</TH>
                  <TH>Period</TH>
                  <TH className="text-right">{compare}</TH>
                  <TH className="text-right">{base}</TH>
                  <TH className="text-right">Variance</TH>
                  <TH className="text-right">Var %</TH>
                  <TH className="text-right">Status</TH>
                </TR>
              </THead>
              <TBody>
                {rows.map((r, i) => (
                  <TR key={i}>
                    <TD className="sticky left-0 bg-card font-medium tabular">{r.account_code}</TD>
                    <TD className="text-muted-foreground">{r.period}</TD>
                    <TD className="text-right tabular text-muted-foreground">{fmtCurrency(r.comparison)}</TD>
                    <TD className="text-right tabular text-muted-foreground">{fmtCurrency(r.actual)}</TD>
                    <TD className={cn("text-right tabular font-medium", statusClass(r.status))}>
                      {fmtCurrency(r.variance)}
                    </TD>
                    <TD className={cn("text-right tabular", statusClass(r.status))}>
                      {fmtPctSigned(r.variance_pct)}
                    </TD>
                    <TD className="text-right">
                      <Badge
                        variant={
                          r.status === "FAVORABLE" ? "pos" : r.status === "UNFAVORABLE" ? "neg" : "neutral"
                        }
                      >
                        {r.status === "FAVORABLE" ? "▲ F" : r.status === "UNFAVORABLE" ? "▼ U" : "—"}
                      </Badge>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </Card>
        </>
      )}
    </>
  );
}

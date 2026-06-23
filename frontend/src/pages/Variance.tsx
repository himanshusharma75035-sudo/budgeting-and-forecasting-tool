import { useQuery } from "@tanstack/react-query";
import {
  Download,
  GitCompareArrows,
  type LucideIcon,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { type ReactNode, useState } from "react";
import { toast } from "sonner";

import { ChartCard } from "../components/ChartCard";
import { buildBridgeRows, VarianceWaterfall } from "../components/charts/VarianceWaterfall";
import { EmptyState } from "../components/EmptyState";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { apiPost, downloadPost } from "../lib/api";
import { fmtCurrency, fmtCurrencyCompact, fmtPctSigned } from "../lib/format";
import type {
  BridgeOut,
  InsightDriverOut,
  VarianceComputeRequest,
  VarianceInsightOut,
  VarianceRowOut,
} from "../lib/types";
import { cn } from "../lib/utils";

const SCENARIOS = ["ACTUAL", "BUDGET", "FORECAST"];

function statusClass(status: string): string {
  if (status === "FAVORABLE") return "text-pos";
  if (status === "UNFAVORABLE") return "text-neg";
  return "text-muted-foreground";
}

/** Render a narrative string with minimal **bold** markdown support. */
function renderNarrative(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((seg, i) =>
    seg.startsWith("**") && seg.endsWith("**") ? (
      <strong key={i} className="font-semibold text-foreground">
        {seg.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{seg}</span>
    ),
  );
}

function DriverList({
  title,
  icon: Icon,
  tone,
  drivers,
}: {
  title: string;
  icon: LucideIcon;
  tone: "pos" | "neg";
  drivers: InsightDriverOut[];
}) {
  if (drivers.length === 0) return null;
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Icon className={cn("size-3.5", tone === "pos" ? "text-pos" : "text-neg")} /> {title}
      </div>
      <ul className="space-y-1.5">
        {drivers.map((d) => (
          <li key={d.code} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate text-foreground">{d.label}</span>
            <span className={cn("tabular font-medium", tone === "pos" ? "text-pos" : "text-neg")}>
              {fmtCurrencyCompact(Math.abs(d.favorable_variance))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Variance() {
  const [base, setBase] = useState("ACTUAL");
  const [compare, setCompare] = useState("BUDGET");
  const [colorblind, setColorblind] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const req: VarianceComputeRequest = { base_scenario: base, compare_scenario: compare };

  async function handleDownload() {
    setDownloading(true);
    try {
      await downloadPost(
        "/reports/variance-pack.xlsx",
        req,
        `variance-board-pack-${base}-vs-${compare}.xlsx`.toLowerCase(),
      );
      toast.success("Board pack downloaded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    } finally {
      setDownloading(false);
    }
  }

  const rowsQ = useQuery({
    queryKey: ["variance", base, compare],
    queryFn: () => apiPost<VarianceRowOut[]>("/variance/compute", req),
  });
  const bridgeQ = useQuery({
    queryKey: ["variance-bridge", base, compare],
    queryFn: () => apiPost<BridgeOut>("/variance/bridge", req),
  });
  const insightsQ = useQuery({
    queryKey: ["variance-insights", base, compare],
    queryFn: () => apiPost<VarianceInsightOut>("/variance/insights", req),
  });

  const rows = (rowsQ.data ?? [])
    .slice()
    .sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance));

  const bridge = bridgeQ.data;
  const insight = insightsQ.data;
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
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={rows.length === 0 || downloading}
              title="Download a formatted Excel board pack"
            >
              <Download />
              {downloading ? "Preparing…" : "Board pack"}
            </Button>
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

          {insight && (
            <Card className="mt-6">
              <CardContent className="pt-5">
                <div className="mb-2 flex items-center gap-2">
                  <Sparkles className="size-4 text-primary" />
                  <h3 className="text-sm font-medium">Insights</h3>
                  <Badge variant={insight.ai_generated ? "accent" : "neutral"}>
                    {insight.ai_generated ? "AI-polished" : "Auto-generated"}
                  </Badge>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {renderNarrative(insight.narrative)}
                </p>
                {(insight.top_unfavorable.length > 0 || insight.top_favorable.length > 0) && (
                  <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <DriverList title="Top drags" icon={TrendingDown} tone="neg" drivers={insight.top_unfavorable} />
                    <DriverList title="Top offsets" icon={TrendingUp} tone="pos" drivers={insight.top_favorable} />
                  </div>
                )}
              </CardContent>
            </Card>
          )}

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

import { useQuery } from "@tanstack/react-query";
import { LineChart as LineChartIcon } from "lucide-react";
import { useState } from "react";

import { ChartCard } from "../components/ChartCard";
import { ForecastFanChart } from "../components/charts/ForecastFanChart";
import { EmptyState } from "../components/EmptyState";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import { Card, CardContent } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { apiGet, apiPost } from "../lib/api";
import { fmtCurrencyCompact, fmtNumber } from "../lib/format";
import type { AccountOut, EntryOut, ForecastRunResponse } from "../lib/types";

function addMonths(label: string, k: number): string {
  const [y, m] = label.split("-").map(Number);
  const idx = y * 12 + (m - 1) + k;
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, "0")}`;
}

const HORIZONS = [6, 12, 18, 24];
const ALL_LEVELS = [80, 90, 95];
const MODELS = [
  { value: "auto", label: "Auto-select (MASE)" },
  { value: "seasonal_naive", label: "Seasonal naive" },
  { value: "naive", label: "Naive" },
  { value: "drift", label: "Drift" },
  { value: "moving_average", label: "Moving average" },
  { value: "window_average", label: "Window average" },
  { value: "straight_line", label: "Straight-line / growth" },
  { value: "simple_linear_regression", label: "Linear regression" },
];

export default function Forecasts() {
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [horizon, setHorizon] = useState(12);
  const [modelOverride, setModelOverride] = useState("auto");
  const [levels, setLevels] = useState<number[]>([80, 95]);

  function toggleLevel(l: number) {
    setLevels((cur) => (cur.includes(l) ? cur.filter((x) => x !== l) : [...cur, l].sort((a, b) => a - b)));
  }

  const accountsQ = useQuery({
    queryKey: ["accounts"],
    queryFn: () => apiGet<AccountOut[]>("/accounts"),
  });

  // Default to the first account until the user picks one. Derived during render
  // (no setState-in-effect) so it stays correct as the accounts list loads.
  const account = selectedAccount ?? accountsQ.data?.[0]?.account_code ?? "";

  const historyQ = useQuery({
    queryKey: ["entries", "ACTUAL", account],
    queryFn: () => apiGet<EntryOut[]>(`/entries?scenario=ACTUAL&account_code=${account}`),
    enabled: !!account,
  });

  const levelsKey = levels.join(",");
  const forecastQ = useQuery({
    queryKey: ["forecast", account, horizon, modelOverride, levelsKey],
    queryFn: () =>
      apiPost<ForecastRunResponse>("/forecasts/run", {
        account_code: account,
        horizon,
        levels: levels.length > 0 ? levels : [80, 95],
        model_override: modelOverride === "auto" ? null : modelOverride,
      }),
    enabled: !!account,
  });

  const history = (historyQ.data ?? [])
    .slice()
    .sort((a, b) => a.period.localeCompare(b.period));
  const historyLabels = history.map((h) => h.period);
  const historyValues = history.map((h) => h.amount);
  const lastLabel = historyLabels.at(-1);
  const forecastLabels = lastLabel
    ? Array.from({ length: horizon }, (_, k) => addMonths(lastLabel, k + 1))
    : undefined;

  const fc = forecastQ.data;
  const selectedScore = fc?.scoreboard.find((s) => s.model === fc.selected_model);

  return (
    <>
      <PageHeader
        title="Forecasts"
        subtitle="Autonomous statistical forecasting — backtested model selection"
        actions={
          <div className="flex items-center gap-2">
            <div className="w-56">
              <Select
                value={account}
                onChange={(e) => setSelectedAccount(e.target.value)}
                aria-label="Account"
              >
                {(accountsQ.data ?? []).map((a) => (
                  <option key={a.account_code} value={a.account_code}>
                    {a.account_code} · {a.account_name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-28">
              <Select
                value={String(horizon)}
                onChange={(e) => setHorizon(Number(e.target.value))}
                aria-label="Horizon"
              >
                {HORIZONS.map((h) => (
                  <option key={h} value={h}>
                    {h} months
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-48">
              <Select
                value={modelOverride}
                onChange={(e) => setModelOverride(e.target.value)}
                aria-label="Model"
              >
                {MODELS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        }
      />

      {forecastQ.isError && (
        <Card className="border-neg/40 p-6">
          <EmptyState
            title="Forecast failed"
            description={
              forecastQ.error instanceof Error ? forecastQ.error.message : "Could not run the forecast."
            }
          />
        </Card>
      )}

      {(forecastQ.isLoading || historyQ.isLoading) && !fc && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
          <Skeleton className="mt-6 h-80" />
        </>
      )}

      {fc && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Selected model" value={fc.selected_model} basis={`seasonality m=${fc.seasonal_period}`} />
            <KpiCard label="Next period" value={fmtCurrencyCompact(fc.point[0] ?? 0)} basis="point forecast" />
            <KpiCard
              label={`Month +${fc.point.length}`}
              value={fmtCurrencyCompact(fc.point.at(-1) ?? 0)}
              basis="horizon end"
            />
            <KpiCard
              label="Backtest MASE"
              value={selectedScore?.mase != null ? fmtNumber(selectedScore.mase) : "—"}
              basis="lower is better"
            />
          </div>

          <ChartCard
            title="Forecast with prediction intervals"
            className="mt-6"
            height={360}
            aside={
              <>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-3 rounded-sm" style={{ background: "var(--chart-ink)" }} />
                  Actual
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-3 rounded-sm border-b-2 border-dashed" style={{ borderColor: "var(--chart-1)" }} />
                  Forecast
                </span>
                <span className="ml-1 flex items-center gap-1.5">
                  <span className="text-muted-foreground">Bands:</span>
                  {ALL_LEVELS.map((l) => (
                    <button
                      key={l}
                      onClick={() => toggleLevel(l)}
                      className={`rounded border px-1.5 py-0.5 ${
                        levels.includes(l)
                          ? "border-primary bg-accent text-accent-foreground"
                          : "border-border text-muted-foreground"
                      }`}
                    >
                      {l}%
                    </button>
                  ))}
                </span>
              </>
            }
          >
            <ForecastFanChart
              history={historyValues}
              historyLabels={historyLabels}
              forecastLabels={forecastLabels}
              point={fc.point}
              lower={fc.lower}
              upper={fc.upper}
            />
          </ChartCard>

          <Card className="mt-6">
            <CardContent className="pt-5">
              <div className="mb-3 flex items-center gap-2">
                <LineChartIcon className="size-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">Model scoreboard</h3>
                <span className="text-xs text-muted-foreground">ranked by backtested MASE</span>
              </div>
              <Table>
                <THead>
                  <TR>
                    <TH>Model</TH>
                    <TH className="text-right">MASE</TH>
                    <TH className="text-right">RMSE</TH>
                    <TH className="text-right">MAE</TH>
                    <TH className="text-right">Selected</TH>
                  </TR>
                </THead>
                <TBody>
                  {fc.scoreboard.map((s) => (
                    <TR key={s.model}>
                      <TD className="font-medium">{s.model}</TD>
                      <TD className="text-right tabular">{s.mase != null ? fmtNumber(s.mase) : "—"}</TD>
                      <TD className="text-right tabular text-muted-foreground">
                        {s.rmse != null ? fmtCurrencyCompact(s.rmse) : "—"}
                      </TD>
                      <TD className="text-right tabular text-muted-foreground">
                        {s.mae != null ? fmtCurrencyCompact(s.mae) : "—"}
                      </TD>
                      <TD className="text-right">
                        {s.model === fc.selected_model && <Badge variant="accent">✓ chosen</Badge>}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
              {fc.notes.length > 0 && (
                <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                  {fc.notes.map((n, i) => (
                    <li key={i}>· {n}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}

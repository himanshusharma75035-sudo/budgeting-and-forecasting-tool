import { useMutation } from "@tanstack/react-query";
import { Play, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ChartCard } from "../components/ChartCard";
import { FinanceTooltip } from "../components/charts/FinanceTooltip";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { apiPost } from "../lib/api";
import { fmtCurrency, fmtCurrencyCompact, fmtNumber } from "../lib/format";
import type { DriverEvalResponse, DriverIn, DriverKind, DriverModelRequest } from "../lib/types";

const HORIZONS = [6, 12];
const CHART_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

interface DriverRow {
  code: string;
  name: string;
  kind: DriverKind;
  definition: string; // a formula, or comma-separated input values (carried forward)
  account: string;
}

// A worked demo: a small P&L built from assumptions, incl. a cross-period prev() example.
const DEMO_ROWS: DriverRow[] = [
  { code: "units", name: "Units sold", kind: "INPUT", definition: "1000, 1100, 1210, 1331, 1464, 1611", account: "" },
  { code: "price", name: "Unit price", kind: "INPUT", definition: "100", account: "" },
  { code: "revenue", name: "Revenue", kind: "FORMULA", definition: "units * price", account: "4000" },
  { code: "cogs", name: "COGS", kind: "FORMULA", definition: "revenue * 0.55", account: "5000" },
  { code: "gross_profit", name: "Gross profit", kind: "FORMULA", definition: "revenue - cogs", account: "" },
  { code: "opex", name: "Operating expenses", kind: "INPUT", definition: "30000", account: "6000" },
  { code: "ebit", name: "EBIT", kind: "FORMULA", definition: "gross_profit - opex", account: "" },
  { code: "cum_ebit", name: "Cumulative EBIT", kind: "FORMULA", definition: "ebit + prev(cum_ebit)", account: "" },
];

function addMonths(label: string, k: number): string {
  const [y, m] = label.split("-").map(Number);
  const idx = y * 12 + (m - 1) + k;
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, "0")}`;
}

function buildRequest(rows: DriverRow[], periods: string[]): DriverModelRequest {
  const drivers: DriverIn[] = rows
    .filter((r) => r.code.trim())
    .map((r) => {
      const code = r.code.trim();
      const name = r.name.trim() || code;
      const account_code = r.account.trim() || null;
      if (r.kind === "FORMULA") {
        return { code, name, kind: "FORMULA", formula: r.definition.trim(), account_code };
      }
      const nums = r.definition.split(",").map((s) => s.trim()).filter((s) => s.length > 0);
      const values: Record<string, number> = {};
      periods.forEach((p, i) => {
        const raw = nums[i] ?? nums.at(-1) ?? "0";
        const n = Number(raw);
        values[p] = Number.isFinite(n) ? n : 0;
      });
      return { code, name, kind: "INPUT", values, account_code };
    });
  return { periods, drivers };
}

export default function Drivers() {
  const [start, setStart] = useState("2026-01");
  const [horizon, setHorizon] = useState(6);
  const [rows, setRows] = useState<DriverRow[]>(DEMO_ROWS);

  const periods = useMemo(
    () => Array.from({ length: horizon }, (_, k) => addMonths(start, k)),
    [start, horizon],
  );

  const mutation = useMutation({
    mutationFn: (req: DriverModelRequest) => apiPost<DriverEvalResponse>("/drivers/evaluate", req),
  });
  const result = mutation.data;

  function update(i: number, patch: Partial<DriverRow>) {
    setRows((cur) => cur.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  const chartData = result
    ? result.periods.map((p, i) => {
        const row: Record<string, number | string> = { t: p };
        for (const a of result.account_lines) row[a.account_code] = a.points[i];
        return row;
      })
    : [];

  return (
    <>
      <PageHeader
        title="Drivers"
        subtitle="Driver-based modeling — build the P&L from assumptions and formulas"
        actions={
          <div className="flex items-center gap-2">
            <Input
              type="month"
              value={start}
              onChange={(e) => setStart(e.target.value || "2026-01")}
              aria-label="Start month"
              className="w-40"
            />
            <div className="w-28">
              <Select value={String(horizon)} onChange={(e) => setHorizon(Number(e.target.value))} aria-label="Horizon">
                {HORIZONS.map((h) => (
                  <option key={h} value={h}>
                    {h} months
                  </option>
                ))}
              </Select>
            </div>
            <Button onClick={() => mutation.mutate(buildRequest(rows, periods))} disabled={mutation.isPending}>
              <Play /> {mutation.isPending ? "Evaluating…" : "Evaluate"}
            </Button>
          </div>
        }
      />

      <Card>
        <CardContent className="pt-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium">Driver model</h3>
            <span className="text-xs text-muted-foreground">
              INPUT = comma-separated values per period (last carried forward) · FORMULA = expression over other
              drivers, e.g. <code className="tabular">units * price</code> or{" "}
              <code className="tabular">prev(revenue) * 1.1</code>
            </span>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <THead>
                <TR>
                  <TH className="w-32">Code</TH>
                  <TH>Name</TH>
                  <TH className="w-28">Type</TH>
                  <TH>Definition</TH>
                  <TH className="w-24">Account</TH>
                  <TH className="w-10" />
                </TR>
              </THead>
              <TBody>
                {rows.map((r, i) => (
                  <TR key={i}>
                    <TD>
                      <Input value={r.code} onChange={(e) => update(i, { code: e.target.value })} placeholder="code" />
                    </TD>
                    <TD>
                      <Input value={r.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="name" />
                    </TD>
                    <TD>
                      <Select value={r.kind} onChange={(e) => update(i, { kind: e.target.value as DriverKind })}>
                        <option value="INPUT">Input</option>
                        <option value="FORMULA">Formula</option>
                      </Select>
                    </TD>
                    <TD>
                      <Input
                        value={r.definition}
                        onChange={(e) => update(i, { definition: e.target.value })}
                        placeholder={r.kind === "FORMULA" ? "expression" : "v1, v2, v3 …"}
                        className="tabular"
                      />
                    </TD>
                    <TD>
                      <Input
                        value={r.account}
                        onChange={(e) => update(i, { account: e.target.value })}
                        placeholder="—"
                      />
                    </TD>
                    <TD>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Remove driver"
                        onClick={() => setRows((cur) => cur.filter((_, idx) => idx !== i))}
                      >
                        <Trash2 className="text-muted-foreground" />
                      </Button>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => setRows((cur) => [...cur, { code: "", name: "", kind: "INPUT", definition: "0", account: "" }])}
          >
            <Plus /> Add driver
          </Button>
        </CardContent>
      </Card>

      {mutation.isError && (
        <Card className="mt-6 border-neg/40 p-6">
          <EmptyState
            title="Could not evaluate the model"
            description={mutation.error instanceof Error ? mutation.error.message : "Check your formulas and try again."}
          />
        </Card>
      )}

      {result && result.account_lines.length > 0 && (
        <ChartCard title="Modelled account lines" className="mt-6" height={320}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />
              <XAxis dataKey="t" axisLine={false} tickLine={false} tick={{ fill: "var(--chart-axis)", fontSize: 12 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                width={56}
                tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
                tickFormatter={(v: number) => fmtCurrencyCompact(v)}
              />
              <Tooltip content={<FinanceTooltip />} />
              {result.account_lines.map((a, idx) => (
                <Line
                  key={a.account_code}
                  name={a.account_code}
                  dataKey={a.account_code}
                  stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      {result && (
        <Card className="mt-6">
          <CardContent className="pt-5">
            <h3 className="mb-3 text-sm font-medium">Evaluated drivers</h3>
            <div className="overflow-x-auto">
              <Table>
                <THead>
                  <TR>
                    <TH>Driver</TH>
                    {result.periods.map((p) => (
                      <TH key={p} className="text-right">
                        {p}
                      </TH>
                    ))}
                  </TR>
                </THead>
                <TBody>
                  {result.series.map((s) => (
                    <TR key={s.code}>
                      <TD>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{s.name}</span>
                          <Badge variant={s.kind === "FORMULA" ? "accent" : "neutral"}>{s.kind.toLowerCase()}</Badge>
                          {s.account_code && <span className="text-xs text-muted-foreground">→ {s.account_code}</span>}
                        </div>
                      </TD>
                      {s.points.map((v, i) => (
                        <TD key={i} className="text-right tabular">
                          {fmtNumber(v)}
                        </TD>
                      ))}
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>

            {result.account_lines.length > 0 && (
              <>
                <h3 className="mb-3 mt-6 text-sm font-medium">Account lines (sum of mapped drivers)</h3>
                <div className="overflow-x-auto">
                  <Table>
                    <THead>
                      <TR>
                        <TH>Account</TH>
                        {result.periods.map((p) => (
                          <TH key={p} className="text-right">
                            {p}
                          </TH>
                        ))}
                        <TH className="text-right">Total</TH>
                      </TR>
                    </THead>
                    <TBody>
                      {result.account_lines.map((a) => (
                        <TR key={a.account_code}>
                          <TD className="font-medium">{a.account_code}</TD>
                          {a.points.map((v, i) => (
                            <TD key={i} className="text-right tabular text-muted-foreground">
                              {fmtCurrencyCompact(v)}
                            </TD>
                          ))}
                          <TD className="text-right tabular font-medium">{fmtCurrency(a.total)}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </div>
              </>
            )}
            {result.notes.length > 0 && (
              <p className="mt-3 text-xs text-muted-foreground">{result.notes.join(" · ")}</p>
            )}
          </CardContent>
        </Card>
      )}
    </>
  );
}

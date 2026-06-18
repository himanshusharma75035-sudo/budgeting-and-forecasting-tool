import { useMutation } from "@tanstack/react-query";
import { Plus, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";

import { ChartCard } from "../components/ChartCard";
import { FinanceTooltip } from "../components/charts/FinanceTooltip";
import { PageHeader } from "../components/PageHeader";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input, Label } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { apiPost } from "../lib/api";
import { fmtCurrency, fmtCurrencyCompact } from "../lib/format";
import type { BudgetMethod, BudgetRunRequest, BudgetRunResponse } from "../lib/types";

interface Col {
  key: string;
  label: string;
  type: "text" | "number";
}

const COLS: Record<BudgetMethod, Col[]> = {
  INCREMENTAL: [
    { key: "account_code", label: "Account", type: "text" },
    { key: "prior_actual", label: "Prior actual", type: "number" },
    { key: "growth_pct", label: "Growth (e.g. 0.08)", type: "number" },
    { key: "one_off", label: "One-off", type: "number" },
  ],
  ACTIVITY_BASED: [
    { key: "name", label: "Activity", type: "text" },
    { key: "prior_cost_pool", label: "Prior cost pool", type: "number" },
    { key: "prior_driver_units", label: "Prior units", type: "number" },
    { key: "forecast_driver_volume", label: "Forecast volume", type: "number" },
  ],
  VALUE_PROPOSITION: [
    { key: "name", label: "Initiative", type: "text" },
    { key: "cost", label: "Cost", type: "number" },
    { key: "value_score", label: "Value score", type: "number" },
  ],
  ZERO_BASED: [
    { key: "name", label: "Decision package", type: "text" },
    { key: "cost", label: "Cost", type: "number" },
    { key: "benefit", label: "Benefit", type: "number" },
  ],
};

type Row = Record<string, string>;

const SEED: Record<BudgetMethod, Row[]> = {
  INCREMENTAL: [
    { account_code: "6100", prior_actual: "200000", growth_pct: "0.08", one_off: "15000" },
    { account_code: "6000", prior_actual: "800000", growth_pct: "0.05", one_off: "0" },
  ],
  ACTIVITY_BASED: [
    { name: "Setups", prior_cost_pool: "400000", prior_driver_units: "700", forecast_driver_volume: "800" },
    { name: "Inspection", prior_cost_pool: "280000", prior_driver_units: "15500", forecast_driver_volume: "16000" },
  ],
  VALUE_PROPOSITION: [
    { name: "Brand campaign", cost: "40000", value_score: "90" },
    { name: "SEO revamp", cost: "30000", value_score: "75" },
    { name: "Trade show", cost: "50000", value_score: "60" },
    { name: "Webinar series", cost: "20000", value_score: "50" },
  ],
  ZERO_BASED: [
    { name: "Core support", cost: "120000", benefit: "100" },
    { name: "Customer success", cost: "60000", benefit: "70" },
    { name: "Community", cost: "90000", benefit: "40" },
  ],
};

const METHOD_LABEL: Record<BudgetMethod, string> = {
  INCREMENTAL: "Incremental",
  ACTIVITY_BASED: "Activity-based",
  VALUE_PROPOSITION: "Value-proposition",
  ZERO_BASED: "Zero-based",
};

const num = (s: string) => Number(s || 0);

export default function Budgets() {
  const [method, setMethod] = useState<BudgetMethod>("INCREMENTAL");
  const [versionName, setVersionName] = useState("FY26 Plan");
  const [fiscalYear, setFiscalYear] = useState(2026);
  const [rowsByMethod, setRowsByMethod] = useState<Record<BudgetMethod, Row[]>>(SEED);
  const [cap, setCap] = useState("100000");
  const [totalFunds, setTotalFunds] = useState("250000");
  const [fixedCosts, setFixedCosts] = useState("0");
  const [volumeMode, setVolumeMode] = useState("STATIC");
  const [cadence, setCadence] = useState("PERIODIC");

  const rows = rowsByMethod[method];
  const cols = COLS[method];

  function setRows(next: Row[]) {
    setRowsByMethod((prev) => ({ ...prev, [method]: next }));
  }

  const mutation = useMutation({
    mutationFn: () => {
      const base: BudgetRunRequest = {
        method,
        version_name: versionName,
        fiscal_year: fiscalYear,
        volume_mode: volumeMode,
        cadence,
      };
      if (method === "INCREMENTAL") {
        base.incremental_lines = rows.map((r) => ({
          account_code: r.account_code,
          prior_actual: num(r.prior_actual),
          growth_pct: num(r.growth_pct),
          one_off: num(r.one_off),
        }));
      } else if (method === "ACTIVITY_BASED") {
        base.activities = rows.map((r) => ({
          name: r.name,
          prior_cost_pool: num(r.prior_cost_pool),
          prior_driver_units: num(r.prior_driver_units),
          forecast_driver_volume: num(r.forecast_driver_volume),
        }));
        base.fixed_costs = num(fixedCosts);
      } else if (method === "VALUE_PROPOSITION") {
        base.initiatives = rows.map((r) => ({
          name: r.name,
          cost: num(r.cost),
          value_score: num(r.value_score),
        }));
        base.cap = num(cap);
      } else {
        base.packages = rows.map((r) => ({
          name: r.name,
          cost: num(r.cost),
          benefit: num(r.benefit),
        }));
        base.total_funds = num(totalFunds);
      }
      return apiPost<BudgetRunResponse>("/budgets/run", base);
    },
    onSuccess: (r) => toast.success(`Budget generated · total ${fmtCurrencyCompact(r.total)}`),
    onError: (e) => toast.error(e instanceof Error ? e.message : "Budget run failed"),
  });

  const result = mutation.data;

  return (
    <>
      <PageHeader
        title="Budgets"
        subtitle="Generate a budget using one of four methods"
        actions={
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            <Sparkles /> {mutation.isPending ? "Running…" : "Generate budget"}
          </Button>
        }
      />

      <Card>
        <CardHeader className="gap-4">
          <Tabs value={method} onValueChange={(v) => setMethod(v as BudgetMethod)}>
            <TabsList>
              {(Object.keys(METHOD_LABEL) as BudgetMethod[]).map((m) => (
                <TabsTrigger key={m} value={m}>
                  {METHOD_LABEL[m]}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <div className="flex flex-wrap gap-4">
            <div className="space-y-1.5">
              <Label>Version name</Label>
              <Input
                value={versionName}
                onChange={(e) => setVersionName(e.target.value)}
                className="w-48"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Fiscal year</Label>
              <Input
                type="number"
                value={fiscalYear}
                onChange={(e) => setFiscalYear(Number(e.target.value))}
                className="w-28"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Volume mode</Label>
              <div className="w-36">
                <Select value={volumeMode} onChange={(e) => setVolumeMode(e.target.value)}>
                  <option value="STATIC">Static</option>
                  <option value="FLEXIBLE">Flexible</option>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Cadence</Label>
              <div className="w-36">
                <Select value={cadence} onChange={(e) => setCadence(e.target.value)}>
                  <option value="PERIODIC">Periodic</option>
                  <option value="ROLLING">Rolling</option>
                </Select>
              </div>
            </div>
            {method === "ACTIVITY_BASED" && (
              <div className="space-y-1.5">
                <Label>Fixed costs</Label>
                <Input
                  type="number"
                  value={fixedCosts}
                  onChange={(e) => setFixedCosts(e.target.value)}
                  className="w-32"
                />
              </div>
            )}
            {method === "VALUE_PROPOSITION" && (
              <div className="space-y-1.5">
                <Label>Budget cap</Label>
                <Input type="number" value={cap} onChange={(e) => setCap(e.target.value)} className="w-32" />
              </div>
            )}
            {method === "ZERO_BASED" && (
              <div className="space-y-1.5">
                <Label>Total funds</Label>
                <Input
                  type="number"
                  value={totalFunds}
                  onChange={(e) => setTotalFunds(e.target.value)}
                  className="w-32"
                />
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <THead>
              <TR>
                {cols.map((c) => (
                  <TH key={c.key} className={c.type === "number" ? "text-right" : ""}>
                    {c.label}
                  </TH>
                ))}
                <TH className="w-10" />
              </TR>
            </THead>
            <TBody>
              {rows.map((row, ri) => (
                <TR key={ri}>
                  {cols.map((c) => (
                    <TD key={c.key} className={c.type === "number" ? "text-right" : ""}>
                      <Input
                        type={c.type === "number" ? "number" : "text"}
                        value={row[c.key] ?? ""}
                        onChange={(e) => {
                          const next = rows.slice();
                          next[ri] = { ...next[ri], [c.key]: e.target.value };
                          setRows(next);
                        }}
                        className="h-8"
                      />
                    </TD>
                  ))}
                  <TD className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8"
                      onClick={() => setRows(rows.filter((_, i) => i !== ri))}
                      aria-label="Remove row"
                    >
                      <Trash2 className="text-muted-foreground" />
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => setRows([...rows, Object.fromEntries(cols.map((c) => [c.key, ""])) as Row])}
          >
            <Plus /> Add row
          </Button>
        </CardContent>
      </Card>

      {result && (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Result — {METHOD_LABEL[method]}</CardTitle>
              <span className="text-sm text-muted-foreground">
                Total <span className="tabular font-semibold text-foreground">{fmtCurrency(result.total)}</span>
              </span>
            </CardHeader>
            <CardContent>
              <Table>
                <THead>
                  <TR>
                    <TH>Line</TH>
                    <TH className="text-right">Amount</TH>
                  </TR>
                </THead>
                <TBody>
                  {result.lines.map((l, i) => (
                    <TR key={i}>
                      <TD className="font-medium">{l.account_code ?? l.name}</TD>
                      <TD className="text-right tabular">{fmtCurrency(l.amount)}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
              {result.notes.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                  {result.notes.map((n, i) => (
                    <li key={i}>· {n}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <ChartCard title="Budget by line">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={result.lines.map((l) => ({ name: l.account_code ?? l.name ?? "", amount: l.amount }))}
                margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
              >
                <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "var(--chart-axis)", fontSize: 12 }} interval={0} />
                <YAxis axisLine={false} tickLine={false} width={56} tick={{ fill: "var(--chart-axis)", fontSize: 12 }} tickFormatter={(v: number) => fmtCurrencyCompact(v)} />
                <Tooltip content={<FinanceTooltip />} cursor={{ fill: "var(--muted)", opacity: 0.4 }} />
                <Bar name="Amount" dataKey="amount" fill="var(--chart-1)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}
    </>
  );
}

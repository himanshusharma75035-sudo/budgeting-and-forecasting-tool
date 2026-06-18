import { useMutation } from "@tanstack/react-query";
import { Download, FileSpreadsheet, UploadCloud } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { uploadFile } from "../lib/api";
import type { UploadReport } from "../lib/types";

const SCENARIOS = ["ACTUAL", "BUDGET", "FORECAST"];

export default function DataImport() {
  const [scenario, setScenario] = useState("ACTUAL");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const mutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a file first");
      return uploadFile<UploadReport>("/uploads", file, { scenario });
    },
    onSuccess: (r) => {
      if (r.rows_rejected > 0) {
        toast.warning(`Imported ${r.inserted} rows · ${r.rows_rejected} rejected`);
      } else {
        toast.success(`Imported ${r.inserted} rows from a ${r.layout} file`);
      }
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Upload failed"),
  });

  const report = mutation.data;

  return (
    <>
      <PageHeader
        title="Data Import"
        subtitle="Upload actuals, budgets or forecasts from CSV / Excel"
        actions={
          <a href={`/api/templates/${scenario}`} download>
            <Button variant="outline">
              <Download /> Download template
            </Button>
          </a>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Upload file</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium">Scenario</span>
                <div className="w-40">
                  <Select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                    {SCENARIOS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </Select>
                </div>
              </label>
            </div>

            <label
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const f = e.dataTransfer.files?.[0];
                if (f) setFile(f);
              }}
              className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
                dragOver ? "border-primary bg-accent/40" : "border-border hover:bg-muted/40"
              }`}
            >
              <UploadCloud className="size-8 text-muted-foreground" />
              <span className="text-sm font-medium">
                {file ? file.name : "Drag a file here, or click to browse"}
              </span>
              <span className="text-xs text-muted-foreground">.csv, .xlsx — wide or long layout</span>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>

            <div className="flex items-center gap-3">
              <Button
                onClick={() => mutation.mutate()}
                disabled={!file || mutation.isPending}
              >
                {mutation.isPending ? "Importing…" : "Import"}
              </Button>
              {file && (
                <Button variant="ghost" onClick={() => setFile(null)}>
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Template</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <FileSpreadsheet className="size-8 text-muted-foreground" />
            <p>
              The <strong className="text-foreground">wide</strong> template lists accounts down rows
              and one column per period (<code className="font-mono">YYYY-MM</code>). Blank cells are
              skipped; numbers only (no currency symbols or thousands separators).
            </p>
            <a href={`/api/templates/${scenario}`} download className="inline-block">
              <Button variant="outline" size="sm">
                <Download /> {scenario} template
              </Button>
            </a>
          </CardContent>
        </Card>
      </div>

      {report && (
        <Card className="mt-6">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Import result</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="neutral">{report.layout}</Badge>
              <Badge variant="pos">{report.inserted} inserted</Badge>
              {report.rows_rejected > 0 && <Badge variant="neg">{report.rows_rejected} rejected</Badge>}
            </div>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-muted-foreground">
              {report.rows_ok} of {report.rows_total} rows valid.
            </p>
            {report.errors.length > 0 && (
              <Table>
                <THead>
                  <TR>
                    <TH>Row</TH>
                    <TH>Field</TH>
                    <TH>Message</TH>
                  </TR>
                </THead>
                <TBody>
                  {report.errors.slice(0, 50).map((e, i) => (
                    <TR key={i}>
                      <TD className="tabular">{String(e.row ?? "—")}</TD>
                      <TD className="font-mono text-xs">{String(e.field ?? "—")}</TD>
                      <TD className="text-neg">{String(e.message ?? "")}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </>
  );
}

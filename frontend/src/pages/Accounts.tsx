import { useQuery } from "@tanstack/react-query";
import { Search, Table2 } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { apiGet } from "../lib/api";
import type { AccountOut } from "../lib/types";
import { cn } from "../lib/utils";

const TYPE_VARIANT: Record<string, "pos" | "neg" | "neutral" | "accent"> = {
  REVENUE: "pos",
  OTHER_INCOME: "pos",
  COGS: "neg",
  OPEX: "neg",
  OTHER_EXPENSE: "neg",
};

export default function Accounts() {
  const [q, setQ] = useState("");
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => apiGet<AccountOut[]>("/accounts"),
  });

  const rows = (data ?? []).filter((a) => {
    const needle = q.trim().toLowerCase();
    if (!needle) return true;
    return (
      a.account_code.toLowerCase().includes(needle) ||
      a.account_name.toLowerCase().includes(needle) ||
      a.account_type.toLowerCase().includes(needle)
    );
  });

  return (
    <>
      <PageHeader
        title="Accounts"
        subtitle="Chart of accounts"
        caption="Amounts in USD"
        actions={
          <div className="relative w-64">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search accounts…"
              className="pl-9"
            />
          </div>
        }
      />

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      )}

      {isError && (
        <Card className="border-neg/40 p-6">
          <EmptyState
            title="Couldn't load accounts"
            description={error instanceof Error ? error.message : "Request failed."}
            action={
              <Button variant="outline" onClick={() => refetch()}>
                Retry
              </Button>
            }
          />
        </Card>
      )}

      {!isLoading && !isError && rows.length === 0 && (
        <Card className="p-6">
          <EmptyState
            icon={Table2}
            title={q ? "No matching accounts" : "No accounts yet"}
            description={
              q ? "Try a different search term." : "Seed the workspace to populate the chart of accounts."
            }
          />
        </Card>
      )}

      {!isLoading && !isError && rows.length > 0 && (
        <Table>
          <THead>
            <TR>
              <TH className="sticky left-0 bg-card">Account</TH>
              <TH>Name</TH>
              <TH>Type</TH>
              <TH>Normal balance</TH>
              <TH className="text-right">Postable</TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((a) => (
              <TR key={a.account_id}>
                <TD className="sticky left-0 bg-card font-medium tabular">{a.account_code}</TD>
                <TD>{a.account_name}</TD>
                <TD>
                  <Badge variant={TYPE_VARIANT[a.account_type] ?? "neutral"}>{a.account_type}</Badge>
                </TD>
                <TD className="text-muted-foreground">{a.normal_balance}</TD>
                <TD className="text-right">
                  <span
                    className={cn("text-sm", a.is_postable ? "text-foreground" : "text-muted-foreground")}
                  >
                    {a.is_postable ? "Yes" : "Roll-up"}
                  </span>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </>
  );
}

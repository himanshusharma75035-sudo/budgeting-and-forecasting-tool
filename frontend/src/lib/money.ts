// Formatting helpers for currency and percentage display.

export function formatMoney(n: number, currency = "USD"): string {
  if (!Number.isFinite(n)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(n);
}

export function formatPct(n: number | null): string {
  if (n === null || !Number.isFinite(n)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(n / 100);
}

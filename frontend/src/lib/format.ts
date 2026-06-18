// Centralized number/currency formatting — Indian standards (₹ INR, lakh/crore, en-IN grouping).

const LOCALE = "en-IN";
const CCY = "INR";

/** 12.3L, 1.2Cr — compact non-currency (Indian scale). */
export const fmtCompact = (n: number): string =>
  Intl.NumberFormat(LOCALE, { notation: "compact", maximumFractionDigits: 2 }).format(n);

/** ₹1.2Cr / ₹9.5L — compact currency for axes/KPIs. */
export const fmtCurrencyCompact = (n: number): string =>
  Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: CCY,
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(n);

/** ₹1,23,45,678.00 — full currency (Indian digit grouping) for tooltips/tables. */
export const fmtCurrency = (n: number): string =>
  Intl.NumberFormat(LOCALE, { style: "currency", currency: CCY, maximumFractionDigits: 2 }).format(n);

/** ₹(1,23,456.00) — accounting style (negatives parenthesized). */
export const fmtAccounting = (n: number): string =>
  Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: CCY,
    currencySign: "accounting",
  }).format(n);

/** +12.3 / -4.0 — signed delta. */
export const fmtDelta = (n: number): string =>
  Intl.NumberFormat(LOCALE, { signDisplay: "exceptZero", maximumFractionDigits: 1 }).format(n);

/** +₹1.2Cr / -₹7.9L — signed compact currency (for chart data labels). */
export const fmtDeltaCompact = (n: number): string =>
  Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: CCY,
    notation: "compact",
    maximumFractionDigits: 1,
    signDisplay: "exceptZero",
  }).format(n);

/** +12.3% / -4.0% — signed percentage (input already a percentage value, e.g. 12.3). */
export const fmtPctSigned = (n: number | null | undefined): string => {
  if (n == null || Number.isNaN(n)) return "—";
  return `${Intl.NumberFormat(LOCALE, {
    signDisplay: "exceptZero",
    maximumFractionDigits: 1,
  }).format(n)}%`;
};

/** Plain number with Indian grouping. */
export const fmtNumber = (n: number): string =>
  Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 }).format(n);

# OpenFP&A — UI Redesign Specification

**App:** OpenFP&A (`/frontend`) · **Stack:** React 19 · Vite 6 · TypeScript · Tailwind CSS v4 · Recharts 3.x
**Constraint:** every runtime dependency must be OSI-licensed (MIT / Apache-2.0 / ISC / SIL OFL). No commercial tiers (AG Grid Enterprise, MUI X Pro/Premium) anywhere in the tree.

---

## 1. Visual Language & Recommended OSS Stack

### 1.1 Visual language

A **quiet, near-monochrome instrument panel.** A 10-step neutral scale does all the structural work; structure comes from whitespace, 1px hairline borders, and alignment rather than fills or shadows. Exactly **one rationed brand accent — deep teal** — is spent on the single primary action per screen, active nav, links, and the focus ring; teal is deliberately *not* green or red so favorable/unfavorable signal colors stay free for data meaning. Typography is **Inter** with tabular, slashed-zero figures so money columns align to the digit. Charts follow IBCS + FT Visual Vocabulary discipline: maximum data-to-ink, horizontal-only hairline gridlines, scenarios encoded by *fill/pattern* not hue, and color reserved exclusively for variance. The result reads like Linear/Mercury/Vercel applied to FP&A: dense where finance teams want density, calm everywhere else, and trustworthy because every number is auditable and shown with its comparison basis.

### 1.2 Final recommended stack

| Layer | Choice | License | How adopted |
|---|---|---|---|
| Component primitives | **shadcn/ui** (copy-in) over **Radix UI** | MIT / MIT | Hand-authored: `npx shadcn@latest init` then `add`. You own the JSX. |
| CSS engine / theming | **Tailwind CSS v4** (CSS-first `@theme`) | MIT | `npm install` (dev) |
| Variant helper | **class-variance-authority** | Apache-2.0 | `npm install` |
| Class merge | **tailwind-merge** + **clsx** | MIT / MIT | `npm install` |
| Icons | **lucide-react** | ISC | `npm install` |
| Toasts | **sonner** | MIT | `npm install` (added via shadcn) |
| Command palette | **cmdk** | MIT | `npm install` |
| Charts | **Recharts 3.x** | MIT | Upgrade from current `^2.13.0` |
| Tables/grids | **TanStack Table v8** | MIT | `npm install` |
| KPI/sparkline patterns | **Tremor** (tremor.so, copy-in) | Apache-2.0 | Hand-authored: copy AreaChart/SparkAreaChart/KPI source, adapt to tokens. **Do NOT install `@tremor/react`** (React-18/Tailwind-v3 only). |
| Font | **Inter Variable** via `@fontsource-variable/inter` | SIL OFL 1.1 | `npm install` (self-hosted) |
| Mono font | **JetBrains Mono** (raw IDs/codes) | SIL OFL 1.1 | `npm install` (optional) |
| Perf escape hatch | **Apache ECharts 6** + `echarts-for-react` | Apache-2.0 / MIT | Documented only; adopt per-chart if a single chart exceeds ~5k SVG points. |

**Install commands**

```bash
# frontend/
npm install recharts@^3 @tanstack/react-table class-variance-authority \
  tailwind-merge clsx lucide-react sonner cmdk \
  @fontsource-variable/inter @fontsource/jetbrains-mono
npm install -D tailwindcss@4 @tailwindcss/vite
npx shadcn@latest init           # choose: Tailwind v4, style "new-york"
npx shadcn@latest add button card table dialog select tabs dropdown-menu \
  badge tooltip sonner separator input label skeleton popover command
```

**Hand-authored (not npm packages):** all shadcn/ui components (copied into `src/components/ui`), the Tremor KPI/sparkline/fan helpers (copied into `src/components/charts` and adapted to our CSS vars), the `AppShell`, `KpiCard`, `DataTable` (TanStack), `ChartCard`, `PageHeader`, `EmptyState`, and the themed Recharts wrappers.

**CI license gate:** run `license-checker` in CI; **fail** on `Commercial`, `SEE LICENSE IN LICENSE`, `GPL`, `AGPL`, `SSPL`, `BSL`. Explicit denylist: `ag-grid-enterprise`, `@mui/x-data-grid-pro`, `@mui/x-data-grid-premium`. Pin versions so a transitive bump cannot introduce a paid tier.

**Recharts note:** pin a known-good React 19 minor with Recharts 3.8.x and smoke-test rendering (Recharts issue #6857 affected some React 19.2.x patches).

---

## 2. Design Tokens

CSS-first Tailwind v4. Put this in `src/index.css`. Colors are OKLCH (primary, surfaces) with hex equivalents called out for data/chart series where exactness matters. `.dark` is toggled on `<html>`.

```css
@import "tailwindcss";
@import "@fontsource-variable/inter";
@import "@fontsource/jetbrains-mono";

@custom-variant dark (&:where(.dark, .dark *));

/* ---------- LIGHT ---------- */
:root {
  /* neutral scale (workhorse) */
  --background:        oklch(0.99 0.002 247);   /* page ~ #FAFAFA */
  --foreground:        oklch(0.21 0.03 256);     /* ink ~ #171717 */
  --card:              oklch(1 0 0);             /* #FFFFFF (content brightest) */
  --card-foreground:   oklch(0.21 0.03 256);
  --popover:           oklch(1 0 0);
  --popover-foreground:oklch(0.21 0.03 256);
  --sidebar:           oklch(0.97 0.003 247);    /* dimmer than content ~ #F5F5F5 */
  --sidebar-foreground:oklch(0.34 0.02 257);
  --muted:             oklch(0.96 0.006 247);
  --muted-foreground:  oklch(0.50 0.02 257);     /* labels, captions (AA on bg) */
  --secondary:         oklch(0.96 0.006 247);
  --secondary-foreground: oklch(0.28 0.03 256);
  --border:            oklch(0.92 0.006 247);    /* 1px hairline ~ #E5E5E5 */
  --input:             oklch(0.92 0.006 247);

  /* ONE accent: deep teal — CTA / active nav / focus ring / link only */
  --primary:            oklch(0.52 0.10 200);    /* deep teal */
  --primary-foreground: oklch(0.99 0.005 197);
  --accent:             oklch(0.95 0.02 200);    /* teal-tint hover/active surface */
  --accent-foreground:  oklch(0.30 0.06 200);
  --ring:               oklch(0.52 0.10 200);

  /* semantic DATA colors — colorblind dual-encode always pairs these with sign+arrow */
  --pos:  oklch(0.52 0.13 150); --pos-foreground: oklch(0.99 0.01 150);   /* favorable #2E7D32 */
  --neg:  oklch(0.51 0.20 27);  --neg-foreground: oklch(0.99 0.005 27);   /* unfavorable #C62828 */
  --warn: oklch(0.72 0.16 75);                                            /* amber #D97706 */
  --destructive: oklch(0.58 0.22 27); --destructive-foreground: oklch(0.99 0.005 197);

  /* colorblind-safe alternate (user toggle): favorable blue / unfavorable orange (Wong) */
  --cb-pos: oklch(0.55 0.14 250);  /* #0072B2 */
  --cb-neg: oklch(0.75 0.15 70);   /* #E69F00 */

  /* chart series (neutral workhorse + teal accent) */
  --chart-1: oklch(0.52 0.10 200);  /* teal — primary series   ~ #0072B2 family */
  --chart-2: oklch(0.62 0.13 165);
  --chart-3: oklch(0.65 0.14 250);
  --chart-4: oklch(0.70 0.15 75);
  --chart-5: oklch(0.58 0.17 320);
  --chart-grid:     oklch(0.92 0.006 247);       /* #E5E5E5 hairline */
  --chart-axis:     oklch(0.50 0.02 257);        /* tick labels */
  --chart-ink:      oklch(0.32 0.01 256);        /* #404040 — IBCS Actual fill */
  --chart-prior:    oklch(0.80 0.004 247);       /* #BFBFBF — IBCS Prior Year */

  /* shape */
  --radius: 0.5rem;                              /* 8px base */
  --shadow-xs: 0 1px 2px 0 oklch(0.21 0.03 256 / 0.05);
  --shadow-sm: 0 1px 3px 0 oklch(0.21 0.03 256 / 0.08), 0 1px 2px -1px oklch(0.21 0.03 256 / 0.08);
  --shadow-md: 0 4px 8px -2px oklch(0.21 0.03 256 / 0.10), 0 2px 4px -2px oklch(0.21 0.03 256 / 0.06);
  --shadow-lg: 0 12px 24px -6px oklch(0.21 0.03 256 / 0.12);

  --font-sans: "Inter Variable", Inter, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}

/* ---------- DARK ---------- */
.dark {
  --background:        oklch(0.18 0.02 257);     /* not pure black — reduces halation */
  --foreground:        oklch(0.96 0.006 247);
  --card:              oklch(0.22 0.02 257);
  --card-foreground:   oklch(0.96 0.006 247);
  --popover:           oklch(0.22 0.02 257);
  --popover-foreground:oklch(0.96 0.006 247);
  --sidebar:           oklch(0.16 0.02 257);
  --sidebar-foreground:oklch(0.74 0.02 257);
  --muted:             oklch(0.27 0.02 257);
  --muted-foreground:  oklch(0.70 0.02 257);
  --secondary:         oklch(0.27 0.02 257);
  --secondary-foreground: oklch(0.96 0.006 247);
  --border:            oklch(1 0 0 / 0.10);      /* white @10% — separation without heavy lines */
  --input:             oklch(1 0 0 / 0.14);

  --primary:            oklch(0.70 0.10 195);    /* lighter teal in dark */
  --primary-foreground: oklch(0.20 0.03 220);
  --accent:             oklch(0.30 0.04 200);
  --accent-foreground:  oklch(0.92 0.03 197);
  --ring:               oklch(0.70 0.10 195);

  --pos:  oklch(0.72 0.16 152); --pos-foreground: oklch(0.20 0.03 150);
  --neg:  oklch(0.70 0.18 25);  --neg-foreground: oklch(0.20 0.03 25);
  --warn: oklch(0.80 0.15 78);
  --destructive: oklch(0.70 0.19 22); --destructive-foreground: oklch(0.20 0.03 25);
  --cb-pos: oklch(0.65 0.13 250); --cb-neg: oklch(0.80 0.14 72);

  --chart-1: oklch(0.70 0.10 195);
  --chart-2: oklch(0.70 0.14 162);
  --chart-3: oklch(0.68 0.14 255);
  --chart-4: oklch(0.78 0.15 78);
  --chart-5: oklch(0.70 0.16 320);
  --chart-grid:  oklch(1 0 0 / 0.10);
  --chart-axis:  oklch(0.70 0.02 257);
  --chart-ink:   oklch(0.85 0.006 247);          /* light "Actual" fill in dark */
  --chart-prior: oklch(0.45 0.01 257);
}

/* ---------- Tailwind v4 token mapping ---------- */
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-pos: var(--pos);
  --color-pos-foreground: var(--pos-foreground);
  --color-neg: var(--neg);
  --color-neg-foreground: var(--neg-foreground);
  --color-warn: var(--warn);
  --color-destructive: var(--destructive);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --font-sans: var(--font-sans);
  --font-mono: var(--font-mono);
}

/* ---------- base ---------- */
html { font-family: var(--font-sans); }
body {
  background: var(--background);
  color: var(--foreground);
  font-feature-settings: "cv05" 1, "cv08" 1, "ss03" 1; /* Inter stylistic tuning */
}
.tabular { font-variant-numeric: tabular-nums slashed-zero; }   /* money / KPIs / axes / totals */
:focus-visible { outline: 2px solid var(--ring); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
```

**Type scale** (Tailwind defaults, roles): `text-xs 12` (KPI label uppercase, captions) · `text-sm 14` (body + table default) · `text-base 16` · `text-lg 18` (H2/section) · `text-xl 20` · `text-2xl 24` (H1 page title) · `text-3xl 30` (KPI hero value). Weights: **400** body, **500** labels/UI, **600** headings + KPI values. `tracking-tight` (-0.02em) on KPI hero numbers and H1. Line-height: headings ~1.2, body ~1.5.

**Spacing** (4px base / 8px grid): page padding `p-6` → `md:p-8`; card padding `p-5`/`p-6`; card gap `gap-4`, section gap `gap-6`. Radius: `rounded-md` (6px) inputs/buttons, `rounded-lg` (8px) cards, `rounded-xl` modals, `rounded-full` pills/avatars only. Elevation: cards rest at `shadow-xs`/`shadow-sm` + 1px border; popovers/tooltips `shadow-md`; modals + command palette `shadow-lg`.

**Number formatting util** (`src/lib/format.ts`) — centralize everything:
```ts
export const fmtCompact = (n:number)=>Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(n);      // 1.2M
export const fmtCurrency = (n:number)=>Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',maximumFractionDigits:1}).format(n); // $1.2M
export const fmtFull = (n:number)=>Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);                    // tooltips
export const fmtAccounting = (n:number)=>Intl.NumberFormat('en-US',{style:'currency',currency:'USD',currencySign:'accounting'}).format(n); // (1,200.00)
export const fmtDelta = (n:number)=>Intl.NumberFormat('en-US',{signDisplay:'exceptZero',maximumFractionDigits:1}).format(n); // +12.3 / -4.0
```

---

## 3. App Shell

```
┌──────────────┬──────────────────────────────────────────────────────────┐
│  Sidebar     │  Top bar  h-14  (breadcrumbs · ⌘K · period/scenario · ☾ · 👤)│
│  w-64 / w-16 ├──────────────────────────────────────────────────────────┤
│  (collapsible│                                                            │
│   icon rail) │   <main> max-w-[1440px] mx-auto p-6 md:p-8                  │
│              │   PageHeader → content                                     │
└──────────────┴──────────────────────────────────────────────────────────┘
```

**`AppShell`** = `flex` row. `<aside>` `w-64 shrink-0 border-r border-border bg-sidebar` (collapses to `w-16` icon rail; state persisted in `localStorage`; below `md` becomes an off-canvas drawer over a scrim). `<div class="flex-1 min-w-0 flex flex-col">` holds the sticky top bar + scrollable main. Content surface (`bg-card`) is the brightest; sidebar is one step dimmer (`bg-sidebar`) so the work area dominates (Linear principle).

**Sidebar contents (top→bottom):**
1. **Company/workspace switcher** — `h-14` row, logo + name + chevron `dropdown-menu`.
2. **Nav groups** — group labels `text-xs uppercase tracking-wide text-muted-foreground px-3 py-2`:
   - **Overview** → Dashboard
   - **Plan** → Budgets, Forecasts
   - **Analyze** → Variance
   - **Data** → Accounts, Data Import
3. Spacer, then **theme toggle** + **user menu** pinned to bottom.

**Nav item:** `flex items-center gap-3 rounded-md px-3 h-9 text-sm text-sidebar-foreground hover:bg-muted`. **Active:** `bg-accent text-accent-foreground font-medium` + a `2px` left indicator (`before:absolute before:left-0 before:h-5 before:w-[2px] before:bg-primary before:rounded-full`) + `aria-current="page"`. lucide icon `size-4`. In rail mode, label hidden, icon centered, tooltip on hover.

**Top bar** `h-14 sticky top-0 z-20 border-b border-border bg-card/95 backdrop-blur flex items-center gap-3 px-4`:
- **Left:** sidebar collapse toggle (`PanelLeft` icon) + **breadcrumbs** (`<nav aria-label="Breadcrumb"><ol>…</ol></nav>`, last crumb `aria-current="page"`).
- **Center-left:** **⌘K trigger** — a muted button `Search… ⌘K` with a `<kbd>` hint; opens the `cmdk` palette. Also global `Cmd/Ctrl+K`.
- **Right:** **period/scenario selector** (`Select`: FY26 · Q2 · Actuals/Budget/Scenario), **theme toggle** (`Sun`/`Moon`, writes `.dark` + `localStorage`, honors `prefers-color-scheme` on first load), **user menu** (`dropdown-menu`).

**Command palette (cmdk):** centered modal `max-w-[640px] rounded-xl shadow-lg`, grouped results (Navigate / Actions / Search), fuzzy filter, arrow-key nav, recent items on open, `Esc` to close, `role="dialog"`, focus trapped + restored. Indexes: page nav (6 pages), entity search (accounts, budgets, forecasts), actions (Create budget, New scenario, Import data, Switch period, Toggle theme). Announce result count via `aria-live="polite"`.

**Responsive:** `<md` sidebar off-canvas; KPI grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`; tables get horizontal scroll with frozen first column; period selector collapses into an overflow menu.

---

## 4. Reusable Component Inventory

All in `src/components/ui` (shadcn copy-in) or `src/components` (composites). Class patterns below are the canonical recipes.

| Component | Key Tailwind class pattern |
|---|---|
| **Button** (cva) | base `inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50`. Variants: `primary` `bg-primary text-primary-foreground hover:bg-primary/90` (the ONE accent CTA); `secondary` `bg-secondary text-secondary-foreground hover:bg-muted`; `outline` `border border-border bg-transparent hover:bg-muted`; `ghost` `hover:bg-muted`; `destructive` `bg-destructive text-destructive-foreground`. Sizes: `sm h-8 px-3`, `default h-9 px-4`, `icon size-9`. |
| **Card** | `rounded-lg border border-border bg-card text-card-foreground shadow-xs`. Sub: `CardHeader p-5 pb-2`, `CardContent p-5 pt-2`, `CardFooter`. |
| **KPICard** | see §5.1. `rounded-lg border border-border bg-card p-5 shadow-xs flex flex-col gap-2`. |
| **Table** (TanStack `DataTable`) | wrapper `relative overflow-auto rounded-lg border border-border`. Header `sticky top-0 z-10 bg-card/95 backdrop-blur`; `th` `text-xs uppercase tracking-wide text-muted-foreground font-medium px-4 py-3 border-b border-border` (numeric `th` `text-right`). `tr` `border-b border-border/60 hover:bg-muted/50` (no zebra, no vertical lines). `td` `px-4 text-sm` (height by density 40/48/56); numeric `td` `text-right tabular`. First column `sticky left-0 bg-card font-medium`. Negatives `text-neg` with parentheses. |
| **Badge / StatusPill** (cva) | `inline-flex items-center rounded-full px-2 h-5 text-xs font-medium`. Variants: `neutral bg-muted text-muted-foreground`; `pos bg-pos/10 text-pos`; `neg bg-neg/10 text-neg`; `warn bg-warn/10 text-warn`; `accent bg-accent text-accent-foreground`. Always include a glyph (✓ ! ▲ ▼) so it's not color-only. |
| **Input** | `h-9 w-full rounded-md border border-input bg-card px-3 text-sm placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring`. Numeric inputs add `text-right tabular`. |
| **Select** (Radix) | trigger matches Input; content `rounded-md border border-border bg-popover shadow-md`; item `h-8 px-2 rounded-sm data-[highlighted]:bg-accent`. |
| **Tabs** (Radix) | list `inline-flex h-9 items-center gap-1 rounded-md bg-muted p-1`; trigger `rounded-sm px-3 text-sm data-[state=active]:bg-card data-[state=active]:shadow-xs`. |
| **Skeleton** | `animate-pulse rounded-md bg-muted` (disabled under `prefers-reduced-motion`). KPI skel `h-24`, table row skel `h-10`. |
| **EmptyState** | centered `flex flex-col items-center gap-3 py-16 text-center`; icon `size-10 text-muted-foreground`; title `text-base font-medium`; help `text-sm text-muted-foreground max-w-sm`; primary `Button`. |
| **Toast** (sonner) | one `<Toaster richColors position="bottom-right" />` at root, ~4s. `toast.success/error` for mutations, `toast.promise` for imports/forecast runs; action only when undoable. |
| **PageHeader** | `flex items-start justify-between gap-4 mb-6`. Left: `h1 text-2xl font-semibold tracking-tight` + optional `text-sm text-muted-foreground` subtitle + "Last updated · source" caption. Right: period/scenario `Select` + **single** primary `Button`. |
| **ChartCard** | `Card` + header (title `text-sm font-medium` + small legend top-right + density/CB toggle) + `CardContent` with `ResponsiveContainer h-[320px]`. |

---

## 5. Page-by-Page Redesign

### 5.1 Dashboard

**Layout:** `PageHeader` ("Dashboard", period selector, primary "Import data") → KPI strip → main charts grid → activity/freshness panel.

**KPI strip** — `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`, 4 uniform `KpiCard`s, identical height:
1. **Cash Balance** · 2. **Net Burn / Runway** · 3. **Revenue MTD (vs plan)** · 4. **Budget Variance**.

`KpiCard` anatomy (strict, uniform):
- Label — `text-xs uppercase tracking-wide text-muted-foreground`.
- Value — `text-3xl font-semibold tabular tracking-tight`.
- Delta row — `inline-flex items-center gap-1 text-sm`: arrow glyph `▲`/`▼` + signed % in `text-pos`/`text-neg` (dual-encoded) + muted basis caption `vs prior period` / `vs Budget`.
- Sparkline — Tremor-style mini `<AreaChart>` `h-8`, `stroke` = matching `--pos`/`--neg` semantic, `dot={false}`, no axes/grid/tooltip.

Each value drills to its source table on click (audit principle).

**Charts grid** — `grid grid-cols-1 lg:grid-cols-3 gap-6`:
- **Revenue & Cash trend** (`lg:col-span-2`) — `ChartCard`, `LineChart`. **Actuals** solid 2px `var(--chart-1)`; **Forecast** same hue `strokeDasharray="5 4"`; **Budget baseline** `var(--chart-prior)` thin. Vertical `ReferenceLine` at "today" labelled "Forecast →". Y ticks compact currency.
- **Budget vs Actual** (1 col) — `ChartCard`, IBCS overlapped columns: wider hollow **Budget** `fill="var(--card)" stroke="var(--chart-ink)"` behind a narrower solid **Actual** `fill="var(--chart-ink)"`; one accent only where over/under matters.

**Activity / freshness panel** — full-width `Card`: recent imports/edits list + **"Last updated 2026-06-18 · source: QuickBooks CSV"** caption. Loading → `Skeleton` cards + rows; empty → `EmptyState` "No data yet → Import data".

### 5.2 Accounts (pro table)

Chart of accounts / balances as the signature dense `DataTable`.

- **Toolbar** above table: search input (+ ⌘K), multi-column filter chips, **density toggle** (40/48/56), column visibility `dropdown-menu`.
- **Columns:** `Account` (frozen left, `font-medium`, text-left) · `Type` (`Badge neutral`) · `Balance` (`text-right tabular`) · `Prior` (`text-right tabular text-muted-foreground`) · `Δ %` (`text-right tabular`, `text-pos`/`text-neg` + arrow) · **Trend** (in-cell sparkline column, `h-6`, no axes).
- Negatives: `text-neg` + accounting parentheses. Default sort: most recent / largest balance. Whole-row hover highlight; row click → account detail drill-down. Header sticky; scale + currency declared once: "USD" caption in the toolbar.
- States: `Skeleton` rows while pending, `EmptyState` on zero, error `Card` (`--neg` accent) with **Retry** → `refetch()`.

### 5.3 Budgets (method wizard + result)

**Method wizard** — `Tabs` or stepper: **Choose method** (Zero-based / % growth / Driver-based / Copy prior) → **Set parameters** (`Input`/`Select`, react-hook-form + zod) → **Review**.

**Result = spreadsheet-like editable grid** (TanStack Table, the signature editing surface): line items down, months across. Sticky first column + sticky header row. Inline-editable numeric cells (`text-right tabular`, click-to-edit, Tab/Enter navigation). **Subtotal/total rows** `font-medium bg-muted/40`. A trailing **vs Actual** column color-codes variance (`text-pos`/`text-neg` + sign). `toast.success` on save; optimistic update via react-query.

### 5.4 Forecasts (fan chart + scoreboard + KPIs)

**Layout:** `PageHeader` with **scenario switcher** in top bar + primary "Run forecast". → KPI row → fan chart → model scoreboard + driver inputs.

- **KPI row** — `KpiCard`s: Projected Revenue (period end), Projected Runway, Forecast vs Plan Δ, Confidence (80% band width).
- **Fan chart** — `ChartCard`, full spec in §6.1. History solid `--chart-ink`; point forecast solid teal line then **dashed** past "today"; 80%/95% bands in teal at graded opacity; "today" `ReferenceLine`.
- **Model scoreboard** — small `DataTable`: Model (ARIMA / Holt-Winters / Linear / Prophet-style) · MAPE · RMSE · MAE · Selected (`Badge accent` ✓). Sort by MAPE asc; best model highlighted. Numbers `tabular`.
- **Driver inputs panel** — `Card` with editable `Input`s (growth %, churn, headcount); editing re-runs forecast (debounced, `toast.promise`). **Compare scenarios** overlay: multiple dashed lines, one hue each from `--chart-1..5`, legend top-right.

### 5.5 Variance (IBCS waterfall bridge + favorable/unfavorable table)

The signature analytical page. Two stacked views.

- **Waterfall bridge** — `ChartCard`, full spec in §6.2. Budget → +/- contributions → Actual. Totals greyscale `--chart-ink`; favorable steps `--pos`, unfavorable `--neg`; thin connector lines; every label signed. Colorblind toggle swaps to `--cb-pos`/`--cb-neg`.
- **Variance table** — `DataTable`, IBCS 3-tier discipline. Columns: `Line item` (frozen) · `Budget` · `Actual` · `Variance $` · `Variance %`. Numeric cols `text-right tabular`. **Variance $/%** color-coded `text-pos`/`text-neg` **with arrow + explicit sign** (`signDisplay:'exceptZero'`); base Budget/Actual columns stay neutral (IBCS: never color base). Negatives in accounting parentheses. Optional in-cell magnitude bars behind variance numbers (low-opacity `--pos`/`--neg`). Optional PuOr diverging heatmap mode anchored at 0 for the variance column. Each line drills to contributing transactions.

### 5.6 Data Import (referenced by shell/nav)

Stepper **Upload → Map columns → Preview → Confirm**. Preview = `DataTable` with **red cell highlight** (`bg-neg/10 ring-1 ring-neg`) on validation errors; `Badge neg` row status. First-class empty/loading/error states; `toast.promise` on commit; "source + row count" caption after import.

---

## 6. Concrete Chart Specs (Recharts 3.x)

**Shared themed wrapper** (`ThemedChart` defaults): `<CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false} />`; axes `axisLine={false} tickLine={false}` ticks `fill: var(--chart-axis)`, `fontSize: 12`, Y `tickFormatter={fmtCurrency}`; custom `<Tooltip>` = `bg-popover border border-border rounded-md shadow-md p-3 text-sm tabular` with labelled rows showing `fmtFull`; legend top-right, small. No chart border/background/3D/shadow.

### 6.1 Forecast Fan Chart

Single blue/teal hue; bands widen with horizon; 80% (z≈1.28) darker, 95% (z≈1.96) lighter.

**Data row:** `{ t, history?, forecast?, lo80?, hi80?, lo95?, hi95? }` where `forecast`/bands are populated only from "today" onward, `history` only up to "today".

**Render** — `ComposedChart`:
```tsx
<ComposedChart data={data}>
  <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false}/>
  <XAxis dataKey="t" axisLine={false} tickLine={false}/>
  <YAxis tickFormatter={fmtCurrency} axisLine={false} tickLine={false}/>
  <Tooltip content={<FinanceTooltip/>}/>

  {/* 95% band: stacked area trick — invisible base lo95, visible (hi95-lo95) */}
  <Area dataKey="lo95" stackId="b95" stroke="none" fill="transparent" isAnimationActive={false}/>
  <Area dataKey="band95" stackId="b95" stroke="none"
        fill="var(--chart-1)" fillOpacity={0.12} isAnimationActive={false}/>

  {/* 80% band on its own stack */}
  <Area dataKey="lo80" stackId="b80" stroke="none" fill="transparent" isAnimationActive={false}/>
  <Area dataKey="band80" stackId="b80" stroke="none"
        fill="var(--chart-1)" fillOpacity={0.25} isAnimationActive={false}/>

  {/* history solid, then forecast dashed (same hue, continuous) */}
  <Line dataKey="history"  stroke="var(--chart-ink)" strokeWidth={2} dot={false}/>
  <Line dataKey="forecast" stroke="var(--chart-1)"  strokeWidth={2} dot={false}
        strokeDasharray="5 4"/>

  <ReferenceLine x={todayT} stroke="var(--chart-axis)" strokeDasharray="3 3"
                 label={{ value:'Forecast →', position:'top', fill:'var(--chart-axis)', fontSize:12 }}/>
</ComposedChart>
```
Precompute `band80 = hi80 - lo80`, `band95 = hi95 - lo95` so each `lo* + band*` stack reproduces the upper bound (stacked-area range technique).

### 6.2 Variance Waterfall (Bridge)

No native waterfall → transparent base bar + visible delta bar with per-point `<Cell>` colors; totals anchored at 0.

**Data row:** `{ name, base, value, type: 'total'|'favorable'|'unfavorable' }` where
`base = type==='total' ? 0 : Math.min(cumPrev, cumNext)` and `value = Math.abs(delta)`.

**Render** — `BarChart`:
```tsx
<BarChart data={rows} barCategoryGap="25%">
  <CartesianGrid stroke="var(--chart-grid)" horizontal vertical={false}/>
  <XAxis dataKey="name" axisLine={false} tickLine={false} interval={0}/>
  <YAxis tickFormatter={fmtCurrency} axisLine={false} tickLine={false}/>
  <Tooltip content={<FinanceTooltip/>}/>
  <ReferenceLine y={0} stroke="var(--chart-axis)"/>

  <Bar dataKey="base"  stackId="w" fill="transparent" isAnimationActive={false}/>
  <Bar dataKey="value" stackId="w" radius={[2,2,0,0]}>
    {rows.map((r,i)=>(
      <Cell key={i} fill={
        r.type==='total'       ? 'var(--chart-ink)' :   /* Budget / Actual totals = grey */
        r.type==='favorable'   ? 'var(--pos)'       :   /* green (or --cb-pos in CB mode) */
                                 'var(--neg)'            /* red   (or --cb-neg in CB mode) */
      }/>
    ))}
    <LabelList dataKey="value" position="top" formatter={fmtDelta}
               className="tabular" fill="var(--chart-axis)" fontSize={12}/>
  </Bar>
</BarChart>
```
First (`Budget`) and last (`Actual`) rows are `type:'total'` → `base:0`, full-height greyscale columns. Add thin connector lines between consecutive step tops via a `customized` SVG layer or per-segment `ReferenceLine`. Color is spent **only** on the +/- steps; every contribution label carries an explicit sign. Colorblind toggle swaps `--pos`/`--neg` → `--cb-pos`/`--cb-neg`; dual encoding (sign + position) means meaning survives in greyscale.

---

**Files referenced:** `c:\Users\user\...\budgeting and forcasting tool\frontend\package.json` (current: React 19, Recharts `^2.13.0` to upgrade to `^3`, no Tailwind/shadcn yet — all additions above are net-new). Tokens land in `c:\Users\user\...\frontend\src\index.css` (replacing the existing 301-line plain-CSS file).
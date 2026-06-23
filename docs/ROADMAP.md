# Product Roadmap — from local FP&A tool to industry-grade platform

> **How this was produced.** Two deep, multi-source research passes (≈220 agent runs, ~4.2M tokens)
> with **adversarial verification** — every load-bearing claim was independently challenged by 3
> reviewers and only kept on a ≥2/3 confirm. Markers below:
>
> - ✅ **Verified** — primary-sourced and survived adversarial verification (citation in the
>   [Sources](#sources--verification) appendix).
> - 📋 **Expert synthesis / re-verify at adoption** — drawn from domain knowledge or a source whose
>   verification vote was cut short by a session limit; treated as high-confidence but flag for a
>   quick license re-check before you actually pull it in.
>
> **Hard constraint (decided):** every recommended dependency must be **OSI-permissive**
> (MIT / BSD / Apache-2.0 / ISC / MPL-2.0). No GPL / AGPL / SSPL / source-available / commercial.
> This roadmap only recommends components that clear that bar, and explicitly flags the traps.
>
> **Direction (decided):** *hybrid* — keep the zero-setup, single-user, local-first default, but
> architect deliberately toward multi-user → team → enterprise. See [DESIGN.md](DESIGN.md) for the
> current build and [ARCHITECTURE.md](ARCHITECTURE.md) for the diagrams.

---

## 1. Where we are vs. the market

We already ship the *analytical core* that most FP&A tools bury behind a paywall: four budgeting
methods, backtested auto-forecasting with conformal intervals, and a sign-correct PVM variance
engine. What we lack is the **platform** around it — collaboration, a spreadsheet-grade editing
surface, driver-based modeling, scenarios at scale, consolidation, integrations, and a reporting
layer.

The good news the research confirmed: **the entire feature surface of the commercial leaders is
reachable with OSI-permissive components.** The cost of the open-source-only rule is real but
narrow (turnkey AI copilots, managed connectors, polished multiplayer) — see [§7](#7-the-oss-only-tax).

### Competitive feature matrix

Legend: ● have · ◐ partial · ○ missing. "Tier" = T (table-stakes across Anaplan/Adaptive/Pigment/
Planful/Cube/Vena/Datarails/Prophix/OneStream/Board/Jirav) vs **D** (premium differentiator). 📋

| Capability | Tier | Us today | Notes |
|---|---|---|---|
| Multi-method budgeting (incl/ZBB/ABB/VPB) | T | ● | Already a differentiator vs many SMB tools |
| Statistical auto-forecasting + intervals | T/D | ● | Conformal intervals are a genuine edge |
| Variance + PVM + waterfall bridge | T | ● | IBCS-style bridge already present |
| Manual grid + CSV/Excel import | T | ◐ | Works, but not spreadsheet-grade (see UI) |
| **Driver-based modeling** (formulas, drivers) | T | ○ | The #1 gap — defines "FP&A" vs "reporting" |
| **Scenario / version management** | T | ◐ | We have budget versions; need first-class scenarios + compare |
| **What-if / sensitivity / Monte Carlo** | D | ○ | High-impact, low-effort with our forecasting core |
| **Multi-dimensional cube / fast pivot** | T | ◐ | Star schema exists; needs an OLAP engine + pivot UI |
| **Rolling forecast** automation | T | ◐ | Cadence modifier exists; needs scheduled re-forecast |
| **Workflow / approvals** | T | ○ | Needed for team tier |
| **Multi-user, RBAC, audit trail** | T | ○ | Needed for team/enterprise tier |
| **Real-time collaboration / comments** | D | ○ | pycrdt makes this reachable |
| **Board-ready report packs / distribution** | T | ○ | PDF/XLSX/PPTX export + schedule |
| **ERP / accounting integrations** | T | ○ | Tally/Zoho/QuickBooks/Xero |
| **Multi-entity, multi-currency consolidation** | D | ○ | Enterprise tier; well-defined contract |
| **AI copilot / NL query / narrative** | D | ○ | Claude API gives us narrative cheaply |
| **Self-serve BI / semantic layer** | D | ○ | Superset/Lightdash-core pattern |

---

## 2. The OSI-permissive toolbox (verified)

This is the spine of the roadmap — the components that let us build each capability without
violating the license rule. **Licenses confirmed by the research are marked ✅.**

### Forecasting & AI/ML — *fully solved, permissively* ✅

| Component | License | Gives us |
|---|---|---|
| **statsforecast** (Nixtla) | Apache-2.0 ✅ | AutoARIMA/ETS/CES/Theta **+ AutoMFLES, AutoTBATS** (multiple seasonalities), exogenous regressors, anomaly detection — a superset of our current baselines |
| **neuralforecast** (Nixtla) | Apache-2.0 ✅ | 30+ deep models (NBEATS/NHITS, TFT, PatchTST, iTransformer) for when we have enough history |
| **hierarchicalforecast** (Nixtla) | Apache-2.0 ✅ | **Coherent reconciliation** (BottomUp/TopDown/MinTrace) so dept/region/account forecasts *sum to* the total — a real FP&A need |
| **MAPIE** | BSD-3 ✅ | Model-agnostic **conformal** prediction intervals for any regressor incl. time series (generalizes our existing conformal bands) |
| **Darts** | Apache-2.0 ✅ | One `fit()/predict()` API over statistical + LightGBM/XGBoost + probabilistic + anomaly + backtesting — good for a unified driver model |
| **PyMC** / **NumPyro** | Apache-2.0 📋 | Bayesian driver models + **Monte Carlo** scenario distributions |
| **SALib** | MIT 📋 | Sensitivity analysis (tornado charts, which drivers move the P&L most) |

### Planning-process backend — *solved, with two traps avoided* ✅

| Need | Use | License | Avoid |
|---|---|---|---|
| AuthN (OIDC/OAuth) | **Authlib** | BSD-3 ✅ | — |
| AuthN (batteries-included) | **fastapi-users** | MIT 📋 | — |
| AuthZ (RBAC/ABAC) | **PyCasbin** | Apache-2.0 ✅ | **oso** — Apache but *deprecated* ✅ |
| Audit trail / versioning | **SQLAlchemy-Continuum** | BSD-3 ✅ | — |
| Approval workflow / state machine | **python-statemachine** or **transitions** | MIT 📋 | **SpiffWorkflow** — *LGPL* ✅ |
| Background jobs / scheduling | **APScheduler** (sched) + **arq** or **Celery** (queue) | MIT / MIT / BSD 📋 | **Dramatiq** — *LGPL* 📋 |
| Job/queue broker | **Valkey** | BSD-3 📋 | **Redis** — now *RSALv2/SSPL* 📋 |
| Real-time collaboration | **pycrdt** (Yjs/Yrs bindings) | MIT ✅ | — |
| Relational DB (team tier) | **PostgreSQL** | PostgreSQL Lic. 📋 | — |
| Analytical/OLAP engine | **DuckDB** | MIT 📋 | — |

### Reporting / BI / export

| Need | Use | License | Avoid |
|---|---|---|---|
| Board PDF packs | **WeasyPrint** (HTML/CSS→PDF) | BSD-3 📋 | — |
| Excel export | **XlsxWriter** / **openpyxl** | BSD-2 / MIT 📋 | — |
| Board decks | **python-pptx** | MIT 📋 | — |
| Polished financial tables | **great_tables** | MIT 📋 | — |
| Self-serve BI / dashboards | **Apache Superset** (embed) or **Lightdash core** | Apache-2.0 / MIT ✅(core) | **Metabase** — *AGPL* ✅; Lightdash **EE dir** — source-available ✅ |
| Charting beyond Recharts | **Apache ECharts**, **visx**, **Nivo**, **Observable Plot** | Apache-2.0 / MIT / MIT / ISC 📋 | — |

### Data / integration / consolidation

| Need | Use | License | Notes |
|---|---|---|---|
| ELT / connectors | **dlt** or **Meltano** (Singer taps) | Apache-2.0 / MIT 📋 | Avoid Airbyte *platform* (ELv2, not OSI) — taps OK |
| Transformation / semantic layer | **dbt-core** | Apache-2.0 📋 | Pairs with DuckDB/Postgres |
| India ERP (Tally) | TallyPrime **native JSON/HTTP POST** | (protocol) ✅ | Native from Tally 7.0; XML/TDL earlier |
| India ERP (Zoho Books) | Zoho Books **REST API** | (protocol) 📋 | OAuth; GST-aware |
| Spreadsheet-grade grid (UI) | **Glide Data Grid** | MIT ✅ | Canvas-rendered, millions of rows |

### Hard licensing traps the research surfaced ✅
- **Firefly III** (finance app) — AGPL-3.0 → excluded.
- **Metabase** OSS — AGPL → excluded (use Superset/Redash).
- **SpiffWorkflow** (BPMN) — LGPL → excluded (use python-statemachine).
- **HyperFormula** (spreadsheet formula engine) — GPLv3/commercial dual → excluded for the formula
  engine; build our own calc graph or use a permissive evaluator. 📋
- **oso** — permissive but *deprecated*; **Vanna** (NL-SQL) — MIT but *repo archived Mar 2026*;
  **WrenAI** — *mixed* Apache+AGPL. Prefer building NL-query directly on the Claude API.

---

## 3. Architecture evolution (the hybrid path)

The goal: **one codebase, three deployment postures.** Achievable because the hard parts are
already proven OSS patterns (Actual Budget = MIT local-first + optional CRDT sync ✅).

```
SOLO (today)          TEAM                          ENTERPRISE
SQLite, no auth   →   SQLite/Postgres, OIDC+RBAC →  Postgres + DuckDB OLAP, multi-tenant
single user           audit trail, approvals        consolidation, integrations, BI, sync
```

Concrete moves, all additive to the current FastAPI/SQLModel app:
1. **DB portability** — keep SQLite default; add Postgres via the same SQLAlchemy layer
   (`OPENFPA_DATABASE_URL` already exists). Add **DuckDB** as the read/analytics engine for pivots
   and large models.
2. **Auth as opt-in** — `Authlib` OIDC; when no IdP is configured, app stays in today's
   single-user local mode (zero-setup preserved).
3. **AuthZ** — `PyCasbin` policies (org → workspace → scenario → cell scope). RBAC first, ABAC later.
4. **Audit + versioning** — `SQLAlchemy-Continuum` on `Entry`, `BudgetVersion`, `Account` →
   "who changed this number, when, from what."
5. **Async** — `APScheduler` (rolling re-forecast, scheduled report distribution) + `arq`/`Celery`
   on `Valkey` for long forecasts/consolidation runs.
6. **Sync/collab** — `pycrdt` for cross-device sync and cell-level comments (Actual Budget's model).
   Note ✅: CRDT cross-device propagation is solved; *simultaneous live co-authoring* is the harder
   frontier — phase it last.
7. **Tenancy** — start single-tenant; add Postgres **row-level security** for multi-tenant SaaS.

---

## 4. Phased roadmap

Effort: **S** ≤1wk · **M** 1–3wk · **L** 1–2mo · **XL** quarter+. Impact: ★→★★★.

### Phase 0 — Deepen the single-user product (biggest ROI, no architecture change)

| # | Feature | Enabling OSS | Area | Effort | Impact |
|---|---|---|---|---|---|
| 0.1 | **Spreadsheet-grade grid** (fast edit, paste, fill, freeze, millions of cells) replacing the basic manual grid | Glide Data Grid (MIT ✅) | UI | M | ★★★ |
| 0.2 | **Driver-based modeling** — define drivers (price, volume, headcount) + formulas; accounts computed from drivers | calc graph (own) + Darts (Apache ✅) | Forecast/Plan | L | ★★★ |
| 0.3 | **Scenario engine** — first-class scenarios (Base/Best/Worst), side-by-side compare, clone & tweak | SQLAlchemy-Continuum (BSD ✅) | Plan | M | ★★★ |
| 0.4 | **What-if + Monte Carlo + sensitivity** (probability cones, tornado) | PyMC/NumPyro 📋, SALib (MIT) 📋 | Forecast | M | ★★ |
| 0.5 | **Forecasting upgrades** — multi-seasonality (AutoMFLES/TBATS), exogenous drivers, **hierarchical reconciliation** (dept/region sum to total), anomaly flags | statsforecast/hierarchicalforecast/MAPIE (Apache/BSD ✅) | Forecast | M | ★★★ |
| 0.6 | **Board report export** — PDF pack + Excel + PPTX, IBCS-styled | WeasyPrint/XlsxWriter/python-pptx/great_tables 📋 | Report | M | ★★ |
| 0.7 | **AI narrative & variance commentary** ("why did margin move?") | Claude API + our variance engine | Report/AI | S | ★★★ |
| 0.8 | **Fast pivot / ad-hoc analysis** over the star schema | DuckDB (MIT) 📋 | Report | M | ★★ |

### Phase 1 — Team tier (multi-user, governed)

| # | Feature | Enabling OSS | Area | Effort | Impact |
|---|---|---|---|---|---|
| 1.1 | **Auth (OIDC) + users/workspaces**, local mode preserved | Authlib (BSD ✅) / fastapi-users (MIT) | Arch | M | ★★★ |
| 1.2 | **RBAC** (owner/editor/viewer, scope to scenario/dept) | PyCasbin (Apache ✅) | Arch | M | ★★★ |
| 1.3 | **Audit trail** (full change history, restore) | SQLAlchemy-Continuum (BSD ✅) | Process | S | ★★ |
| 1.4 | **Approval workflows** (submit → review → approve budget) | python-statemachine (MIT) 📋 | Process | M | ★★ |
| 1.5 | **Comments / cell annotations** | pycrdt (MIT ✅) | Collab | M | ★★ |
| 1.6 | **Postgres option + background jobs** (rolling re-forecast, scheduled distribution) | Postgres 📋, APScheduler/arq/Valkey 📋 | Arch | M | ★★ |
| 1.7 | **Workforce & capex planning** modules (headcount→cost, asset→deprec schedule) | own, on driver engine | Plan | L | ★★ |

### Phase 2 — Enterprise tier (consolidation, integrations, BI)

| # | Feature | Enabling OSS | Area | Effort | Impact |
|---|---|---|---|---|---|
| 2.1 | **Multi-entity consolidation** — account mapping, **intercompany eliminations** (net-change/fixed, wildcard, trading-partner dim), **CTA** for FX translation | own, per verified contract ✅ | Consol | XL | ★★★ |
| 2.2 | **Accounting/ERP connectors** — Tally (native JSON ✅), Zoho Books, QuickBooks/Xero | dlt/Meltano taps (Apache/MIT) 📋 | Data | L | ★★★ |
| 2.3 | **Semantic layer + self-serve BI** | dbt-core (Apache) + Superset/Lightdash-core 📋✅ | Report | L | ★★ |
| 2.4 | **Data lineage & governance** | own metadata + Continuum 📋 | Data | M | ★ |
| 2.5 | **Real-time multiplayer** editing | pycrdt (MIT ✅) | Collab | XL | ★★ |
| 2.6 | **Multi-tenant SaaS** (Postgres RLS) | Postgres 📋 | Arch | L | ★★ |

---

## 5. UI/UX — does it need a rework?

**Yes, in one specific way.** The current React 19 + Tailwind v4 + Recharts 3 stack is modern and
the visual design is clean — keep it. But FP&A *is* a spreadsheet, and a DOM-based grid can't deliver
that. The research is unambiguous ✅: **Glide Data Grid** (MIT) is canvas-rendered, scales to
millions of rows with native scrolling, and the maintainers explicitly abandoned DOM virtualization
because it scrolled choppily. **This is the single highest-leverage UI change.**

Recommended UI moves:
1. **Adopt Glide Data Grid** for the planning/budget/actuals surface (Phase 0.1) — keep Tailwind/
   shadcn shell and Recharts for charts.
2. **Modeling affordances** — formula bar, driver inspector, scenario toggle in the header, inline
   variance heatmap, expand/collapse account hierarchy.
3. **Charting**: keep Recharts for standard charts; add **ECharts** (Apache-2.0) 📋 only where you
   need heavy/financial chart types (large candlesticks, complex waterfalls, dense small-multiples).
4. **Dashboards**: a draggable widget canvas (react-grid-layout, MIT 📋) for self-serve dashboards.
5. **Command palette** (already have cmdk) → extend into an **AI "ask your model"** entry point.

---

## 6. India-market specifics

| Need | Approach | Source |
|---|---|---|
| **Schedule III** statement formats (Division I = AS, Division II = Ind AS) | Model as a **reporting overlay**: map our Schedule III chart of accounts to the statutory line-item taxonomy; render Balance Sheet / P&L / cash-flow in the mandated format | ICAI Guidance Note on Division II 📋✅(authoritative) |
| **Tally** integration | TallyPrime **native JSON over HTTP POST** (`tallyrequest`: Import/Export/Execute); XML/TDL for older Tally.ERP 9 | ✅ verified |
| **Zoho Books** integration | REST API (OAuth), GST-aware ledgers | 📋 |
| **GST** in FP&A | Keep GST **out of the core P&L model** (it's a balance-sheet pass-through: output GST liability, input GST credit); model **net-of-GST** revenue/cost and add a GST working-capital schedule | taxguru / domain 📋 |
| **Festive seasonality** | Our seasonal models already capture this; add India holiday regressors (Diwali/GST-quarter) as exogenous features in statsforecast | 📋 |

---

## 7. The OSS-only tax (honest trade-offs)

Where the permissive-only rule genuinely costs vs commercial tools:

1. **AI copilots** — Anaplan/Pigment ship tuned NL-query + planning copilots. Permissive NL-to-SQL
   OSS is weak right now (Vanna *archived*, WrenAI *mixed-license* ✅). **Mitigation:** build NL-query
   and narrative directly on the **Claude API** over a constrained semantic layer — your *code* stays
   permissive; the model is a service, not a bundled dependency.
2. **Turnkey managed connectors** — Airbyte's *platform* is ELv2 (not OSI). **Mitigation:** dlt/Meltano
   (permissive) + per-ERP work; more effort, no license risk.
3. **Enterprise BI polish** — Metabase's nice UX is AGPL; Lightdash's best bits are in the
   source-available EE dir. **Mitigation:** Superset (Apache) is powerful but heavier to theme.
4. **Real-time multiplayer co-authoring** — CRDT cross-device sync is solved (pycrdt ✅), but Google-
   Sheets-grade live co-editing is a hard, long build. Phase it last.
5. **Spreadsheet formula engine** — the best JS engine (HyperFormula) is GPL/commercial. **Mitigation:**
   build a scoped calc graph (we control the formula surface anyway) or a permissive evaluator.

None of these is a blocker — each has a permissive path. They're effort, not impossibility.

---

## 8. Build this next (the shortlist)

If I had to sequence the first push for maximum "this feels industry-grade" impact:

1. **Glide Data Grid planning surface** (0.1) — turns "a form" into "a spreadsheet." *Biggest perceived leap.*
2. **Driver-based modeling + scenarios** (0.2, 0.3) — this is what makes it *FP&A*, not reporting.
3. **AI variance narrative via Claude API** (0.7) — cheap, demoable, genuinely useful, S-effort.
4. **Forecasting depth** (0.5) — hierarchical reconciliation + multi-seasonality + anomaly flags; we
   already have the engine, this is mostly wiring verified libraries.
5. **Board report export** (0.6) — PDF/XLSX/PPTX pack; finance teams live and die by the deck.
6. *Then* open the **team tier** (1.1–1.3: auth + RBAC + audit) once the single-user product is deep.

Rationale: maximize product depth *before* platform complexity. Each Phase-0 item is independently
shippable, needs no architecture change, and uses a verified permissive library.

---

## Sources & verification

Produced by two adversarially-verified research passes. Selected primary sources (full list in the
run transcripts):

- Forecasting: github.com/Nixtla/statsforecast · /neuralforecast · /hierarchicalforecast ·
  github.com/scikit-learn-contrib/MAPIE · github.com/unit8co/darts ✅
- Architecture/process libs: github.com/apache/casbin-pycasbin · github.com/authlib/authlib ·
  pypi.org/project/SQLAlchemy-Continuum · github.com/osohq/oso · github.com/sartography/SpiffWorkflow ·
  y-crdt.github.io/pycrdt ✅
- Local-first/sync & grid: github.com/actualbudget/actual · github.com/glideapps/glide-data-grid ✅
- BI/licensing: github.com/lightdash/lightdash · metabase.com/license · github.com/firefly-iii/firefly-iii ✅
- Consolidation contract: Microsoft Dynamics 365 Finance docs · Oracle NetSuite docs ✅
- India: TallyPrime integration docs ✅ · ICAI Guidance Note on Schedule III Division II 📋

**Caveats.** (1) License facts are point-in-time (mid-2026) — **re-verify at adoption**, especially
open-core boundaries (Lightdash EE). (2) Items marked 📋 had their verification vote cut by a session
limit; they're high-confidence but unverified by the harness. (3) Library *capability* claims describe
documented features, not measured FP&A-context performance. (4) Effort/impact sizing is my estimate,
not a verified figure. (5) One refuted claim worth noting ✅: multi-tier FX consolidation does **not**
require an intermediate legal entity per currency tier — direct translation with a CTA account works.

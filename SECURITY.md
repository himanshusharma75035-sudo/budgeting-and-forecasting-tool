# Security Policy

The maintainer takes the security of this project seriously. Thank you for helping keep it and
its users safe.

## Supported versions

This project is pre-1.0 and ships from `main`. Security fixes are applied to the latest commit on
`main`; there are no separately maintained release branches yet.

| Version        | Supported          |
| -------------- | ------------------ |
| `main` (latest)| :white_check_mark: |
| older commits  | :x:                |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately through one of these channels:

1. **GitHub Security Advisory (preferred)** — open a private report at
   [Security → Report a vulnerability](https://github.com/himanshusharma75035-sudo/budgeting-and-forecasting-tool/security/advisories/new).
2. **Email** — <Himanshusharma75035@gmail.com> with the subject line `SECURITY:`.

Please include, as far as you can:

- a description of the issue and its impact,
- steps to reproduce or a proof of concept,
- affected component(s) and version/commit,
- any suggested remediation.

### What to expect

| Stage                 | Target                          |
| --------------------- | ------------------------------- |
| Acknowledgement       | within **3 business days**      |
| Initial assessment    | within **7 business days**      |
| Fix / mitigation plan | communicated after triage       |

Coordinated disclosure is appreciated: please give a reasonable window to release a fix before any
public disclosure. Credit will be given to reporters who wish to be named.

### Safe harbor

Good-faith security research conducted in accordance with this policy — and only against your own
local instance and data — is welcome. Do not access, modify, or exfiltrate data that is not yours,
and do not run denial-of-service tests against infrastructure you do not own.

## Security posture

This is a **local-first, single-user** tool: by default it binds to localhost and stores data in a
local SQLite file. It does not ship with authentication, and it is **not hardened for direct
exposure to the public internet**. If you deploy it on a network, place it behind an
authenticating reverse proxy (and enable TLS + HSTS — see below).

### Application-layer controls (`backend/app/security.py`)

Defence-in-depth middleware, all dependency-free and configurable via `OPENFPA_*` env vars:

- **Secure response headers** — `Content-Security-Policy`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` (clickjacking), `Referrer-Policy`,
  `Permissions-Policy`, cross-origin isolation (`COOP`/`CORP`), and optional **HSTS**
  (`OPENFPA_ENABLE_HSTS=true`, only behind TLS). The `Server` header is masked.
- **Host allow-list** (`TrustedHostMiddleware`) — mitigates Host-header spoofing / DNS rebinding.
- **Strict CORS** — origins limited to the dev SPA; credentials disabled; methods/headers pinned.
- **Request body cap** (`max_request_bytes`, default 25 MiB) — bounds memory on uploads (DoS guard).
- **Rate limiting** — sliding-window, per-client-IP limiter (`rate_limit_per_minute`, default 240).

### Data & query safety

- All database access goes through **SQLModel / SQLAlchemy** parameterized queries (no string-built
  SQL), so the engine is not exposed to SQL injection.
- Monetary values are stored as **integer minor units** and computed in `Decimal` — no float drift.
- SQLite runs with **foreign keys enforced** and **WAL** journaling.

### Supply-chain & CI controls

- **CodeQL** static analysis (Python + JS/TS), `security-extended` queries.
- **Dependabot** weekly updates for pip, npm, and GitHub Actions.
- **Secret scanning** (gitleaks) on every push/PR — **blocking**.
- **Dependency CVE audits** — `pip-audit` and `npm audit`.
- **OpenSSF Scorecard** supply-chain assessment.
- **License gate** — CI fails on any GPL/AGPL/SSPL/BSL/commercial dependency.

## Hardening checklist for non-local deployments

- [ ] Put the API behind an authenticating reverse proxy (the app has no built-in auth).
- [ ] Terminate TLS at the proxy and set `OPENFPA_ENABLE_HSTS=true`.
- [ ] Set `OPENFPA_TRUSTED_HOSTS` and `OPENFPA_CORS_ORIGINS` to your real hostnames.
- [ ] Tune `OPENFPA_RATE_LIMIT_PER_MINUTE` / `OPENFPA_MAX_REQUEST_BYTES` for your workload.
- [ ] Keep dependencies current (merge Dependabot PRs); watch the Security tab for CodeQL alerts.
- [ ] Restrict filesystem permissions on the SQLite database file.

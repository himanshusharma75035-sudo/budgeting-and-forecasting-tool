# Contributing

Thanks for your interest in improving this project! Contributions of all kinds are welcome — bug
reports, fixes, features, docs, and tests.

- **Maintainer:** Himanshu Sharma — <Himanshusharma75035@gmail.com>
- Please also read the [Code of Conduct](CODE_OF_CONDUCT.md) and the [Security Policy](SECURITY.md).

> ⚠️ **Never commit confidential or production financial data.** Use only synthetic/sample data
> (the seed script generates invented numbers). Secret scanning runs on every push.

## Ways to contribute

- **Found a bug?** Open a [bug report](https://github.com/himanshusharma75035-sudo/budgeting-and-forecasting-tool/issues/new/choose).
- **Have an idea?** Open a feature request.
- **Security issue?** Report it **privately** — see [SECURITY.md](SECURITY.md). Do not open a public issue.
- **Question?** Email <Himanshusharma75035@gmail.com>.

## Development setup

### Backend (FastAPI + SQLite)

```
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/seed.py
uvicorn app.main:app --reload --reload-dir app
```

Add the heavy statistical models with `pip install -e ".[dev,forecasting]"`.

### Frontend (React + Vite)

```
cd frontend
npm install
npm run dev
```

## Before you open a pull request

Run the same gates CI runs — PRs must be green.

**Backend**

```
cd backend
ruff check .
mypy app
pytest -q
```

**Frontend**

```
cd frontend
npm run typecheck
npm run lint
npm run test -- --run
npm run build
```

## Coding standards

- **Python:** `ruff` (lint + format) and `mypy` (typed; keep it clean). Money lives in integer minor
  units at the persistence boundary and `Decimal` in domain math — never `float`.
- **TypeScript:** strict mode; `eslint` + `prettier`. Use the shared formatters in
  `frontend/src/lib/format.ts` for currency/number display (Indian `en-IN` / ₹ conventions).
- **Tests:** add or update tests with every behavioral change. The worked examples in
  `docs/DESIGN.md` are the canonical fixtures for the financial logic.
- **Dependencies:** must be OSI-permissive (MIT / BSD / Apache-2.0 / ISC / MPL-2.0). The CI license
  gate fails the build on GPL/AGPL/SSPL/BSL/commercial licenses.

## Commits & pull requests

1. Fork and create a topic branch (`feat/...`, `fix/...`, `docs/...`).
2. Keep commits focused; write clear messages (imperative mood, e.g. "Add rolling-window ABB").
3. **Sign off** your commits (Developer Certificate of Origin):

   ```
   git commit -s -m "Your message"
   ```

   This adds a `Signed-off-by:` trailer certifying you have the right to submit the contribution
   under the project's MIT license.
4. Fill out the PR template and make sure all checks pass.
5. Be responsive to review feedback. Squash-merge is the default.

## License

By contributing, you agree that your contributions are licensed under the project's
[MIT License](LICENSE).

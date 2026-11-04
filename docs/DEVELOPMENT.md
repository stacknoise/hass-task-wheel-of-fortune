# Development

For contributors. [← Back to the README](../README.md)

Short version of the rules (details in KONZEPT.md §10):

- Backend: Python 3.13, Home Assistant custom integration; frontend: Lit 3 + TypeScript (strict), built with Vite
- Factory + Strategy + Repository: factories create rule strategies by registration without `if/elif` chains, storage only through repositories
- Clear layers (constants, entry point, interfaces, application, domain, infrastructure); the import direction is checked in CI
- No literals in the code, everything through constants; no duplicated code
- Security and performance first: validated inputs, configuration for administrators only, drawing only in the backend
- **Every code change is logged in [docs/CODE_DOKU.md](CODE_DOKU.md)**; the README is updated for visible changes

Commands:

```bash
# Backend (Python 3.13)
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
ruff check . && ruff format --check . && mypy && lint-imports && pytest

# Frontend (Node 22)
cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build && npm run bundle-budget

# End-to-end test (Playwright against a real, fresh HA instance with the integration; runs in CI as job `e2e`)
# Procedure: build the frontend, start `hass -c <config>` with `custom_components/task_wheel`, then
cd e2e && npm ci && npx playwright install chromium && HA_URL=http://localhost:8123 npx playwright test

# Regenerate the README screenshots (a fresh HA instance with the integration is running on :8123, English UI)
cd e2e && npm ci && HA_LANGUAGE=en SHOT_DIR=../docs/screenshots npm run screenshots

# Generate the code documentation (code-doku/index.html) and check thresholds
python3 docs/code-doku/generate.py --check
```

## Continuous integration

Pull requests and `main` run the jobs `hassfest`, `HACS validation`, `lint`, `typecheck`, `architecture`
(import direction, duplicates), `test-backend`, `test-frontend`, `build-frontend` (incl. bundle budget), `e2e` (Playwright against a real Home Assistant), `audit` and
`docs-check` (code, tools, e2e tests or workflows changed ⇒ `docs/CODE_DOKU.md` has a new change-log row; versions and the module table are consistent) and `code-doku` (the generator runs, thresholds from `docs/CODE_DOKU.md` §1.1 are met). A weekly `Audit` workflow checks the npm and pip dependencies for new advisories. Dependabot keeps pip, npm and GitHub Actions up to date.

Please report security vulnerabilities confidentially, see [SECURITY.md](../SECURITY.md).


## Releasing (for developers)

1. Raise the version in all places, via pull request to `main`: `custom_components/task_wheel/manifest.json`,
   `pyproject.toml`, `frontend/package.json` and `e2e/package.json` (each with its `package-lock.json`, root package
   and top-level `version`), and the "Code-Version" in the header of `docs/CODE_DOKU.md`; add an entry to `CHANGELOG.md`
   and to the change log of `docs/CODE_DOKU.md`. `python3 tools/check_docs_consistency.py` (CI job `docs-check`) fails if
   the versions differ.
2. Wait until the CI of the merge commit on `main` is green, then set the tag: `git tag v0.4.0 && git push origin v0.4.0`,
   or enter the tag on GitHub under *Actions → Release → Run workflow* (the workflow creates it at the state of `main`)
3. The `Release` workflow checks that the tag and the manifest version match, that the commit is part of `main` and that
   all CI jobs are green on it (it waits for running jobs), builds the panel without write permissions on
   the repository and attaches `task_wheel.zip` and its checksum `SHA256SUMS` to the new GitHub release (see `hacs.json`:
   `zip_release`). Tags with a suffix (`v0.4.0-beta.1`) are published as a pre-release.

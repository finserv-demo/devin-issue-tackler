# Testing the Dashboard App

## Prerequisites

- Python 3.11+ with `pip install -e ".[dev]"` run from repo root
- Node.js with `npm install` run from `dashboard/` directory
- `GITHUB_TOKEN` env var: a GitHub PAT with read access to issues and PRs on the target repo (stored as org secret `GITHUB_TOKEN`)
- `TARGET_REPO` env var: the GitHub repo to query (e.g. `finserv-demo/finserv`)

## Starting the App

### Backend (port 8000)
```bash
cd /home/ubuntu/repos/devin-issue-tackler
GITHUB_TOKEN="${GITHUB_TOKEN}" TARGET_REPO="finserv-demo/finserv" uvicorn orchestrator.main:app --reload --port 8000
```

Note: `fastapi dev` requires `fastapi[standard]` which is not installed. Use `uvicorn` directly.

### Frontend (port 5173)
```bash
cd /home/ubuntu/repos/devin-issue-tackler/dashboard
npm run dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## Testing Flow

1. Navigate to http://localhost:5173
2. Verify layout: "Issue Tackler" header, 7d/30d toggle, 3 metric cards, 2 list sections
3. With valid GITHUB_TOKEN: metric cards show real data, issue lists populate
4. Without GITHUB_TOKEN: red error banners appear ("Failed to load metrics", "Failed to load issues")
5. Toggle between 7d/30d: first metric card label changes between "this week" and "this month"
6. Click an issue row: opens the GitHub issue in a new tab

## Backend API Endpoints

- `GET /api/dashboard/metrics?days=7` — hero metrics (days must be exactly 7 or 30)
- `GET /api/dashboard/lists` — needs-attention and in-progress issue lists

## Lint & Test Commands

```bash
# Python
cd /home/ubuntu/repos/devin-issue-tackler && ruff check .
cd /home/ubuntu/repos/devin-issue-tackler && pytest

# Frontend
cd /home/ubuntu/repos/devin-issue-tackler/dashboard && npx eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0
cd /home/ubuntu/repos/devin-issue-tackler/dashboard && npx vitest run
```

# Job Match Portal

A shared web app for you and a friend to upload resumes, fetch jobs from external APIs, and highlight **close matches** on a shared dashboard.

## Features

- JWT auth (max 2 users)
- Resume upload (PDF/DOCX) with skill/title extraction
- Job fetch from Adzuna (+ optional JSearch fallback)
- Match scoring: Close (≥75%), Good (55–74%), Weak (<55%)
- Dashboard, job board with filters, save/applied tracking
- Toggle between your matches and your friend's matches

## Quick start (local)

```bash
# Backend only (serves API; frontend needs build or Docker)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit with your keys

cd backend
python seed.py         # creates george@example.com / friend@example.com (changeme123)
uvicorn main:app --reload --port 8000
```

With frontend (requires Node.js):

```bash
cd frontend && npm install && npm run build
# API serves static files from frontend/dist
```

Or use the helper script:

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

Default logins (change after first use):
- `george@example.com` / `changeme123`
- `friend@example.com` / `changeme123`

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (SQLite for local dev) |
| `JWT_SECRET` | Secret for signing tokens |
| `ADZUNA_APP_ID` | Adzuna API app ID |
| `ADZUNA_APP_KEY` | Adzuna API key |
| `ADZUNA_COUNTRY` | Country code (default: `in`) |
| `RAPIDAPI_KEY` | Optional JSearch fallback |
| `DEFAULT_LOCATION` | Default city (default: `Bangalore`) |
| `RUN_SEED` | Set to `1` on first Railway deploy to seed users |

## Deploy to Railway

> **Note:** Your Railway trial has expired. Upgrade at [railway.app](https://railway.app) to create new projects, or use the Render alternative below.

1. Push this repo to GitHub
2. Create a new Railway project → Deploy from GitHub repo
3. Add **PostgreSQL** plugin (Railway sets `DATABASE_URL` automatically)
4. Set environment variables: `JWT_SECRET`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
5. Set `RUN_SEED=1` for the first deploy, then remove it
6. Railway builds via Dockerfile and exposes an HTTPS URL — share with your friend

Or use the CLI (after upgrading your plan):

```bash
railway login
railway init --name job-match-portal
railway add --database postgres
railway variables set JWT_SECRET=$(openssl rand -hex 32)
railway variables set ADZUNA_APP_ID=your_id ADZUNA_APP_KEY=your_key RUN_SEED=1
railway up
railway domain
```

## Deploy to Render (free alternative)

1. Push this repo to GitHub or GitLab
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your repo — Render reads `render.yaml` and provisions web + Postgres
4. Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in the dashboard
5. After first deploy, remove `RUN_SEED` or set it to `0`

## API endpoints

- `POST /api/auth/login` — Login
- `POST /api/auth/register` — Register (disabled after 2 users)
- `POST /api/resumes/upload` — Upload resume
- `GET /api/resumes/me` — Get parsed resume
- `POST /api/jobs/refresh` — Fetch jobs + run matcher
- `GET /api/jobs` — List jobs with filters (`match`, `user_id`, `saved`, `applied`)
- `PATCH /api/jobs/{id}/status` — Save/applied/notes
- `GET /api/dashboard` — Dashboard stats
- `PUT /api/profile` — Update search location/keywords

## Project structure

```
job-portal/
├── backend/          # FastAPI app
├── frontend/         # React + Vite + Tailwind
├── scripts/          # start.sh, seed helpers
├── Dockerfile
├── railway.toml
└── requirements.txt
```

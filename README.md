# Job Match Portal

A shared web app for you and a friend to upload resumes, fetch jobs from external APIs, and highlight **close matches** on a shared dashboard.

## Features

- JWT auth (max 3 users)
- Resume upload (PDF/DOCX) with skill/title extraction
- Job fetch from Adzuna (+ optional JSearch + Apify LinkedIn)
- Multi-city search: Dubai, Kochi, Bangalore, Abu Dhabi, Singapore
- Match scoring: Close (≥75%), Good (55–74%), Weak (<55%)
- Dashboard, job board with filters, save/applied tracking
- Toggle between your matches and your friend's matches

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit with your keys

cd backend
python seed.py
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
- `gkolath85@hotmail.com` / `changeme123`
- `friend@example.com` / `changeme123`
- `emailshameela@gmail.com` / `changeme123`

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (SQLite for local dev) |
| `JWT_SECRET` | Secret for signing tokens |
| `ADZUNA_APP_ID` | Adzuna API app ID |
| `ADZUNA_APP_KEY` | Adzuna API key |
| `ADZUNA_COUNTRY` | Default country code (default: `in`) |
| `RAPIDAPI_KEY` | Optional JSearch fallback |
| `APIFY_TOKEN` | Apify API token for LinkedIn job scrape ([create one](https://console.apify.com/settings/integrations)) |
| `APIFY_ENABLED` | Set `false` to disable Apify scrape |
| `APIFY_MAX_ITEMS` | Max LinkedIn jobs per title×location (default `25`) |
| `DEFAULT_LOCATION` | Default city (default: `Bangalore`) |
| `RUN_SEED` | Set to `1` on first Render deploy to seed users |

## Deploy to Render

Render is the recommended host — free tier includes a web service + PostgreSQL.

### Option A: Blueprint (easiest)

1. Push this repo to **GitHub** or **GitLab**
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your repo — Render reads `render.yaml` and provisions:
   - Web service (Docker build)
   - PostgreSQL database
4. When prompted, set these secrets in the dashboard:
   - `ADZUNA_APP_ID`
   - `ADZUNA_APP_KEY`
   - `APIFY_TOKEN` (recommended — LinkedIn jobs via Apify)
   - `RAPIDAPI_KEY` (optional)
5. Deploy — Render gives you an `https://*.onrender.com` URL to share
6. After first successful deploy, set `RUN_SEED` to `0` (or remove it)

### Option B: Manual setup

1. **New → PostgreSQL** (free plan) — note the internal connection string
2. **New → Web Service** → connect repo → **Docker** runtime
3. Set environment variables:
   - `DATABASE_URL` — from Postgres service
   - `JWT_SECRET` — generate with `openssl rand -hex 32`
   - `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
   - `RUN_SEED=1` (first deploy only)
4. Health check path: `/api/health`

See `scripts/deploy-render.sh` for a step-by-step checklist.

### Render free tier notes

- Web service spins down after 15 min idle (~30s cold start on next visit)
- Free Postgres expires after 30 days (upgrade to keep data)
- Uploaded resumes live on the container filesystem — they reset on redeploy unless you add a persistent disk

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
├── scripts/          # start.sh, deploy-render.sh
├── Dockerfile
├── render.yaml       # Render Blueprint
└── requirements.txt
```

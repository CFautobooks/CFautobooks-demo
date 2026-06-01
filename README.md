# Horse Racing Analytics MVP

A live-data-first horse racing analytics MVP with:

- FastAPI backend
- PostgreSQL/Supabase-compatible schema
- Next.js frontend
- JSON auth with server-side subscription status
- Stripe Checkout and webhook plumbing
- Generic racing form and odds provider adapters
- Web-sourced scraping provider adapters with rate limiting and scrape status logs
- Scheduled sync and scraping job entrypoints
- Deterministic ratings for fair odds, expected value, confidence, and best-bets ranking

The app does not fabricate tips. If racing form or odds providers are not configured, dashboards show `No live provider connected` and no fake race data is generated.

## Run locally with one command

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

The Docker Compose file includes safe local-development defaults. For real credentials, set environment variables in your shell or create `backend/.env` from `backend/.env.example`.

## Local backend without Docker

```bash
python3 -m pip install -r requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env and set DATABASE_URL, SECRET_KEY, and ADMIN_API_TOKEN
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## Local frontend without Docker

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Required environment variables

Backend:

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/horseracing
SECRET_KEY=replace-with-at-least-32-random-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
ADMIN_API_TOKEN=replace-with-admin-only-token
SYNC_LOOKAHEAD_DAYS=1
HTTP_TIMEOUT_SECONDS=15

RACING_FORM_PROVIDER=generic_http
RACING_FORM_API_BASE_URL=
RACING_FORM_API_KEY=
RACING_FORM_API_KEY_HEADER=Authorization
RACING_FORM_MEETINGS_PATH=/racecards
RACING_FORM_RACECARD_PATH=/racecards/{meeting_id}
RACING_FORM_RESULTS_PATH=/results

ODDS_PROVIDER=generic_http
ODDS_API_BASE_URL=
ODDS_API_KEY=
ODDS_API_KEY_HEADER=Authorization
ODDS_MARKETS_PATH=/odds

SCRAPING_RATE_LIMIT_SECONDS=3
SCRAPING_HTTP_TIMEOUT_SECONDS=20
SCRAPING_USER_AGENT=HorseRacingAnalyticsBot/0.1
TAB_SCRAPE_URL=
SPORTSBET_SCRAPE_URL=
RACING_COM_SCRAPE_URL=
PUNTERS_SCRAPE_URL=

STRIPE_API_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=
```

Frontend:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Do not expose `ADMIN_API_TOKEN` through a `NEXT_PUBLIC_` variable. The admin sync page asks an admin to enter the token in the browser.

## Pages built

- `/login`
- `/register`
- `/daily`
- `/best-bets`
- `/runners/[id]`
- `/results`
- `/admin/sync`
- `/pricing`

## API endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /racing/provider-status`
- `GET /racing/dashboard/daily`
- `GET /racing/dashboard/best-bets` - requires active subscription
- `GET /racing/runners/{runner_id}`
- `GET /racing/results/tracker`
- `GET /racing/admin/sync-status` - requires `X-Admin-Token`
- `POST /racing/admin/sync` - requires `X-Admin-Token`
- `POST /racing/admin/scrape` - triggers web-sourced scraping; requires `X-Admin-Token`
- `POST /billing/create-checkout-session`
- `POST /billing/webhook`
- `GET /billing/subscription`

## Scheduled sync jobs

Run from cron, a hosted scheduler, or manually:

```bash
python3 -m backend.jobs.sync_racing_data --sync racecards --date 2026-06-01
python3 -m backend.jobs.sync_racing_data --sync odds
python3 -m backend.jobs.sync_racing_data --sync results --date 2026-06-01
python3 -m backend.jobs.sync_racing_data --sync all --date 2026-06-01
python3 -m backend.jobs.sync_racing_data --sync scraping --date 2026-06-01
python3 -m backend.jobs.scrape_racing_data --source all --date 2026-06-01
```

## Web-sourced data collection

Scraper modules live in `backend/services/racing/scrapers/`:

- `base_scraper.py`
- `tab_scraper.py`
- `sportsbet_scraper.py`
- `racing_com_scraper.py`
- `punters_scraper.py`

Scraped records are written to the same normalized database tables first and labelled as `web-sourced data` via `data_source='web_sourced'` before any model rating uses them. The statistical model only reads structured runners, weights, barriers, past form, and odds snapshots from the database; it does not rate from raw webpage text.

Scraping includes rate limiting, missing-field quality checks, duplicate prevention through provider/external IDs, runner matching by external ID and normalized horse name, and odds update history via `odds_snapshots`. If a source URL is missing, blocked, or unreliable, status logs show `unavailable` or `failed` and dashboards show `No live provider connected`, `Data source unavailable`, or `Insufficient data` rather than fake results.

Important: check each source's robots.txt, terms of use, and licensing before using any scraper commercially. Prefer official APIs where available.

## Provider integration TODO

Generic provider hooks are in place, but live data requires actual provider documentation and API access. See:

- `backend/services/racing/providers.py`
- `backend/services/racing/provider_adapters/provider_todo.py`

Needed from the racing data provider:

1. Authentication scheme and rate limits.
2. Racecard endpoint shape for meetings, races, runners, jockeys, trainers, barriers, weights, past form, track conditions, and scratchings.
3. Results endpoint shape for positions, margins, starting prices, race IDs, and runner IDs.
4. Stable external IDs for meetings, races, runners, jockeys, and trainers.

Needed from the odds provider:

1. Authentication scheme and rate limits.
2. Market endpoint shape for bookmaker, market type, decimal odds, race ID, runner ID/name, timestamp, and market movement.
3. Rules for matching odds runners to racing form runners.

## Stripe TODO

Stripe Checkout and webhook routes are present. To make paid access live, set:

- `STRIPE_API_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_WEBHOOK_SECRET`

Then configure the webhook endpoint in Stripe as `/billing/webhook`.

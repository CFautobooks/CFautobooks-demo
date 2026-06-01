# CF AutoBooks Full Demo (Front-end + Back-end + OCR)

## Overview

This directory contains a fully integrated demo of **CF AutoBooks**, including:
- **frontend/**: Static website (HTML/CSS/JS) for the products (DIY, Carmichael, White-Label).
- **backend/**: FastAPI backend scaffold with user authentication, invoice models, and Stripe placeholders.
- **OCR service** via Docker image (FastAPI + pytesseract).
- **docker-compose.yml** to stand up PostgreSQL, OCR service, API, and a static Nginx front end.

### Directory Structure

```
CF_AutoBooks_Full_Demo/
  frontend/          # Static front-end files (CF AutoBooks Modern v9)
  backend/           # FastAPI backend scaffold (with Dockerfile)
  docker-compose.yml # Orchestrates db, ocr-service, api, frontend
  README.md          # This file
```

## Prerequisites

- Docker and Docker Compose installed on your machine.
- (Optional) On Linux/Mac: `sudo` or ensure current user can run Docker.

## Setup Instructions

1. **Copy & configure environment variables**  
   ```bash
   cd CF_AutoBooks_Full_Demo/backend
   cp config/.env.example config/.env
   ```
   Edit `config/.env` and set values:
   ```
   DATABASE_URL=postgresql://postgres:password@db:5432/cfautobooks
   SECRET_KEY=YOUR_JWT_SECRET
   STRIPE_API_KEY=sk_test_placeholder
   STRIPE_WEBHOOK_SECRET=whsec_placeholder
   OCR_SERVICE_URL=http://ocr-service:8000/api/ocr
   ```
   For a local demo, placeholders are fine (except `DATABASE_URL` should match docker-compose).

2. **Launch all services**  
   From the root directory:
   ```bash
   docker-compose up --build
   ```
   This will start:
   - **Postgres** on port 5432
   - **OCR service** on port 8001 (`http://localhost:8001/api/ocr`)
   - **API backend** on port 8000 (`http://localhost:8000`)
   - **Frontend** on port 80 (`http://localhost/`)

3. **Access the demo**  
   - Open your browser to [http://localhost](http://localhost). You’ll see the CF AutoBooks front end.
   - Navigate “Products → DIY AutoBooks”.
     - If not logged in, you will be prompted to log in (even though login isn’t functional until you register).
     - To simulate a logged in user, open browser console and run:
       ```
       localStorage.setItem("authToken", "demo_token");
       ```
   - Upload a test invoice image (PNG or JPEG) via “Upload & Process”. The OCR service will process and return line items to the table.

4. **Test API endpoints**  
   - **Register**:  
     ```bash
     curl -X POST "http://localhost:8000/auth/register"        -H "Content-Type: application/json"        -d '{"email":"test@example.com","password":"mypassword","plan":"DIY"}'
     ```
   - **Login**:
     ```bash
     curl -X POST "http://localhost:8000/auth/login"        -H "Content-Type: application/x-www-form-urlencoded"        -d "username=test@example.com&password=mypassword"
     ```
     This returns a JSON with a `access_token`. Store it for authenticated requests.

   - **View invoices** (none yet):
     ```bash
     curl -X GET "http://localhost:8000/dashboard/"        -H "Authorization: Bearer <access_token>"
     ```

   - **Admin view** (use a user with plan=`CARMICHAEL`):
     ```bash
     curl -X GET "http://localhost:8000/admin/invoices"        -H "Authorization: Bearer <access_token>"
     ```

## Next Steps

- Replace placeholder Stripe keys with real ones, and implement subscription logic.
- Hook up `/dashboard/upload` to forward invoice files to the OCR service and store results in the database.
- Create “review invoice” endpoints and UI for handling `requires_review` items.
- Implement Xero/MYOB integration for pushing finalized transactions.

This setup gives you a fully integrated local demo. Visit `http://localhost/` to explore.
## Horse Racing Analytics Foundation

This branch adds the first live-data foundation for a horse racing analytics product. Manual CSV upload is not part of the primary flow. Racing form and odds data are pulled from configured external APIs using environment variables for credentials.

### Secure environment variables

Copy `backend/.env.example` to `backend/.env` for local development and set real provider credentials outside source control:

```bash
DATABASE_URL=postgresql://...supabase.co:5432/postgres
RACING_FORM_API_BASE_URL=https://your-racing-form-provider.example
RACING_FORM_API_KEY=...
ODDS_API_BASE_URL=https://your-odds-provider.example
ODDS_API_KEY=...
ADMIN_API_TOKEN=...
```

### Provider layer

The default adapters are generic HTTP providers configured by URL/path environment variables. To swap providers later, add a provider adapter in `backend/services/racing/providers.py` that implements the `RacingFormProvider` or `OddsProvider` protocol and select it with `RACING_FORM_PROVIDER` or `ODDS_PROVIDER`.

### Database schema

Supabase/PostgreSQL schema is in `supabase/migrations/0001_racing_core.sql` and includes:

- race meetings, races, runners, jockeys, trainers
- odds snapshots and market movement payloads
- results
- model ratings with fair odds, expected value, confidence, transparent calculation inputs, and insufficient-data statuses
- API sync run monitoring and missing-field logging

### Scheduled API sync

Run from cron or a hosted scheduler:

```bash
python3 -m backend.jobs.sync_racing_data --sync all --date $(date +%F)
python3 -m backend.jobs.sync_racing_data --sync odds
python3 -m backend.jobs.sync_racing_data --sync results --date $(date +%F)
```

### API endpoints

- `GET /racing/dashboard/daily` - daily race dashboard data
- `GET /racing/dashboard/best-bets` - deterministic best bets sorted by expected value
- `GET /racing/calculators/fair-odds?probability=0.25`
- `GET /racing/calculators/expected-value?probability=0.25&decimal_odds=5.0`
- `GET /racing/results/tracker`
- `GET /racing/admin/sync-status` - admin sync monitoring
- `POST /racing/admin/sync?sync_type=all` - admin sync trigger

The model does not choose tips randomly. Ratings are calculated from API-supplied past form, barrier, weight, and market odds. If required fields are unavailable, the runner/rating is marked `insufficient data` and excluded from best-bet output. OpenAI should only be used later to explain an already calculated rating, not to select runners.

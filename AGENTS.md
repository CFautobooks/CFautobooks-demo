# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is

Multi-product Python monorepo (no npm): **CF AutoBooks** static site (`frontend/`), **Horse Racing Analytics** FastAPI API (`backend/`), optional **OCR** microservice (`Step1_OCR_Service/`). See `README.md` for product details and endpoint list.

### Dependency install (automatic)

The VM update script runs `pip install -r requirements.txt` and pins `bcrypt==4.2.1`. Without the bcrypt pin, `passlib` + bcrypt 5.x fails on `/auth/register` with `ValueError: password cannot be longer than 72 bytes` during passlib’s backend self-test. Restart the API process after changing bcrypt.

Add `export PATH="$HOME/.local/bin:$PATH"` in your shell (pip installs `uvicorn` under `~/.local/bin`).

### Environment files

Copy `backend/.env.example` to `backend/.env`. When starting the API from repo root (`/workspace`), also copy or symlink to `/workspace/.env` — `backend/core/config.py` loads `.env` from the **current working directory**, not `backend/` automatically.

For quickest local API dev without Postgres, use SQLite (default in settings): `DATABASE_URL=sqlite:///./local-dev.db`. Set `SECRET_KEY` and `ADMIN_API_TOKEN` for auth and `/racing/admin/*` routes.

### Services (local dev without Docker)

Docker is optional; this VM often has no Docker daemon. Prefer:

| Service | Command (from repo root unless noted) | URL |
|---------|----------------------------------------|-----|
| **API** | `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` | http://127.0.0.1:8000 (Swagger: `/docs`) |
| **Frontend** | `cd frontend && python3 -m http.server 8080 --bind 0.0.0.0` | http://127.0.0.1:8080/ |
| **OCR** (optional) | `cd Step1_OCR_Service && uvicorn main:app --port 8001` — requires system `tesseract-ocr` | http://127.0.0.1:8001/api/ocr |

Use **tmux** for long-running dev servers (see Cloud Agent shell rules).

`docker-compose.yml` references `./backend/Dockerfile`, which is **missing**; the working API image is built from the repo-root `Dockerfile`.

### Lint / tests

No pytest, ruff, or pre-commit in this repo. Reasonable checks: `python3 -m compileall backend` and manual `curl` against `/docs` and `/racing/calculators/*`.

### Racing sync / external APIs

Live race data needs real `RACING_FORM_*` and `ODDS_*` credentials in `.env`. Sync job: `python3 -m backend.jobs.sync_racing_data --sync all --date $(date +%F)` from `/workspace` with deps installed.

### Auth smoke test

```bash
curl -X POST "http://127.0.0.1:8000/auth/register?email=user@example.com&password=secret&plan=DIY"
curl -X POST "http://127.0.0.1:8000/auth/login?email=user@example.com&password=secret"
```

Register/login use **query parameters**, not JSON bodies.

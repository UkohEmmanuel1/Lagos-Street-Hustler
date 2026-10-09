# Lagos Street Hustler

A Lagos-inspired browser 3D open-world game prototype. Current scope includes a 3D exploration scene, missions, an in-game phone UI, account registration/login, and authenticated real-time text chat through the FastAPI service.

## Repository structure
- apps/web: Next.js, React, React Three Fiber client.
- apps/api/app/main.py: FastAPI REST/WebSocket API.
- Dockerfile: Render API container.
- render.yaml: Render blueprint for web, API, PostgreSQL and Redis resource.
- docs/IMPLEMENTATION_PLAN.md: scope, architecture, limitations and phased delivery.

## Local development

API (Windows CMD):
```bat
cd apps\api
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
set SQLITE_PATH=%TEMP%\lagos-street-hustler.db
set JWT_SECRET_KEY=local-development-secret-change-this-123456
uvicorn app.main:app --reload --port 8000
```

Web (second terminal):
```bat
cd apps\web
npm install
set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```
Open the URL printed by Next.js. Register/login in the phone to connect to the API.

## Deployment configuration
Render blueprint reads DATABASE_URL from the managed PostgreSQL service and generates JWT_SECRET_KEY. Verify the actual Render service URLs and set CORS_ORIGINS to the exact frontend origin before deploying. For Vercel, set the project root to apps/web and configure NEXT_PUBLIC_API_URL to the public API URL.

## Status honesty
The phone supports authenticated account flows, player contacts, GPS coordinates and text chat when the API is reachable. Voice is signalling-only, not yet a functional audio call. Bank/wallet, social feed, ride-hailing and jobs/business are UI placeholders; the displayed money balance is not server-authoritative. Realtime presence is single-process and must not be scaled horizontally until Redis pub/sub is wired. See the implementation plan for production gaps.

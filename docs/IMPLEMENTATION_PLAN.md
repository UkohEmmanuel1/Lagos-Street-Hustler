# Lagos Street Hustler — implementation plan

## Product scope selected
- Open-world multiplayer as the target session model.
- In-game phone: Map/GPS, Bank & Wallet, Contacts, Social Feed, Ride-hailing, Jobs & Business.
- Chat: private messages, nearby/world chat, group chat, and voice chat.
- Keep the game playable as a browser 3D prototype while backend capabilities are introduced incrementally.

## Implemented in this change
- API account registration/login using PBKDF2 password hashes and signed JWT bearer tokens.
- Protected player profile, player directory, app catalogue, message history, and mission endpoints.
- WebSocket /ws?token=... for online presence, movement updates, nearby chat, private messages, group membership/chat, and WebRTC signalling relay.
- In-game phone UI, account forms, contacts list, GPS coordinates, and text chat panels.
- PostgreSQL support via DATABASE_URL, SQLite local fallback, Render database/JWT/CORS environment configuration, and initial API tests/CI updates.

## Important limitations
- Current WebSocket presence and group membership are process-local. Deploy one API instance only until Redis-backed presence/pub-sub and cross-instance fanout are implemented. Redis is provisioned in the blueprint but is not yet wired into live messaging.
- Voice chat is not yet a working audio call. The API can relay signalling payloads, but browser WebRTC offer/answer/ICE flow, microphone permission UX, TURN service, call lifecycle and abuse controls still need implementation.
- Bank & wallet balance is still local demo state. Do not accept real money or use it for purchases until a server-authoritative ledger, transaction idempotency, audit history, rate limits and reconciliation are implemented.
- Social feed, ride-hailing and jobs/business screens are currently placeholders. They need persistent domain models, moderation/safety, business rules and endpoint tests.
- Mission rewards are not persisted as authoritative balances yet.
- WebSocket uses a bearer token in its query string because browser WebSocket APIs do not support custom Authorization headers. Use short-lived WebSocket tickets and log redaction before a public production launch.
- Production must set JWT_SECRET_KEY to a stable secret and CORS_ORIGINS to the exact frontend origin. Render blueprint assumes named *.onrender.com service URLs; adjust if service names or custom domains differ.

## Architecture target
- Next.js + React Three Fiber client.
- FastAPI REST + WebSocket gateway.
- PostgreSQL for durable accounts, messages, profiles, wallet ledger, jobs and social content.
- Redis pub/sub and presence for multi-instance realtime fanout.
- WebRTC for peer audio; TURN relay for users behind restrictive NATs.
- Observability: structured logs with secrets redacted, health/readiness probes, metrics, abuse reporting, chat rate limits, block/mute tools, and account recovery.

## Suggested delivery sequence
1. Foundation (current): authenticated accounts, persisted text messages, one-instance realtime chat, phone shell, CI tests.
2. Hardening: short-lived WebSocket tickets, message rate limits, blocking/reporting, moderation, pagination, database migrations and test coverage.
3. True open-world sessions: authoritative movement validation, Redis-backed presence/fanout, rooms/shards and reconnect/resume.
4. Voice: WebRTC peer negotiation, ICE candidates, microphone permission UX, TURN configuration, mute/end-call and consent.
5. Phone services: server-authoritative wallet ledger, social feed, rides, jobs and business data models.
6. Launch readiness: load tests, vulnerability review, backup/restore drill, error monitoring, cost controls and verified deployment.

## Local verification
API: from apps/api, install requirements.txt and requirements-dev.txt, set SQLITE_PATH and JWT_SECRET_KEY, then run pytest -q.
Web: from apps/web, run npm install, npm run typecheck and npm run build.

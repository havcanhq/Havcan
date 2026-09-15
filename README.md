# HAVCAN

Creative work, handled from idea to delivery.

## Phase 1 foundation

Phase 1 keeps the existing single-file HAVCAN UI intact and adds the seams
needed for a production application:

- `index.html` remains the current client experience and is not rebuilt.
- `frontend/api-client.js` provides an opt-in JSON API client at `/api`.
- `frontend/app-state.js` provides shared loading and error state for future
  API-backed screens without changing current mock interactions.
- `backend/app/` contains the FastAPI application, environment configuration,
  and a lazy MongoDB adapter boundary.
- `GET /api/health` is the initial liveness/readiness endpoint.
- `manifest.webmanifest`, `service-worker.js`, and `assets/icons/` provide the
  PWA shell foundation.

The architecture is intentionally domain-neutral. Future modules can be added
behind the same boundaries for client authentication, admin, professionals,
services, projects/orders, files, real-time chat, notifications, payments, and
reviews. Those business features are not part of Phase 1.

## Local development

### Backend

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and adjust the MongoDB values when a local
   MongoDB instance is available.

3. Start the API:

   ```bash
   .venv/bin/python -m backend.app
   ```

4. Check the health endpoint:

   ```bash
   curl http://127.0.0.1:8000/api/health
   ```

MongoDB is optional for the Phase 1 health endpoint. When `MONGO_URI` is
unset, the response reports `database: "not_configured"` instead of failing
the API process.

### Existing UI and PWA

Serve the repository root over HTTP so service-worker registration is allowed:

```bash
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/index.html`. The current HAVCAN screens, branding,
navigation, search, project wizard, chat, and profile flows remain in
`index.html`. The service worker caches the local shell and deliberately does
not intercept cross-origin CDN assets.

### Tests

Run the API and static foundation tests from the repository root:

```bash
python3 -m pytest -q
```
# Deployment guide

> **Nothing has been deployed.** The configuration below is untested; no live URL exists. Verify each step.

## Option A: Docker Compose (local or a single VM)
```bash
cp .env.example .env            # optional: set JWT_SECRET, POSTGRES_PASSWORD, GEMINI_API_KEY
docker compose up --build       # UI http://localhost:5173, API http://localhost:8000/docs
```
The backend container runs `alembic upgrade head` before starting. Data persists in the `pgdata` and `appdata` volumes. Add `INSTALL_FULL=true EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 MATCHER=faiss` for semantic search (large image, about 1 GB RAM).

## Option B: Render (render.yaml)
1. Push the repository to GitHub; in Render choose *New -> Blueprint* and select it.
2. Set the `sync: false` variables: `CORS_ORIGINS` (frontend URL), `VITE_API_BASE_URL` (`https://<api-host>/api/v1`), optionally `GEMINI_API_KEY`.
3. After the first deploy open `https://<api-host>/api/v1/health` (should return `"status": "ok"`).

## Production checklist
- [ ] `APP_ENV=production`, `DEBUG=false` (the app refuses to start otherwise)
- [ ] `JWT_SECRET` >= 32 random characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- [ ] `DATABASE_URL` is managed PostgreSQL (`postgres://` URLs are normalised to the psycopg driver)
- [ ] `CORS_ORIGINS` is the exact frontend origin (no `*`)
- [ ] `VITE_API_BASE_URL` was set at frontend **build** time
- [ ] migrations applied (`alembic upgrade head`; automatic in the Docker image)
- [ ] persistent disk or object storage for `/data` if uploads, models, indexes and reports must survive redeploys
- [ ] HTTPS in front of both services; reverse-proxy forwarded-IP handling configured so rate limits see real client IPs
- [ ] `GEMINI_API_KEY` stored as a secret (optional; AI features are off without it)

## Resource notes
Lightweight demo mode (`EMBEDDING_MODEL=hashing`, `MATCHER=numpy`) fits small instances. PyTorch/sentence-transformers/FAISS need roughly 1-2 GB of RAM and several GB of disk, which free tiers do not provide. Free tiers also sleep when idle and may expire databases; the container filesystem is ephemeral. Background jobs run in-process, so a restart during parsing leaves that upload `PROCESSING` (delete is blocked; see KNOWN_LIMITATIONS). Run a single backend instance: rate limits and file storage are per instance.

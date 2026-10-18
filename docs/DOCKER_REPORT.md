# Docker Work — Short Report (Stage 1 runtime)

**Goal:** get a free, offline Endee vector-DB server running locally after the cloud
login turned out to be walled to workspace emails.

## What I did
1. **Located Docker** — Docker Desktop was installed but its CLI wasn't on the shell
   PATH; found it at `AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe`.
2. **Started the engine** — launched Docker Desktop; engine came up (Docker 29.8.2).
3. **Pulled the server image** — `endeeio/endee-server:latest` (543 MB, public, no login).
4. **Ran the container** on port 8080; confirmed `GET /api/v1/health` → `{"status":"ok"}`.
5. **Identified the API** — the server is the **v1 "index" API**, confirmed by dumping
   the route table from the binary (`/api/v1/index/create`, `/index/<n>/vector/insert`,
   `/index/<n>/search`, …). Matched it to SDK **endee==1.0.0**.
6. **Fixed a storage hang** — LMDB failed ("resource temporarily unavailable") on a
   Windows bind mount; switched to a Docker **named volume** (`endee_data`) → fixed.
7. **Fixed a client hang** — forced the `requests` HTTP backend (httpx/HTTP2 hung).
8. **Verified a full round-trip** — create index → upsert → query → delete, all OK.
9. **Ran the Stage 1 smoke test** — 50 real signatures ingested; one retrieved itself
   at rank 0. **PASS.**

## Result
A local, offline Endee server, reproducible from `docs/RUN_ENDEE.md`.

| Item | Value |
|---|---|
| Image | `endeeio/endee-server:latest` (543 MB) |
| Container | `endee-server` on `localhost:8080` |
| Storage | Docker named volume `endee_data` |
| API | v1 index API (`/api/v1`) |
| SDK | `endee==1.0.0`, `http_library="requests"` |
| Auth | none (unauthenticated local dev server) |

## Container management
```bash
docker stop endee-server     # pause
docker start endee-server    # resume (data persists in endee_data volume)
docker logs endee-server     # inspect
```

## Three gotchas to remember
1. Named volume, NOT a Windows bind mount (LMDB hangs over WSL2).
2. SDK `endee==1.0.0` (v1 index API) — newer SDKs 405 against this server.
3. `http_library="requests"` (httpx/HTTP2 path hangs).

# Running the local Endee server (free, offline, no login/license)

Prereq: Docker Desktop running.

```bash
docker pull endeeio/endee-server:latest
docker volume create endee_data
docker run -d --ulimit nofile=100000:100000 -p 8080:8080 \
  -v endee_data:/data --name endee-server --restart unless-stopped \
  endeeio/endee-server:latest
curl http://localhost:8080/api/v1/health      # {"status":"ok"}
```

GOTCHAS (learned the hard way):
- Use a Docker NAMED VOLUME (`-v endee_data:/data`), NOT a Windows bind mount
  (`-v ./endee-data:/data`). The server's LMDB store hangs / "resource temporarily
  unavailable" on a bind-mounted Windows folder over WSL2.
- SDK must be `endee==1.0.0` — it speaks the v1 index API (`create_index`,
  `get_index`, `idx.upsert`, `idx.query`) that THIS server exposes
  (`/api/v1/index/create`, `/index/<n>/vector/insert`, `/index/<n>/search`).
  SDK 1.2+/2.x use the cloud "collection" API and return 405 against this server.
- Init the client with `http_library="requests"` (httpx/http2 path can hang) and
  `set_base_url("http://localhost:8080/api/v1")`. No token needed (unauthenticated).

Stop / start:  docker stop endee-server  |  docker start endee-server

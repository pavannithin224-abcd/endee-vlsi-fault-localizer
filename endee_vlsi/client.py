"""Endee client helper — self-hosted Endee server (free Docker image, no login/license).

Server:  docker run -d --ulimit nofile=100000:100000 -p 8080:8080 \
           -v endee_data:/data --name endee-server endeeio/endee-server:latest
IMPORTANT: use a Docker NAMED VOLUME (endee_data), NOT a Windows bind mount — the
server's LMDB store hangs / fails ("resource temporarily unavailable") on a
bind-mounted Windows folder over WSL2.

SDK: endee==1.0.0 (v1 index API: create_index / get_index / upsert / query).
     Newer SDKs (1.2+, 2.x) speak the cloud "collection" API and do NOT match this
     server. Force http_library="requests" (the httpx/http2 path can hang).
"""
import os

BASE_URL = os.environ.get("ENDEE_BASE_URL", "http://localhost:8080/api/v1")
TOKEN = os.environ.get("ENDEE_TOKEN")  # usually None for the local dev server


def get_client():
    from endee import Endee
    c = Endee(token=TOKEN, http_library="requests")
    c.set_base_url(BASE_URL)
    return c

"""Endee client helper — loads token from the ENDEE_TOKEN env var (never hard-coded).

Set it first (PowerShell):   $env:ENDEE_TOKEN = "your-token"
or put it in a .env file (git-ignored) and this loads it automatically.
Get a token: sign in at https://app.endee.io -> create a database -> copy its token.
"""
import os


def _load_dotenv():
    here = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(here):
        for line in open(here, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_client():
    _load_dotenv()
    token = os.environ.get("ENDEE_TOKEN")
    if not token:
        raise SystemExit(
            "ENDEE_TOKEN not set. Get a token at https://app.endee.io, then either\n"
            "  set it:   $env:ENDEE_TOKEN = \"...\"   (PowerShell)\n"
            "  or add a line  ENDEE_TOKEN=...  to the .env file in the project root."
        )
    from endee import Endee
    return Endee(token=token)

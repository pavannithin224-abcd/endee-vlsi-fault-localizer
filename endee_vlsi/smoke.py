"""Stage 1 smoke test — prove the full Endee round-trip before building anything real.

Encoding here is deliberately MINIMAL (just the 256-bit signature hex -> 256-dim 0/1
vector). This is NOT the final capture encoding (that's Stage 2); it exists only to
confirm: create collection -> upsert -> search -> a signature retrieves ITSELF at rank 0.

Run:  .venv/Scripts/python.exe endee_vlsi/smoke.py
"""
import json, os, sys
from client import get_client

CIRCUIT = "picorv32_cpu"          # smallest (471 sigs)
COLLECTION = "smoke_picorv32"
N = 50                             # ingest a small slice for the smoke test
DIM = 256                          # a signature is 64 hex chars = 256 bits


def sig_to_vec(hexsig: str):
    """256-bit signature hex -> list of 256 floats in {0.0, 1.0}."""
    bits = bin(int(hexsig, 16))[2:].zfill(DIM)
    return [float(b) for b in bits]


def load_signatures():
    data = os.path.join(os.path.dirname(__file__), "..", "data", "signatures.jsonl")
    rows = []
    for line in open(data, encoding="utf-8"):
        r = json.loads(line)
        if r["circuit"] == CIRCUIT:
            rows.append(r)
            if len(rows) >= N:
                break
    return rows


def main():
    client = get_client()
    print("health:", client.health())

    # clean slate
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass

    client.create_collection(COLLECTION, fields=[
        {"name": "sig", "type": "vector",
         "params": {"dimension": DIM, "space_type": "l2", "precision": "float32"}},
    ])
    col = client.get_collection(COLLECTION)

    rows = load_signatures()
    objects = [{
        "id": f"{r['circuit']}:{i}",
        "meta": {"sites": r["sites"], "stuck": r["stuck"]},
        "filter": {"circuit": r["circuit"]},
        "fields": {"sig": sig_to_vec(r["signature"])},
    } for i, r in enumerate(rows)]
    col.upsert(objects)
    print(f"upserted {len(objects)} signatures")

    # query with signature #7's own vector -> it must come back at rank 0, distance ~0
    probe = rows[7]
    res = col.search(
        fields={"sig": {"query": sig_to_vec(probe["signature"]), "limit": 3}},
        filter=[{"circuit": {"$eq": CIRCUIT}}],
    )
    hits = res["results"]["sig"]
    print("top-3 hits:", [(h["id"], round(h["similarity"], 4)) for h in hits])

    top = hits[0]
    ok = top["id"] == f"{CIRCUIT}:7"
    print(f"\nEXIT CRITERION — signature retrieves itself at rank 0: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

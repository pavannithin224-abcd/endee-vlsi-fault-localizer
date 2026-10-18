"""Stage 1 smoke test — prove the full Endee round-trip on real signatures.

Encoding here is MINIMAL (256-bit signature hex -> 256-dim 0/1 vector). NOT the
final capture encoding (Stage 2); it only proves:
create_index -> upsert -> query -> a signature retrieves ITSELF at rank 0.

Run:  .venv/Scripts/python.exe endee_vlsi/smoke.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from client import get_client
from endee import Precision

CIRCUIT = "picorv32_cpu"      # smallest (471 sigs)
INDEX = "fl_smoke_picorv32"
N = 50
DIM = 256                     # a signature = 64 hex chars = 256 bits


def sig_to_vec(hexsig):
    bits = bin(int(hexsig, 16))[2:].zfill(DIM)
    return [float(b) for b in bits]


def load_signatures():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "signatures.jsonl")
    rows = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r["circuit"] == CIRCUIT:
            rows.append(r)
            if len(rows) >= N:
                break
    return rows


def main():
    c = get_client()
    try:
        c.delete_index(INDEX)
    except Exception:
        pass
    c.create_index(name=INDEX, dimension=DIM, space_type="l2", precision=Precision.INT8)
    idx = c.get_index(name=INDEX)

    rows = load_signatures()
    idx.upsert([{
        "id": f"{CIRCUIT}:{i}",
        "vector": sig_to_vec(r["signature"]),
        "meta": {"sites": r["sites"], "stuck": r["stuck"]},
        "filter": {"circuit": r["circuit"]},
    } for i, r in enumerate(rows)])
    print(f"upserted {len(rows)} signatures")

    probe = rows[7]
    hits = idx.query(vector=sig_to_vec(probe["signature"]), top_k=3,
                     filter=[{"circuit": {"$eq": CIRCUIT}}])
    print("top-3:", [(h["id"], round(h.get("distance", 0), 4)) for h in hits])

    ok = hits and hits[0]["id"] == f"{CIRCUIT}:7"
    print(f"\nEXIT CRITERION — signature retrieves itself at rank 0: {'PASS' if ok else 'FAIL'}")
    c.delete_index(INDEX)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

"""Stage 3 — index a behaviour catalogue into Endee and expose localization.

index_catalogue(circuit): build an Endee index from data/catalogue_<circuit>.jsonl.
  Each detected fault -> one object: vector = behaviour bits (0/1 floats),
  meta = {net, sa, behaviour}, filter = {circuit}.

localize(circuit, observed_bits): detection + retrieval -> verdict.
  FAULT_FREE   observed == golden
  EXACT        one fault matches the observed behaviour
  AMBIGUOUS    several faults share the observed behaviour (candidate set)
  UNKNOWN      observed behaviour not in the catalogue (Faultiva's "do not guess")
When observed is noise-corrupted it won't match exactly; nearest() returns the
ANN-ranked nearest catalogued fault(s) for the noise-tolerance experiment (Stage 4).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from client import get_client
from endee import Precision

OUT = os.path.join(os.path.dirname(__file__), "..", "data")


def _catalogue(circuit):
    rows = [json.loads(l) for l in open(os.path.join(OUT, f"catalogue_{circuit}.jsonl"), encoding="utf-8")]
    meta = json.load(open(os.path.join(OUT, f"golden_{circuit}.json")))
    return rows, meta


def _bits(s):
    return [float(ch) for ch in s]


def index_name(circuit):
    return f"fl_{circuit}"


def index_catalogue(circuit, precision=Precision.FLOAT32):
    rows, meta = _catalogue(circuit)
    dim = meta["dim"]
    c = get_client()
    try:
        c.delete_index(index_name(circuit))
    except Exception:
        pass
    c.create_index(name=index_name(circuit), dimension=dim, space_type="l2", precision=precision)
    idx = c.get_index(name=index_name(circuit))
    # upsert in batches (<=10k/call; here small)
    objs = [{"id": r["id"], "vector": _bits(r["behaviour"]),
             "meta": {"net": r["net"], "sa": r["sa"], "behaviour": r["behaviour"]},
             "filter": {"circuit": circuit}} for r in rows]
    for i in range(0, len(objs), 500):
        idx.upsert(objs[i:i + 500])
    return idx, meta, rows


if __name__ == "__main__":
    circuit = sys.argv[1] if len(sys.argv) > 1 else "c432"
    idx, meta, rows = index_catalogue(circuit)
    print(f"indexed {len(rows)} faults for {circuit} (dim={meta['dim']})")

    # --- diagnostic: nail the server's distance semantics ---
    probe = rows[0]
    q = _bits(probe["behaviour"])
    hits = idx.query(vector=q, top_k=5, filter=[{"circuit": {"$eq": circuit}}])
    print(f"\nEXACT query (fault {probe['id']}):")
    for h in hits:
        print(f"  id={h['id']:>12}  distance={h.get('distance')}  similarity={h.get('similarity')}")

    # flip 3 bits -> near but not exact
    b = list(probe["behaviour"]); 
    for p in (5, 50, 120):
        b[p] = "1" if b[p] == "0" else "0"
    hits2 = idx.query(vector=_bits("".join(b)), top_k=5, filter=[{"circuit": {"$eq": circuit}}])
    print(f"\n3-bit-flipped query (true fault {probe['id']}):")
    for h in hits2:
        print(f"  id={h['id']:>12}  distance={h.get('distance')}  similarity={h.get('similarity')}")

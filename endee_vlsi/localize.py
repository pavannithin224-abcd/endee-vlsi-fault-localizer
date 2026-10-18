"""Stage 3 — localization verdicts over the Endee behaviour index.

similarity field from the server == Hamming distance for 0/1 vectors
(0 = identical behaviour). We use it directly.

Verdict:
  FAULT_FREE  observed == golden
  EXACT       exactly one catalogued fault has identical behaviour (sim==0)
  AMBIGUOUS   several faults share the behaviour (candidate SET; sim==0)
  UNKNOWN     no exact behaviour match (Faultiva's "do not guess"); we still
              expose the ANN-nearest fault for the noise experiment.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from client import get_client
from index import index_name, _bits, _catalogue

TOP_K = 24  # > largest ambiguous group so a whole candidate set is captured


def localize(idx, circuit, observed_bits, golden_bits, top_k=TOP_K):
    if observed_bits == golden_bits:
        return {"verdict": "FAULT_FREE", "candidates": [], "nearest": None}
    hits = idx.query(vector=_bits(observed_bits), top_k=top_k,
                     filter=[{"circuit": {"$eq": circuit}}])
    exact = [h for h in hits if h.get("similarity") == 0]
    if exact:
        cand = [{"net": h["meta"]["net"], "sa": h["meta"]["sa"], "id": h["id"]} for h in exact]
        return {"verdict": "EXACT" if len(cand) == 1 else "AMBIGUOUS",
                "candidates": cand, "nearest": None}
    top = hits[0] if hits else None
    return {"verdict": "UNKNOWN", "candidates": [],
            "nearest": ({"id": top["id"], "sim": top.get("similarity")} if top else None)}


def validate(circuit):
    from index import index_catalogue
    idx, meta, rows = index_catalogue(circuit)
    golden = meta["golden"]
    print(f"validating {circuit}: {len(rows)} catalogued faults, dim={meta['dim']}")

    # 1) golden -> FAULT_FREE
    gf = localize(idx, circuit, golden, golden)
    print(f"  golden -> {gf['verdict']}  [{'PASS' if gf['verdict']=='FAULT_FREE' else 'FAIL'}]")

    # 2) every catalogued fault -> EXACT/AMBIGUOUS with TRUE fault inside candidate set
    ok = exact = amb = 0
    bad = []
    for r in rows:
        res = localize(idx, circuit, r["behaviour"], golden)
        ids = {c["id"] for c in res["candidates"]}
        if res["verdict"] in ("EXACT", "AMBIGUOUS") and r["id"] in ids:
            ok += 1
            exact += res["verdict"] == "EXACT"
            amb += res["verdict"] == "AMBIGUOUS"
        else:
            bad.append((r["id"], res["verdict"]))
    print(f"  faults localized correctly : {ok}/{len(rows)}  (EXACT={exact}, AMBIGUOUS={amb})")
    if bad:
        print(f"  FAILURES ({len(bad)}): {bad[:6]}")
    passed = (gf["verdict"] == "FAULT_FREE") and ok == len(rows)
    print(f"\nSTAGE 3 EXIT CRITERION: {'PASS' if passed else 'FAIL'}")
    return passed


if __name__ == "__main__":
    circuit = sys.argv[1] if len(sys.argv) > 1 else "c432"
    sys.exit(0 if validate(circuit) else 1)

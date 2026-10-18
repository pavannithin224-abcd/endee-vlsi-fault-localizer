"""Build a fault CATALOGUE from a .bench circuit: each detected stuck-at fault ->
a locality-preserving behaviour vector (outputs across N test patterns), plus its
fault site (net, stuck-value). Faults with identical behaviour form AMBIGUOUS groups
(physically indistinguishable from outputs alone) — exactly Faultiva's candidate-set
semantics, but in RAW behaviour space so approximate retrieval is meaningful.

Writes data/catalogue_<circuit>.jsonl : {id, net, sa, behaviour(bitstring), n_diff}
and  data/golden_<circuit>.json       : {circuit, n_patterns, n_outputs, golden}
"""
import json, os, sys, argparse
sys.path.insert(0, os.path.dirname(__file__))
from faultsim import Circuit, gen_patterns

OUT = os.path.join(os.path.dirname(__file__), "..", "data")


def build(circuit_name, n_patterns=64, seed=0):
    text = open(os.path.join(OUT, "bench", f"{circuit_name}.bench"), encoding="utf-8").read()
    c = Circuit(text)
    pats = gen_patterns(c, n_patterns, seed=seed)
    golden = [c.simulate(p) for p in pats]
    golden_flat = "".join(str(b) for row in golden for b in row)

    rows, groups = [], {}
    for net, sa in c.all_faults():
        beh = [c.simulate(p, fault=(net, sa)) for p in pats]
        beh_flat = "".join(str(b) for row in beh for b in row)
        n_diff = sum(a != b for a, b in zip(golden_flat, beh_flat))
        if n_diff == 0:
            continue                      # undetectable by these patterns -> not catalogued
        rows.append({"id": f"{net}__SA{sa}", "net": net, "sa": sa,
                     "behaviour": beh_flat, "n_diff": n_diff})
        groups.setdefault(beh_flat, []).append(f"{net}__SA{sa}")

    with open(os.path.join(OUT, f"catalogue_{circuit_name}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    json.dump({"circuit": circuit_name, "n_patterns": len(pats),
               "n_outputs": len(c.outputs), "dim": len(golden_flat),
               "golden": golden_flat, "seed": seed},
              open(os.path.join(OUT, f"golden_{circuit_name}.json"), "w"))

    total_faults = len(c.all_faults())
    distinct = len(groups)
    singletons = sum(1 for g in groups.values() if len(g) == 1)
    biggest = max((len(g) for g in groups.values()), default=0)
    print(f"circuit {circuit_name}: nets={len(c.nets)} outputs={len(c.outputs)} "
          f"patterns={len(pats)} dim={len(golden_flat)}")
    print(f"  stuck-at faults total     : {total_faults}")
    print(f"  detected (catalogued)     : {len(rows)}")
    print(f"  distinct behaviours       : {distinct}  (= EXACT-resolvable groups)")
    print(f"  singleton (EXACT) groups  : {singletons}")
    print(f"  largest AMBIGUOUS group   : {biggest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", nargs="?", default="c432")
    ap.add_argument("--patterns", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    build(a.circuit, a.patterns, a.seed)

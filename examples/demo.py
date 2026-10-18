"""Demo — localize a fault through Endee, blind, then reveal the truth.

Truth is withheld from the pipeline and printed only AFTER the verdict, so this is
a genuine prediction, not a replay. Also shows noise tolerance: corrupt the observed
behaviour and watch Endee still localize it where exact lookup would fail.

Run (server must be up):  .venv/Scripts/python.exe examples/demo.py --circuit c432
"""
import argparse, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "endee_vlsi"))
from index import index_catalogue, _bits          # noqa: E402
from localize import localize                      # noqa: E402


def banner(t): print("\n" + "=" * 64 + f"\n{t}\n" + "=" * 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuit", default="c432")
    ap.add_argument("--flips", type=int, default=6, help="bit-flips for the noise demo")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    idx, meta, rows = index_catalogue(a.circuit)
    golden = meta["golden"]
    rng = random.Random(a.seed)
    fault = rng.choice(rows)

    banner(f"Fault localization via Endee  ({a.circuit}, dim={meta['dim']})")
    print(f"catalogue : {len(rows)} characterized stuck-at faults")
    print(f"observed  : behaviour across {meta['n_patterns']} test patterns "
          f"(truth withheld)")

    # 1) clean observed behaviour
    res = localize(idx, a.circuit, fault["behaviour"], golden)
    total_sites = len({r["net"] for r in rows})
    print(f"\n[clean capture]")
    print(f"  VERDICT        : {res['verdict']}")
    print(f"  candidate set  : {len(res['candidates'])} site(s)   "
          f"(narrowed from {total_sites} possible)")
    print(f"  sites          : {[c['id'] for c in res['candidates']]}")
    print(f"  -- reveal truth: {fault['id']}  "
          f"{'IN candidate set' if fault['id'] in {c['id'] for c in res['candidates']} else 'MISSED'}")

    # 2) noise-corrupted observed behaviour
    b = list(fault["behaviour"])
    for p in rng.sample(range(len(b)), a.flips):
        b[p] = "1" if b[p] == "0" else "0"
    corrupted = "".join(b)
    res2 = localize(idx, a.circuit, corrupted, golden)
    print(f"\n[same fault, {a.flips} bits corrupted in the observed response]")
    print(f"  exact dictionary lookup : "
          f"{'MATCH' if corrupted == fault['behaviour'] else 'NO MATCH -> UNKNOWN (gives up)'}")
    if res2["verdict"] == "UNKNOWN":
        near = res2["nearest"]
        print(f"  Endee ANN nearest       : {near['id']}  (Hamming {near['sim']})   "
              f"{'CORRECT group' if idx_behaviour(rows, near['id']) == fault['behaviour'] else 'wrong'}")
    else:
        hit = fault["id"] in {c["id"] for c in res2["candidates"]}
        print(f"  Endee ANN verdict       : {res2['verdict']}  "
              f"-> true fault {'recovered' if hit else 'missed'}")
    print("\nExact lookup fails the moment the response is noisy; Endee still localizes.")


def idx_behaviour(rows, fid):
    for r in rows:
        if r["id"] == fid:
            return r["behaviour"]
    return None


if __name__ == "__main__":
    main()

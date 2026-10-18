"""Stage 4 — the noise-tolerance experiment (the headline result).

Corrupt an observed behaviour with k random bit-flips (realistic chip/capture noise)
and measure how often we still localize the true fault:

  EXACT-match baseline (= Faultiva's hash/exact lookup): succeeds only when the
     corrupted behaviour EXACTLY equals a catalogued behaviour of the true fault's
     group. One flipped bit normally destroys the match -> recall collapses.
  Endee ANN (nearest by Hamming): returns the catalogued fault whose clean behaviour
     is nearest. The true fault's own behaviour is only k bits away, so it is usually
     still nearest -> graceful degradation.

Success criterion (honest): the returned fault is behaviourally INDISTINGUISHABLE
from the true fault (same clean behaviour group) — because such faults genuinely
cannot be separated from outputs alone.

Outputs: results/noise_recall_<circuit>.png  and  results/noise_recall_<circuit>.json
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from index import index_catalogue, index_name, _bits
from client import get_client

OUT = os.path.join(os.path.dirname(__file__), "..", "data")
RES = os.path.join(os.path.dirname(__file__), "..", "results")
K_VALUES = [0, 1, 2, 4, 8, 16, 32]
TRIALS = 5
SAMPLE = 120


def flip(bits, k, rng):
    b = list(bits)
    for p in rng.sample(range(len(b)), k):
        b[p] = "1" if b[p] == "0" else "0"
    return "".join(b)


def run(circuit, seed=0):
    os.makedirs(RES, exist_ok=True)
    idx, meta, rows = index_catalogue(circuit)
    dim = meta["dim"]
    behaviour_set = {r["behaviour"] for r in rows}      # exact-lookup catalogue (dict)
    rng = random.Random(seed)
    sample = rng.sample(rows, min(SAMPLE, len(rows)))
    print(f"{circuit}: dim={dim}, {len(rows)} faults, sampling {len(sample)}, {TRIALS} trials/k")

    exact_recall, ann_recall = [], []
    for k in K_VALUES:
        ex_hit = ann_hit = total = 0
        for r in sample:
            true_beh = r["behaviour"]
            for _ in range(TRIALS):
                total += 1
                corrupted = flip(true_beh, k, rng) if k else true_beh
                # EXACT baseline: does corrupted exactly match the true fault's behaviour?
                if corrupted in behaviour_set and corrupted == true_beh:
                    ex_hit += 1
                # ANN: nearest catalogued fault; success if same clean-behaviour group
                hits = idx.query(vector=_bits(corrupted), top_k=1,
                                 filter=[{"circuit": {"$eq": circuit}}])
                if hits and hits[0]["meta"]["behaviour"] == true_beh:
                    ann_hit += 1
        exact_recall.append(ex_hit / total)
        ann_recall.append(ann_hit / total)
        print(f"  k={k:>2}: exact={ex_hit/total:.3f}  ANN={ann_hit/total:.3f}")

    data = {"circuit": circuit, "dim": dim, "k_values": K_VALUES,
            "trials": TRIALS, "sample": len(sample),
            "exact_recall": exact_recall, "ann_recall": ann_recall}
    json.dump(data, open(os.path.join(RES, f"noise_recall_{circuit}.json"), "w"), indent=2)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(7, 4.3))
    plt.plot(K_VALUES, ann_recall, "o-", color="#2a9d4a", lw=2.4, label="Endee ANN retrieval")
    plt.plot(K_VALUES, exact_recall, "s--", color="#d1495b", lw=2.4, label="Exact dictionary lookup")
    plt.xlabel("bit-flips injected into observed behaviour")
    plt.ylabel("localization recall@1")
    plt.title(f"Noise-tolerant fault localization on Endee ({circuit}, dim={dim})")
    plt.ylim(-0.03, 1.03); plt.grid(alpha=0.3); plt.legend()
    plt.tight_layout()
    png = os.path.join(RES, f"noise_recall_{circuit}.png")
    plt.savefig(png, dpi=130)
    print(f"\nwrote {png}")
    return data


if __name__ == "__main__":
    circuit = sys.argv[1] if len(sys.argv) > 1 else "c432"
    run(circuit)

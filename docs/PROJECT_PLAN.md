# endee-vlsi-fault-localizer — Project Plan & Stages

Build-to-hire submission for Endee's ML Intern role. New public repo, separate from Faultiva.
Companion docs: `BUILD_SPEC.md` (how), `README_FRAMING.md` (positioning), `preview.html` (target look).

**Golden rule:** nothing goes public until it runs clean from a fresh clone. Honesty over hype on every surface.

---

## Stage 0 — Data extraction  (½ day)
Turn Faultiva's shipped dictionary into ingestion-ready data.
- Read `C:/Program Files/Faultiva/_internal/models/faultiva_signature_dictionary.npz` (zipfile + .npy headers, or numpy in venv).
- For each circuit, reconstruct CSR: sites for signature *i* = `sites[offsets[i]:offsets[i+1]]`, stuck same slice.
- Emit `data/signatures.jsonl`: one row per signature = `{circuit, signature(hex), sites:[...], stuck:[...]}`.
- Also parse `ANSWERS.json` + the 64-vector captures into `data/queries.jsonl` (ground-truth test cases).
- **Exit criteria:** JSONL row counts match npz (2505/471/28189/11654); a spot-checked signature's site set matches the dictionary.

## Stage 1 — Endee up + smoke test  (½–1 day)
Prove we can index and query before building anything real.
- Decide Cloud (fast) vs Enterprise-Docker (offline). Get token / container running.
- Create a collection; ingest ONE circuit (picorv32, smallest at 471); run a trivial search.
- **Exit criteria:** a known signature retrieves itself at distance 0 through the Endee SDK.

## Stage 2 — Encoding  (1–1.5 days)
Decide how a 64×256-bit capture becomes one vector.
- Option A (default): concat 64×256-bit → 16,384-bit binary vector, Endee `binary` quantization + Hamming.
- Option B (fallback): reduced float vector + cosine.
- Probe recall@k on held-out faults; pick the winner on evidence, not taste.
- **Exit criteria:** chosen encoding documented with a recall@k number justifying it.

## Stage 3 — Core pipeline  (1.5–2 days)
The working localizer.
- `index.py` — build Endee collection from `signatures.jsonl` (all 4 circuits, payload = sites+stuck+circuit).
- `localize.py` — capture → encode → `search()` with filter `circuit=$eq` → candidate set → verdict.
- Verdict logic: EXACT (single, dist 0) / AMBIGUOUS (set, print size) / FAULT_FREE (no sig in band).
- Validate against `queries.jsonl`: every faulty case's true site inside the returned set, no clean case flagged.
- **Exit criteria:** matches `ANSWERS.json` expected_result on all shipped test cases.

## Stage 4 — The killer experiment  (1–1.5 days)
The result that makes the submission stand out.
- `noise_experiment.py` — inject k random bit-flips (k=0,1,2,4,8) into faulty responses.
- Measure recall@k: exact-match baseline (collapses at 1 bit) vs Endee ANN (graceful).
- Produce `results/noise_recall.png` + the numbers.
- **Exit criteria:** the recall-vs-bitflips chart exists and shows the expected divergence; numbers reproducible via one command.

## Stage 5 — Demo + README + polish  (1–1.5 days)
Make it reviewer-ready.
- `examples/demo.py` — blind verdict then truth reveal; print the 36,784→N narrowing.
- `README.md` in the locked section order: problem → why-retrieval → **how Endee is used** (name the primitives) → results+chart → honest-fit analysis → setup/run.
- `HONEST_LIMITS.md`: unobservable fractions (73.2/75.4/2.9/5.3%), candidate-set rule, crypto-vs-CPU boundary, "overkill at this scale / real win at scale+edge."
- Authorship surfaces: README top line, `LICENSE` (Apache-2.0), `AUTHORS`/`NOTICE` — Faultiva is Pavan's own work, built from scratch; GitHub `pavannithin224-abcd`, LinkedIn.
- **Exit criteria:** `requirements.txt` + README steps run end-to-end from a fresh clone on a clean machine/venv.

## Stage 6 — Publish + submit  (½ day)
- Verify clean-checkout run one more time (copy to temp dir, cleared PYTHONPATH, run shipped examples as subprocesses).
- Flip repo public. ⭐ Star `github.com/endee-io/endee` (their explicit requirement).
- Submit the public repo link in the Endee application form.
- **Exit criteria:** a stranger could clone, follow README, and reproduce the demo + chart.

---

## Timeline
- Focused: **~4–6 days.**  Part-time (2–3 hr/day): **~8–12 days.**
- Critical path is Stages 2–4 (encoding → pipeline → experiment); Stages 0/1 are fast now that data is unblocked.

## Repo skeleton (target)
```
endee-vlsi-fault-localizer/
  README.md  LICENSE  NOTICE  AUTHORS  requirements.txt
  endee_vlsi/   parse.py  encode.py  index.py  localize.py  noise_experiment.py
  examples/     demo.py
  data/         signatures.jsonl  queries.jsonl  (+ sample captures)
  results/      noise_recall.png
  docs/         HONEST_LIMITS.md
```

## Risks
- **Endee SDK friction / Cloud signup or Docker eval hiccup** → Stage 1 exists to surface this early; fall back Cloud↔Docker.
- **Encoding doesn't separate fault classes** (bad recall@k) → Stage 2 gate catches it before we build on sand.
- **Binary-vector width (16,384 bits)** may need a quantization/metric adjustment in Endee → tune in Stage 2.

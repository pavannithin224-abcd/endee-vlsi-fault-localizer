# Endee VLSI Fault-Retrieval — Build Spec

**Goal:** A build-to-hire submission for Endee's ML Intern role. Demonstrate Endee as the retrieval layer for VLSI fault **localization**, built on Pavan's Faultiva data — and extend it with **noise-tolerant (approximate) signature retrieval**, a capability the exact-match V2.2 engine does not have.

**Why this wins:** Endee lists anomaly/fault detection as a use case but has zero showcase. This fills that gap with a domain nobody else applying can fake (VLSI fault diagnosis), and it doubles as Faultiva portfolio proof.

---

## 0. What we are NOT doing
- NOT modifying Endee's engine (closed source — repo has no code).
- NOT doing fault *detection* with Endee (that's Faultiva's NN). Endee does **localization/diagnosis = retrieval**.
- NOT claiming scale wins (student-size data; the win is correctness + noise tolerance, stated honestly).

## 1. Platform
- Primary: **Endee Serverless / Cloud** (`app.endee.io`) — create DB, get token, use SDK. Free to start.
- Alt (offline/air-gapped demo, matches Faultiva ethos): **Endee Enterprise** local Docker, 30-day eval. Don't start the eval clock until data + embeddings are ready.

## 2. Source data (already owned)
`C:/Users/Dell/OneDrive/Desktop/Faultiva inputs/faultiva inputsv22/`
- Capture file = header + **64 response vectors**, each a 256-bit value (64 hex) + `timeout protocol cycles` flags.
- `ANSWERS.json` = ground truth: `{file, circuit, true_site, true_type (SA0/SA1), candidate_sites, expected_result}`.
- Characterized signature counts available: opentitan_hmac_sha256=2,504 · picorv32_cpu=470 · secworks_aes=28,188 · secworks_sha256=11,653.
- `expected_result` ∈ {EXACT, AMBIGUOUS, FAULT_FREE} — localization returns a candidate SET, never a forced single site.

## 3. Signature → vector encoding (the core design decision)
A capture is 64 lines × 256-bit response. Turn one capture into ONE fixed-length embedding:
- **Option A (faithful, recommended):** concatenate the 64 × 256-bit responses → 16,384-bit binary vector. Store with Endee **`binary` quantization** + Hamming/`l2`. Exact match = distance 0; near match = small Hamming distance → noise tolerance falls out naturally.
- **Option B (compact):** per-response bit-density / feature reduction → float vector, `cosine`. Smaller, but lossy; only if A is too wide.
- Decide empirically: validate recall@k on held-out faults (§6). Start with A.
- Include the `timeout/protocol/cycles` flags as metadata, not in the vector.

## 4. Endee schema
- One **collection per project** (or one, filtered by circuit).
- Object per **characterized fault signature**:
  - `id` = `{circuit}:{site}:{type}`
  - dense `vector` field = signature embedding (§3)
  - `meta`/`filter`: `circuit`, `true_site`, `fault_type` (SA0/SA1), `block` (if derivable)
- Query = observed capture → embed → `search()` with **filter `circuit = $eq <this circuit>`** → top-k → candidate site set.
- This natively stores signature→sites (closes Faultiva's flagged gap: frozen dict held only `__keys`/`__sizes`, counts not sites).

## 5. Pipeline
```
capture.txt --parse--> 64x256bit --encode(§3)--> query vector
   --Endee search(filter circuit)--> top-k candidates
   --threshold--> {EXACT | AMBIGUOUS(set) | FAULT_FREE}
```
- EXACT: single candidate at distance 0.
- AMBIGUOUS: multiple within distance band → print the whole set + its size (honesty rule).
- FAULT_FREE: clean signature matches the golden/clean capture (no fault signature within band).

## 6. The killer experiment — noise tolerance
Exact dictionary lookup FAILS when the observed response is corrupted. ANN does not.
- Take known faulty captures, inject k random bit-flips (k = 1,2,4,8,…) into the response.
- Exact-match baseline: recall collapses to ~0 as soon as any bit flips.
- Endee ANN retrieval: plot recall@k vs bit-flip count → graceful degradation.
- **Deliverable chart:** "Fault localization recall vs response corruption — exact vs approximate retrieval." This is the reviewer-stopping result.

## 7. Honesty guardrails (carry over from Faultiva deliverable)
- Localization returns a SET; always print its size; never truncate to look decisive.
- Report the unobservable fraction per circuit (73.2% / 75.4% / 2.9% / 5.3%).
- A clean verdict never proves fault-free — state it.
- Crypto circuits = strong demo; CPU circuits = honest boundary. Show both; the contrast is the result.

## 8. Repo / submission structure
```
endee-vlsi/
  README.md            # problem, approach, how Endee is used, setup, results, the noise chart
  endee_vlsi/
    parse.py           # capture.txt -> array
    encode.py          # array -> embedding (§3)
    index.py           # build Endee collection from signature dictionary
    localize.py        # query -> candidate set + verdict
    noise_experiment.py# §6
  examples/
    demo.py            # withhold truth, print verdict, reveal truth after (prediction not replay)
  data/                # small sample captures + ANSWERS.json (NOT the full corpus)
  docs/
    HONEST_LIMITS.md
  requirements.txt
```
README must cover, in order: problem statement → system design → **explicit "how Endee is used"** (their stated requirement) → setup/run → results + noise chart. Submit the GitHub repo link in the application form.

## 9. Open questions before coding
1. ~~Where the real signature→site mapping lives~~ **RESOLVED.** Full CSR mapping ships in `C:\Program Files\Faultiva\_internal\models\faultiva_signature_dictionary.npz` — per-circuit `signatures`/`sites`/`stuck`/`offsets` arrays, ~42,800 signatures across 4 circuits. Q1 is a trivial dump, not a regenerate. The 198GB build-system corpus is NOT needed.
2. Serverless vs Enterprise-Docker for the demo (offline preference vs setup speed).
3. Encoding Option A vs B — decide after a quick recall@k probe.

## 10. Data & authorship (settled — Pavan)
- **Faultiva is being made public** — the full signature dictionary may ship in this repo. No need to sample down.
- **Authorship is a HARD requirement.** Every surface must state clearly that **Faultiva is Pavan's own work, designed and built from scratch by him.** Put it in:
  - README top: a line crediting Faultiva as Pavan's original project (with author name + links: GitHub `pavannithin224-abcd`, LinkedIn).
  - A `LICENSE` + `AUTHORS`/`NOTICE` naming Pavan as sole author of the Faultiva-derived data and method.
  - The "prior work" paragraph: Faultiva = his DL VLSI fault-detection project (CircuitSage-HMAC), built independently from scratch — this repo is a retrieval application layered on its output.
- Do NOT let the framing imply Endee or anyone else contributed to Faultiva. The Endee project is the thin public application; Faultiva is Pavan's engine.

**Next action:** Phase 0 — write the npz extractor that dumps per-circuit `(signature, [sites], [stuck])` to ingestion-ready JSONL, then stand up a throwaway Endee collection with one circuit and confirm exact-match localization before the noise experiment.

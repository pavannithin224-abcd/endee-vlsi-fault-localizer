#!/usr/bin/env python3
"""
Phase 0 extractor — Faultiva signature dictionary -> ingestion-ready JSONL.

Reads the shipped frozen dictionary:
  C:/Program Files/Faultiva/_internal/models/faultiva_signature_dictionary.npz
Reconstructs the CSR mapping (signature -> candidate sites + stuck type) per circuit
and writes:
  data/signatures.jsonl   one row per signature {circuit, signature, sites, stuck}
  data/queries.jsonl      ground-truth test cases from ANSWERS.json + captures

Pure stdlib: parses the .npz (a zip of .npy) and .npy headers by hand, so it runs
with no numpy/pip. Faultiva is Pavan's own work, built from scratch by him.
"""
import ast, json, os, struct, sys, zipfile

NPZ = r"C:/Program Files/Faultiva/_internal/models/faultiva_signature_dictionary.npz"
INPUTS = r"C:/Users/Dell/OneDrive/Desktop/Faultiva inputs/faultiva inputsv22"
OUT = os.path.join(os.path.dirname(__file__), "..", "data")

CIRCUITS = ["opentitan_hmac_sha256", "picorv32_cpu", "secworks_aes", "secworks_sha256"]


def read_npy(raw: bytes):
    """Parse a .npy byte blob -> (list_of_values, shape, descr). Handles <U*, <i8, |u1."""
    assert raw[:6] == b"\x93NUMPY", "not a .npy"
    major = raw[6]
    if major == 1:
        hlen = struct.unpack("<H", raw[8:10])[0]
        off = 10
    else:
        hlen = struct.unpack("<I", raw[8:12])[0]
        off = 12
    header = ast.literal_eval(raw[off:off + hlen].decode("latin1").strip())
    descr, shape = header["descr"], header["shape"]
    body = raw[off + hlen:]
    n = 1
    for d in shape:
        n *= d
    if descr.startswith("<U"):                 # unicode, UTF-32-LE
        width = int(descr[2:])
        step = width * 4
        vals = []
        for i in range(n):
            chunk = body[i * step:(i + 1) * step]
            vals.append(chunk.decode("utf-32-le").rstrip("\x00"))
    elif descr in ("<i8", "|i8", "<i4"):
        isz = 8 if descr.endswith("8") else 4
        fmt = "<q" if isz == 8 else "<i"
        vals = [struct.unpack(fmt, body[i * isz:(i + 1) * isz])[0] for i in range(n)]
    elif descr in ("|u1", "<u1"):
        vals = list(body[:n])
    else:
        raise ValueError(f"unhandled descr {descr}")
    return vals, shape, descr


def main():
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(NPZ)
    arrays = {}
    for name in z.namelist():
        key = name[:-4] if name.endswith(".npy") else name
        try:
            arrays[key] = read_npy(z.read(name))[0]
        except ValueError as e:
            print(f"  skip {key}: {e}")

    sig_path = os.path.join(OUT, "signatures.jsonl")
    counts = {}
    with open(sig_path, "w", encoding="utf-8") as f:
        for c in CIRCUITS:
            sigs = arrays[f"{c}__signatures"]
            sites = arrays[f"{c}__sites"]
            stuck = arrays[f"{c}__stuck"]
            offs = arrays[f"{c}__offsets"]
            assert len(offs) == len(sigs) + 1, f"{c}: offsets/sigs mismatch"
            assert offs[-1] == len(sites) == len(stuck), f"{c}: CSR length mismatch"
            for i, sig in enumerate(sigs):
                lo, hi = offs[i], offs[i + 1]
                row = {
                    "circuit": c,
                    "signature": sig,
                    "sites": sites[lo:hi],
                    "stuck": [("SA1" if s else "SA0") for s in stuck[lo:hi]],
                }
                f.write(json.dumps(row) + "\n")
            counts[c] = len(sigs)
    print("signatures.jsonl written:", counts, "total", sum(counts.values()))

    # queries.jsonl from ANSWERS.json + capture files
    q_path = os.path.join(OUT, "queries.jsonl")
    ans = json.load(open(os.path.join(INPUTS, "ANSWERS.json"), encoding="utf-8"))
    nq = 0
    with open(q_path, "w", encoding="utf-8") as f:
        for a in ans:
            cap = os.path.join(INPUTS, a["file"])
            responses = []
            if os.path.exists(cap):
                for line in open(cap, encoding="utf-8"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    responses.append(line.split()[0])
            f.write(json.dumps({**a, "responses": responses, "n_responses": len(responses)}) + "\n")
            nq += 1
    print("queries.jsonl written:", nq, "cases")


if __name__ == "__main__":
    main()

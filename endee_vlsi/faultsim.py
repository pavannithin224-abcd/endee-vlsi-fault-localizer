"""Stuck-at fault simulator for ISCAS-85-style .bench gate netlists.

Produces a fault CATALOGUE: for each stuck-at fault (net stuck-at-0/1), the circuit's
OUTPUT BEHAVIOUR across a set of test patterns. Unlike Faultiva's hashed signatures,
these behaviour vectors are LOCALITY-PRESERVING: a small change in the response is a
small change in the vector — which is exactly what makes approximate (ANN) retrieval
meaningful. This is the data the Endee behaviour-space index is built from.

.bench format:
    INPUT(a)  OUTPUT(z)
    g = NAND(a, b)        # gate types: AND NAND OR NOR XOR XNOR NOT BUFF/BUF
"""
import re
from itertools import product

GATES = {
    "AND":  lambda ins: int(all(ins)),
    "NAND": lambda ins: int(not all(ins)),
    "OR":   lambda ins: int(any(ins)),
    "NOR":  lambda ins: int(not any(ins)),
    "XOR":  lambda ins: int(sum(ins) % 2 == 1),
    "XNOR": lambda ins: int(sum(ins) % 2 == 0),
    "NOT":  lambda ins: int(not ins[0]),
    "BUFF": lambda ins: int(bool(ins[0])),
    "BUF":  lambda ins: int(bool(ins[0])),
}


class Circuit:
    def __init__(self, text):
        self.inputs, self.outputs, self.gates, self.order = [], [], {}, []
        for raw in text.splitlines():
            line = raw.split("#")[0].strip()
            if not line:
                continue
            m = re.match(r"INPUT\(([^)]+)\)", line, re.I)
            if m: self.inputs.append(m.group(1).strip()); continue
            m = re.match(r"OUTPUT\(([^)]+)\)", line, re.I)
            if m: self.outputs.append(m.group(1).strip()); continue
            m = re.match(r"(\S+)\s*=\s*(\w+)\s*\(([^)]*)\)", line)
            if m:
                net, gtype, args = m.group(1).strip(), m.group(2).upper(), \
                    [a.strip() for a in m.group(3).split(",")]
                self.gates[net] = (gtype, args)
                self.order.append(net)
        self._toposort()
        self.nets = list(self.inputs) + list(self.order)

    def _toposort(self):
        resolved, order = set(self.inputs), []
        pending = list(self.order)
        while pending:
            progressed = False
            for net in list(pending):
                _, args = self.gates[net]
                if all(a in resolved for a in args):
                    order.append(net); resolved.add(net); pending.remove(net); progressed = True
            if not progressed:
                raise ValueError(f"cycle/undriven nets: {pending[:5]}")
        self.order = order

    def simulate(self, pattern, fault=None):
        """pattern: dict input->0/1. fault: (net, value) stuck-at. Returns output tuple."""
        val = dict(pattern)
        if fault and fault[0] in val:               # fault on a primary input
            val[fault[0]] = fault[1]
        for net in self.order:
            gtype, args = self.gates[net]
            out = GATES[gtype]([val[a] for a in args])
            if fault and net == fault[0]:
                out = fault[1]
            val[net] = out
        return tuple(val[o] for o in self.outputs)

    def all_faults(self):
        """Every stuck-at-0 and stuck-at-1 on every net (inputs + gate outputs)."""
        return [(net, sa) for net in self.nets for sa in (0, 1)]


def gen_patterns(circuit, n, seed=0):
    """Deterministic test patterns. Exhaustive if 2^#inputs <= n, else pseudo-random."""
    import random
    k = len(circuit.inputs)
    if k <= 16 and (1 << k) <= n:
        combos = product((0, 1), repeat=k)
        return [dict(zip(circuit.inputs, c)) for c in combos]
    rng = random.Random(seed)
    return [{inp: rng.randint(0, 1) for inp in circuit.inputs} for _ in range(n)]


C17 = """
INPUT(1)
INPUT(2)
INPUT(3)
INPUT(6)
INPUT(7)
OUTPUT(22)
OUTPUT(23)
10 = NAND(1, 3)
11 = NAND(3, 6)
16 = NAND(2, 11)
19 = NAND(11, 7)
22 = NAND(10, 16)
23 = NAND(16, 19)
"""

if __name__ == "__main__":
    c = Circuit(C17)
    print("inputs:", c.inputs, "outputs:", c.outputs, "nets:", len(c.nets))
    pats = gen_patterns(c, 32)
    print("patterns:", len(pats), "(exhaustive for 5 inputs)")
    # golden behaviour
    golden = [c.simulate(p) for p in pats]
    print("golden (first 4):", golden[:4])
    # a sample fault behaviour
    faults = c.all_faults()
    print("total stuck-at faults:", len(faults))
    net, sa = faults[0]
    beh = [c.simulate(p, fault=(net, sa)) for p in pats]
    diff = sum(1 for g, b in zip(golden, beh) if g != b)
    print(f"fault {net}/SA{sa}: differs from golden on {diff}/{len(pats)} patterns")

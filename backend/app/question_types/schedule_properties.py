import re

from app.common import *


# --------------------------------------------------------------------------- #
# Per-difficulty configuration.
# - n_tx     : number of transactions T1..Tn in the schedule
# - objects  : data objects the operations may touch
# - ops_min  : minimum number of read/write operations per transaction
# - ops_max  : maximum number of read/write operations per transaction
# A transaction always ends with exactly one terminal operation (commit/abort)
# after its read/write operations.
# --------------------------------------------------------------------------- #
DIFFICULTY_SETTINGS = {
    "easy": {"n_tx": 2, "objects": ["x", "y", "z"], "ops_min": 2, "ops_max": 3},
    "medium": {"n_tx": 3, "objects": ["x", "y", "z"], "ops_min": 2, "ops_max": 3},
    "hard": {"n_tx": 3, "objects": ["x", "y", "z"], "ops_min": 3, "ops_max": 4},
}

# Desired ``(serializable, all_commit)`` profile, rotated by ``seed`` so the
# generated schedules cover serializable/non-serializable and with/without an
# abort. Correctness is always computed exactly from the schedule; this only
# steers the distribution and is best-effort. NB: an abort only yields a
# non-trivial serializability graph when at least two transactions still commit,
# so the abort profiles are only used when ``n_tx >= 3`` (see ``_build``).
TARGET_PROFILES = [
    (True, True),    # serializable, all transactions commit
    (False, True),   # not serializable, all transactions commit
    (True, False),   # serializable, one transaction aborts
    (False, False),  # not serializable, one transaction aborts
]

# The five properties assessed, in the order shown in the lecture/exercise.
# Each entry: (field id, German label).
PROPERTIES = [
    ("is_serial", "seriell"),
    ("is_serializable", "serialisierbar"),
    ("is_recoverable", "rücksetzbar"),
    ("is_aca", "vermeidet kaskadierendes Rücksetzen (ACA)"),
    ("is_strict", "strikt"),
]

# The four histories from exercise 3 of the task sheet — used as guaranteed
# fallbacks (and as fixed, well-understood instances).
FALLBACK_HISTORIES = [
    "w1[x] w1[y] c1 r2[x] w2[z] c2 r3[y] a3",
    "w1[x] w2[x] w2[y] w1[y] w1[z] c1 c2",
    "r1[x] w1[x] r2[x] w2[y] r1[y] w1[z] c1 c2 r3[z] w3[x] c3",
    "r1[x] w1[y] r2[y] w1[z] w2[z] c1 w2[x] c2",
]

# Number of random schedules sampled per instance to build the distinct-schedule
# pool. Large enough that the pool (and thus the per-seed variety) is rich.
SEARCH_TRIES = 2000

_OP_RE = re.compile(r"([rw])(\d+)\[([^\]]+)\]|([ca])(\d+)")


def parse_history(text):
    """Parse a history string such as ``"w1[x] r2[x] c1 a2"`` into a list of
    operation dicts ``{"kind": "r"|"w"|"c"|"a", "t": int, "obj": str|None}``.
    Raises ``ValueError`` on malformed input."""
    ops = []
    for token in str(text).split():
        m = _OP_RE.fullmatch(token)
        if not m:
            raise ValueError(f"Ungültige Operation: {token!r}")
        if m.group(1):  # read / write
            ops.append({"kind": m.group(1), "t": int(m.group(2)), "obj": m.group(3)})
        else:  # commit / abort
            ops.append({"kind": m.group(4), "t": int(m.group(5)), "obj": None})
    return ops


class SchedulePropertiesQuestion:
    """Eigenschaften von Historien (Schedules).

    Gegeben ist eine Historie ``H`` über Operationen ``ri[x]`` (Lesen), ``wi[x]``
    (Schreiben), ``ci`` (Commit) und ``ai`` (Abort). Zu bestimmen ist, welche der
    folgenden Eigenschaften ``H`` besitzt — entsprechend den Definitionen aus der
    Vorlesung *„09 Operational Consistency“*:

    * **seriell** — die Transaktionen laufen nacheinander ab, es gibt keine
      Verzahnung (jede Transaktion bildet einen zusammenhängenden Block).
    * **serialisierbar** — der Serialisierbarkeitsgraph (Konfliktgraph) der
      *festgeschriebenen* Transaktionen ist azyklisch (Folie „Determine
      Serializability“). Knoten = Transaktionen, Kante ``Ti → Tj`` für jede
      Konfliktoperation (read-write / write-read / write-write auf demselben
      Objekt) mit ``Ti`` vor ``Tj``.
    * **rücksetzbar (RC)** — wann immer ``Ti`` von ``Tj`` liest und ``ci ∈ H``,
      gilt ``cj < ci``.
    * **vermeidet kaskadierendes Rücksetzen (ACA)** — wann immer ``Ti`` von
      ``Tj`` liest, gilt ``cj < ri[x]`` (es wird nur von festgeschriebenen
      Transaktionen gelesen).
    * **strikt (ST)** — für ``wj[x] < oi[x]`` (mit ``oi[x] = ri[x]`` oder
      ``wi[x]``, ``i ≠ j``) gilt ``aj < oi[x]`` oder ``cj < oi[x]`` (auf ein von
      ``Tj`` geschriebenes Objekt wird erst nach Ende von ``Tj`` zugegriffen).

    Die Musterlösung zeigt zusätzlich den Serialisierbarkeitsgraphen. Alles wird
    deterministisch aus ``seed`` berechnet, womit die Aufgabe selbstprüfend ist.
    """

    def __init__(self, seed=None, difficulty="easy", **kwargs):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"
        self.cfg = DIFFICULTY_SETTINGS[self.difficulty]

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        # The chosen schedule (list of operation dicts) — ground truth.
        self.ops = self._build()

        self.transactions = sorted({op["t"] for op in self.ops})
        self.committed = sorted(self._committed(self.ops))
        self.aborted = sorted(self._aborted(self.ops))

        # Conflict (serializability) graph over the committed projection.
        self.graph_edges, self.graph_nodes = self._conflict_edges(self.ops)
        self.graph_cycles = self._find_cycles(self.graph_nodes, self.graph_edges)

        # Ground-truth property values, computed up front.
        self.props = {
            "is_serial": self._is_serial(self.ops),
            "is_serializable": not self._has_cycle(self.graph_nodes, self.graph_edges),
            "is_recoverable": self._is_recoverable(self.ops),
            "is_aca": self._is_aca(self.ops),
            "is_strict": self._is_strict(self.ops),
        }

    # ------------------------------------------------------------------ #
    # Basic accessors (pure helpers — operate on the argument)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _committed(ops):
        return {op["t"] for op in ops if op["kind"] == "c"}

    @staticmethod
    def _aborted(ops):
        return {op["t"] for op in ops if op["kind"] == "a"}

    @staticmethod
    def _commit_index(ops):
        """tx -> index of its commit (only committed transactions)."""
        return {op["t"]: i for i, op in enumerate(ops) if op["kind"] == "c"}

    @staticmethod
    def _terminal_index(ops):
        """tx -> index of its terminal operation (commit *or* abort)."""
        return {op["t"]: i for i, op in enumerate(ops) if op["kind"] in ("c", "a")}

    @staticmethod
    def _reads_from(ops):
        """The reads-from relation: a list of ``(reader, writer, obj, read_idx)``.

        ``Ti`` *reads ``x`` from ``Tj``* (``j != i``) when ``Tj``'s write is the
        most recent write of ``x`` before ``ri[x]`` whose value still stands at
        the read. A writer that **aborted before the read** has had its value
        undone, so it is skipped and the search continues to the previous writer
        (a writer that aborts *after* the read still counts — that is exactly the
        dirty read). Reading one's own most-recent write is not a reads-from."""
        abort_idx = {op["t"]: i for i, op in enumerate(ops) if op["kind"] == "a"}
        out = []
        for i, op in enumerate(ops):
            if op["kind"] != "r":
                continue
            reader = op["t"]
            for j in range(i - 1, -1, -1):
                wj = ops[j]
                if wj["kind"] != "w" or wj["obj"] != op["obj"]:
                    continue
                writer = wj["t"]
                if writer == reader:
                    break  # reads its own most-recent write
                aborted_at = abort_idx.get(writer)
                if aborted_at is not None and aborted_at < i:
                    continue  # writer aborted before the read -> value undone
                out.append((reader, writer, op["obj"], i))
                break
        return out

    # ------------------------------------------------------------------ #
    # Properties (each implements the corresponding lecture definition)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_serial(ops):
        """Serial iff no transaction is re-entered after another's operation has
        run in between (each transaction forms one contiguous block)."""
        last = None
        finished = set()
        for op in ops:
            t = op["t"]
            if t != last:
                if t in finished:
                    return False
                if last is not None:
                    finished.add(last)
                last = t
        return True

    def _conflict_edges(self, ops):
        """Serializability/precedence graph over the *committed* transactions
        (Folie „Determine Serializability“: precedence graph of committed
        transactions). Returns ``(edges, nodes)`` with ``edges`` a set of
        ``(i, j)`` integer pairs and ``nodes`` the sorted committed transactions.

        An edge ``i -> j`` is added for every pair of conflicting operations
        (same object, at least one write, different transactions) where ``Ti``'s
        operation precedes ``Tj``'s."""
        committed = self._committed(ops)
        nodes = sorted(committed)
        by_obj = {}
        for op in ops:
            if op["kind"] in ("r", "w") and op["t"] in committed:
                by_obj.setdefault(op["obj"], []).append(op)

        edges = set()
        for lst in by_obj.values():
            for a in range(len(lst)):
                for b in range(a + 1, len(lst)):
                    p, q = lst[a], lst[b]
                    if p["t"] == q["t"]:
                        continue
                    if p["kind"] == "w" or q["kind"] == "w":
                        edges.add((p["t"], q["t"]))
        return edges, nodes

    @staticmethod
    def _has_cycle(nodes, edges):
        adj = {n: [] for n in nodes}
        for a, b in edges:
            if a in adj:
                adj[a].append(b)
        color = {n: 0 for n in nodes}  # 0 white, 1 grey, 2 black

        def visit(u):
            color[u] = 1
            for v in adj.get(u, []):
                if color.get(v, 0) == 1:
                    return True
                if color.get(v, 0) == 0 and visit(v):
                    return True
            color[u] = 2
            return False

        return any(color[n] == 0 and visit(n) for n in nodes)

    @staticmethod
    def _find_cycles(nodes, edges):
        """All simple directed cycles (each a vertex list without the repeated
        start), deduplicated by canonical min-rotation. Bounded DFS — trivial for
        the small graphs here."""
        adj = {n: [] for n in nodes}
        for a, b in edges:
            if a in adj:
                adj[a].append(b)

        cycles = []
        seen = set()

        def canon(path):
            m = min(range(len(path)), key=lambda i: path[i])
            return tuple(path[m:] + path[:m])

        def dfs(start, node, stack, visited):
            for nxt in adj.get(node, []):
                if nxt == start and len(stack) >= 2:
                    key = canon(stack)
                    if key not in seen:
                        seen.add(key)
                        cycles.append(list(key))
                elif nxt not in visited:
                    dfs(start, nxt, stack + [nxt], visited | {nxt})

        for s in nodes:
            dfs(s, s, [s], {s})
        return cycles

    def _is_recoverable(self, ops):
        """RC: whenever Ti reads from Tj and ci in H, then cj < ci."""
        commit_idx = self._commit_index(ops)
        for reader, writer, _obj, _ridx in self._reads_from(ops):
            if reader in commit_idx:
                ci = commit_idx[reader]
                cj = commit_idx.get(writer)
                if cj is None or cj >= ci:
                    return False
        return True

    def _is_aca(self, ops):
        """ACA: whenever Ti reads from Tj, then cj < ri[x]."""
        commit_idx = self._commit_index(ops)
        for _reader, writer, _obj, ridx in self._reads_from(ops):
            cj = commit_idx.get(writer)
            if cj is None or cj >= ridx:
                return False
        return True

    def _is_strict(self, ops):
        """ST: for wj[x] < oi[x] (oi = ri[x] or wi[x], i != j), aj < oi[x] or
        cj < oi[x] — Tj must have ended before any other transaction accesses an
        object it wrote."""
        term = self._terminal_index(ops)
        by_obj = {}
        for i, op in enumerate(ops):
            if op["kind"] in ("r", "w"):
                by_obj.setdefault(op["obj"], []).append((i, op))
        for lst in by_obj.values():
            for a in range(len(lst)):
                ia, opa = lst[a]
                if opa["kind"] != "w":
                    continue
                for b in range(a + 1, len(lst)):
                    ib, opb = lst[b]
                    if opb["t"] == opa["t"]:
                        continue
                    tend = term.get(opa["t"])
                    if tend is None or tend >= ib:
                        return False
        return True

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def _gen_tx_sequence(self, t, terminal):
        """A single transaction's operation list: some read/writes followed by
        its terminal. Ensures a mix of reads and writes when it has >= 2
        operations, so reads-from relations are likely to form."""
        n = self.rng.randint(self.cfg["ops_min"], self.cfg["ops_max"])
        ops = [
            {"kind": self.rng.choice(["r", "w"]), "t": t, "obj": self.rng.choice(self.cfg["objects"])}
            for _ in range(n)
        ]
        if n >= 2 and len({o["kind"] for o in ops}) == 1:
            flip = self.rng.randrange(n)
            ops[flip]["kind"] = "w" if ops[flip]["kind"] == "r" else "r"
        ops.append({"kind": terminal, "t": t, "obj": None})
        return ops

    def _random_schedule(self, all_commit):
        """Random valid schedule: build each transaction's operations, then
        randomly merge them preserving per-transaction order. When
        ``all_commit`` is False, exactly one transaction aborts."""
        n_tx = self.cfg["n_tx"]
        abort_tx = None if all_commit else self.rng.randint(1, n_tx)
        seqs = [
            self._gen_tx_sequence(t, "a" if t == abort_tx else "c")
            for t in range(1, n_tx + 1)
        ]

        pointers = [0] * n_tx
        total = sum(len(s) for s in seqs)
        out = []
        while len(out) < total:
            avail = [i for i in range(n_tx) if pointers[i] < len(seqs[i])]
            i = self.rng.choice(avail)
            out.append(seqs[i][pointers[i]])
            pointers[i] += 1
        return out

    def _build(self):
        """Build a schedule matching the seed's target profile (serializable vs.
        not, with/without an abort) and a non-trivial conflict graph.

        Rather than returning the first match (which makes many seeds collapse to
        the same few shapes), a pool of *distinct* valid schedules is collected
        and one is chosen with the seeded RNG — giving much more variety per
        difficulty. An abort only leaves a non-trivial graph when ``n_tx >= 3``,
        so all-commit is forced otherwise. Schedules matching the serializability
        target are preferred; any non-trivial schedule is kept as a soft
        fallback, and the exercise histories as a last resort."""
        target_ser, all_commit = TARGET_PROFILES[self.seed % len(TARGET_PROFILES)]
        if self.cfg["n_tx"] < 3:
            all_commit = True

        on_target, off_target, seen = [], [], set()
        for _ in range(SEARCH_TRIES):
            ops = self._random_schedule(all_commit)
            edges, nodes = self._conflict_edges(ops)
            if not edges:
                continue  # trivial graph (no conflicts) — skip
            key = self._format_history(ops)
            if key in seen:
                continue
            seen.add(key)
            bucket = on_target if (not self._has_cycle(nodes, edges)) == target_ser else off_target
            bucket.append(ops)

        pool = on_target or off_target
        if pool:
            return self.rng.choice(pool)
        return parse_history(FALLBACK_HISTORIES[self.seed % len(FALLBACK_HISTORIES)])

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #
    @staticmethod
    def _fmt_op(op):
        if op["kind"] in ("r", "w"):
            return f"{op['kind']}{op['t']}[{op['obj']}]"
        return f"{op['kind']}{op['t']}"

    @classmethod
    def _format_history(cls, ops):
        return " ".join(cls._fmt_op(op) for op in ops)

    def _history_str(self):
        return self._format_history(self.ops)

    def _tx_label(self, t):
        return f"T{t}"

    def _step_table(self):
        """Step-by-step table: one row per operation, placed in its
        transaction's column."""
        columns = ["Schritt"] + [self._tx_label(t) for t in self.transactions]
        rows = []
        for i, op in enumerate(self.ops, start=1):
            row = [str(i)] + ["" for _ in self.transactions]
            row[1 + self.transactions.index(op["t"])] = self._fmt_op(op)
            rows.append(row)
        return {
            "type": "table",
            "label": "Historie (schrittweise)",
            "columns": columns,
            "rows": rows,
        }

    def _graph_payload(self):
        """Structured serializability-graph data for the read-only graph element
        and the builder-style ``expected`` struct."""
        return {
            "nodes": [self._tx_label(t) for t in self.graph_nodes],
            "edges": [[self._tx_label(a), self._tx_label(b)] for (a, b) in sorted(self.graph_edges)],
            "cycles": [[self._tx_label(t) for t in cyc] for cyc in self.graph_cycles],
            "serializable": self.props["is_serializable"],
            "aborted": [self._tx_label(t) for t in self.aborted],
        }

    # ------------------------------------------------------------------ #
    # Worked solution (instance-specific; only delivered via evaluate())
    # ------------------------------------------------------------------ #
    def _yesno(self, value):
        return "**Ja**" if value else "**Nein**"

    def _cycles_str(self):
        return "; ".join(
            " → ".join(self._tx_label(t) for t in (cyc + [cyc[0]])) for cyc in self.graph_cycles
        )

    def _serial_reason(self):
        if self.props["is_serial"]:
            return f"{self._yesno(True)} – keine Verzahnung."
        return f"{self._yesno(False)} – verzahnt."

    def _serializable_reason(self):
        if self.props["is_serializable"]:
            return f"{self._yesno(True)} – kein Zyklus (siehe oben)."
        return f"{self._yesno(False)} – Zyklus {self._cycles_str()} (siehe oben)."

    def _recoverable_reason(self):
        commit_idx = self._commit_index(self.ops)
        for reader, writer, obj, _ridx in self._reads_from(self.ops):
            if reader in commit_idx:
                cj = commit_idx.get(writer)
                if cj is None or cj >= commit_idx[reader]:
                    tail = (
                        f"`{self._tx_label(writer)}` committet nie"
                        if cj is None
                        else f"`c{writer}` liegt nicht vor `c{reader}`"
                    )
                    return (
                        f"{self._yesno(False)} – `{self._tx_label(reader)}` liest von "
                        f"`{self._tx_label(writer)}`, aber {tail}."
                    )
        return f"{self._yesno(True)}."

    def _aca_reason(self):
        commit_idx = self._commit_index(self.ops)
        for reader, writer, obj, ridx in self._reads_from(self.ops):
            cj = commit_idx.get(writer)
            if cj is None or cj >= ridx:
                return (
                    f"{self._yesno(False)} – `{self._tx_label(reader)}` liest `{obj}` von der "
                    f"noch nicht festgeschriebenen Transaktion `{self._tx_label(writer)}`."
                )
        return f"{self._yesno(True)}."

    def _strict_reason(self):
        term = self._terminal_index(self.ops)
        by_obj = {}
        for i, op in enumerate(self.ops):
            if op["kind"] in ("r", "w"):
                by_obj.setdefault(op["obj"], []).append((i, op))
        for obj, lst in by_obj.items():
            for a in range(len(lst)):
                ia, opa = lst[a]
                if opa["kind"] != "w":
                    continue
                for b in range(a + 1, len(lst)):
                    ib, opb = lst[b]
                    if opb["t"] == opa["t"]:
                        continue
                    tend = term.get(opa["t"])
                    if tend is None or tend >= ib:
                        return (
                            f"{self._yesno(False)} – `{opb['kind']}{opb['t']}[{obj}]` greift auf "
                            f"das von `{self._tx_label(opa['t'])}` geschriebene `{obj}` vor dessen "
                            "Ende zu."
                        )
        return f"{self._yesno(True)}."

    def _build_solution(self):
        return (
            f"- **seriell:** {self._serial_reason()}\n"
            f"- **serialisierbar:** {self._serializable_reason()}\n"
            f"- **rücksetzbar:** {self._recoverable_reason()}\n"
            f"- **ACA:** {self._aca_reason()}\n"
            f"- **strikt:** {self._strict_reason()}"
        )

    # ------------------------------------------------------------------ #
    # Layout + evaluation
    # ------------------------------------------------------------------ #
    def generate(self):
        checkboxes = [
            {"type": "checkbox_input", "id": fid, "label": label}
            for fid, label in PROPERTIES
        ]
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "### Eigenschaften von Historien\n\n"
                        "Gegeben ist eine Historie über die Operationen `r` (Lesen), "
                        "`w` (Schreiben), `c` (Commit) und `a` (Abort); die Zahl ist die "
                        "Transaktion, der Ausdruck in eckigen Klammern `[ ]` das "
                        "Datenobjekt. **Bestimme, welche der folgenden Eigenschaften die "
                        "Historie besitzt.**"
                    ),
                },
                {
                    "type": "Text",
                    "content": f"**Historie H:**\n\n`{self._history_str()}`",
                },
                self._step_table(),
                *checkboxes,
                {
                    "type": "serializability_graph",
                    "id": "graph",
                    "title": "Serialisierbarkeitsgraph",
                },
                {
                    "type": "solution_box",
                    "id": "solution",
                    "title": "Musterlösung",
                },
            ]
        }

    def evaluate(self, user_input):
        user_input = user_input or {}
        results = {}

        for fid, label in PROPERTIES:
            truth = bool(self.props[fid])
            chosen = bool(user_input.get(fid))
            results[fid] = {
                "correct": chosen == truth,
                "expected": "trifft zu" if truth else "trifft nicht zu",
            }

        # Serializability graph — always "correct" (display only); the worked
        # answer is delivered as a structured payload for the graph element.
        results["graph"] = {"correct": True, "expected": self._graph_payload()}

        # Worked solution — delivered only here (never in the question payload).
        results["solution"] = {"correct": True, "expected": self._build_solution()}

        return results

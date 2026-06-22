import json

from app.common import *


# Per-difficulty configuration.
# - n_tx            : number of transactions T1..Tn
# - n_elem          : number of data elements (a, b, c, ...)
# - want_cycles_min : for a deadlock instance, the preferred minimum number of
#                     distinct simple cycles (hard => several cycles sharing one
#                     vertex, like the lecture/exam example). Best-effort only.
# - min_edges       : for an acyclic instance, the minimum number of wait edges
#                     so the "no deadlock" case stays non-trivial (>= 2).
DIFFICULTY_SETTINGS = {
    "easy": {"n_tx": 3, "n_elem": 3, "want_cycles_min": 1, "min_edges": 2},
    "medium": {"n_tx": 4, "n_elem": 4, "want_cycles_min": 1, "min_edges": 2},
    "hard": {"n_tx": 5, "n_elem": 6, "want_cycles_min": 2, "min_edges": 3},
}

# Desired outcome (deadlock vs. acyclic), rotated by ``seed`` so both show up
# across seeds. Correctness is always computed exactly from the lock state; this
# only steers the distribution and is best-effort.
TARGET_DEADLOCK = [True, False]

# Probability that a given transaction has a pending lock request. Below 1.0 so
# the requests are spread *unevenly* across transactions — some transactions
# only hold locks and wait for nobody (the sinks of the wait-for graph).
REQUEST_PROB = 0.7

# Probability of *each additional* request beyond the first (kept much lower, so
# a transaction occasionally waits on more than one lock at once).
MULTI_REQUEST_PROB = 0.18

# Label of the dropdown option that means "no rollback needed".
ROLLBACK_NONE = "Keine Transaktion (keine Verklemmung)"


class WaitForGraphQuestion:
    """Erkenne Verklemmungen (Deadlocks) über den Wartegraph unter striktem
    Zwei-Phasen-Sperren (S2PL).

    Gegeben sind die von jeder Transaktion *gehaltenen* Sperren (``s`` = Shared /
    Lesesperre, ``x`` = Exclusive / Schreibsperre) sowie die *angeforderten*
    Sperren (Großbuchstaben ``S`` / ``X``). Die meisten Transaktionen fordern
    keine oder eine Sperre an; selten fordert eine Transaktion mehrere an
    gleichzeitig. Daraus wird der Wartegraph abgeleitet: ``Ti -> Tj`` genau dann,
    wenn ``Ti`` eine Sperre auf einem Element anfordert, die mit einer von ``Tj``
    gehaltenen Sperre in Konflikt steht (angeforderte S kollidiert mit gehaltener
    X; angeforderte X kollidiert mit gehaltener S oder X). Eine einzelne
    Anforderung kann mehrere Kanten erzeugen (z. B. ``T1`` fordert ``X(c)`` an,
    das ``T3`` und ``T4`` halten ``-> T1->T3, T1->T4``).

    Eine Verklemmung liegt genau dann vor, wenn der gerichtete Wartegraph einen
    Zyklus enthält. Die Auflösung erfolgt durch Zurücksetzen einer Transaktion,
    deren Entfernen den Graphen zyklenfrei macht. Alles wird deterministisch aus
    ``seed`` berechnet, womit die Aufgabe selbstprüfend ist.
    """

    def __init__(self, seed=None, difficulty="easy", **kwargs):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        cfg = DIFFICULTY_SETTINGS[self.difficulty]
        self.n_tx = cfg["n_tx"]
        self.n_elem = cfg["n_elem"]
        self.want_cycles_min = cfg["want_cycles_min"]
        self.min_edges = cfg["min_edges"]

        self.transactions = [f"T{i + 1}" for i in range(self.n_tx)]
        self.elements = [chr(ord("a") + i) for i in range(self.n_elem)]

        # held[tx][elem] in {"s", "x"}; requests[tx] = list of ("S"|"X", elem)
        # (empty when the transaction has no pending request).
        self.held, self.requests = self._build()

        # Ground-truth answer, computed up front (never recomputed in evaluate()).
        self.edges = self._derive_edges(self.held, self.requests)
        self.cycles = self._find_cycles(self.edges)
        self.deadlock = bool(self.cycles)
        self.valid_rollback = self._valid_rollbacks(self.edges)

    # ------------------------------------------------------------------ #
    # Core wait-for logic (pure helpers — operate on the arguments)
    # ------------------------------------------------------------------ #
    def _conflicts(self, ti, mode, e, held):
        """Transactions (other than ``ti``) that hold a lock on ``e`` conflicting
        with a request of mode ``mode``: a requested ``S`` conflicts with a held
        ``X``; a requested ``X`` conflicts with a held ``S`` or ``X``."""
        out = []
        for tj in self.transactions:
            if tj == ti:
                continue
            held_mode = held[tj].get(e)
            if held_mode is None:
                continue
            if mode == "X" or held_mode == "x":
                out.append(tj)
        return out

    def _derive_edges(self, held, requests):
        """Wait-for edges derived purely from the lock state (ground truth). A
        transaction may have several pending requests; its out-edges are the
        union of the conflicting holders over all of them."""
        edges = set()
        for ti, reqs in requests.items():
            for mode, e in reqs:
                for tj in self._conflicts(ti, mode, e, held):
                    edges.add((ti, tj))
        return edges

    def _has_cycle(self, edges):
        """True iff the directed graph over ``self.transactions`` with the given
        edge set contains a cycle (DFS three-colouring)."""
        adj = {t: [] for t in self.transactions}
        for a, b in edges:
            if a in adj:
                adj[a].append(b)

        WHITE, GREY, BLACK = 0, 1, 2
        color = {t: WHITE for t in self.transactions}

        def visit(u):
            color[u] = GREY
            for v in adj.get(u, []):
                if color.get(v, WHITE) == GREY:
                    return True
                if color.get(v, WHITE) == WHITE and visit(v):
                    return True
            color[u] = BLACK
            return False

        return any(color[t] == WHITE and visit(t) for t in self.transactions)

    def _find_cycles(self, edges):
        """All simple directed cycles, each as a vertex list (without the
        repeated start). Deduplicated by canonical (min-)rotation. Bounded DFS —
        trivial for the small graphs here (n_tx <= 5)."""
        adj = {t: [] for t in self.transactions}
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

        for s in self.transactions:
            dfs(s, s, [s], {s})
        return cycles

    def _valid_rollbacks(self, edges):
        """All transactions whose removal makes the graph acyclic. Empty when
        there is no deadlock."""
        if not self._has_cycle(edges):
            return set()
        out = set()
        for v in self.transactions:
            sub = {(a, b) for (a, b) in edges if a != v and b != v}
            if not self._has_cycle(sub):
                out.add(v)
        return out

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def _random_state(self):
        """A consistent held-lock state plus one request per transaction.

        Per element the holders are kept compatible: either any number of
        S-holders, or exactly one X-holder (with no S-holders), or none. Each
        transaction requests one element it does not already hold, biased toward
        elements held (conflictingly) by others so that wait edges form.
        """
        held = {t: {} for t in self.transactions}

        for e in self.elements:
            mode = self.rng.choice(["s", "x", "none"])
            if mode == "x":
                holder = self.rng.choice(self.transactions)
                held[holder][e] = "x"
            elif mode == "s":
                k = self.rng.randint(1, max(1, self.n_tx - 1))
                for t in self.rng.sample(self.transactions, k):
                    held[t][e] = "s"

        requests = {}
        for t in self.transactions:
            pool = [e for e in self.elements if e not in held[t]]
            # Unevenly distributed: not every transaction issues a request.
            if not pool or self.rng.random() >= REQUEST_PROB:
                requests[t] = []
                continue

            reqs = []
            held_by_others = [
                e for e in pool
                if any(e in held[o] for o in self.transactions if o != t)
            ]
            # First request — biased toward an element held (conflictingly) by
            # someone else so that a wait edge actually forms.
            if held_by_others and self.rng.random() < 0.85:
                first = self.rng.choice(held_by_others)
            else:
                first = self.rng.choice(pool)
            reqs.append((self.rng.choice(["S", "X"]), first))
            pool.remove(first)

            # Occasionally (much lower probability) ask for further locks.
            while pool and self.rng.random() < MULTI_REQUEST_PROB:
                extra = self.rng.choice(pool)
                reqs.append((self.rng.choice(["S", "X"]), extra))
                pool.remove(extra)

            requests[t] = reqs
        return held, requests

    def _build(self):
        """Try to hit the seed's target (deadlock vs. non-trivial acyclic).

        For a deadlock target, ``valid_rollback`` must be non-empty (a single
        transaction resolves every cycle); the search prefers instances with at
        least ``want_cycles_min`` cycles but keeps a simpler resolvable deadlock
        as a fallback. For an acyclic target, the graph must have no cycle and at
        least ``min_edges`` wait edges. Hand-crafted fallbacks guarantee a valid
        instance if the random search comes up empty.
        """
        target_deadlock = TARGET_DEADLOCK[self.seed % len(TARGET_DEADLOCK)]
        fallback = None

        for _ in range(2000):
            held, requests = self._random_state()
            edges = self._derive_edges(held, requests)

            if target_deadlock:
                if not self._has_cycle(edges):
                    continue
                if not self._valid_rollbacks(edges):
                    continue  # must be resolvable by rolling back one transaction
                if fallback is None:
                    fallback = (held, requests)
                if len(self._find_cycles(edges)) >= self.want_cycles_min:
                    return held, requests
            else:
                if self._has_cycle(edges):
                    continue
                if len(edges) < self.min_edges:
                    continue
                return held, requests

        if fallback is not None:
            return fallback
        return self._fallback_deadlock() if target_deadlock else self._fallback_acyclic()

    def _fallback_deadlock(self):
        """Guaranteed deadlock (the exam example): every cycle passes through
        ``T1``, so rolling back ``T1`` resolves all of them. Resets the labels to
        this fixed instance, mirroring the synthesis-algorithm fallbacks.

        Held:    T1 x(a), s(b), s(e);  T2 s(b);  T3 s(c), s(e);
                 T4 s(c), x(d), s(e);  T5 x(f).
        Requests: T1(X,c), T2(S,f), T3(X,b), T4(S,a), T5(X,d).
        Edges:   T1->{T3,T4}, T2->{T5}, T3->{T1,T2}, T4->{T1}, T5->{T4}.
        """
        self.transactions = ["T1", "T2", "T3", "T4", "T5"]
        self.elements = ["a", "b", "c", "d", "e", "f"]
        held = {
            "T1": {"a": "x", "b": "s", "e": "s"},
            "T2": {"b": "s"},
            "T3": {"c": "s", "e": "s"},
            "T4": {"c": "s", "d": "x", "e": "s"},
            "T5": {"f": "x"},
        }
        requests = {
            "T1": [("X", "c")],
            "T2": [("S", "f")],
            "T3": [("X", "b")],
            "T4": [("S", "a")],
            "T5": [("X", "d")],
        }
        return held, requests

    def _fallback_acyclic(self):
        """Guaranteed acyclic graph with two wait edges (non-trivial, no
        deadlock): T2 and T3 both wait for T1, which waits for nobody."""
        self.transactions = ["T1", "T2", "T3"]
        self.elements = ["a", "b", "c"]
        held = {"T1": {"a": "x"}, "T2": {"b": "s"}, "T3": {}}
        requests = {"T1": [], "T2": [("X", "a")], "T3": [("S", "a")]}
        return held, requests

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #
    def _fmt_held_for_tx(self, t):
        """e.g. ``T1(x, a), T1(s, b), T1(s, e)`` — held locks, lowercase mode."""
        parts = [f"{t}({mode}, {e})" for e, mode in sorted(self.held[t].items())]
        return ", ".join(parts) if parts else "—"

    def _fmt_request(self, t):
        """e.g. ``T1(X, c)`` or ``T1(X, c), T1(S, f)`` — requested lock(s),
        uppercase mode; ``—`` if the transaction requests nothing."""
        reqs = sorted(self.requests[t], key=lambda r: (r[1], r[0]))
        if not reqs:
            return "—"
        return ", ".join(f"{t}({mode}, {e})" for mode, e in reqs)

    def _fmt_one_request(self, t, mode, e):
        return f"{t}({mode}, {e})"

    def _fmt_edge(self, edge):
        a, b = edge
        return f"{a} → {b}"

    def _sorted_edges(self):
        return sorted(self.edges)

    def _edges_as_pairs(self):
        """Structured form for the builder's ``expected``: ``[["T1","T3"], ...]``."""
        return [[a, b] for (a, b) in self._sorted_edges()]

    # ------------------------------------------------------------------ #
    # Worked solution (instance-specific; only delivered via evaluate())
    # ------------------------------------------------------------------ #
    def _build_solution(self):
        deriv = []
        for t in self.transactions:
            for mode, e in sorted(self.requests[t], key=lambda r: (r[1], r[0])):
                targets = self._conflicts(t, mode, e, self.held)
                label = self._fmt_one_request(t, mode, e)
                if targets:
                    kind = "S- bzw. X-Sperre" if mode == "X" else "X-Sperre"
                    deriv.append(
                        f"- **{label}** wartet auf "
                        + ", ".join(sorted(targets))
                        + f" (Konflikt mit der auf **{e}** gehaltenen {kind})."
                    )
                else:
                    deriv.append(
                        f"- **{label}** wartet auf niemanden "
                        f"(keine konfliktäre Sperre auf **{e}**)."
                    )

        edges_txt = ", ".join(self._fmt_edge(x) for x in self._sorted_edges()) or "keine"

        if self.deadlock:
            cyc_txt = "; ".join(" → ".join(c + [c[0]]) for c in self.cycles)
            verdict = (
                f"Der Wartegraph enthält (mindestens) einen Zyklus: **{cyc_txt}**. "
                "Daraus folgt: Es liegt eine **Verklemmung (Deadlock)** vor."
            )
            roll = sorted(self.valid_rollback)
            roll_txt = (
                "Das Zurücksetzen einer der folgenden Transaktionen macht den "
                f"Wartegraphen zyklenfrei: **{', '.join(roll)}**. Es genügt, "
                "**eine** davon zurückzusetzen."
            )
        else:
            verdict = (
                "Der Wartegraph ist **zyklenfrei**, daher liegt **keine "
                "Verklemmung** vor."
            )
            roll_txt = (
                "Es muss **keine** Transaktion zurückgesetzt werden "
                f"(*{ROLLBACK_NONE}*)."
            )

        return (
            "#### Wartegraph ableiten\n\n"
            "Konfliktregel: Eine angeforderte **S**-Sperre steht im Konflikt mit "
            "einer gehaltenen **X**-Sperre; eine angeforderte **X**-Sperre steht "
            "im Konflikt mit einer gehaltenen **S- oder X**-Sperre. "
            "`Ti(s,a)` / `Ti(x,a)` = gehaltene Sperre, "
            "`Ti(S,a)` / `Ti(X,a)` = angeforderte Sperre.\n\n"
            + "\n".join(deriv)
            + f"\n\n**Kanten des Wartegraphen:** {edges_txt}.\n\n"
            "#### Verklemmung\n\n"
            f"{verdict}\n\n"
            "#### Rücksetzen\n\n"
            f"{roll_txt}"
        )

    # ------------------------------------------------------------------ #
    # Parsing of user input
    # ------------------------------------------------------------------ #
    def _parse_edges(self, raw):
        """Parse the builder's JSON string of directed edges into a set of
        ``(from, to)`` tuples. ``'[["T1","T3"],["T1","T4"]]'`` ->
        ``{("T1","T3"), ("T1","T4")}``. Malformed input -> empty set (never
        raises)."""
        valid = set(self.transactions)
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            return set()
        if not isinstance(data, (list, tuple)):
            return set()
        out = set()
        for item in data:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                return set()
            a, b = str(item[0]).strip(), str(item[1]).strip()
            if a not in valid or b not in valid or a == b:
                return set()
            out.add((a, b))
        return out

    # ------------------------------------------------------------------ #
    # Layout + evaluation
    # ------------------------------------------------------------------ #
    def generate(self):
        held_table = {
            "type": "table",
            "label": "Gehaltene Sperren",
            "columns": ["Transaktion", "Gehaltene Sperren"],
            "rows": [[t, self._fmt_held_for_tx(t)] for t in self.transactions],
        }
        request_table = {
            "type": "table",
            "label": "Angeforderte Sperren (je eine weitere Anforderung)",
            "columns": ["Transaktion", "Angeforderte Sperre"],
            "rows": [[t, self._fmt_request(t)] for t in self.transactions],
        }

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "### Wartegraph & Verklemmung (striktes 2PL)\n\n"
                        "Notation: `Ti(s, a)` / `Ti(x, a)` = `Ti` **hält** eine "
                        "S-/X-Sperre auf `a`; `Ti(S, a)` / `Ti(X, a)` = `Ti` "
                        "**fordert** sie an.\n\n"
                        "Zeichne den **Wartegraphen** (`Ti → Tj`, wenn `Ti` auf "
                        "eine konfliktäre Sperre von `Tj` wartet), entscheide, ob "
                        "eine **Verklemmung** vorliegt, und gib ggf. eine "
                        "zurückzusetzende Transaktion an."
                    ),
                },
                held_table,
                request_table,
                {
                    "type": "wait_for_graph_builder",
                    "id": "wait_for",
                    "transactions": list(self.transactions),
                    "title": "Wartegraph zeichnen",
                },
                {
                    "type": "multiple_choice",
                    "id": "deadlock_decision",
                    "label": "Liegt eine Verklemmung (Deadlock) vor?",
                    "options": ["Ja", "Nein"],
                },
                {
                    "type": "dropdown_input",
                    "id": "rollback_choice",
                    "label": "Welche Transaktion zurücksetzen?",
                    "options": list(self.transactions) + [ROLLBACK_NONE],
                    "placeholder": "Transaktion wählen…",
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

        # (1) Wait-for graph: parsed drawn edge set == expected edge set.
        drawn = self._parse_edges(user_input.get("wait_for"))
        results["wait_for"] = {
            "correct": drawn == set(self.edges),
            "expected": {
                "edges": self._edges_as_pairs(),
                "deadlock": self.deadlock,
                "cycles": [list(c) for c in self.cycles],
                "rollback": sorted(self.valid_rollback),
            },
        }

        # (2) Deadlock decision — graded vs. German "Ja"/"Nein".
        expected_decision = "Ja" if self.deadlock else "Nein"
        user_decision = str(user_input.get("deadlock_decision", "")).strip()
        results["deadlock_decision"] = {
            "correct": user_decision == expected_decision,
            "expected": expected_decision,
        }

        # (3) Rollback choice — any transaction that resolves all cycles is fine.
        choice = str(user_input.get("rollback_choice", "")).strip()
        if self.deadlock:
            correct = choice in self.valid_rollback
            expected_text = (
                "Eine der Transaktionen "
                + ", ".join(sorted(self.valid_rollback))
                + " zurücksetzen (eine genügt)."
            )
        else:
            correct = choice == ROLLBACK_NONE
            expected_text = ROLLBACK_NONE
        results["rollback_choice"] = {"correct": correct, "expected": expected_text}

        # (4) Worked solution — delivered only here (never in the question payload).
        results["solution"] = {"correct": True, "expected": self._build_solution()}

        return results

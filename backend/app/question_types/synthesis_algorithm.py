import itertools

from app.common import *


# Per-difficulty configuration.
# - n_attr    : number of attributes in the relation schema R
# - n_fd      : number of functional dependencies in F
# - lhs_sizes : pool the left-hand-side size is sampled from. Sizes >= 2 are what
#               make a left-reduction possible.
# - rhs_sizes : pool the right-hand-side size is sampled from. Sizes >= 2 (or a
#               transitively derivable single attribute) make a right-reduction
#               possible.
DIFFICULTY_SETTINGS = {
    "easy": {"n_attr": 4, "n_fd": 3, "lhs_sizes": [1, 1, 2], "rhs_sizes": [1, 1, 2]},
    "medium": {"n_attr": 5, "n_fd": 4, "lhs_sizes": [1, 2, 2], "rhs_sizes": [1, 2, 2]},
    "hard": {"n_attr": 6, "n_fd": 5, "lhs_sizes": [1, 2, 2, 3], "rhs_sizes": [1, 2, 3]},
}


class SynthesisAlgorithmQuestion:
    """Work through the 3NF synthesis algorithm step by step.

    Given a relation schema R and a set F of functional dependencies, the
    student performs — one verified step at a time — the calculation of the
    canonical cover (left reduction, right reduction, removal of ``α -> ∅``,
    union of equal left-hand sides) and the synthesis into 3NF relation schemas
    (build schemas, add a key relation if needed, drop contained schemas).

    Everything is computed deterministically from ``seed`` strictly following the
    lecture definitions (Folie 47 + 62). The left and right reductions are
    order-dependent, so a step can have **several** equally valid results. Grading
    follows the branch the student selected: every valid result of a step is
    accepted, and the submitted one becomes the basis for the following steps. If
    a step's answer is invalid, the deterministic sorted-order result is used as
    the basis so later steps can still be graded independently. ``mode`` only
    changes the layout:

    - ``steps`` : one view per step; all valid results of each step are shown
                  (via a ``solution_box`` delivered only through ``evaluate``),
                  the submitted one highlighted, serving as the starting point for
                  the next step.
    - ``exam``  : a single view with every step at once, one submission; every
                  step is graded along the path the student typed in, but no
                  results are revealed in between.
    """

    # Ordered (field_id, solution_box_id, short title) of the seven steps.
    STEP_IDS = [
        ("step_left", "sol_left", "Linksreduktion"),
        ("step_right", "sol_right", "Rechtsreduktion"),
        ("step_empty", "sol_empty", "Entferne α→∅"),
        ("step_union", "sol_union", "Vereinigung (kanonische Überdeckung)"),
        ("step_schemas", "sol_schemas", "Relationenschemata bilden"),
        ("step_key", "sol_key", "Schlüsselrelation ergänzen"),
        ("step_final", "sol_final", "Teilmengen-Schemata entfernen"),
    ]
    FD_STEPS = {"step_left", "step_right", "step_empty", "step_union"}

    def __init__(self, seed=None, difficulty="easy", mode="steps", **kwargs):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"

        self.mode = str(mode).lower() if mode else "steps"
        if self.mode not in ("steps", "exam"):
            self.mode = "steps"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        cfg = DIFFICULTY_SETTINGS[self.difficulty]
        self.n_attr = cfg["n_attr"]
        self.n_fd = cfg["n_fd"]
        self.lhs_sizes = list(cfg["lhs_sizes"])
        self.rhs_sizes = list(cfg["rhs_sizes"])

        self.attributes = [chr(ord("A") + i) for i in range(self.n_attr)]
        self.all_attrs = frozenset(self.attributes)

        self.fds = self._build()
        self._compute_chain()

    # ------------------------------------------------------------------ #
    # Core FD logic (pure helpers — operate on the arguments, not on self)
    # ------------------------------------------------------------------ #
    def _closure(self, attrs, fds):
        closure = set(attrs)
        changed = True
        while changed:
            changed = False
            for lhs, rhs in fds:
                if set(lhs) <= closure and not set(rhs) <= closure:
                    closure |= set(rhs)
                    changed = True
        return closure

    def _dedup(self, fds):
        """Deduplicate FDs and return them in a canonical, deterministic order.
        Empty right-hand sides are kept (they are only dropped in step 3)."""
        uniq = {(frozenset(lhs), frozenset(rhs)) for lhs, rhs in fds}
        return sorted(uniq, key=lambda fd: (sorted(fd[0]), sorted(fd[1])))

    def _left_reduce(self, fds):
        """Folie 47/48: for every FD α→β with |α|>1 and every X∈α, X is
        superfluous if β ⊆ (α∖{X})⁺ computed over the (progressively reduced) F.

        Processing the FDs in a canonical (sorted) order makes the result
        deterministic when FDs interact (e.g. two FDs share a left-hand side)."""
        work = [(set(lhs), set(rhs)) for lhs, rhs in self._dedup(fds)]
        for i in range(len(work)):
            lhs, rhs = work[i]
            if len(lhs) <= 1:
                continue
            for x in sorted(work[i][0]):  # snapshot of the original LHS
                if x not in lhs or len(lhs) <= 1:
                    continue
                cand = lhs - {x}
                if rhs <= self._closure(cand, work):
                    lhs = cand
                    work[i] = (lhs, rhs)  # commit so later tests see the reduction
            work[i] = (lhs, rhs)
        return self._dedup(work)

    def _right_reduce(self, fds):
        """Folie 47/53: for every FD α→β and every Y∈β, Y is superfluous if
        Y ∈ α⁺ computed over (F∖{α→β}) ∪ {α→(β∖{Y})}.

        Processing the FDs in a canonical (sorted) order makes the result
        deterministic when FDs interact (e.g. two FDs share a left-hand side)."""
        work = [(set(lhs), set(rhs)) for lhs, rhs in self._dedup(fds)]
        for i in range(len(work)):
            lhs, rhs = work[i]
            for y in sorted(work[i][1]):  # snapshot of the original RHS
                if y not in rhs:
                    continue
                trial = list(work)
                trial[i] = (lhs, rhs - {y})
                if y in self._closure(lhs, trial):
                    rhs = rhs - {y}
                    work[i] = (lhs, rhs)
            work[i] = (lhs, rhs)
        return self._dedup(work)

    def _remove_empty(self, fds):
        """Folie 47, step 3: drop FDs of the form α→∅."""
        return self._dedup([(lhs, rhs) for lhs, rhs in fds if rhs])

    def _union_same_lhs(self, fds):
        """Folie 47, step 4: α→β1, α→β2, … ⇒ α→β1∪β2∪…"""
        merged = {}
        for lhs, rhs in fds:
            merged.setdefault(frozenset(lhs), set()).update(rhs)
        return self._dedup([(lhs, rhs) for lhs, rhs in merged.items()])

    def _candidate_keys(self, all_attrs, fds):
        """All minimal attribute sets whose closure is the whole relation."""
        all_attrs = set(all_attrs)
        keys = []
        for size in range(1, len(all_attrs) + 1):
            for comb in itertools.combinations(sorted(all_attrs), size):
                cand = set(comb)
                if any(set(k) <= cand for k in keys):  # superset of a key -> not minimal
                    continue
                if self._closure(cand, fds) == all_attrs:
                    keys.append(frozenset(cand))
        return keys

    def _schemas_from_cover(self, cover):
        """Step 5: one schema R_i = α∪β per FD of the canonical cover."""
        return {frozenset(set(lhs) | set(rhs)) for lhs, rhs in cover}

    def _drop_contained(self, schemas):
        """Step 7: drop any schema that is a (proper) subset of another."""
        schemas = set(schemas)
        return {s for s in schemas if not any(s < t for t in schemas)}

    # ------------------------------------------------------------------ #
    # Normalisation + enumeration of ALL valid reduction results
    # ------------------------------------------------------------------ #
    def _norm_fds(self, fds):
        """Canonical hashable form of an FD set."""
        return frozenset((frozenset(lhs), frozenset(rhs)) for lhs, rhs in fds)

    def _norm_schemas(self, schemas):
        """Canonical hashable form of a set of relation schemas."""
        return frozenset(frozenset(s) for s in schemas)

    def _all_left_reductions(self, fds):
        """Every left-reduced FD set reachable by removing extraneous left
        attributes one at a time (Folie 47/48). The result is order-dependent, so
        in general there is more than one valid outcome; this returns all of them.
        The sorted-order result of ``_left_reduce`` is always among them."""
        seen, terminals, stack = set(), set(), [self._norm_fds(fds)]
        while stack:
            state = stack.pop()
            if state in seen:
                continue
            seen.add(state)
            work = [(set(lhs), set(rhs)) for lhs, rhs in state]
            moves = []
            for i, (lhs, rhs) in enumerate(work):
                if len(lhs) <= 1:
                    continue
                for x in sorted(lhs):
                    if rhs <= self._closure(lhs - {x}, work):
                        moves.append((i, x))
            if not moves:
                terminals.add(state)
                continue
            for i, x in moves:
                nxt = [(set(lhs), set(rhs)) for lhs, rhs in work]
                nxt[i] = (nxt[i][0] - {x}, nxt[i][1])
                stack.append(self._norm_fds(nxt))
        return terminals

    def _all_right_reductions(self, fds):
        """Every right-reduced FD set reachable by removing extraneous right
        attributes one at a time (Folie 47/53). As with the left reduction the
        outcome is order-dependent; this returns all valid results (FDs that
        become α→∅ are kept — they are only dropped in step 3). The sorted-order
        result of ``_right_reduce`` is always among them."""
        seen, terminals, stack = set(), set(), [self._norm_fds(fds)]
        while stack:
            state = stack.pop()
            if state in seen:
                continue
            seen.add(state)
            work = [(set(lhs), set(rhs)) for lhs, rhs in state]
            moves = []
            for i, (lhs, rhs) in enumerate(work):
                for y in sorted(rhs):
                    trial = list(work)
                    trial[i] = (lhs, rhs - {y})
                    if y in self._closure(lhs, trial):
                        moves.append((i, y))
            if not moves:
                terminals.add(state)
                continue
            for i, y in moves:
                nxt = [(set(lhs), set(rhs)) for lhs, rhs in work]
                nxt[i] = (nxt[i][0], nxt[i][1] - {y})
                stack.append(self._norm_fds(nxt))
        return terminals

    # ------------------------------------------------------------------ #
    # Deterministic computation of the whole chain
    # ------------------------------------------------------------------ #
    def _compute_chain(self):
        self.f0 = self._dedup(self.fds)
        self.f1 = self._left_reduce(self.f0)
        self.f2 = self._right_reduce(self.f1)
        self.f3 = self._remove_empty(self.f2)
        self.cover = self._union_same_lhs(self.f3)  # F_c

        self.schemas = self._schemas_from_cover(self.cover)  # S5
        self.keys = self._candidate_keys(self.all_attrs, self.f0)
        self.key_contained = any(
            set(k) <= s for s in self.schemas for k in self.keys
        )
        self.chosen_key = min(self.keys, key=lambda k: (len(k), sorted(k))) if self.keys else None

        self.schemas_with_key = set(self.schemas)
        if not self.key_contained and self.chosen_key is not None:
            self.schemas_with_key.add(frozenset(self.chosen_key))  # S6

        self.final_schemas = self._drop_contained(self.schemas_with_key)  # S7
        self.removed_schemas = self.schemas_with_key - self.final_schemas

    # ------------------------------------------------------------------ #
    # Instance generation
    # ------------------------------------------------------------------ #
    def _generate_candidate_fd(self):
        attrs = self.attributes
        lhs_size = min(self.rng.choice(self.lhs_sizes), len(attrs) - 1)
        lhs = set(self.rng.sample(attrs, lhs_size))
        rhs_pool = [a for a in attrs if a not in lhs]
        if not rhs_pool:
            return None
        rhs_size = min(self.rng.choice(self.rhs_sizes), len(rhs_pool))
        rhs = set(self.rng.sample(rhs_pool, rhs_size))
        return frozenset(lhs), frozenset(rhs)

    def _generate_fds(self):
        fds = []
        seen = set()
        tries = 0
        while len(fds) < self.n_fd and tries < 500:
            tries += 1
            cand = self._generate_candidate_fd()
            if cand is None:
                continue
            if cand in seen:
                continue
            seen.add(cand)
            fds.append(cand)
        return fds

    def _evaluate_instance(self, fds):
        """Run the full chain on ``fds`` and return quality metrics used to steer
        generation toward instances that exercise the algorithm."""
        f0 = self._dedup(fds)
        if not f0:
            return None
        if {a for lhs, rhs in f0 for a in set(lhs) | set(rhs)} != set(self.attributes):
            return None  # every attribute must appear in some FD (no lost attributes)

        f1 = self._left_reduce(f0)
        f2 = self._right_reduce(f1)
        f3 = self._remove_empty(f2)
        cover = self._union_same_lhs(f3)
        schemas = self._schemas_from_cover(cover)
        keys = self._candidate_keys(self.all_attrs, f0)
        key_contained = any(set(k) <= s for s in schemas for k in keys)
        s6 = set(schemas)
        if not key_contained and keys:
            s6.add(frozenset(min(keys, key=lambda k: (len(k), sorted(k)))))
        s7 = self._drop_contained(s6)
        covered = set().union(*s7) if s7 else set()

        return {
            "left_changed": set(f1) != set(f0),
            "right_changed": set(f2) != set(f1),
            "empty_removed": len(f2) != len(f3),
            "union_changed": len(cover) < len(f3),
            "num_schemas": len(schemas),
            "num_final": len(s7),
            "single_key": len(keys) == 1,
            "has_key": bool(keys),
            "covers_all": covered == set(self.attributes),
        }

    def _meets_difficulty(self, m):
        common = (
            m["num_schemas"] >= 2
            and m["num_final"] >= 2
            and m["has_key"]
            and m["covers_all"]
        )
        if not common:
            return False
        reduction_any = m["left_changed"] or m["right_changed"] or m["empty_removed"] or m["union_changed"]
        if self.difficulty == "medium":
            return reduction_any
        if self.difficulty == "hard":
            return m["left_changed"] and (m["right_changed"] or m["empty_removed"])
        return True  # easy

    def _build(self):
        """Generate (R, F) that exercise the algorithm. Prefer instances with a
        single candidate key (so step 6 is unambiguous) that meet the difficulty
        criteria; fall back to anything sensible."""
        fallback = None
        soft = None  # meets difficulty but multiple keys
        for _ in range(3000):
            fds = self._generate_fds()
            if len(fds) < self.n_fd:
                continue
            m = self._evaluate_instance(fds)
            if m is None:
                continue
            if fallback is None and m["num_schemas"] >= 2 and m["has_key"] and m["covers_all"]:
                fallback = fds
            if self._meets_difficulty(m):
                if m["single_key"]:
                    return fds
                if soft is None:
                    soft = fds
        if soft is not None:
            return soft
        if self.difficulty == "hard":
            return self._hard_fallback()
        return fallback or self._safe_fallback()

    def _safe_fallback(self):
        """A tiny hand-made instance guaranteeing a valid, non-trivial chain that
        covers every attribute (two schemas, a single key)."""
        attrs = self.attributes
        a, b, c = attrs[0], attrs[1], attrs[2]
        rest = attrs[3:]
        second = frozenset(rest) if rest else frozenset({c})
        return [
            (frozenset({a}), frozenset({b, c})),
            (frozenset({b}), second),
        ]

    def _hard_fallback(self):
        """A constructed 6-attribute instance that provably exercises both a left
        reduction (AB→C collapses to A→C) and a right reduction (A→DE collapses to
        A→D), used only if the random search comes up empty for ``hard``."""
        a, b, c, d, e, f = self.attributes[:6]
        return [
            (frozenset({a}), frozenset({c})),
            (frozenset({a, b}), frozenset({c})),
            (frozenset({a}), frozenset({d, e})),
            (frozenset({d}), frozenset({e})),
            (frozenset({e}), frozenset({f})),
        ]

    # ------------------------------------------------------------------ #
    # Parsing of user input
    # ------------------------------------------------------------------ #
    def _letters_to_attrs(self, text):
        """Parse a side like ``"A, B"``, ``"AB"`` or ``"A B"`` into a set of
        attributes. Returns ``None`` for unknown attributes / empty input."""
        text = str(text).strip().upper()
        if not text:
            return None
        valid = set(self.attributes)
        out = set()
        for tok in (t for t in re.split(r"[,\s]+", text) if t):
            if len(tok) == 1:
                if tok not in valid:
                    return None
                out.add(tok)
            else:  # concatenated attributes, e.g. "AB"
                for ch in tok:
                    if ch not in valid:
                        return None
                    out.add(ch)
        return out or None

    def _parse_fds(self, raw):
        """Parse an FD set. Empty -> set(); malformed -> None.
        Accepts ``->``/``→``/``=>``, ``;``/newline between FDs."""
        text = str(raw or "").strip()
        if not text:
            return set()
        text = text.replace("→", "->").replace("⟶", "->").replace("=>", "->")
        out = set()
        for part in re.split(r"[;\n]+", text):
            piece = part.strip()
            if not piece:
                continue
            if "->" not in piece:
                return None
            lhs_raw, rhs_raw = piece.split("->", 1)
            lhs = self._letters_to_attrs(lhs_raw)
            if lhs is None:
                return None
            # An empty right-hand side (α→∅) is a valid intermediate FD: it can
            # arise from the right reduction and is only dropped in step 3.
            rhs_stripped = rhs_raw.strip()
            if rhs_stripped.lower() in ("", "∅", "{}", "{ }", "\\empty", "\\emptyset", "\\leer"):
                rhs = set()
            else:
                rhs = self._letters_to_attrs(rhs_stripped)
                if rhs is None:
                    return None
            out.add((frozenset(lhs), frozenset(rhs)))
        return out

    def _parse_relation_set(self, raw):
        """Parse a set of relation schemas like ``"{A,B}; {C,D}"`` (relation
        names and brackets optional). Empty -> set(); malformed -> None."""
        text = str(raw or "").strip()
        if not text:
            return set()
        out = set()
        for part in re.split(r"[;\n]+", text):
            piece = part.strip()
            if not piece:
                continue
            m = re.search(r"[({\[](.*)[)}\]]", piece)
            inner = m.group(1) if m else piece
            attrs = self._letters_to_attrs(inner)
            if attrs is None:
                return None
            out.add(frozenset(attrs))
        return out

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #
    def _fmt_fd(self, fd):
        lhs, rhs = fd
        rhs_txt = "".join(sorted(rhs)) if rhs else "∅"
        return f"{''.join(sorted(lhs))} → {rhs_txt}"

    def _fmt_fds(self, fds):
        if not fds:
            return "∅"
        return ";  ".join(self._fmt_fd(fd) for fd in self._dedup(fds))

    def _fmt_set(self, s):
        return "{" + ", ".join(sorted(s)) + "}"

    def _fmt_schemas(self, schemas):
        if not schemas:
            return "∅"
        ordered = sorted(schemas, key=lambda s: (len(s), sorted(s)))
        return ";  ".join(self._fmt_set(s) for s in ordered)

    def _keys_text(self):
        ordered = sorted(self.keys, key=lambda k: (len(k), sorted(k)))
        return ", ".join(self._fmt_set(k) for k in ordered) if ordered else "∅"

    # ------------------------------------------------------------------ #
    # Per-step worked solutions (delivered only via evaluate())
    #
    # A step can have more than one valid result (the left/right reduction are
    # order-dependent). The solution lists every valid result for the step *given
    # the branch the student selected in the previous steps* and highlights the
    # selected one; from there only that branch is followed.
    # ------------------------------------------------------------------ #
    def _fmt_value(self, field_id, value):
        if field_id in self.FD_STEPS:
            return self._fmt_fds(value)
        return self._fmt_schemas(value)

    def _format_options_block(self, field_id, info):
        options = info["options"]
        selected = info["selected"]
        ordered = sorted(options, key=lambda o: self._fmt_value(field_id, o))
        if len(ordered) <= 1:
            return f"**{self._fmt_value(field_id, selected)}**"

        lines = []
        for opt in ordered:
            text = self._fmt_value(field_id, opt)
            if opt == selected:
                lines.append(f"- ✅ **{text}**  ← deine Auswahl (wird weiter berücksichtigt)")
            else:
                lines.append(f"- {text}")
        note = (
            "\n\n*Mehrere Ergebnisse sind gültig – **alle** oben gelisteten sind korrekt. "
            "Für die folgenden Schritte wird deine abgegebene (hervorgehobene) Lösung "
            "weiter berücksichtigt.*"
        )
        return "Gültige Ergebnisse:\n" + "\n".join(lines) + note

    def _solution_builder(self, sol_id, path):
        field_id = next(f for f, s, _t in self.STEP_IDS if s == sol_id)
        return self._format_options_block(field_id, path[field_id])

    def _full_solution(self, path):
        parts = [
            "### Synthesealgorithmus – Musterlösung",
            f"R({', '.join(self.attributes)}), F = **{self._fmt_fds(self.f0)}**, "
            f"Kandidatenschlüssel: **{self._keys_text()}**.",
        ]
        for index, (field_id, _sol_id, title) in enumerate(self.STEP_IDS, start=1):
            parts.append(
                f"#### {index}. Schritt – {title}\n\n"
                + self._format_options_block(field_id, path[field_id])
            )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ #
    # Expected answers + grading per step
    # ------------------------------------------------------------------ #
    def _expected_value(self, field_id):
        return {
            "step_left": lambda: set(self.f1),
            "step_right": lambda: set(self.f2),
            "step_empty": lambda: set(self.f3),
            "step_union": lambda: set(self.cover),
            "step_schemas": lambda: set(self.schemas),
            "step_key": lambda: set(self.schemas_with_key),
            "step_final": lambda: set(self.final_schemas),
        }[field_id]()

    def _expected_text(self, field_id):
        if field_id in self.FD_STEPS:
            return self._fmt_fds(self._expected_value(field_id))
        return self._fmt_schemas(self._expected_value(field_id))

    def _resolve_path(self, user_input):
        """Walk the solution tree following the student's submitted answers.

        At each branching step the student's answer becomes the basis for the
        following steps *iff* it is one of the valid results for that step;
        otherwise the deterministic sorted-order result is used as the basis so
        later steps can still be graded (independent carry-forward). Returns, per
        step field, the set of all valid results (``options``) and the selected
        basis (``selected``)."""
        ui = user_input or {}

        def choose(field_id, options, default):
            parser = self._parse_fds if field_id in self.FD_STEPS else self._parse_relation_set
            raw = ui.get(field_id)
            parsed = parser(raw) if raw is not None else None
            selected = default
            if parsed is not None:
                norm = (self._norm_fds(parsed) if field_id in self.FD_STEPS
                        else self._norm_schemas(parsed))
                if norm in options:
                    selected = norm
            return {"options": set(options), "selected": selected}

        path = {}

        # Step 1 — left reduction (branching)
        left_opts = self._all_left_reductions(self.f0)
        path["step_left"] = choose("step_left", left_opts, self._norm_fds(self.f1))
        sel_left = path["step_left"]["selected"]

        # Step 2 — right reduction from the selected left result (branching)
        right_opts = self._all_right_reductions(sel_left)
        path["step_right"] = choose(
            "step_right", right_opts, self._norm_fds(self._right_reduce(sel_left))
        )
        sel_right = path["step_right"]["selected"]

        # Step 3 — remove α→∅ (deterministic given the branch)
        sel_f3 = self._norm_fds(self._remove_empty(sel_right))
        path["step_empty"] = choose("step_empty", {sel_f3}, sel_f3)

        # Step 4 — union (deterministic)
        sel_cover = self._norm_fds(self._union_same_lhs(sel_f3))
        path["step_union"] = choose("step_union", {sel_cover}, sel_cover)

        # Step 5 — build schemas (deterministic)
        sel_schemas = self._norm_schemas(self._schemas_from_cover(sel_cover))
        path["step_schemas"] = choose("step_schemas", {sel_schemas}, sel_schemas)

        # Step 6 — key relation (branches over candidate keys when none is contained)
        schemas_set = set(sel_schemas)
        key_contained = any(set(k) <= s for s in schemas_set for k in self.keys)
        if key_contained or not self.keys:
            key_opts = {sel_schemas}
            default_key = sel_schemas
        else:
            key_opts = {self._norm_schemas(schemas_set | {frozenset(k)}) for k in self.keys}
            default_key = self._norm_schemas(schemas_set | {frozenset(self.chosen_key)})
        path["step_key"] = choose("step_key", key_opts, default_key)
        sel_s6 = path["step_key"]["selected"]

        # Step 7 — drop contained schemas (deterministic given the branch)
        sel_final = self._norm_schemas(self._drop_contained(set(sel_s6)))
        path["step_final"] = choose("step_final", {sel_final}, sel_final)

        return path

    def _grade_step(self, field_id, raw, path):
        info = path[field_id]
        parser = self._parse_fds if field_id in self.FD_STEPS else self._parse_relation_set
        parsed = parser(raw) if raw is not None else None
        correct = False
        if parsed is not None:
            norm = (self._norm_fds(parsed) if field_id in self.FD_STEPS
                    else self._norm_schemas(parsed))
            correct = norm in info["options"]
        return {"correct": bool(correct), "expected": self._fmt_value(field_id, info["selected"])}

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _intro_markdown(self):
        return (
            "### Synthesealgorithmus (3NF)\n\n"
            f"Gegeben sei die Relation **R({', '.join(self.attributes)})** mit den "
            f"funktionalen Abhängigkeiten\n\n**F = {self._fmt_fds(self.f0)}**.\n\n"
            "Führe den 3NF-Synthesealgorithmus schrittweise durch. FD-Mengen im "
            "Format `AB->C; D->E`, Schemamengen im Format `{A,B}; {C,D}`.\n\n"
            "*Tipp: Für die leere Menge ∅ kannst du `\\empty` eingeben.*"
        )

    def _step_prompt(self, field_id):
        return {
            "step_left": "**1. Schritt – Linksreduktion.** Gib die FD-Menge nach der Linksreduktion an.",
            "step_right": "**2. Schritt – Rechtsreduktion.** Gib die FD-Menge nach der Rechtsreduktion an.",
            "step_empty": "**3. Schritt – Entferne α→∅.** Streiche FDs mit leerer rechter Seite.",
            "step_union": "**4. Schritt – Vereinigung.** Fasse FDs mit gleicher linker Seite zur kanonischen Überdeckung Fc zusammen.",
            "step_schemas": "**5. Schritt – Relationenschemata.** Bilde für jede FD aus Fc ein Relationenschema.",
            "step_key": "**6. Schritt – Schlüsselrelation.** Ergänze eine Relation mit einem Kandidatenschlüssel, falls kein Schema einen enthält.",
            "step_final": "**7. Schritt – Teilmengen entfernen.** Gib das Endschema an (entferne enthaltene Schemata).",
        }[field_id]

    def _input_label(self, field_id):
        return {
            "step_left": "FD-Menge nach Linksreduktion",
            "step_right": "FD-Menge nach Rechtsreduktion",
            "step_empty": "FD-Menge nach Entfernen von α→∅",
            "step_union": "Kanonische Überdeckung Fc",
            "step_schemas": "Relationenschemata",
            "step_key": "Schemata (ggf. mit Schlüsselrelation)",
            "step_final": "Endschema",
        }[field_id]

    def _input_element(self, field_id):
        return {
            "type": "text_input",
            "id": field_id,
            "rows": 3,
            "label": self._input_label(field_id),
        }

    def _steps_layout(self):
        layout = {}
        for index, (field_id, sol_id, title) in enumerate(self.STEP_IDS, start=1):
            elements = []
            if index == 1:
                elements.append({"type": "Text", "content": self._intro_markdown()})
            elements.append({"type": "Text", "content": self._step_prompt(field_id)})
            elements.append(self._input_element(field_id))
            elements.append({
                "type": "solution_box",
                "id": sol_id,
                "title": f"Ergebnis: {title}",
            })
            layout[f"view{index}"] = elements
        return layout

    def _exam_layout(self):
        elements = [{"type": "Text", "content": self._intro_markdown()}]
        for field_id, _sol_id, _title in self.STEP_IDS:
            elements.append({"type": "Text", "content": self._step_prompt(field_id)})
            elements.append(self._input_element(field_id))
        elements.append({
            "type": "solution_box",
            "id": "solution",
            "title": "Musterlösung",
        })
        return {"view1": elements}

    def generate(self):
        if self.mode == "exam":
            return self._exam_layout()
        return self._steps_layout()

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def evaluate(self, user_input):
        user_input = user_input or {}
        path = self._resolve_path(user_input)
        results = {}

        for field_id, sol_id, _title in self.STEP_IDS:
            results[field_id] = self._grade_step(field_id, user_input.get(field_id), path)
            # All valid results for the selected branch (submitted one highlighted)
            # — delivered only here, so it never leaks through the question payload.
            results[sol_id] = {"correct": True, "expected": self._solution_builder(sol_id, path)}

        # Full worked solution along the selected path (exam mode).
        results["solution"] = {"correct": True, "expected": self._full_solution(path)}
        return results

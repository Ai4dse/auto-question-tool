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
    lecture definitions (Folie 47 + 62). Each step is graded against the
    *canonical* chain, so the verified intermediate result of one step is always
    the starting point for the next — independent of what the student entered
    before. ``mode`` only changes the layout:

    - ``steps`` : one view per step; the verified result of each step is shown
                  (via a ``solution_box`` delivered only through ``evaluate``) and
                  serves as the visible starting point for the next step.
    - ``exam``  : a single view with every step at once, one submission, every
                  step graded, but no intermediate results revealed in between.
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
            if rhs_stripped in ("", "∅", "{}", "{ }"):
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
    # ------------------------------------------------------------------ #
    def _sol_left(self):
        return (
            "**Linksreduktion.** Prüfe für jede FD α→β mit |α|>1 und jedes X∈α, ob "
            "β ⊆ (α∖{X})⁺ bzgl. F. Falls ja, ist X überflüssig.\n\n"
            f"Ergebnis: **{self._fmt_fds(self.f1)}**"
        )

    def _sol_right(self):
        return (
            "**Rechtsreduktion.** Prüfe für jede FD α→β und jedes Y∈β, ob "
            "Y ∈ α⁺ bzgl. (F∖{α→β}) ∪ {α→(β∖{Y})}. Falls ja, ist Y überflüssig.\n\n"
            f"Ergebnis: **{self._fmt_fds(self.f2)}**"
        )

    def _sol_empty(self):
        if len(self.f2) == len(self.f3):
            return (
                "**Entferne α→∅.** Es gibt keine FD mit leerer rechter Seite – keine "
                f"Änderung.\n\nErgebnis: **{self._fmt_fds(self.f3)}**"
            )
        return (
            "**Entferne α→∅.** FDs mit leerer rechter Seite (durch die Rechtsreduktion "
            "entstanden) werden gestrichen.\n\n"
            f"Ergebnis: **{self._fmt_fds(self.f3)}**"
        )

    def _sol_union(self):
        note = (
            "FDs mit gleicher linker Seite werden zusammengefasst."
            if len(self.cover) < len(self.f3)
            else "Keine zwei FDs teilen sich eine linke Seite – keine Zusammenfassung nötig."
        )
        return (
            f"**Vereinigung.** {note}\n\n"
            f"Kanonische Überdeckung **Fc = {self._fmt_fds(self.cover)}**"
        )

    def _sol_schemas(self):
        return (
            "**Schemata bilden.** Für jede FD α→β ∈ Fc entsteht ein Relationenschema "
            "R_i = α ∪ β.\n\n"
            f"Schemata: **{self._fmt_schemas(self.schemas)}**"
        )

    def _sol_key(self):
        if self.key_contained:
            return (
                f"**Schlüsselrelation.** Ein Kandidatenschlüssel (Kandidatenschlüssel: "
                f"{self._keys_text()}) ist bereits in einem Schema enthalten – keine "
                "zusätzliche Relation nötig.\n\n"
                f"Schemata: **{self._fmt_schemas(self.schemas_with_key)}**"
            )
        return (
            "**Schlüsselrelation.** Kein Schema enthält einen Kandidatenschlüssel von R "
            f"(Kandidatenschlüssel: {self._keys_text()}). Ergänze eine Relation mit dem "
            f"Schlüssel K = {self._fmt_set(self.chosen_key)}.\n\n"
            f"Schemata: **{self._fmt_schemas(self.schemas_with_key)}**"
        )

    def _sol_final(self):
        if self.removed_schemas:
            removed = self._fmt_schemas(self.removed_schemas)
            note = f"Entferne in anderen Schemata enthaltene Schemata ({removed})."
        else:
            note = "Kein Schema ist in einem anderen enthalten – keine Entfernung nötig."
        return (
            f"**Teilmengen entfernen.** {note}\n\n"
            f"Endschema: **{self._fmt_schemas(self.final_schemas)}**"
        )

    def _solution_builder(self, sol_id):
        return {
            "sol_left": self._sol_left,
            "sol_right": self._sol_right,
            "sol_empty": self._sol_empty,
            "sol_union": self._sol_union,
            "sol_schemas": self._sol_schemas,
            "sol_key": self._sol_key,
            "sol_final": self._sol_final,
        }[sol_id]()

    def _full_solution(self):
        return (
            "### Synthesealgorithmus – Musterlösung\n\n"
            f"Gegeben: **R({', '.join(self.attributes)})**, "
            f"F = **{self._fmt_fds(self.f0)}**.\n\n"
            f"Kandidatenschlüssel von R: **{self._keys_text()}**.\n\n"
            "#### Schritt 1 — " + self._sol_left() + "\n\n"
            "#### Schritt 2 — " + self._sol_right() + "\n\n"
            "#### Schritt 3 — " + self._sol_empty() + "\n\n"
            "#### Schritt 4 — " + self._sol_union() + "\n\n"
            "#### Schritt 5 — " + self._sol_schemas() + "\n\n"
            "#### Schritt 6 — " + self._sol_key() + "\n\n"
            "#### Schritt 7 — " + self._sol_final()
        )

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

    def _grade_step(self, field_id, raw):
        expected = self._expected_value(field_id)
        if field_id in self.FD_STEPS:
            parsed = self._parse_fds(raw)
        else:
            parsed = self._parse_relation_set(raw)

        if field_id == "step_key" and not self.key_contained and self.keys:
            # Any candidate key is an acceptable addition, not only the chosen one.
            correct = parsed is not None and any(
                parsed == (set(self.schemas) | {frozenset(k)}) for k in self.keys
            )
        else:
            correct = parsed is not None and parsed == expected

        return {"correct": bool(correct), "expected": self._expected_text(field_id)}

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _intro_markdown(self):
        return (
            "### Synthesealgorithmus (3NF)\n\n"
            f"Gegeben sei die Relation **R({', '.join(self.attributes)})** mit den "
            f"funktionalen Abhängigkeiten\n\n**F = {self._fmt_fds(self.f0)}**.\n\n"
            "Führen Sie den 3NF-Synthesealgorithmus schrittweise durch. FD-Mengen im "
            "Format `AB->C; D->E`, Schemamengen im Format `{A,B}; {C,D}`."
        )

    def _step_prompt(self, field_id):
        return {
            "step_left": (
                "**Schritt 1 – Linksreduktion.** Entfernen Sie überflüssige Attribute "
                "auf den linken Seiten (nur bei FDs mit mehr als einem Attribut links). "
                "Geben Sie die FD-Menge **nach** der Linksreduktion an."
            ),
            "step_right": (
                "**Schritt 2 – Rechtsreduktion.** Ausgangspunkt ist die linksreduzierte "
                "FD-Menge aus Schritt 1 (siehe Musterlösung oben). Entfernen Sie "
                "überflüssige Attribute auf den rechten Seiten."
            ),
            "step_empty": (
                "**Schritt 3 – Entferne α→∅.** Streichen Sie aus dem Ergebnis von "
                "Schritt 2 (siehe oben) alle FDs mit leerer rechter Seite."
            ),
            "step_union": (
                "**Schritt 4 – Vereinigung.** Fassen Sie FDs mit gleicher linker Seite "
                "zusammen. Das Ergebnis ist die **kanonische Überdeckung Fc**."
            ),
            "step_schemas": (
                "**Schritt 5 – Schemata bilden.** Bilden Sie für jede FD α→β aus Fc "
                "(Schritt 4, siehe oben) ein Relationenschema R_i = α ∪ β. Geben Sie die "
                "Schemata als Mengen an, z.B. `{A,B}; {C,D}`."
            ),
            "step_key": (
                "**Schritt 6 – Schlüsselrelation.** Falls **kein** Schema aus Schritt 5 "
                "einen Kandidatenschlüssel von R enthält, ergänzen Sie eine Relation mit "
                "einem Kandidatenschlüssel. Geben Sie die (ggf. ergänzte) Schemamenge an."
            ),
            "step_final": (
                "**Schritt 7 – Teilmengen entfernen.** Entfernen Sie Schemata, die "
                "vollständig in einem anderen Schema enthalten sind. Geben Sie das "
                "**Endschema** an."
            ),
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
        results = {}

        for field_id, sol_id, _title in self.STEP_IDS:
            results[field_id] = self._grade_step(field_id, user_input.get(field_id))
            # Verified intermediate result (steps mode) — delivered only here, so
            # it never leaks through the question payload.
            results[sol_id] = {"correct": True, "expected": self._solution_builder(sol_id)}

        # Full worked solution (exam mode).
        results["solution"] = {"correct": True, "expected": self._full_solution()}
        return results

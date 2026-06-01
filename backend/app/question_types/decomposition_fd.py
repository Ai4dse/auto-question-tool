from app.common import *


# Per-difficulty configuration.
# - n_attr      : number of attributes in the relation schema R
# - n_fd        : number of functional dependencies in F
# - lhs_sizes   : pool the left-hand-side size is sampled from
# - max_overlap : largest allowed |R1 ∩ R2| (the shared attributes)
DIFFICULTY_SETTINGS = {
    "easy": {"n_attr": 4, "n_fd": 3, "lhs_sizes": [1, 1], "max_overlap": 1},
    "medium": {"n_attr": 5, "n_fd": 4, "lhs_sizes": [1, 1, 2], "max_overlap": 2},
    "hard": {"n_attr": 6, "n_fd": 5, "lhs_sizes": [1, 2, 2], "max_overlap": 2},
}

# Desired (lossless, dependency-preserving) outcome, rotated by ``seed`` so that
# every combination shows up across seeds. Correctness is always computed
# exactly; this only steers the distribution and is best-effort.
TARGET_COMBOS = [(True, True), (True, False), (False, True), (False, False)]


class DecompositionFDQuestion:
    """Decide whether a binary decomposition of R into R1 and R2 is
    lossless-join and/or dependency-preserving w.r.t. a set of functional
    dependencies F.

    The schema R, the FD set F and the decomposition {R1, R2} are generated
    locally and deterministically from ``seed``. The two properties are computed
    exactly (tableau chase for the lossless-join test, the projection/closure
    algorithm for dependency preservation), so the question is self-checking.
    """

    def __init__(self, seed=None, difficulty="easy", **kwargs):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        cfg = DIFFICULTY_SETTINGS[self.difficulty]
        self.n_attr = cfg["n_attr"]
        self.n_fd = cfg["n_fd"]
        self.lhs_sizes = list(cfg["lhs_sizes"])
        self.max_overlap = cfg["max_overlap"]

        self.attributes = [chr(ord("A") + i) for i in range(self.n_attr)]

        self.fds, self.fragments = self._build()
        self.lossless = self._lossless(self.fragments, self.fds)
        self.preserving = self._preserving(self.fragments, self.fds)

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def _generate_fds(self):
        attrs = self.attributes
        fds = []
        seen = set()

        tries = 0
        while len(fds) < self.n_fd and tries < 500:
            tries += 1
            lhs_size = min(self.rng.choice(self.lhs_sizes), len(attrs) - 1)
            lhs = frozenset(self.rng.sample(attrs, lhs_size))
            rhs_pool = [a for a in attrs if a not in lhs]
            rhs = frozenset({self.rng.choice(rhs_pool)})

            sig = (lhs, rhs)
            if sig in seen:
                continue
            seen.add(sig)
            fds.append((lhs, rhs))

        return fds

    def _generate_decomposition(self):
        """Split R into two proper, overlapping fragments whose union is R."""
        attrs = self.attributes
        n = len(attrs)

        overlap_size = self.rng.randint(1, min(self.max_overlap, n - 2))
        overlap = set(self.rng.sample(attrs, overlap_size))

        rest = [a for a in attrs if a not in overlap]
        self.rng.shuffle(rest)
        cut = self.rng.randint(1, len(rest) - 1)

        r1 = frozenset(overlap | set(rest[:cut]))
        r2 = frozenset(overlap | set(rest[cut:]))
        return [r1, r2]

    def _build(self):
        """Try to hit the seed's target combination; fall back to any instance."""
        desired = TARGET_COMBOS[self.seed % len(TARGET_COMBOS)]
        fallback = None

        for _ in range(800):
            fds = self._generate_fds()
            frags = self._generate_decomposition()
            outcome = (self._lossless(frags, fds), self._preserving(frags, fds))

            if fallback is None:
                fallback = (fds, frags)
            if outcome == desired:
                return fds, frags

        return fallback

    # ------------------------------------------------------------------ #
    # Core FD logic (pure helpers — operate on the arguments, not on self)
    # ------------------------------------------------------------------ #
    def _closure(self, attrs, fds):
        closure = set(attrs)
        changed = True
        while changed:
            changed = False
            for lhs, rhs in fds:
                if lhs <= closure and not rhs <= closure:
                    closure |= rhs
                    changed = True
        return closure

    def _lossless(self, fragments, fds):
        """Tableau-chase test for the lossless-join property.

        One tableau row per fragment: attribute ``a`` gets the distinguished
        symbol ``("a", a)`` if it belongs to the fragment, otherwise a distinct
        symbol ``("b", row, a)``. FDs are applied until a fixpoint: rows that
        agree on the LHS are forced to agree on the RHS (preferring the
        distinguished symbol). The decomposition is lossless iff some row ends
        up entirely distinguished.
        """
        attrs = self.attributes
        rows = []
        for i, frag in enumerate(fragments):
            rows.append({a: ("a", a) if a in frag else ("b", i, a) for a in attrs})

        changed = True
        while changed:
            changed = False
            for lhs, rhs in fds:
                lhs_attrs = sorted(lhs)
                groups = {}
                for i, row in enumerate(rows):
                    key = tuple(row[a] for a in lhs_attrs)
                    groups.setdefault(key, []).append(i)

                for idxs in groups.values():
                    if len(idxs) < 2:
                        continue
                    for b in rhs:
                        symbols = [rows[i][b] for i in idxs]
                        target = next((s for s in symbols if s[0] == "a"), None)
                        if target is None:
                            target = min(symbols, key=lambda s: s[1])
                        for i in idxs:
                            if rows[i][b] != target:
                                rows[i][b] = target
                                changed = True

        return any(all(row[a][0] == "a" for a in attrs) for row in rows)

    def _preserving(self, fragments, fds):
        """Projection/closure test for dependency preservation.

        For each FD ``X -> Y`` in F, grow ``Z`` (starting at X) by repeatedly
        adding ``(Z ∩ Ri)+ ∩ Ri`` for every fragment Ri. The FD is preserved iff
        Y ends up inside Z. The decomposition is dependency-preserving iff every
        FD in F is preserved.
        """
        for lhs, rhs in fds:
            z = set(lhs)
            changed = True
            while changed:
                changed = False
                for frag in fragments:
                    t = self._closure(z & frag, fds) & frag
                    if not t <= z:
                        z |= t
                        changed = True
            if not rhs <= z:
                return False
        return True

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #
    def _format_fd(self, fd):
        lhs, rhs = fd
        return f"{''.join(sorted(lhs))} -> {''.join(sorted(rhs))}"

    def _format_relation(self, name, frag):
        return f"{name}({', '.join(sorted(frag))})"

    def _fmt_set(self, s):
        return "{" + ", ".join(sorted(s)) + "}"

    # ------------------------------------------------------------------ #
    # Worked solution (instance-specific; only delivered via evaluate())
    # ------------------------------------------------------------------ #
    def _explain_lossless(self):
        r1, r2 = set(self.fragments[0]), set(self.fragments[1])
        overlap = r1 & r2
        clos = self._closure(overlap, self.fds)
        r1_ok = r1 <= clos
        r2_ok = r2 <= clos

        parts = [
            f"R1 ∩ R2 = {self._fmt_set(overlap)}, mit Hülle (R1 ∩ R2)⁺ = {self._fmt_set(clos)}.",
            f"R1 = {self._fmt_set(r1)} {'⊆' if r1_ok else '⊄'} (R1 ∩ R2)⁺  ·  "
            f"R2 = {self._fmt_set(r2)} {'⊆' if r2_ok else '⊄'} (R1 ∩ R2)⁺.",
        ]
        if r1_ok or r2_ok:
            which = "R1" if r1_ok else "R2"
            parts.append(
                f"Da (R1 ∩ R2) → {which} ∈ F⁺ gilt, ist die Zerlegung **verlustfrei**."
            )
        else:
            parts.append(
                "Da die gemeinsamen Attribute weder R1 noch R2 bestimmen, ist die "
                "Zerlegung **verlustbehaftet** (R1 ⋈ R2 erzeugt Zusatztupel)."
            )
        return " ".join(parts)

    def _explain_preservation(self):
        """One markdown bullet per FD, tracing how (or whether) it can be
        rebuilt from the locally checkable FDs of the fragments."""
        lines = []
        for lhs, rhs in self.fds:
            z = set(lhs)
            steps = []  # (fragment_name, used_attrs, gained_attrs)
            done = rhs <= z
            # Prefer fragments that contain an RHS attribute, so the trace
            # reaches the goal directly instead of taking detours.
            order = sorted(
                range(len(self.fragments)),
                key=lambda i: 0 if (self.fragments[i] & rhs) else 1,
            )
            changed = True
            while changed and not done:
                changed = False
                for i in order:
                    frag = self.fragments[i]
                    local = z & frag
                    if not local:
                        continue
                    gained = (self._closure(local, self.fds) & frag) - z
                    if gained:
                        steps.append((f"R{i + 1}", set(local), set(gained)))
                        z |= gained
                        changed = True
                        if rhs <= z:  # stop as soon as the RHS is reached
                            done = True
                            break

            fd_str = f"{''.join(sorted(lhs))} → {''.join(sorted(rhs))}"
            if rhs <= z:
                if steps:
                    trace = "; ".join(
                        f"über {name}: {self._fmt_set(used)} → {self._fmt_set(gained)}"
                        for name, used, gained in steps
                    )
                    lines.append(f"- **{fd_str}** ✓ — {trace}.")
                else:
                    lines.append(f"- **{fd_str}** ✓ — direkt lokal prüfbar.")
            else:
                lines.append(
                    f"- **{fd_str}** ✗ — lokal nur {self._fmt_set(z)} ableitbar, "
                    f"{self._fmt_set(rhs)} nicht erreichbar."
                )
        return lines

    def _build_solution(self):
        lossless_txt = self._explain_lossless()
        pres_lines = "\n".join(self._explain_preservation())
        if self.preserving:
            pres_concl = (
                "Da alle FDs aus F so rekonstruierbar sind, ist die Zerlegung "
                "**abhängigkeitsbewahrend**."
            )
        else:
            pres_concl = (
                "Da mindestens eine FD aus F nicht rekonstruierbar ist, ist die "
                "Zerlegung **nicht abhängigkeitsbewahrend**."
            )

        return (
            "#### Verlustfreiheit\n\n"
            "Kriterium: verlustfrei ⇔ (R1 ∩ R2) → R1 ∈ F⁺ **oder** (R1 ∩ R2) → R2 ∈ F⁺.\n\n"
            f"{lossless_txt}\n\n"
            "#### Abhängigkeitsbewahrung\n\n"
            "Kriterium: bewahrend ⇔ (F1 ∪ F2)⁺ = F⁺. Eine FD darf auch *indirekt* über "
            "die gemeinsamen Attribute erzwingbar sein. Prüfung pro FD:\n\n"
            f"{pres_lines}\n\n"
            f"{pres_concl}"
        )

    # ------------------------------------------------------------------ #
    # Layout + evaluation
    # ------------------------------------------------------------------ #
    def generate(self):
        attr_text = ", ".join(self.attributes)
        fd_text = "; ".join(self._format_fd(fd) for fd in self.fds)
        r1_text = self._format_relation("R1", self.fragments[0])
        r2_text = self._format_relation("R2", self.fragments[1])

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "### Verlustfreiheit & Abhängigkeitsbewahrung\n\n"
                        f"Gegeben sei die Relation **R({attr_text})**\n\n"
                        f"mit den funktionalen Abhängigkeiten **{fd_text}**.\n\n"
                        "Die Relation wird zerlegt in:\n\n"
                        f"- **{r1_text}**\n"
                        f"- **{r2_text}**"
                    ),
                },
                {
                    "type": "multiple_choice",
                    "id": "lossless_decision",
                    "label": "Ist die Zerlegung verlustfrei?",
                    "options": ["Ja", "Nein"],
                },
                {
                    "type": "multiple_choice",
                    "id": "preserving_decision",
                    "label": "Ist die Zerlegung abhängigkeitsbewahrend?",
                    "options": ["Ja", "Nein"],
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

        for field_id, prop in (
            ("lossless_decision", self.lossless),
            ("preserving_decision", self.preserving),
        ):
            expected = "Ja" if prop else "Nein"
            user_decision = str(user_input.get(field_id, "")).strip()
            results[field_id] = {
                "correct": user_decision == expected,
                "expected": expected,
            }

        # Detailed worked solution — delivered only here (after submission), so
        # it is never part of the question payload sent up front.
        results["solution"] = {"correct": True, "expected": self._build_solution()}

        return results

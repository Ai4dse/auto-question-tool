import itertools

from app.common import *


# Per-difficulty configuration.
# - n_attr    : number of attributes in the relation schema R
# - n_fd      : number of functional dependencies in F
# - lhs_sizes : pool the left-hand-side size is sampled from. A size of 2 is
#               what makes 3NF-but-higher and partial-dependency cases possible.
# - domain    : value domain for the sample instance (kept small so FDs bite)
# - base_size : target number of rows in the sample instance
DIFFICULTY_SETTINGS = {
    "easy": {"n_attr": 3, "n_fd": 3, "lhs_sizes": [1, 1, 2], "domain": [1, 2, 3, 4, 5], "base_size": 3},
    "medium": {"n_attr": 4, "n_fd": 4, "lhs_sizes": [1, 1, 2], "domain": [1, 2, 3, 4, 5], "base_size": 3},
    "hard": {"n_attr": 5, "n_fd": 5, "lhs_sizes": [1, 2, 2], "domain": [1, 2, 3, 4, 5, 6], "base_size": 4},
}

# Answer indicating R is not even in 1NF (non-atomic values).
NONE_NF = "Keine NF"

# Selectable answers, lowest to highest.
NF_OPTIONS = [NONE_NF, "1NF", "2NF", "3NF"]
NF_RANK = {NONE_NF: 0, "1NF": 1, "2NF": 2, "3NF": 3}

# Target answer, rotated by ``seed`` so every level shows up across seeds.
# Correctness is always computed exactly; this only steers the distribution.
TARGET_NFS = [NONE_NF, "1NF", "2NF", "3NF"]


class NormalFormsFDQuestion:
    """Determine the highest normal form (Keine NF / 1NF / 2NF / 3NF) a relation
    R is in with respect to a set of functional dependencies F.

    The schema R, the FD set F and a small sample instance are generated locally
    and deterministically from ``seed``. Candidate keys, prime attributes and the
    2NF/3NF tests are computed exactly from the textbook definitions (not from
    simplified course-slide heuristics). 1NF cannot be decided from R and F
    alone: whether a value is atomic is only visible in an actual instance, so a
    sample instance is always shown. Some instances contain a non-atomic
    (multi-valued) cell, in which case R is not even in 1NF -> "Keine NF".
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
        self.domain = list(cfg["domain"])
        self.base_size = cfg["base_size"]

        self.attributes = [chr(ord("A") + i) for i in range(self.n_attr)]
        self.all_attrs = set(self.attributes)

        self.fds, self.atomic = self._build()
        self.candidate_keys = self._candidate_keys(self.all_attrs, self.fds)
        self.prime_attributes = self._prime_attributes(self.candidate_keys)

        # FD-based normal form assuming atomicity (1NF/2NF/3NF); the actual
        # answer is "Keine NF" when the instance turns out non-atomic.
        self.fd_based_nf = self._highest_nf(self.all_attrs, self.fds)
        self.highest_nf = self.fd_based_nf if self.atomic else NONE_NF

        # Sample instance (always shown). nonatomic_cells holds (row, attr) of
        # the multi-valued cells when the relation is meant to violate 1NF.
        self.nonatomic_cells = []
        self.instance = self._build_instance()
        if not self.atomic:
            self._inject_multivalues()

    # ------------------------------------------------------------------ #
    # FD generation
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

    def _is_interesting(self, fds):
        """Skip degenerate instances that make 2NF/3NF hold vacuously: there
        must be at least one non-prime attribute."""
        keys = self._candidate_keys(self.all_attrs, fds)
        prime = self._prime_attributes(keys)
        return bool(self.all_attrs - prime)

    def _first_interesting_fds(self):
        fallback = None
        for _ in range(800):
            fds = self._generate_fds()
            if fallback is None:
                fallback = fds
            if self._is_interesting(fds):
                return fds
        return fallback

    def _fds_for_target(self, target):
        """Best-effort: find an interesting FD set whose FD-based NF == target."""
        fallback = None
        for _ in range(800):
            fds = self._generate_fds()
            if not self._is_interesting(fds):
                continue
            if fallback is None:
                fallback = fds
            if self._highest_nf(self.all_attrs, fds) == target:
                return fds
        return fallback if fallback is not None else self._generate_fds()

    def _build(self):
        """Pick the seed's target answer and return (fds, atomic).

        For "Keine NF" the FD-based level is irrelevant (the answer is driven by
        non-atomicity), so any interesting FD set will do.
        """
        target = TARGET_NFS[self.seed % len(TARGET_NFS)]
        if target == NONE_NF:
            return self._first_interesting_fds(), False
        return self._fds_for_target(target), True

    # ------------------------------------------------------------------ #
    # Sample instance
    # ------------------------------------------------------------------ #
    def _random_tuple(self):
        return {a: self.rng.choice(self.domain) for a in self.attributes}

    def _key(self, t):
        return tuple(t[a] for a in self.attributes)

    def _violates_fds(self, t, instance):
        """True if adding ``t`` to ``instance`` would break any FD."""
        for lhs, rhs in self.fds:
            for s in instance:
                if all(s[a] == t[a] for a in lhs) and any(s[b] != t[b] for b in rhs):
                    return True
        return False

    def _build_instance(self):
        """A small FD-consistent instance (only scalar values)."""
        instance = []
        attempts = 0
        while len(instance) < self.base_size and attempts < 600:
            attempts += 1
            t = self._random_tuple()
            if any(self._key(t) == self._key(s) for s in instance):
                continue
            if not self._violates_fds(t, instance):
                instance.append(t)

        if not instance:  # a single row trivially satisfies every FD
            instance.append(self._random_tuple())
        return instance

    def _inject_multivalues(self):
        """Turn 1-2 cells of one attribute into multi-valued (list) cells, so
        the instance visibly violates 1NF."""
        attr = self.rng.choice(self.attributes)
        n_rows = len(self.instance)
        k = min(self.rng.randint(1, 2), n_rows)
        for ri in sorted(self.rng.sample(range(n_rows), k)):
            base = self.instance[ri][attr]
            others = [v for v in self.domain if v != base]
            extra = self.rng.choice(others) if others else base
            self.instance[ri][attr] = [base, extra]
            self.nonatomic_cells.append((ri, attr))

    def _format_cell(self, value):
        if isinstance(value, list):
            return "{" + ", ".join(str(v) for v in value) + "}"
        return str(value)

    def _instance_rows(self):
        return [[self._format_cell(t[a]) for a in self.attributes] for t in self.instance]

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

    def _candidate_keys(self, all_attrs, fds):
        """All minimal attribute sets whose closure is the whole relation."""
        all_attrs = set(all_attrs)
        attrs_sorted = sorted(all_attrs)
        keys = []

        for size in range(1, len(attrs_sorted) + 1):
            for comb in itertools.combinations(attrs_sorted, size):
                cand = set(comb)
                if any(k <= cand for k in keys):  # superset of a key -> not minimal
                    continue
                if self._closure(cand, fds) == all_attrs:
                    keys.append(frozenset(cand))

        return keys

    def _prime_attributes(self, keys):
        prime = set()
        for k in keys:
            prime |= set(k)
        return prime

    def _is_2nf(self, all_attrs, fds, keys, prime):
        """No non-prime attribute is partially dependent on a candidate key.

        Closure is monotone, so testing the maximal proper subsets ``K \\ {x}``
        of every key suffices."""
        nonprime = set(all_attrs) - prime
        for k in keys:
            if len(k) < 2:
                continue
            for x in k:
                if self._closure(set(k) - {x}, fds) & nonprime:
                    return False
        return True

    def _is_3nf(self, all_attrs, fds, prime):
        """For every non-trivial X -> A: X is a superkey or A is prime.
        Testing the given FDs is exact for 3NF (standard theorem)."""
        all_attrs = set(all_attrs)
        for lhs, rhs in fds:
            for a in rhs:
                if a in lhs:
                    continue
                if self._closure(lhs, fds) == all_attrs or a in prime:
                    continue
                return False
        return True

    def _highest_nf(self, all_attrs, fds):
        """FD-based highest normal form, assuming atomicity (1NF/2NF/3NF)."""
        all_attrs = set(all_attrs)
        keys = self._candidate_keys(all_attrs, fds)
        prime = self._prime_attributes(keys)

        if self._is_3nf(all_attrs, fds, prime):
            return "3NF"
        if self._is_2nf(all_attrs, fds, keys, prime):
            return "2NF"
        return "1NF"

    # ------------------------------------------------------------------ #
    # Violation finders (used by the worked solution)
    # ------------------------------------------------------------------ #
    def _partial_dependencies(self):
        """Distinct (subkey, attr) pairs witnessing a 2NF violation."""
        nonprime = self.all_attrs - self.prime_attributes
        out = []
        seen = set()
        for k in self.candidate_keys:
            if len(k) < 2:
                continue
            for x in sorted(k):
                subkey = frozenset(set(k) - {x})
                for a in sorted(self._closure(subkey, self.fds) & nonprime):
                    if (subkey, a) in seen:
                        continue
                    seen.add((subkey, a))
                    out.append((subkey, a))
        return out

    def _transitive_violations(self):
        """FDs X -> A violating 3NF: X not a superkey and A not prime."""
        out = []
        for lhs, rhs in self.fds:
            for a in sorted(rhs):
                if a in lhs:
                    continue
                if self._closure(lhs, self.fds) != self.all_attrs and a not in self.prime_attributes:
                    out.append((lhs, a))
        return out

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #
    def _format_fd(self, fd):
        lhs, rhs = fd
        return f"{''.join(sorted(lhs))} → {''.join(sorted(rhs))}"

    def _fmt_set(self, s):
        return "{" + ", ".join(sorted(s)) + "}"

    def _fmt_closure(self, attrs):
        return f"{''.join(sorted(attrs))}⁺ = {self._fmt_set(self._closure(attrs, self.fds))}"

    # ------------------------------------------------------------------ #
    # Worked solution (instance-specific; only delivered via evaluate())
    # ------------------------------------------------------------------ #
    def _explain_2nf(self):
        if not (self.all_attrs - self.prime_attributes):
            return ("2NF erfüllt", "Es gibt keine Nicht-Primattribute, daher ist 2NF trivial erfüllt.")

        if all(len(k) < 2 for k in self.candidate_keys):
            return (
                "2NF erfüllt",
                "Jeder Kandidatenschlüssel ist einelementig, daher kann kein Nicht-Primattribut "
                "von einem *echten* Teil eines Schlüssels abhängen.",
            )

        parts = self._partial_dependencies()
        if not parts:
            return (
                "2NF erfüllt",
                "Kein Nicht-Primattribut hängt von einer echten Teilmenge eines "
                "Kandidatenschlüssels ab (keine partielle Abhängigkeit).",
            )

        subkey, a = parts[0]
        return (
            "2NF verletzt",
            f"Das Nicht-Primattribut **{a}** hängt schon von der echten Teilmenge "
            f"{self._fmt_set(subkey)} eines Kandidatenschlüssels ab "
            f"({self._fmt_closure(subkey)} ∋ {a}) — eine partielle Abhängigkeit.",
        )

    def _explain_3nf(self):
        viol = self._transitive_violations()
        if not viol:
            return (
                "3NF erfüllt",
                "Für jede nichttriviale FD ist die linke Seite ein Superschlüssel "
                "oder die rechte Seite ein Primattribut.",
            )
        lhs, a = viol[0]
        return (
            "3NF verletzt",
            f"Die FD **{''.join(sorted(lhs))} → {a}** verletzt 3NF: "
            f"{self._fmt_closure(lhs)} ist kein Superschlüssel und **{a}** ist kein "
            f"Primattribut (transitive Abhängigkeit).",
        )

    def _solution_non_atomic(self):
        ri, attr = self.nonatomic_cells[0]
        value = self._format_cell(self.instance[ri][attr])
        return (
            "#### 1. Normalform (1NF)\n\n"
            "*Kriterium:* alle Attributwerte sind atomar (keine mehrwertigen oder "
            "zusammengesetzten Einträge).\n\n"
            f"In der Beispielausprägung enthält Spalte **{attr}** in Zeile **{ri + 1}** den "
            f"mehrwertigen Wert **{value}** — kein atomarer Wert. Damit ist R **nicht in 1. "
            "Normalform**; funktionale Abhängigkeiten und höhere Normalformen setzen 1NF "
            "voraus und werden daher nicht weiter betrachtet.\n\n"
            "#### Ergebnis\n\n"
            f"Die höchste erfüllte Normalform ist **{NONE_NF}**."
        )

    def _build_solution(self):
        if not self.atomic:
            return self._solution_non_atomic()

        keys_text = ", ".join(
            self._fmt_set(k) for k in sorted(self.candidate_keys, key=lambda k: (len(k), sorted(k)))
        )
        prime_text = self._fmt_set(self.prime_attributes) if self.prime_attributes else "∅"
        nonprime = self.all_attrs - self.prime_attributes
        nonprime_text = self._fmt_set(nonprime) if nonprime else "∅"

        v2, e2 = self._explain_2nf()
        rank = NF_RANK[self.highest_nf]

        lines = [
            "#### Kandidatenschlüssel & Primattribute",
            "",
            f"- Kandidatenschlüssel: **{keys_text}**",
            f"- Primattribute: {prime_text}  ·  Nicht-Primattribute: {nonprime_text}",
            "",
            "#### 1. Normalform (1NF)",
            "",
            "*Kriterium:* alle Attributwerte sind atomar.",
            "",
            "Alle Werte der Beispielausprägung sind atomar → **1NF erfüllt**.",
            "",
            "#### 2. Normalform (2NF)",
            "",
            "*Kriterium:* kein Nicht-Primattribut hängt von einer echten Teilmenge eines Kandidatenschlüssels ab.",
            "",
            f"**{v2}.** {e2}",
            "",
            "#### 3. Normalform (3NF)",
            "",
            "*Kriterium:* für jede nichttriviale FD X → A ist X Superschlüssel **oder** A ein Primattribut.",
            "",
        ]

        if rank < NF_RANK["2NF"]:
            lines.append("**3NF verletzt.** Da bereits 2NF verletzt ist, kann 3NF nicht gelten (3NF ⟹ 2NF).")
        else:
            _, e3 = self._explain_3nf()
            v3 = "3NF erfüllt" if rank >= NF_RANK["3NF"] else "3NF verletzt"
            lines.append(f"**{v3}.** {e3}")

        lines += [
            "",
            "#### Ergebnis",
            "",
            f"Die höchste erfüllte Normalform ist **{self.highest_nf}**.",
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Layout + evaluation
    # ------------------------------------------------------------------ #
    def generate(self):
        attr_text = ", ".join(self.attributes)
        fd_text = "; ".join(self._format_fd(fd) for fd in self.fds)

        instance_table = {
            "type": "table",
            "label": "Beispielausprägung von R",
            "columns": list(self.attributes),
            "rows": self._instance_rows(),
        }

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "### Normalform bestimmen\n\n"
                        f"Gegeben sei die Relation **R({attr_text})** mit den funktionalen "
                        f"Abhängigkeiten **{fd_text}** sowie der unten stehenden Beispielausprägung.\n\n"
                        "Bestimmen Sie die **höchste** Normalform, in der R vorliegt."
                    ),
                },
                instance_table,
                {
                    "type": "multiple_choice",
                    "id": "highest_nf",
                    "label": "Höchste erfüllte Normalform",
                    "options": list(NF_OPTIONS),
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

        user_choice = str(user_input.get("highest_nf", "")).strip()
        results = {
            "highest_nf": {
                "correct": user_choice == self.highest_nf,
                "expected": self.highest_nf,
            },
            # Detailed worked solution — delivered only here (after submission),
            # so it is never part of the question payload sent up front.
            "solution": {"correct": True, "expected": self._build_solution()},
        }
        return results

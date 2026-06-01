from app.common import *


# Per-difficulty configuration.
# - n_attr / n_fd  : size of the relation schema and FD set
# - lhs_sizes       : pool the left-hand-side size is sampled from
#                     ([1] => only single-attribute determinants, easiest to read)
# - base_size       : number of tuples in the current (consistent) instance
# - domain          : small value domain so tuples frequently agree on a LHS,
#                     which is what makes FD violations possible
# - targets         : desired multiset of violation counts across the candidates
DIFFICULTY_SETTINGS = {
    "easy": {
        "n_attr": 3,
        "n_fd": 2,
        "lhs_sizes": [1],
        "base_size": 3,
        # domain larger than base_size guarantees an unused determinant value,
        # so insertable (non-duplicate) tuples always exist
        "domain": [1, 2, 3, 4],
        "targets": [0, 0, 1, 1, 1],
    },
    "medium": {
        "n_attr": 4,
        "n_fd": 3,
        "lhs_sizes": [1, 1, 2],
        "base_size": 4,
        "domain": [1, 2, 3, 4, 5],
        "targets": [0, 0, 1, 1, 2],
    },
    "hard": {
        "n_attr": 5,
        "n_fd": 5,
        "lhs_sizes": [1, 2, 2],
        "base_size": 4,
        "domain": [1, 2, 3, 4, 5],
        "targets": [0, 1, 1, 2, 2],
    },
}

NUM_TUPLES = 5


class TupleInsertionFDQuestion:
    """Decide whether candidate tuples can be inserted into a relation without
    violating any functional dependency. If not, name the violating FD(s).

    The schema R, the FD set, a small consistent instance and the candidate
    tuples are all generated locally so that difficulty (schema width, FD count
    and FD complexity) can be tuned precisely.
    """

    def __init__(self, seed=None, difficulty="easy", num_tuples=None, **kwargs):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        cfg = DIFFICULTY_SETTINGS[self.difficulty]
        self.domain = list(cfg["domain"])
        self.base_size = cfg["base_size"]
        self.lhs_sizes = list(cfg["lhs_sizes"])
        self.targets = list(cfg["targets"])
        self.num_tuples = int(num_tuples) if num_tuples else NUM_TUPLES

        self.attributes, self.fds = self._generate_relation(cfg["n_attr"], cfg["n_fd"])
        self.instance = self._build_instance()
        self.candidates = self._build_candidates()

    # ------------------------------------------------------------------ #
    # Schema + FD generation
    # ------------------------------------------------------------------ #
    def _generate_relation(self, n_attr, n_fd):
        attributes = [chr(ord("A") + i) for i in range(n_attr)]
        fds = []
        seen = set()

        tries = 0
        while len(fds) < n_fd and tries < 500:
            tries += 1
            lhs_size = min(self.rng.choice(self.lhs_sizes), n_attr - 1)
            lhs = set(self.rng.sample(attributes, lhs_size))
            rhs_pool = [a for a in attributes if a not in lhs]
            rhs = {self.rng.choice(rhs_pool)}

            sig = (tuple(sorted(lhs)), tuple(sorted(rhs)))
            if sig in seen:
                continue
            seen.add(sig)
            fds.append((lhs, rhs))

        return attributes, fds

    # ------------------------------------------------------------------ #
    # Core FD logic
    # ------------------------------------------------------------------ #
    def _violations(self, t, instance):
        """Return the list of FD indices that inserting ``t`` would violate.

        Since ``instance`` already satisfies every FD, a violation can only
        involve the new tuple: FD ``X -> Y`` is violated iff some existing tuple
        agrees with ``t`` on ``X`` but disagrees on ``Y``.
        """
        violated = []
        for idx, (lhs, rhs) in enumerate(self.fds):
            for s in instance:
                if all(s[a] == t[a] for a in lhs) and any(s[b] != t[b] for b in rhs):
                    violated.append(idx)
                    break
        return violated

    def _random_tuple(self):
        return {a: self.rng.choice(self.domain) for a in self.attributes}

    def _key(self, t):
        return tuple(t[a] for a in self.attributes)

    # ------------------------------------------------------------------ #
    # Instance + candidate generation
    # ------------------------------------------------------------------ #
    def _build_instance(self):
        instance = []
        attempts = 0
        while len(instance) < self.base_size and attempts < 500:
            attempts += 1
            t = self._random_tuple()
            if any(self._key(t) == self._key(s) for s in instance):
                continue
            if not self._violations(t, instance):
                instance.append(t)

        # Safety net: a non-empty instance is required for violations to exist.
        if not instance:
            instance.append(self._random_tuple())
        return instance

    def _craft_violator(self, fd_idx):
        """Best-effort tuple that violates ``fd_idx`` against the instance."""
        lhs, rhs = self.fds[fd_idx]
        s = self.rng.choice(self.instance)
        t = self._random_tuple()
        for a in lhs:
            t[a] = s[a]  # agree on LHS
        for b in rhs:  # force disagreement on RHS
            others = [v for v in self.domain if v != s[b]]
            if others:
                t[b] = self.rng.choice(others)
        return t

    def _build_candidates(self):
        chosen = []
        # Exclude tuples identical to an existing row: a duplicate is trivially
        # insertable and looks like a mistake to the student.
        instance_keys = {self._key(s) for s in self.instance}
        chosen_keys = set()

        def try_add(t):
            if t is None:
                return False
            k = self._key(t)
            if k in chosen_keys or k in instance_keys:
                return False
            violated = self._violations(t, self.instance)
            chosen.append({"values": t, "violated": violated})
            chosen_keys.add(k)
            return True

        max_violations = len(self.fds)
        for raw_want in self.targets[: self.num_tuples]:
            want = min(raw_want, max_violations)
            added = False
            for _ in range(300):
                if want == 0:
                    t = self._random_tuple()
                    if self._violations(t, self.instance):
                        continue
                else:
                    fd_idx = self.rng.randrange(len(self.fds))
                    t = self._craft_violator(fd_idx)
                    if len(self._violations(t, self.instance)) != want:
                        continue
                if try_add(t):
                    added = True
                    break
            if not added:
                # Fall back to any distinct tuple; the exact mix is cosmetic.
                for _ in range(300):
                    if try_add(self._random_tuple()):
                        break

        # Pad in the unlikely case some additions collided.
        guard = 0
        while len(chosen) < self.num_tuples and guard < 500:
            guard += 1
            try_add(self._random_tuple())

        self.rng.shuffle(chosen)
        chosen = chosen[: self.num_tuples]
        for c in chosen:
            c["insertable"] = len(c["violated"]) == 0
        return chosen

    # ------------------------------------------------------------------ #
    # Formatting + parsing
    # ------------------------------------------------------------------ #
    def _format_fd(self, fd):
        lhs, rhs = fd
        return f"{''.join(sorted(lhs))}->{''.join(sorted(rhs))}"

    def _canon_fd(self, fd):
        lhs, rhs = fd
        return (frozenset(lhs), frozenset(rhs))

    def _side_to_set(self, raw, valid_attrs):
        text = str(raw).strip().upper()
        if not text:
            return None
        if "," in text or " " in text:
            tokens = [tok for tok in re.split(r"[,\s]+", text) if tok]
        else:
            tokens = list(text)

        result = set()
        for tok in tokens:
            if len(tok) != 1 or tok not in valid_attrs:
                return None
            result.add(tok)
        return result or None

    def _parse_fds(self, raw):
        """Parse user FD input into a set of canonical ``(frozenset, frozenset)``.

        Returns an empty set for blank input and ``None`` for malformed input.
        Accepts ``->``, ``→`` and ``=>`` arrows, ``;``/newline between FDs and
        comma/concatenated attributes on each side.
        """
        text = str(raw or "").strip()
        if not text:
            return set()

        text = text.replace("→", "->").replace("=>", "->")
        valid_attrs = set(self.attributes)
        out = set()

        for part in re.split(r"[;\n]+", text):
            piece = part.strip()
            if not piece:
                continue
            if "->" not in piece:
                return None
            lhs_raw, rhs_raw = piece.split("->", 1)
            lhs = self._side_to_set(lhs_raw, valid_attrs)
            rhs = self._side_to_set(rhs_raw, valid_attrs)
            if lhs is None or rhs is None:
                return None
            out.add((frozenset(lhs), frozenset(rhs)))

        return out

    # ------------------------------------------------------------------ #
    # Layout + evaluation
    # ------------------------------------------------------------------ #
    def generate(self):
        attr_text = ", ".join(self.attributes)
        fd_text = "; ".join(self._format_fd(fd) for fd in self.fds)

        instance_table = {
            "type": "table",
            "label": "Aktuelle Ausprägung von R",
            "columns": list(self.attributes),
            "rows": [[str(t[a]) for a in self.attributes] for t in self.instance],
        }

        header = [{"type": "text", "value": f"**{a}**"} for a in self.attributes]
        header.append({"type": "text", "value": "**Einfügbar?**"})
        header.append({"type": "text", "value": "**Verletzte FD(s)**"})

        cells = [header]
        for i, cand in enumerate(self.candidates):
            row = [{"type": "text", "value": str(cand["values"][a])} for a in self.attributes]
            row.append({
                "type": "multiple_choice",
                "id": f"tuple_{i}_decision",
                "options": ["Ja", "Nein"],
            })
            row.append({
                "type": "text_input",
                "id": f"tuple_{i}_fds",
            })
            cells.append(row)

        candidate_table = {
            "type": "layout_table",
            "id": "candidates",
            "title": "Zu prüfende Tupel",
            "rows": len(cells),
            "cols": len(self.attributes) + 2,
            "alignment": "middle",
            "cells": cells,
        }

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "### Einfügbarkeit von Tupeln\n\n"
                        "Entscheide für jedes Tupel in der unteren Tabelle, ob es in "
                        "**R** eingefügt werden kann, ohne eine funktionale Abhängigkeit "
                        "zu verletzen. Wähle **Ja** oder **Nein**; bei **Nein** gib alle "
                        "verletzten FDs an (Format `A->B; AB->C`, mehrere mit `;`).\n\n"
                        f"**Relation:** R({attr_text})\n\n"
                        f"**Funktionale Abhängigkeiten:** {fd_text}"
                    ),
                },
                instance_table,
                candidate_table,
            ]
        }

    def evaluate(self, user_input):
        user_input = user_input or {}
        results = {}

        for i, cand in enumerate(self.candidates):
            insertable = cand["insertable"]

            decision_id = f"tuple_{i}_decision"
            expected_decision = "Ja" if insertable else "Nein"
            user_decision = str(user_input.get(decision_id, "")).strip()
            results[decision_id] = {
                "correct": user_decision == expected_decision,
                "expected": expected_decision,
            }

            fd_id = f"tuple_{i}_fds"
            if insertable:
                user_raw = str(user_input.get(fd_id, "")).strip()
                results[fd_id] = {
                    "correct": user_raw == "",
                    "expected": "—",
                }
            else:
                violated_set = {self._canon_fd(self.fds[idx]) for idx in cand["violated"]}
                violated_text = "; ".join(
                    self._format_fd(self.fds[idx]) for idx in cand["violated"]
                )
                parsed = self._parse_fds(user_input.get(fd_id))
                results[fd_id] = {
                    "correct": parsed is not None and parsed == violated_set,
                    "expected": violated_text,
                }

        return results

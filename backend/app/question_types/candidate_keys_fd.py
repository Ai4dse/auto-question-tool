import itertools

from app.common import *


DIFFICULTY_SETTINGS = {
    "easy": {"attr_range": (4, 5), "fd_range": (3, 5)},
    "medium": {"attr_range": (5, 6), "fd_range": (4, 7)},
    "hard": {"attr_range": (6, 7), "fd_range": (6, 9)},
}


class CandidateKeysFDQuestion:
    def __init__(self, seed=None, difficulty="easy", **kwargs):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.settings = settings
        min_attr, max_attr = settings["attr_range"]
        min_fd, max_fd = settings["fd_range"]

        self.num_attributes = self.rng.randint(min_attr, max_attr)
        self.num_fds = self.rng.randint(min_fd, max_fd)

        self.attributes = [chr(ord("A") + i) for i in range(self.num_attributes)]
        self.fds = self._generate_fds(self.num_fds)
        self.candidate_keys = self._find_candidate_keys()

    def _closure(self, attrs):
        closure_set = set(attrs)
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.fds:
                if lhs.issubset(closure_set) and not rhs.issubset(closure_set):
                    closure_set |= rhs
                    changed = True
        return closure_set

    def _find_candidate_keys(self):
        all_attrs = set(self.attributes)
        keys = []

        for size in range(1, len(self.attributes) + 1):
            for comb in itertools.combinations(self.attributes, size):
                subset = set(comb)

                if any(existing.issubset(subset) for existing in keys):
                    continue

                if self._closure(subset) == all_attrs:
                    keys.append(subset)

        return keys

    def _generate_candidate_fd(self):
        attrs = self.attributes
        lhs_sizes = [1, 1, 1, 2, 2, 3] if len(attrs) >= 6 else [1, 1, 1, 2, 2]

        lhs_size = min(self.rng.choice(lhs_sizes), len(attrs))
        lhs = set(self.rng.sample(attrs, lhs_size))

        rhs_pool = [a for a in attrs if a not in lhs]
        if not rhs_pool:
            return None

        rhs_size = 1 if len(rhs_pool) == 1 else self.rng.choice([1, 1, 2])
        rhs_size = min(rhs_size, len(rhs_pool))
        rhs = set(self.rng.sample(rhs_pool, rhs_size))

        return lhs, rhs

    def _lhs_distribution_ok(self, fds):
        counts = {}
        for lhs, _ in fds:
            key = tuple(sorted(lhs))
            counts[key] = counts.get(key, 0) + 1
        max_same_lhs = max(counts.values()) if counts else 0
        return max_same_lhs <= max(2, len(fds) // 2)

    def _not_single_dominator(self, fds):
        attrs = set(self.attributes)
        for a in attrs:
            if self._closure({a}) == attrs:
                return False
        return True

    def _has_rhs_gap(self, fds):
        rhs_union = set()
        for _, rhs in fds:
            rhs_union |= set(rhs)
        return len(rhs_union) < len(self.attributes)

    def _generate_fds(self, target_fd_count):
        all_attrs = set(self.attributes)
        max_tries = 500

        for _ in range(max_tries):
            fds = []
            seen = set()

            while len(fds) < target_fd_count:
                cand = self._generate_candidate_fd()
                if cand is None:
                    continue
                lhs, rhs = cand

                sig = (tuple(sorted(lhs)), tuple(sorted(rhs)))
                if sig in seen:
                    continue
                seen.add(sig)
                fds.append((lhs, rhs))

            self.fds = fds
            keys = self._find_candidate_keys()

            if not keys:
                continue
            if len(keys) > 6:
                continue
            if not all(self._closure(k) == all_attrs for k in keys):
                continue
            if not self._lhs_distribution_ok(fds):
                continue
            if not self._not_single_dominator(fds):
                continue

            if self.difficulty in ("medium", "hard") and not self._has_rhs_gap(fds):
                continue

            return fds

        fallback = []
        core = set(self.attributes[:2])
        for attr in self.attributes[2:]:
            fallback.append((set(core), {attr}))
        if len(self.attributes) >= 4:
            fallback.append(({self.attributes[2]}, {self.attributes[0]}))
        self.fds = fallback
        return fallback

    def _format_fd(self, fd):
        lhs, rhs = fd
        return f"{''.join(sorted(lhs))} -> {''.join(sorted(rhs))}"

    def _format_key(self, key):
        return "{" + ",".join(sorted(key)) + "}"

    def _parse_user_keys(self, raw):
        text = str(raw or "").strip()
        if not text:
            return None

        groups = [g.strip() for g in text.split(";") if g.strip()]
        parsed = []
        valid_attrs = set(self.attributes)

        for g in groups:
            if not (g.startswith("{") and g.endswith("}")):
                return None
            inner = g[1:-1].strip()
            if not inner:
                return None

            parts = [p.strip() for p in inner.split(",") if p.strip()]
            if not parts:
                return None

            key_set = set()
            for p in parts:
                if len(p) != 1:
                    return None
                attr = p.upper()
                if attr not in valid_attrs:
                    return None
                key_set.add(attr)
            parsed.append(key_set)

        return parsed

    def _generate_steps_layout(self):
        fd_text = "; ".join(self._format_fd(fd) for fd in self.fds)
        attr_text = ", ".join(self.attributes)

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "### Schlüsselsuche mit Funktionalen Abhängigkeiten\n\n"
                        f"Gegeben sei die Relation **R({attr_text})**\n\n"
                        f"und die Funktionale Abhaengigkeiten: **{fd_text}.**\n\n"
                        "Bestimmen Sie alle Kandidatenschlüssel.\n\n"
                        "Format: **{A,B}; {C,D}**."
                    ),
                },
                {
                    "type": "text_input",
                    "id": "candidate_keys",
                    "rows": 3,
                    "label": "Kandidatenschlüssel",
                },
            ]
        }

    def generate(self):
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        parsed_user_keys = self._parse_user_keys(user_input.get("candidate_keys"))

        expected_sets = {frozenset(k) for k in self.candidate_keys}
        expected_text = "; ".join(self._format_key(k) for k in sorted(self.candidate_keys, key=lambda x: (len(x), sorted(x))))

        if parsed_user_keys is None:
            return {
                "candidate_keys": {
                    "correct": False,
                    "expected": expected_text,
                }
            }

        user_sets = {frozenset(k) for k in parsed_user_keys}

        return {
            "candidate_keys": {
                "correct": user_sets == expected_sets,
                "expected": expected_text,
            }
        }

    def evaluate(self, user_input):
        return self._evaluate_steps(user_input)

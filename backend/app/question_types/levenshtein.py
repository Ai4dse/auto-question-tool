import json
import random
from pathlib import Path


RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources" / "levenshtein" / "word_pairs.json"


class LevenshteinQuestion:
    def __init__(self, seed=None, difficulty="easy"):
        self.difficulty = str(difficulty).lower()
        if self.difficulty not in {"easy", "medium", "hard"}:
            self.difficulty = "easy"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        rng = random.Random(self.seed)

        with RESOURCE_PATH.open("r", encoding="utf-8") as f:
            pools = json.load(f)

        pool = pools.get(self.difficulty) or pools.get("easy") or []
        if not pool:
            raise ValueError("No Levenshtein word pairs configured")

        self.word_a, self.word_b = rng.choice(pool)
        self.dp = self._build_dp(self.word_a, self.word_b)
        self.valid_paths = self._build_all_optimal_paths(self.word_a, self.word_b, self.dp)
        self.valid_paths_sorted = sorted(self.valid_paths)

    def _build_dp(self, a, b):
        rows = len(a) + 1
        cols = len(b) + 1
        dp = [[0 for _ in range(cols)] for _ in range(rows)]

        for i in range(rows):
            dp[i][0] = i
        for j in range(cols):
            dp[0][j] = j

        for i in range(1, rows):
            for j in range(1, cols):
                repl_cost = 0 if a[i - 1] == b[j - 1] else 1
                diag = dp[i - 1][j - 1] + repl_cost
                delete = dp[i - 1][j] + 1
                insert = dp[i][j - 1] + 1
                dp[i][j] = min(diag, delete, insert)

        return dp

    def _grid_payload(self):
        return {
            "type": "LevenshteinGrid",
            "id": "lev_grid",
            "label": "Levenshtein-Tabelle",
            "wordA": self.word_a,
            "wordB": self.word_b,
            "topBorder": self.dp[0],
            "leftBorder": [self.dp[i][0] for i in range(len(self.word_a) + 1)],
            "fieldPrefix": "lev",
        }

    def _build_all_optimal_paths(self, a, b, dp):
        m = len(a)
        n = len(b)
        memo = {}

        def dfs(i, j):
            key = (i, j)
            if key in memo:
                return memo[key]
            if i == m and j == n:
                memo[key] = {""}
                return memo[key]

            out = set()
            current = dp[i][j]

            if i < m and j < n:
                if a[i] == b[j] and dp[i + 1][j + 1] == current:
                    for suffix in dfs(i + 1, j + 1):
                        out.add("C" + suffix)
                if a[i] != b[j] and dp[i + 1][j + 1] == current + 1:
                    for suffix in dfs(i + 1, j + 1):
                        out.add("R" + suffix)

            if i < m and dp[i + 1][j] == current + 1:
                for suffix in dfs(i + 1, j):
                    out.add("D" + suffix)

            if j < n and dp[i][j + 1] == current + 1:
                for suffix in dfs(i, j + 1):
                    out.add("I" + suffix)

            memo[key] = out
            return out

        return dfs(0, 0)

    def _normalize_path(self, raw):
        text = str(raw or "").upper()
        return "".join(ch for ch in text if ch in {"C", "R", "D", "I"})

    def generate(self):
        valid_paths_text = ", ".join(self.valid_paths_sorted)
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Berechne die Levenshtein-Distanz schrittweise. "
                        "Die Randwerte sind vorgegeben. "
                        "Pro Vergleichsfeld sind Hilfsfelder für die Lösch-, Einfüge und Kopier-/Ersetzoperation gegeben. Das rot hinterlegte Feld soll die Kosten für die günstigste Operation kennzeichnen."
                    ),
                },
                {
                    "type": "Text",
                    "content": f"Wort A: {self.word_a} | Wort B: {self.word_b}",
                },
                self._grid_payload(),
            ],
            "view2": [
                {
                    "type": "Text",
                    "content": (
                        "Gib einen optimalen Operationspfad an. "
                        "Verwende C (Kopieren), R (Ersetzen), D (Löschen), I (Einfügen). "
                        "Alle optimalen Pfade sind gültig."
                    ),
                },
                {
                    "type": "TextInput",
                    "id": "lev_path",
                    "label": "Optimaler Pfad (z. B. CDRR)",
                },
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": f"Finale Levenshtein-Distanz: {self.dp[len(self.word_a)][len(self.word_b)]}",
                }
            ],
        }

    def evaluate(self, user_input):
        user_input = user_input or {}
        results = {}

        for i in range(1, len(self.word_a) + 1):
            for j in range(1, len(self.word_b) + 1):
                repl_cost = 0 if self.word_a[i - 1] == self.word_b[j - 1] else 1
                expected_diag = self.dp[i - 1][j - 1] + repl_cost
                expected_delete = self.dp[i - 1][j] + 1
                expected_insert = self.dp[i][j - 1] + 1
                expected_min = self.dp[i][j]

                row_prefix = f"lev_{i}_{j}"
                expected_values = [
                    expected_diag,
                    expected_delete,
                    expected_insert,
                    expected_min,
                ]

                for offset, expected in enumerate(expected_values, start=1):
                    field_id = f"{row_prefix}_{offset}"
                    actual = str(user_input.get(field_id, "")).strip()
                    expected_text = str(expected)
                    results[field_id] = {
                        "correct": actual == expected_text,
                        "expected": expected_text,
                    }

        normalized_user_path = self._normalize_path(user_input.get("lev_path", ""))
        all_valid_display = ", ".join(self.valid_paths_sorted)
        results["lev_path"] = {
            "correct": normalized_user_path in self.valid_paths,
            "expected": f"Alle gültigen optimalen Pfade: {all_valid_display}",
        }

        return results

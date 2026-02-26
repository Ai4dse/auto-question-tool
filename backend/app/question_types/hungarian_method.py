import itertools
import math
import random

import numpy as np

from app.resources.number_norm_helper import normalize_number
from app.resources.synonyms import synonym_pairs


DIFFICULTY_SETTINGS = {
    "easy": {"matrix_size": [3], "steps": [0], "discrete": [True]},
    "medium": {"matrix_size": [3, 4], "steps": [0, 1], "discrete": [True, False]},
    "hard": {"matrix_size": [4, 5], "steps": [1, 2], "discrete": [False]},
}


class HungarianMethodQuestion:
    def __init__(self, seed=None, difficulty="easy", mode="steps"):
        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        self.matrix_size = random.choice(config["matrix_size"])
        self.steps = random.choice(config["steps"])
        self.discrete = random.choice(config["discrete"])

        self.mode = (mode or "steps").lower()
        if self.mode not in {"steps", "exam"}:
            self.mode = "steps"

        self.pairs = random.sample(synonym_pairs, self.matrix_size)
        self.schema_a = [a for a, _ in self.pairs]
        self.schema_b = [b for _, b in self.pairs]
        random.shuffle(self.schema_a)
        random.shuffle(self.schema_b)

        self.numbers = []
        self.step1_matrix = tuple()
        self.step2_matrix = tuple()
        self.step_routes = []
        self.valid_assignment_tuples = []
        self.expected_assignment_tuple = tuple()

        self._initialize_instance_for_requested_depth()

    # ------------------------------------------------------------------
    # Hungarian internals
    # ------------------------------------------------------------------
    def random_numbers(self, n, discrete=True, seed=None, low=0, high=10):
        rng = np.random.default_rng(seed)
        if discrete:
            return rng.integers(low, high + 1, size=n).tolist()
        return rng.uniform(low, high, size=n).round(1).tolist()

    def check_coverage(self, comb, zeros, matrix_size):
        for element in comb:
            if element >= matrix_size:
                idx = element - matrix_size
                zeros = [t for t in zeros if t[1] != idx]
            else:
                zeros = [t for t in zeros if t[0] != element]
        return len(zeros) == 0

    def get_minimal_lines(self, zeros, matrix_size):
        indices = list(range(2 * matrix_size))
        combs = []
        i = 0
        for i in range(1, matrix_size + 1):
            found = False
            for comb in itertools.combinations(indices, i):
                if self.check_coverage(comb, zeros, matrix_size):
                    found = True
                    combs.append(comb)
            if found:
                break
        return combs, i

    def uncovered_indices(self, comb, matrix_size):
        rows_cov = {i for i in comb if i < matrix_size}
        cols_cov = {i - matrix_size for i in comb if i >= matrix_size}
        return [
            (r, c)
            for r in range(matrix_size)
            for c in range(matrix_size)
            if r not in rows_cov and c not in cols_cov
        ]

    def uncovered_rows(self, comb, matrix_size):
        covered_rows = {i for i in comb if i < matrix_size}
        return [
            (r, c)
            for r in range(matrix_size)
            for c in range(matrix_size)
            if r not in covered_rows
        ]

    def covered_cols(self, comb, matrix_size):
        covered = {i - matrix_size for i in comb if i >= matrix_size}
        return [(r, c) for c in covered for r in range(matrix_size)]

    def all_zero_assignments(self, matrix, matrix_size):
        z = matrix == 0
        return [
            tuple((r, p[r]) for r in range(matrix_size))
            for p in itertools.permutations(range(matrix_size))
            if np.all(z[range(matrix_size), p])
        ]

    def step_one(self, matrix_size, numbers):
        mat = np.array(numbers).reshape(matrix_size, matrix_size)
        return mat - mat.min(axis=1, keepdims=True)

    def step_two(self, matrix):
        mat = np.array(matrix)
        return mat - mat.min(axis=0, keepdims=True)

    def step_three(self, matrix, matrix_size):
        zeros = list(map(tuple, np.argwhere(matrix == 0)))
        return self.get_minimal_lines(zeros, matrix_size)

    def step_four(self, comb, matrix, matrix_size):
        uncov = self.uncovered_indices(comb, matrix_size)
        if not uncov:
            return matrix

        min_val = min(matrix[r, c] for r, c in uncov)

        uncovered_rows = self.uncovered_rows(comb, matrix_size)
        if uncovered_rows:
            matrix[tuple(zip(*uncovered_rows))] -= min_val

        covered_cols = self.covered_cols(comb, matrix_size)
        if covered_cols:
            matrix[tuple(zip(*covered_cols))] += min_val

        return matrix

    # ------------------------------------------------------------------
    # Route graph construction
    # ------------------------------------------------------------------
    def _matrix_to_tuple(self, matrix):
        arr = np.array(matrix)
        return tuple(tuple(float(arr[r, c]) for c in range(arr.shape[1])) for r in range(arr.shape[0]))

    def _cover_to_tuple(self, comb):
        rows = tuple(sorted(i for i in comb if i < self.matrix_size))
        cols = tuple(sorted(i - self.matrix_size for i in comb if i >= self.matrix_size))
        return rows, cols

    def _assignment_pairs_to_tuple(self, match):
        mapping = [None] * self.matrix_size
        for row, col in match:
            mapping[int(row)] = int(col)
        return tuple(mapping)

    def _build_routes_for_numbers(self, numbers):
        step1 = self.step_one(self.matrix_size, numbers)
        step2 = self.step_two(step1)

        step1_tuple = self._matrix_to_tuple(step1)
        step2_tuple = self._matrix_to_tuple(step2)

        routes = []

        def recurse(current_matrix, chosen_covers, step4_matrices):
            combs, lines = self.step_three(current_matrix, self.matrix_size)
            cover_options = [self._cover_to_tuple(c) for c in combs]

            if lines == self.matrix_size:
                assignments = self.all_zero_assignments(current_matrix, self.matrix_size)
                assignment_tuples = sorted({self._assignment_pairs_to_tuple(a) for a in assignments})
                terminal_matrix = self._matrix_to_tuple(current_matrix)

                for term_cover in cover_options:
                    routes.append(
                        {
                            "step1_matrix": step1_tuple,
                            "step2_matrix": step2_tuple,
                            "step3_covers": list(chosen_covers),
                            "step4_matrices": list(step4_matrices),
                            "terminal_matrix": terminal_matrix,
                            "terminal_cover": term_cover,
                            "assignment_tuples": assignment_tuples,
                            "depth": len(step4_matrices),
                        }
                    )
                return

            for comb in combs:
                adjusted = self.step_four(comb, np.array(current_matrix, copy=True), self.matrix_size)
                recurse(
                    adjusted,
                    chosen_covers + [self._cover_to_tuple(comb)],
                    step4_matrices + [self._matrix_to_tuple(adjusted)],
                )

        recurse(step2, [], [])
        return step1_tuple, step2_tuple, routes

    def _initialize_instance_for_requested_depth(self):
        max_attempts = 350
        first_candidate = None

        for attempt in range(max_attempts):
            attempt_seed = self.seed + attempt
            numbers = self.random_numbers(
                self.matrix_size * self.matrix_size,
                self.discrete,
                attempt_seed,
            )

            step1, step2, routes = self._build_routes_for_numbers(numbers)
            if not routes:
                continue

            candidate = {
                "numbers": numbers,
                "step1": step1,
                "step2": step2,
                "routes": routes,
            }
            if first_candidate is None:
                first_candidate = candidate

            depths = {r["depth"] for r in routes}
            if len(depths) == 1 and self.steps in depths:
                self.numbers = numbers
                self.step1_matrix = step1
                self.step2_matrix = step2
                self.step_routes = routes
                break
        else:
            if first_candidate is None:
                raise ValueError("Failed to initialize Hungarian question instance")
            self.numbers = first_candidate["numbers"]
            self.step1_matrix = first_candidate["step1"]
            self.step2_matrix = first_candidate["step2"]
            self.step_routes = first_candidate["routes"]
            self.steps = self.step_routes[0]["depth"]

        all_assignments = set()
        for route in self.step_routes:
            all_assignments.update(route["assignment_tuples"])
        self.valid_assignment_tuples = sorted(all_assignments)
        self.expected_assignment_tuple = self.valid_assignment_tuples[0] if self.valid_assignment_tuples else tuple()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _as_values(self, matrix_tuple):
        return [
            [self._format_expected_value(cell) for cell in row]
            for row in matrix_tuple
        ]

    def _matrix_input(self, matrix_id, title, values=None):
        payload = {
            "type": "MatrixInput",
            "id": matrix_id,
            "title": title,
            "rows": [[a] for a in self.schema_a],
            "cols": [[b] for b in self.schema_b],
        }
        if values is not None:
            payload["values"] = values
        return payload

    def _cover_matrix_id(self, step_index):
        return f"hm_cover_{step_index}"

    def _terminal_cover_matrix_id(self):
        return "hm_cover_terminal"

    def _display_matrix_id_for_cover_step(self, step_index):
        return f"hm_step3_display_{step_index}"

    def _display_matrix_id_for_terminal_cover(self):
        return "hm_step3_terminal_display"

    def _source_values_for_cover_step(self, step_index):
        if step_index == 1:
            return self._as_values(self.step2_matrix)

        source_idx = step_index - 2
        if self.step_routes and len(self.step_routes[0]["step4_matrices"]) > source_idx:
            return self._as_values(self.step_routes[0]["step4_matrices"][source_idx])
        return None

    def _source_values_for_terminal_cover_step(self):
        if self.steps == 0:
            return self._as_values(self.step2_matrix)

        if self.step_routes and self.step_routes[0]["step4_matrices"]:
            return self._as_values(self.step_routes[0]["step4_matrices"][self.steps - 1])
        return None

    def _generate_steps_layout(self):
        base = {}

        base["view1"] = [
            {
                "type": "Text",
                "content": (
                    "Schritt 1: Zeilenreduktion. Subtrahieren Sie in jeder Zeile das Minimum "
                    "von allen Eintragen."
                ),
            },
            self._matrix_input(
                "hm_step1",
                "Ausgangsmatrix (bearbeiten Sie die Felder fur Schritt 1)",
                values=[
                    self.numbers[i:i + self.matrix_size]
                    for i in range(0, len(self.numbers), self.matrix_size)
                ],
            ),
        ]

        base["view2"] = [
            {
                "type": "Text",
                "content": (
                    "Schritt 2: Spaltenreduktion. Verwenden Sie Ihr Ergebnis aus Schritt 1 und "
                    "subtrahieren Sie in jeder Spalte das jeweilige Minimum."
                ),
            },
            self._matrix_input(
                "hm_step2",
                "Schritt 2 Matrix",
                values=self._as_values(self.step1_matrix),
            ),
        ]

        view_idx = 3
        for i in range(1, self.steps + 1):
            cover_id = self._cover_matrix_id(i)
            display_matrix_id = self._display_matrix_id_for_cover_step(i)
            base[f"view{view_idx}"] = [
                {
                    "type": "Text",
                    "content": (
                        f"Schritt 3.{i}: Uberdecken Sie alle Nullen mit minimaler Anzahl an Linien "
                        "(Strike row / Strike col)."
                    ),
                },
                {
                    **self._matrix_input(
                        display_matrix_id,
                        f"Linienauswahl fur Schritt 3.{i}",
                        values=self._source_values_for_cover_step(i),
                    ),
                    "checkboxId": cover_id,
                },
            ]
            view_idx += 1

            base[f"view{view_idx}"] = [
                {
                    "type": "Text",
                    "content": (
                        f"Schritt 4.{i}: Bilden Sie die neue Matrix anhand der gewahlten Linien."
                    ),
                },
                self._matrix_input(f"hm_step4_{i}", f"Schritt 4.{i} Matrix"),
            ]
            view_idx += 1

        terminal_cover_id = self._terminal_cover_matrix_id()
        terminal_display_matrix_id = self._display_matrix_id_for_terminal_cover()
        base[f"view{view_idx}"] = [
            {
                "type": "Text",
                "content": (
                    "Finaler Schritt 3: Uberdecken Sie alle Nullen mit n Linien. Danach kann die "
                    "optimale Zuordnung bestimmt werden."
                ),
            },
            {
                **self._matrix_input(
                    terminal_display_matrix_id,
                    "Finale Linienauswahl",
                    values=self._source_values_for_terminal_cover_step(),
                ),
                "checkboxId": terminal_cover_id,
            },
        ]
        view_idx += 1

        assignment_header = [{"type": "text", "value": a} for a in self.schema_a]
        assignment_inputs = [
            {
                "type": "DropdownInput",
                "id": f"hm_final_assign_{row}",
                "label": f"Zuordnung fur {self.schema_a[row]}",
                "placeholder": "Bitte auswahlen...",
                "options": self.schema_b,
            }
            for row in range(self.matrix_size)
        ]

        base[f"view{view_idx}"] = [
            {
                "type": "Text",
                "content": "Finale Zuordnung: Wahlen Sie fur jede Zeile aus Schema A genau ein Attribut aus Schema B.",
            },
            {
                "type": "layout_table",
                "title": "Finale Zuordnung (A -> B)",
                "rows": 2,
                "cols": self.matrix_size,
                "cells": [assignment_header, assignment_inputs],
            },
        ]

        base["lastView"] = [
            {
                "type": "Text",
                "content": "Ubung abgeschlossen.",
            }
        ]
        return base

    def _generate_exam_layout(self):
        start_matrix = [
            [self.schema_a[r]] + self.numbers[r * self.matrix_size:(r + 1) * self.matrix_size]
            for r in range(self.matrix_size)
        ]
        assignment_header = [{"type": "text", "value": a} for a in self.schema_a]
        assignment_inputs = [
            {
                "type": "DropdownInput",
                "id": f"exam_assign_{row}",
                "label": f"Zuordnung fur {self.schema_a[row]}",
                "placeholder": "Bitte auswahlen...",
                "options": self.schema_b,
            }
            for row in range(self.matrix_size)
        ]

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Exam-Modus: Geben Sie nur die finale optimale Zuordnung an. "
                        "Zwischenschritte werden nicht bewertet."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Distanzmatrix",
                    "columns": ["Schema A"] + self.schema_b,
                    "rows": start_matrix,
                },
                {
                    **self._matrix_input(
                        "hm_exam_work",
                        "Arbeitsmatrix (frei bearbeitbar, nicht benotet)",
                        values=[
                            self.numbers[i:i + self.matrix_size]
                            for i in range(0, len(self.numbers), self.matrix_size)
                        ],
                    ),
                    "checkboxId": "hm_exam_work",
                },
                {
                    "type": "layout_table",
                    "title": "Finale Zuordnung (A -> B)",
                    "rows": 2,
                    "cols": self.matrix_size,
                    "cells": [assignment_header, assignment_inputs],
                },
            ],
            "lastView": [{"type": "Text", "content": ""}],
        }

    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
        return self._generate_steps_layout()

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------
    def _to_float(self, value):
        try:
            if value is None:
                return None
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    def _format_expected_value(self, value):
        if isinstance(value, bool):
            return str(value)

        normalized = normalize_number(value, max_decimals=6)
        if normalized is None:
            return ""
        return str(normalized)

    def _compare_numeric(self, actual, expected):
        actual_f = self._to_float(actual)
        expected_f = self._to_float(expected)
        if actual_f is not None and expected_f is not None:
            return math.isclose(actual_f, expected_f, rel_tol=1e-9, abs_tol=1e-8)
        return self._format_expected_value(actual) == self._format_expected_value(expected)

    def _matrix_stage_matches(self, user_input, matrix_id, expected_matrix):
        for r in range(self.matrix_size):
            for c in range(self.matrix_size):
                key = f"{matrix_id}:cell:{r},{c}"
                if key not in user_input:
                    continue
                if not self._compare_numeric(user_input.get(key), expected_matrix[r][c]):
                    return False
        return True

    def _cover_stage_matches(self, user_input, matrix_id, expected_cover):
        rows_expected, cols_expected = expected_cover
        rows_expected = set(rows_expected)
        cols_expected = set(cols_expected)

        for r in range(self.matrix_size):
            key = f"{matrix_id}:row:{r}"
            if key not in user_input:
                continue
            if bool(user_input.get(key)) != (r in rows_expected):
                return False

        for c in range(self.matrix_size):
            key = f"{matrix_id}:col:{c}"
            if key not in user_input:
                continue
            if bool(user_input.get(key)) != (c in cols_expected):
                return False

        return True

    def _routes_matching_prefix(self, user_input, stage_name):
        routes = list(self.step_routes)

        if stage_name in {
            "step2",
            "step3_1",
            "step4_1",
            "step3_terminal",
            "final",
        }:
            routes = [
                r for r in routes if self._matrix_stage_matches(user_input, "hm_step1", r["step1_matrix"])
            ]

        if stage_name in {"step3_1", "step4_1", "step3_terminal", "final"}:
            routes = [
                r for r in routes if self._matrix_stage_matches(user_input, "hm_step2", r["step2_matrix"])
            ]

        for i in range(1, self.steps + 1):
            cover_stage = f"step3_{i}"
            matrix_stage = f"step4_{i}"

            if stage_name in {matrix_stage, "step3_terminal", "final"}:
                cover_id = self._cover_matrix_id(i)
                routes = [
                    r
                    for r in routes
                    if self._cover_stage_matches(user_input, cover_id, r["step3_covers"][i - 1])
                ]

            if stage_name in {f"step3_{i + 1}", "step3_terminal", "final"} or (
                i < self.steps and stage_name in {f"step4_{i + 1}", "step3_terminal", "final"}
            ):
                routes = [
                    r
                    for r in routes
                    if self._matrix_stage_matches(user_input, f"hm_step4_{i}", r["step4_matrices"][i - 1])
                ]

        if stage_name == "final":
            terminal_id = self._terminal_cover_matrix_id()
            routes = [
                r
                for r in routes
                if self._cover_stage_matches(user_input, terminal_id, r["terminal_cover"])
            ]

        return routes

    def _expected_matrix_for_stage(self, routes, selector):
        mats = []
        for r in routes:
            mats.append(selector(r))
        return mats

    def _fallback_routes(self, routes):
        if routes:
            return routes
        return list(self.step_routes)

    def _format_expected_options(self, values):
        uniq = []
        seen = set()
        for v in values:
            text = self._format_expected_value(v)
            if text not in seen:
                seen.add(text)
                uniq.append(text)
        if not uniq:
            return ""
        if len(uniq) == 1:
            return uniq[0]
        return "one of: " + " | ".join(uniq[:4])

    def _evaluate_matrix_stage(self, results, user_input, matrix_id, expected_matrices):
        for r in range(self.matrix_size):
            for c in range(self.matrix_size):
                key = f"{matrix_id}:cell:{r},{c}"
                actual = user_input.get(key)
                expected_vals = [m[r][c] for m in expected_matrices]
                correct = any(self._compare_numeric(actual, e) for e in expected_vals)
                results[key] = {
                    "correct": correct,
                    "expected": self._format_expected_options(expected_vals),
                }

    def _evaluate_cover_stage(self, results, user_input, matrix_id, expected_covers):
        row_options = []
        col_options = []
        for cover in expected_covers:
            row_options.append(set(cover[0]))
            col_options.append(set(cover[1]))

        for r in range(self.matrix_size):
            key = f"{matrix_id}:row:{r}"
            actual = bool(user_input.get(key))
            expected_vals = [r in rows for rows in row_options]
            results[key] = {
                "correct": actual in expected_vals,
                "expected": self._format_expected_options(expected_vals),
            }

        for c in range(self.matrix_size):
            key = f"{matrix_id}:col:{c}"
            actual = bool(user_input.get(key))
            expected_vals = [c in cols for cols in col_options]
            results[key] = {
                "correct": actual in expected_vals,
                "expected": self._format_expected_options(expected_vals),
            }

    # ------------------------------------------------------------------
    # Evaluation entrypoints
    # ------------------------------------------------------------------
    def _evaluate_steps(self, user_input):
        results = {}

        self._evaluate_matrix_stage(results, user_input, "hm_step1", [self.step1_matrix])

        routes_after_step1 = self._routes_matching_prefix(user_input, "step2")
        routes_after_step1 = self._fallback_routes(routes_after_step1)
        self._evaluate_matrix_stage(
            results,
            user_input,
            "hm_step2",
            self._expected_matrix_for_stage(routes_after_step1, lambda r: r["step2_matrix"]),
        )

        for i in range(1, self.steps + 1):
            routes_for_cover = self._routes_matching_prefix(user_input, f"step4_{i}")
            routes_for_cover = self._fallback_routes(routes_for_cover)
            cover_id = self._cover_matrix_id(i)
            self._evaluate_cover_stage(
                results,
                user_input,
                cover_id,
                [r["step3_covers"][i - 1] for r in routes_for_cover],
            )

            routes_for_step4 = self._routes_matching_prefix(user_input, f"step3_{i + 1}")
            routes_for_step4 = self._fallback_routes(routes_for_step4)
            self._evaluate_matrix_stage(
                results,
                user_input,
                f"hm_step4_{i}",
                [r["step4_matrices"][i - 1] for r in routes_for_step4],
            )

        routes_for_terminal_cover = self._routes_matching_prefix(user_input, "final")
        routes_for_terminal_cover = self._fallback_routes(routes_for_terminal_cover)
        terminal_cover_id = self._terminal_cover_matrix_id()
        self._evaluate_cover_stage(
            results,
            user_input,
            terminal_cover_id,
            [r["terminal_cover"] for r in routes_for_terminal_cover],
        )

        valid_assignment_set = set()
        for r in routes_for_terminal_cover:
            valid_assignment_set.update(r["assignment_tuples"])
        if not valid_assignment_set:
            valid_assignment_set = set(self.valid_assignment_tuples)

        selected = []
        for row in range(self.matrix_size):
            label = user_input.get(f"hm_final_assign_{row}")
            if label not in self.schema_b:
                selected.append(None)
            else:
                selected.append(self.schema_b.index(label))
        selected_tuple = tuple(selected)

        valid_tuples = list(valid_assignment_set)
        is_globally_correct = selected_tuple in valid_assignment_set

        for row in range(self.matrix_size):
            field_id = f"hm_final_assign_{row}"
            label = user_input.get(field_id)
            expected_labels = sorted({self.schema_b[t[row]] for t in valid_tuples if t[row] is not None})
            if is_globally_correct:
                row_correct = True
            else:
                row_correct = label in expected_labels
            results[field_id] = {
                "correct": row_correct,
                "expected": self._format_expected_options(expected_labels),
            }

        return results

    def _evaluate_exam(self, user_input):
        results = {}

        selected_cols = []
        has_missing_or_invalid = False
        for row in range(self.matrix_size):
            field_id = f"exam_assign_{row}"
            chosen_label = user_input.get(field_id)
            if chosen_label not in self.schema_b:
                has_missing_or_invalid = True
                selected_cols.append(None)
            else:
                selected_cols.append(self.schema_b.index(chosen_label))

        selected_tuple = tuple(selected_cols)
        is_correct_final = (
            (not has_missing_or_invalid)
            and selected_tuple in set(self.valid_assignment_tuples)
        )

        valid_tuples = list(self.valid_assignment_tuples)
        for row in range(self.matrix_size):
            field_id = f"exam_assign_{row}"
            expected_labels = sorted({self.schema_b[t[row]] for t in valid_tuples if t[row] is not None})
            row_label = user_input.get(field_id)
            row_correct = is_correct_final or row_label in expected_labels
            results[field_id] = {
                "correct": row_correct,
                "expected": self._format_expected_options(expected_labels),
            }

        return results

    def evaluate(self, user_input):
        if self.mode == "exam":
            return self._evaluate_exam(user_input)
        return self._evaluate_steps(user_input)

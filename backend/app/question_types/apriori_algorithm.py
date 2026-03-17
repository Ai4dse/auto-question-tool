import json
import random

from app.question_types.frequent_itemset_helper import (
    format_itemset,
    format_probability,
    generate_transaction_dataset,
    parse_itemset_text,
    parse_probability,
    run_apriori_levels,
)


DIFFICULTY_SETTINGS = {
    "easy": {
        "num_items": 4,
        "num_transactions": 8,
        "min_items": 1,
        "max_items": 3,
        "minsup_range": (0.45, 0.60),
        "min_non_empty_levels": 2,
    },
    "medium": {
        "num_items": 5,
        "num_transactions": 9,
        "min_items": 1,
        "max_items": 4,
        "minsup_range": (0.35, 0.50),
        "min_non_empty_levels": 2,
    },
    "hard": {
        "num_items": 6,
        "num_transactions": 10,
        "min_items": 2,
        "max_items": 5,
        "minsup_range": (0.25, 0.40),
        "min_non_empty_levels": 3,
    },
}


class AprioriAlgorithmQuestion:
    def __init__(self, seed=None, difficulty="easy", mode="steps"):
        self.difficulty = str(difficulty).lower()
        self.config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = str(mode or "steps").lower()
        if self.mode not in {"steps", "exam"}:
            self.mode = "steps"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.minsup = round(self.rng.uniform(*self.config["minsup_range"]), 2)
        self.base_items = []
        self.transactions = []
        self.levels = []
        self.minsup_count = 1
        self._initialize_instance()

    def _initialize_instance(self):
        chosen = None
        for attempt in range(70):
            local_rng = random.Random(self.seed + attempt)
            base_items, transactions = generate_transaction_dataset(
                local_rng,
                self.config["num_items"],
                self.config["num_transactions"],
                self.config["min_items"],
                self.config["max_items"],
            )

            levels, minsup_count = run_apriori_levels(transactions, base_items, self.minsup)
            non_empty = sum(1 for lvl in levels if lvl["frequents"])
            chosen = (base_items, transactions, levels, minsup_count)
            if non_empty >= self.config["min_non_empty_levels"]:
                break

        if not chosen:
            raise ValueError("Failed to generate Apriori instance.")
        self.base_items, self.transactions, self.levels, self.minsup_count = chosen

    def _transaction_rows(self):
        return [[f"T{i + 1}", ", ".join(sorted(list(tx)))] for i, tx in enumerate(self.transactions)]

    @staticmethod
    def _itemset_slug(itemset):
        return "_".join(itemset)

    def _support_key(self, k, itemset):
        return f"apr_s{k}_support_{self._itemset_slug(itemset)}"

    def _prob_key(self, k, itemset):
        return f"apr_s{k}_prob_{self._itemset_slug(itemset)}"

    def _below_key(self, k, itemset):
        return f"apr_s{k}_below_{self._itemset_slug(itemset)}"

    def _prefilled_c1_rows(self, level):
        k = level["k"]
        rows = []
        for entry in level["candidates"]:
            itemset = entry["itemset"]
            rows.append(
                {
                    "id": f"apr_s{k}_c_{self._itemset_slug(itemset)}",
                    "fields": [
                        format_itemset(itemset),
                        {"kind": "input", "id": self._support_key(k, itemset)},
                    ],
                }
            )
        return rows

    def _prefilled_l1_rows(self, level):
        k = level["k"]
        rows = []
        for entry in level["candidates"]:
            itemset = entry["itemset"]
            rows.append(
                {
                    "id": f"apr_s{k}_l_{self._itemset_slug(itemset)}",
                    "fields": [
                        format_itemset(itemset),
                        {"kind": "input", "id": self._support_key(k, itemset)},
                        {"kind": "input", "id": self._prob_key(k, itemset)},
                        {"kind": "checkbox", "id": self._below_key(k, itemset)},
                    ],
                }
            )
        return rows

    def _generate_steps_layout(self):
        base = {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Führe den Apriori-Algorithmus Schritt für Schritt aus.\n"
                        f"- Grundmenge: {', '.join(self.base_items)}\n"
                        f"- minsup = {self.minsup} ({self.minsup_count} von {len(self.transactions)} Transaktionen)\n"
                        "- $$C_1/L_1$$ sind vorgegeben. Danach baust du $$C_k/L_k$$ selbst auf und markierst welches Itemset unter den minsup fällt.\n"
                        "- Reihenfolge von Zeilen und Reihenfolge innerhalb eines Itemsets spielen bei der Bewertung keine Rolle.\n"
                        "- Setze die Termination-Checkbox genau dann, wenn kein nächstes Kandidatenset $$C_{(k+1)}$$ mehr gebildet werden kann oder $$L_k$$ leer ist."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Transaktionen",
                    "columns": ["Tid", "Items"],
                    "rows": self._transaction_rows(),
                },
            ],
        }

        if self.levels:
            level1 = self.levels[0]
            base["view1"].extend([
                {
                    "type": "Text",
                    "content": (
                        "### Schritt 1\n"
                        "Fülle $$C_1$$ und $$L_1$$ aus. Trage den Support $$\\sigma$$ als auch die zugehörige Wahrscheinlichkeit **P** ein. Markiere welches Itemset unter den minsup fällt."
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 1,
                    "cols": 2,
                    "alignment": "top",
                    "cells": [[
                        {
                            "type": "TableInput",
                            "label": "C1: Kandidaten",
                            "columns": ["Itemset", "Support"],
                            "rows": self._prefilled_c1_rows(level1),
                        },
                        {
                            "type": "TableInput",
                            "label": "L1",
                            "columns": ["Itemset", "Support", "P", "fällt unter minsup?"],
                            "rows": self._prefilled_l1_rows(level1),
                        },
                    ]],
                },
                {
                    "type": "CheckboxInput",
                    "id": "apr_s1_terminate",
                    "label": "Terminiert der Algorithmus nach Schritt 1?",
                },
            ])

        for level in self.levels[1:]:
            k = level["k"]
            view_name = f"view{k}"
            base[view_name] = [
                {
                    "type": "Text",
                    "content": (
                        f"### Schritt {k}\n Starte mit leeren Zeilen und füge bei Bedarf weitere hinzu. $$L_k$$ wird automatisch mit $$C_k$$ synchronisiert."
                    ),
                },
                {
                    "type": "AprioriLevelBuilder",
                    "id": f"apr_s{k}_builder",
                    "label": f"C{k}/L{k}",
                    "initialRows": 3,
                    "level": k,
                },
                {
                    "type": "CheckboxInput",
                    "id": f"apr_s{k}_terminate",
                    "label": f"Terminiert der Algorithmus nach Schritt {k}?",
                },
            ]

        frequent_rows = [
            [f"L{level['k']}", format_itemset(entry["itemset"]), str(entry["count"]), format_probability(entry["probability"])]
            for level in self.levels
            for entry in level["frequents"]
        ]

        base["lastView"] = [
            {"type": "Text", "content": "Algorithmus beendet. Übersicht aller frequent itemsets:"},
            {
                "type": "Table",
                "title": "Frequent Itemsets",
                "columns": ["Level", "Itemset", "Support", "P"],
                "rows": frequent_rows or [["-", "-", "-", "-"]],
            },
        ]
        return base

    def _generate_exam_layout(self):
        solution_elements = []
        solution_elements.append(
            {
                "type": "Text",
                "content": "Referenzlösung (Apriori-Kette):",
            }
        )

        for level in self.levels:
            k = level["k"]
            rows = []
            for entry in level["candidates"]:
                support = int(entry["count"])
                rows.append([
                    format_itemset(entry["itemset"]),
                    str(support),
                    format_probability(float(entry["probability"])),
                    str(support < self.minsup_count),
                ])

            solution_elements.append(
                {
                    "type": "Text",
                    "content": f"### Level {k} ($$C_{k}/L_{k}$$)\nTermination nach diesem Level: {str(bool(level['terminate']))}",
                }
            )
            solution_elements.append(
                {
                    "type": "Table",
                    "title": f"Level {k} Referenz",
                    "columns": ["Itemset", "Support", "P", "fällt unter minsup?"],
                    "rows": rows if rows else [["-", "-", "-", "-"]],
                }
            )

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Exam-Modus: Anzahl der Schritte wird nicht vorgegeben.\n"
                        "Füge pro Level Zeilen hinzu und trage **Itemset**, **Support $$\\sigma$$**, **P** und **fällt unter minsup?** ein.\n"
                        "Bewertung erfolgt strikt in Level-Reihenfolge; Reihenfolge innerhalb eines Itemsets ist egal.\n"
                        f"minsup = {self.minsup} ({self.minsup_count} von {len(self.transactions)} Transaktionen)."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Transaktionen",
                    "columns": ["Tid", "Items"],
                    "rows": self._transaction_rows(),
                },
                {"type": "Text", "content": ("Füge beliebig viele Level hinzu. $$C_k$$ und $$L_k$$ teilen sich Itemset/Support.")},
                {"type": "AprioriExamBuilder", "id": "apriori_exam", "label": "Apriori Algorithmus"},
            ],
            "lastView": solution_elements,
        }

    def generate(self):
        return self._generate_exam_layout() if self.mode == "exam" else self._generate_steps_layout()

    @staticmethod
    def _bool_value(value):
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on"}

    @staticmethod
    def _int_value(value):
        raw = "" if value is None else str(value).strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def _prob_matches(actual, expected):
        return actual is not None and abs(actual - expected) <= 0.005

    def _evaluate_prefilled_level1(self, user_input):
        results = {}
        if not self.levels:
            return results

        level = self.levels[0]
        k = level["k"]
        for entry in level["candidates"]:
            itemset = entry["itemset"]
            support_key = self._support_key(k, itemset)
            prob_key = self._prob_key(k, itemset)
            below_key = self._below_key(k, itemset)

            expected_support = int(entry["count"])
            expected_prob = float(entry["probability"])
            expected_below = expected_support < self.minsup_count

            results[support_key] = {
                "correct": self._int_value(user_input.get(support_key)) == expected_support,
                "expected": str(expected_support),
            }
            results[prob_key] = {
                "correct": self._prob_matches(parse_probability(user_input.get(prob_key)), expected_prob),
                "expected": format_probability(expected_prob),
            }
            results[below_key] = {
                "correct": self._bool_value(user_input.get(below_key)) == expected_below,
                "expected": str(expected_below),
            }

        terminate_key = "apr_s1_terminate"
        results[terminate_key] = {
            "correct": self._bool_value(user_input.get(terminate_key)) == bool(level["terminate"]),
            "expected": str(bool(level["terminate"])),
        }
        return results

    def _canonical_expected_rows(self, level):
        rows = []
        for entry in level["candidates"]:
            support = int(entry["count"])
            prob = float(entry["probability"])
            rows.append((tuple(entry["itemset"]), support, format_probability(prob), support < self.minsup_count))
        return sorted(rows, key=lambda x: x[0])

    def _solution_level(self, level):
        rows = []
        for entry in level["candidates"]:
            support = int(entry["count"])
            rows.append(
                {
                    "itemset": format_itemset(entry["itemset"]),
                    "support": str(support),
                    "probability": format_probability(float(entry["probability"])),
                    "below": str(support < self.minsup_count),
                }
            )

        return {
            "level": int(level["k"]),
            "rows": rows,
            "terminate": str(bool(level["terminate"])),
        }

    def _solution_payload(self, message, levels=None):
        source_levels = self.levels if levels is None else levels
        return {
            "message": message,
            "levels": [self._solution_level(level) for level in source_levels],
        }

    def _grade_rows(self, rows_list, expected_rows, key_factory, level_label):
        allowed_itemsets = ", ".join(format_itemset(row[0]) for row in expected_rows)
        expected_map = {row[0]: row for row in expected_rows}

        results = {}
        seen_itemsets = set()
        matched_expected_itemsets = set()
        duplicate = False
        actual_rows = []

        for row_idx, row in enumerate(rows_list):
            row = row or {}
            item_raw = str(row.get("itemset") or "").strip()
            support_raw = str(row.get("support") or "").strip()
            prob_raw = str(row.get("probability") or "").strip()
            below_raw = self._bool_value(row.get("belowMinsup"))

            itemset = parse_itemset_text(item_raw)
            row_has_content = bool(item_raw or support_raw or prob_raw or below_raw)

            item_key = key_factory(row_idx, "itemset")
            support_key = key_factory(row_idx, "support")
            prob_key = key_factory(row_idx, "probability")
            below_key = key_factory(row_idx, "belowMinsup")

            if not itemset:
                if row_has_content:
                    results[item_key] = {"correct": False, "expected": "Itemset erforderlich"}
                    results[support_key] = {"correct": False, "expected": "Support erforderlich"}
                    results[prob_key] = {"correct": False, "expected": "P erforderlich"}
                    results[below_key] = {"correct": False, "expected": "fällt unter minsup? setzen"}
                continue

            expected_row = expected_map.get(itemset)
            is_duplicate = itemset in seen_itemsets
            seen_itemsets.add(itemset)
            duplicate = duplicate or is_duplicate

            expected_support = expected_row[1] if expected_row else None
            expected_prob = expected_row[2] if expected_row else None
            expected_below = expected_row[3] if expected_row else None

            support = self._int_value(row.get("support"))
            prob = parse_probability(row.get("probability"))

            item_ok = expected_row is not None and not is_duplicate
            support_ok = item_ok and support == expected_support
            prob_ok = item_ok and expected_prob is not None and self._prob_matches(prob, float(expected_prob))
            below_ok = item_ok and below_raw == expected_below

            results[item_key] = {
                "correct": item_ok,
                "expected": (
                    "Duplikat: Itemset bereits eingetragen"
                    if is_duplicate
                    else (format_itemset(itemset) if expected_row else f"Erlaubte Itemsets in {level_label}: {allowed_itemsets}")
                ),
            }
            results[support_key] = {
                "correct": support_ok,
                "expected": str(expected_support) if expected_support is not None else f"Support zu einem Itemset aus {level_label}",
            }
            results[prob_key] = {
                "correct": prob_ok,
                "expected": expected_prob if expected_prob is not None else f"P zu einem Itemset aus {level_label}",
            }
            results[below_key] = {
                "correct": below_ok,
                "expected": str(expected_below) if expected_below is not None else f"Below minsup zu einem Itemset aus {level_label}",
            }

            if item_ok:
                matched_expected_itemsets.add(itemset)
                actual_rows.append(
                    (
                        itemset,
                        support,
                        None if prob is None else format_probability(prob),
                        below_raw,
                    )
                )

        actual_rows = sorted(actual_rows, key=lambda x: x[0])
        is_correct = (not duplicate) and (actual_rows == expected_rows)
        missing_rows = [row for row in expected_rows if row[0] not in matched_expected_itemsets]

        return {
            "results": results,
            "is_correct": is_correct,
            "missing_rows": missing_rows,
        }

    def _grade_dynamic_level_rows(self, k, user_input, expected_level):
        builder_key = f"apr_s{k}_builder"
        solution_payload = self._solution_payload(f"Referenzlösung für Schritt {k}", [expected_level])

        raw = user_input.get(builder_key, "")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return {
                builder_key: {
                    "correct": False,
                    "expected": solution_payload,
                }
            }

        rows_list = parsed.get("rows") if isinstance(parsed, dict) else []
        rows_list = rows_list if isinstance(rows_list, list) else []

        def row_key(row_idx, suffix):
            return f"{builder_key}_r{row_idx}_{suffix}"

        graded = self._grade_rows(
            rows_list,
            self._canonical_expected_rows(expected_level),
            row_key,
            f"C{k}",
        )
        results = dict(graded["results"])
        is_correct = graded["is_correct"]

        results[builder_key] = {
            "correct": is_correct,
            "expected": solution_payload,
        }
        return results

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}

        results.update(self._evaluate_prefilled_level1(user_input))

        for level in self.levels[1:]:
            k = level["k"]
            results.update(self._grade_dynamic_level_rows(k, user_input, level))

            terminate_key = f"apr_s{k}_terminate"
            results[terminate_key] = {
                "correct": self._bool_value(user_input.get(terminate_key)) == bool(level["terminate"]),
                "expected": str(bool(level["terminate"])),
            }

        return results

    def _fail(self, message):
        return {"apriori_exam": {"correct": False, "expected": self._solution_payload(message)}}

    def _canonical_expected_level(self, level):
        return {
            "rows": self._canonical_expected_rows(level),
            "terminate": bool(level["terminate"]),
        }

    def _evaluate_exam(self, user_input):
        raw = (user_input or {}).get("apriori_exam", "")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return self._fail("Ungültige Builder-Daten. Bitte Eingaben im Builder vornehmen.")

        user_levels = parsed.get("levels") if isinstance(parsed, dict) else []
        if not isinstance(user_levels, list):
            user_levels = []

        expected_levels = [self._canonical_expected_level(level) for level in self.levels]
        results = {}
        overall_correct = True
        messages = []

        if len(user_levels) != len(expected_levels):
            overall_correct = False
            messages.append(
                f"Falsche Anzahl von Levels. Erwartet: {len(expected_levels)}, gegeben: {len(user_levels)}."
            )

        shared_count = min(len(user_levels), len(expected_levels))

        for level_idx in range(shared_count):
            user_level = user_levels[level_idx] if isinstance(user_levels[level_idx], dict) else {}
            expected_level = expected_levels[level_idx]

            rows = user_level.get("rows", [])
            rows_list = rows if isinstance(rows, list) else []
            expected_rows = expected_level["rows"]

            def row_key(row_idx, suffix):
                return f"apriori_exam_l{level_idx}_r{row_idx}_{suffix}"

            graded = self._grade_rows(
                rows_list,
                expected_rows,
                row_key,
                f"Level {level_idx + 1}",
            )
            results.update(graded["results"])

            if not graded["is_correct"]:
                overall_correct = False
                messages.append(f"Level {level_idx + 1} hat falsche oder fehlende Zeilen.")

            missing_rows = graded["missing_rows"]
            if missing_rows:
                missing_labels = ", ".join(format_itemset(row[0]) for row in missing_rows)
                messages.append(f"Level {level_idx + 1} fehlt: {missing_labels}")

                missing_offset = len(rows_list)
                for miss_idx, miss_row in enumerate(missing_rows):
                    row_idx = missing_offset + miss_idx
                    item_key = f"apriori_exam_l{level_idx}_r{row_idx}_itemset"
                    support_key = f"apriori_exam_l{level_idx}_r{row_idx}_support"
                    prob_key = f"apriori_exam_l{level_idx}_r{row_idx}_probability"
                    below_key = f"apriori_exam_l{level_idx}_r{row_idx}_belowMinsup"

                    results[item_key] = {"correct": False, "expected": format_itemset(miss_row[0])}
                    results[support_key] = {"correct": False, "expected": str(miss_row[1])}
                    results[prob_key] = {"correct": False, "expected": miss_row[2]}
                    results[below_key] = {"correct": False, "expected": str(miss_row[3])}

            term_key = f"apriori_exam_l{level_idx}_terminate"
            term_actual = self._bool_value(user_level.get("terminate"))
            term_expected = bool(expected_level["terminate"])
            results[term_key] = {
                "correct": term_actual == term_expected,
                "expected": str(term_expected),
            }
            if term_actual != term_expected:
                overall_correct = False
                messages.append(f"Termination in Level {level_idx + 1} ist falsch.")

        if len(user_levels) > len(expected_levels):
            for extra_idx in range(len(expected_levels), len(user_levels)):
                term_key = f"apriori_exam_l{extra_idx}_terminate"
                results[term_key] = {"correct": False, "expected": "Kein zusätzliches Level"}

        if len(user_levels) < len(expected_levels):
            messages.append("Es fehlen Level in der Eingabe.")

        summary = "Alle Schritte inkl. Termination korrekt." if overall_correct else " | ".join(messages) if messages else "Nicht korrekt."
        results["apriori_exam"] = {
            "correct": overall_correct,
            "expected": self._solution_payload(summary),
        }
        return results

    def evaluate(self, user_input):
        return self._evaluate_exam(user_input) if self.mode == "exam" else self._evaluate_steps(user_input)

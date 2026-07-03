import json
import random
import re
from itertools import combinations

from app.question_types.frequent_itemset_helper import (
    format_itemset,
    format_probability,
    generate_transaction_dataset,
    parse_probability,
    run_apriori_levels,
)


DIFFICULTY_SETTINGS = {
    "easy": {
        "num_items": 4,
        "num_transactions": 8,
        "min_items": 1,
        "max_items": 3,
        "minsup_range": (0.40, 0.60),
        "min_conf_range": (0.60, 0.75),
        "target_itemset_count": 1,
        "prefer_target_sizes": (2, 3),
        "min_target_rule_count": 2,
        "min_accepted_rule_count": 1,
    },
    "medium": {
        "num_items": 5,
        "num_transactions": 9,
        "min_items": 1,
        "max_items": 4,
        "minsup_range": (0.30, 0.50),
        "min_conf_range": (0.65, 0.80),
        "target_itemset_count": 2,
        "prefer_target_sizes": (3, 2),
        "min_target_rule_count": 4,
        "min_accepted_rule_count": 1,
    },
    "hard": {
        "num_items": 6,
        "num_transactions": 10,
        "min_items": 2,
        "max_items": 5,
        "minsup_range": (0.25, 0.40),
        "min_conf_range": (0.70, 0.85),
        "target_itemset_count": 2,
        "prefer_target_sizes": (3, 2),
        "min_target_rule_count": 6,
        "min_accepted_rule_count": 1,
    },
}


class AssociationRuleMiningQuestion:
    """
    Association-rule question based on already frequent itemsets.

    The generated instance gives L1, L2 and L3 frequent itemsets, but only selects
    one or two frequent 2-/3-itemsets as target itemsets. Students build the
    possible rules for those targets and calculate the confidence formula in the
    probability notation used in the exercise sheet:

        conf(A => B) = P(A intersection B) / P(A)
        P(A) = sigma(A) / |Transactions|

    The dynamic UI lets students add/remove rule blocks and edit both sides of
    the arrow. Numeric formula fields use probabilities, while the evaluator also
    accepts the corresponding support counts for compatibility.

    Expected frontend payload for the dynamic UI component:
        {
            "groups": [
                {
                    "target": "ABD",
                    "rows": [
                        {
                            "lhs": "A",
                            "rhs": "BD",
                            "numerator": "3",
                            "denominator": "5",
                            "confidence": "0.60",
                            "accepted": false
                        }
                    ]
                }
            ]
        }
    """

    FIELD_ID = "arm_formula_rules"

    def __init__(self, seed=None, difficulty="easy", mode="steps"):
        self.difficulty = str(difficulty).lower()
        self.config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = str(mode or "steps").lower()
        if self.mode not in {"steps", "exam"}:
            self.mode = "steps"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.minsup = round(self.rng.uniform(*self.config["minsup_range"]), 2)
        self.min_confidence = round(self.rng.uniform(*self.config["min_conf_range"]), 2)

        self.base_items = []
        self.transactions = []
        self.levels = []
        self.minsup_count = 1
        self.frequent_itemsets = []
        self.target_itemsets = []
        self.support_map = {}
        self.target_rules = []
        self.accepted_target_rules = []

        self._initialize_instance()

    @staticmethod
    def _normalize_itemset(items):
        return tuple(sorted(str(item).strip().upper() for item in items if str(item).strip()))

    @classmethod
    def _itemset_key(cls, items):
        return "|".join(cls._normalize_itemset(items))

    @classmethod
    def _compact_itemset(cls, items):
        return "".join(cls._normalize_itemset(items))

    @classmethod
    def parse_itemset_text(cls, value):
        """Accepts A,B / A B / A;B / A|B / AB / ab for single-letter item names."""
        raw = str(value or "").strip().upper()
        if not raw:
            return tuple()

        if any(sep in raw for sep in [",", ";", " ", "/", "|"]):
            parts = [part for part in re.split(r"[,;\s/|]+", raw) if part]
        else:
            # Compact notation: AB means A,B. This assumes single-letter item names.
            parts = list(raw)

        return cls._normalize_itemset(parts)

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
    def _confidence_matches(actual, expected):
        return actual is not None and abs(float(actual) - float(expected)) <= 0.005

    def _initialize_instance(self):
        chosen = None

        for attempt in range(160):
            local_rng = random.Random(self.seed + attempt)
            base_items, transactions = generate_transaction_dataset(
                local_rng,
                self.config["num_items"],
                self.config["num_transactions"],
                self.config["min_items"],
                self.config["max_items"],
            )

            levels, minsup_count = run_apriori_levels(transactions, base_items, self.minsup)
            frequent_itemsets = self._collect_frequent_itemsets(levels)
            support_map = self._build_support_map(frequent_itemsets)
            target_itemsets = self._choose_target_itemsets(frequent_itemsets, support_map, local_rng)
            target_rules = self._generate_rules_for_targets(target_itemsets, support_map)
            accepted_rules = [rule for rule in target_rules if rule["accepted"]]

            chosen = (
                base_items,
                transactions,
                levels,
                minsup_count,
                frequent_itemsets,
                target_itemsets,
                support_map,
                target_rules,
                accepted_rules,
            )

            if (
                target_itemsets
                and len(target_rules) >= self.config["min_target_rule_count"]
                and len(accepted_rules) >= self.config["min_accepted_rule_count"]
            ):
                break

        if not chosen:
            raise ValueError("Failed to generate association-rule mining instance.")

        (
            self.base_items,
            self.transactions,
            self.levels,
            self.minsup_count,
            self.frequent_itemsets,
            self.target_itemsets,
            self.support_map,
            self.target_rules,
            self.accepted_target_rules,
        ) = chosen

    def _collect_frequent_itemsets(self, levels):
        itemsets = []
        for level in levels:
            k = int(level["k"])
            if k > 3:
                continue
            for entry in level["frequents"]:
                itemset = self._normalize_itemset(entry["itemset"])
                itemsets.append(
                    {
                        "level": k,
                        "itemset": itemset,
                        "count": int(entry["count"]),
                        "probability": float(entry["probability"]),
                    }
                )
        return sorted(itemsets, key=lambda x: (x["level"], x["itemset"]))

    def _build_support_map(self, frequent_itemsets):
        return {self._itemset_key(entry["itemset"]): int(entry["count"]) for entry in frequent_itemsets}

    def _non_empty_proper_subsets(self, itemset):
        items = list(self._normalize_itemset(itemset))
        result = []
        for size in range(1, len(items)):
            for subset in combinations(items, size):
                result.append(tuple(subset))
        return result

    def _rules_for_itemset(self, itemset, support_map):
        full_itemset = self._normalize_itemset(itemset)
        full_support = support_map.get(self._itemset_key(full_itemset))
        if not full_support or len(full_itemset) < 2:
            return []

        rules = []
        for lhs in self._non_empty_proper_subsets(full_itemset):
            lhs = self._normalize_itemset(lhs)
            rhs = tuple(item for item in full_itemset if item not in set(lhs))
            rhs = self._normalize_itemset(rhs)
            lhs_support = support_map.get(self._itemset_key(lhs))
            if not lhs_support:
                continue

            confidence = float(full_support) / float(lhs_support)
            rule = {
                "target": full_itemset,
                "lhs": lhs,
                "rhs": rhs,
                "support_xy": int(full_support),
                "support_x": int(lhs_support),
                "confidence": confidence,
                "accepted": confidence + 1e-12 >= self.min_confidence,
            }
            rule["key"] = self._rule_key(rule["lhs"], rule["rhs"])
            rules.append(rule)

        return sorted(rules, key=lambda r: (len(r["lhs"]), r["lhs"], r["rhs"]))

    def _choose_target_itemsets(self, frequent_itemsets, support_map, rng):
        candidates = [entry for entry in frequent_itemsets if 2 <= len(entry["itemset"]) <= 3]
        candidates = [entry for entry in candidates if self._rules_for_itemset(entry["itemset"], support_map)]
        if not candidates:
            return []

        amount = min(int(self.config["target_itemset_count"]), len(candidates))
        prefer_sizes = tuple(self.config.get("prefer_target_sizes", (2, 3)))

        by_size = {size: [entry for entry in candidates if len(entry["itemset"]) == size] for size in {2, 3}}
        for entries in by_size.values():
            rng.shuffle(entries)

        selected = []
        for size in prefer_sizes:
            while by_size.get(size) and len(selected) < amount:
                selected.append(by_size[size].pop(0))

        if len(selected) < amount:
            remaining = [entry for entry in candidates if entry not in selected]
            rng.shuffle(remaining)
            selected.extend(remaining[: amount - len(selected)])

        return sorted(selected, key=lambda x: (len(x["itemset"]), x["itemset"]))

    def _generate_rules_for_targets(self, target_itemsets, support_map):
        rules = []
        for target in target_itemsets:
            rules.extend(self._rules_for_itemset(target["itemset"], support_map))
        return sorted(rules, key=lambda r: (r["target"], len(r["lhs"]), r["lhs"], r["rhs"]))

    @classmethod
    def _rule_key(cls, lhs, rhs):
        return f"{cls._itemset_key(lhs)}=>{cls._itemset_key(rhs)}"

    def _transaction_rows(self):
        return [[f"T{i + 1}", ", ".join(sorted(list(tx)))] for i, tx in enumerate(self.transactions)]

    def _frequent_itemset_rows(self):
        return [
            [
                f"L{entry['level']}",
                format_itemset(entry["itemset"]),
                str(entry["count"]),
                format_probability(entry["probability"]),
            ]
            for entry in self.frequent_itemsets
        ]

    def _target_itemset_rows(self):
        transaction_count = max(1, len(self.transactions))
        return [
            [
                format_itemset(entry["itemset"]),
                str(entry["count"]),
                format_probability(float(entry["count"]) / float(transaction_count)),
                str(len(self._rules_for_itemset(entry["itemset"], self.support_map))),
            ]
            for entry in self.target_itemsets
        ]

    def _component_payload(self, steps=True):
        transaction_count = max(1, len(self.transactions))
        return {
            "type": "AssociationRuleFormulaBuilder",
            "id": self.FIELD_ID,
            "label": "Assoziationsregeln: Konfidenz",
            "minConfidence": float(self.min_confidence),
            "transactionCount": transaction_count,
            "formulaText": "conf(A ⇒ B) = P(A∩B) / P(A)",
            "probabilityDefinition": "P(A) = σ(A) / |Transactions|",
            "supportItemsets": [
                {
                    "items": list(entry["itemset"]),
                    "support": int(entry["count"]),
                    "probability": float(entry["probability"]),
                    "level": int(entry["level"]),
                }
                for entry in self.frequent_itemsets
            ],
            "targetItemsets": [
                {
                    "items": list(entry["itemset"]),
                    "support": int(entry["count"]),
                    "probability": float(entry["count"]) / float(transaction_count),
                }
                for entry in self.target_itemsets
            ],
            "showFormula": True,
            "showDecisionInput": True,
            # Students should build the rules themselves: they can add/remove
            # blocks and edit both sides of A ⇒ B in steps and exam mode.
            "prefillRuleSides": False,
            "allowRuleEditing": True,
            "allowAddRows": True,
            "initialRowsPerTarget": 2,
        }

    def _rule_solution_rows(self, rules=None):
        source_rules = self.target_rules if rules is None else rules
        transaction_count = max(1, len(self.transactions))
        return [
            [
                format_itemset(rule["target"]),
                format_itemset(rule["lhs"]),
                format_itemset(rule["rhs"]),
                format_probability(float(rule["support_xy"]) / float(transaction_count)),
                format_probability(float(rule["support_x"]) / float(transaction_count)),
                format_probability(rule["confidence"]),
                str(bool(rule["accepted"])),
            ]
            for rule in source_rules
        ]

    def _solution_payload(self, message):
        groups = []
        for target in self.target_itemsets:
            target_key = self._compact_itemset(target["itemset"])
            rows = []
            for rule in self.target_rules:
                if rule["target"] != target["itemset"]:
                    continue
                rows.append(
                    {
                        "lhs": format_itemset(rule["lhs"]),
                        "rhs": format_itemset(rule["rhs"]),
                        "numerator": format_probability(float(rule["support_xy"]) / float(max(1, len(self.transactions)))),
                        "denominator": format_probability(float(rule["support_x"]) / float(max(1, len(self.transactions)))),
                        "supportXY": str(rule["support_xy"]),
                        "supportX": str(rule["support_x"]),
                        "confidence": format_probability(rule["confidence"]),
                        "accepted": str(bool(rule["accepted"])),
                    }
                )
            groups.append({"target": target_key, "rows": rows})

        return {
            "message": message,
            "minConfidence": format_probability(self.min_confidence),
            "groups": groups,
        }

    def _generate_steps_layout(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Erzeuge die Assoziationsregeln für die angegebenen frequent itemsets (FIS) "
                        "und berechne die Konfidenz mit der Notation aus der Übung.\n"
                        f"- Mindestkonfidenz $$d = {format_probability(self.min_confidence)}$$.\n"
                        "- Lege für jede Regel einen Block an und trage die Itemsets links und rechts des Pfeils ein.\n"
                        "- Trage dann die Wahrscheinlichkeiten $$P(A\\cap B)$$ und $$P(A)$$ sowie die Konfidenz ein.\n"
                        "- Für die Wahrscheinlichkeiten gilt: $$P(A)=\\frac{\\sigma(A)}{|Transactions|}$$.\n\n"
                        "$$conf(A \\Rightarrow B)=\\frac{P(A\\cap B)}{P(A)}$$"
                    ),
                },
                {
                    "type": "Table",
                    "title": "Gegebene frequent itemsets",
                    "columns": ["Level", "FIS", "σ", "P"],
                    "rows": self._frequent_itemset_rows(),
                },
                {
                    "type": "Table",
                    "title": "Ziel-Itemsets für die Regelerzeugung",
                    "columns": ["FIS", "σ", "P", "Anzahl möglicher Regeln"],
                    "rows": self._target_itemset_rows(),
                },
                self._component_payload(steps=True),
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": "Referenzlösung: Alle Regeln der Ziel-FIS mit Wahrscheinlichkeiten, Konfidenz und Entscheidung.",
                },
                {
                    "type": "Table",
                    "title": "Regeln aus den Ziel-FIS",
                    "columns": ["FIS", "A", "B", "P(A∩B)", "P(A)", "conf", "conf ≥ d?"],
                    "rows": self._rule_solution_rows() or [["-", "-", "-", "-", "-", "-", "-"]],
                },
            ],
        }

    def _generate_exam_layout(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Exam-Modus: Erzeuge die Assoziationsregeln für die angegebenen Ziel-FIS und berechne die Konfidenz.\n"
                        f"Mindestkonfidenz: $$d = {format_probability(self.min_confidence)}$$. "
                        "Verwende $$conf(A \\Rightarrow B)=\\frac{P(A\\cap B)}{P(A)}$$ und "
                        "$$P(A)=\\frac{\\sigma(A)}{|Transactions|}$$."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Gegebene frequent itemsets",
                    "columns": ["Level", "FIS", "σ", "P"],
                    "rows": self._frequent_itemset_rows(),
                },
                {
                    "type": "Table",
                    "title": "Ziel-Itemsets für die Regelerzeugung",
                    "columns": ["FIS", "σ", "P", "Anzahl möglicher Regeln"],
                    "rows": self._target_itemset_rows(),
                },
                self._component_payload(steps=False),
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": "Referenzlösung: Alle Regeln der Ziel-FIS mit Wahrscheinlichkeiten, Konfidenz und Entscheidung.",
                },
                {
                    "type": "Table",
                    "title": "Regeln aus den Ziel-FIS",
                    "columns": ["FIS", "A", "B", "P(A∩B)", "P(A)", "conf", "conf ≥ d?"],
                    "rows": self._rule_solution_rows() or [["-", "-", "-", "-", "-", "-", "-"]],
                },
            ],
        }

    def generate(self):
        return self._generate_exam_layout() if self.mode == "exam" else self._generate_steps_layout()

    def _parse_builder_payload(self, user_input):
        raw = (user_input or {}).get(self.FIELD_ID, "")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        groups = parsed.get("groups", [])
        return groups if isinstance(groups, list) else []

    def _expected_group_rule_maps(self):
        by_target = {}
        for target_idx, target in enumerate(self.target_itemsets):
            target_key = self._compact_itemset(target["itemset"])
            by_target[target_key] = {
                "target_idx": target_idx,
                "rules": {},
            }

        for rule in self.target_rules:
            target_key = self._compact_itemset(rule["target"])
            by_target.setdefault(target_key, {"target_idx": 0, "rules": {}})
            by_target[target_key]["rules"][rule["key"]] = rule

        return by_target

    def _grade_rows(self, groups):
        """Grade the dynamic rule-builder payload.

        The returned shape mirrors FPTreeBuilder/evaluate_fp_tree: the main
        component key contains the global result plus nested detailed results.
        The flat field ids are still returned for backwards compatibility, but
        the React component can now read everything through
        evaluationResults[FIELD_ID].field_results and .rule_results.
        """
        results = {}
        field_results = {}
        rule_results = {}
        missing = []
        extra = []

        expected_by_target = self._expected_group_rule_maps()
        all_expected_rules = {rule["key"]: rule for rule in self.target_rules}
        matched_rule_keys = set()
        seen_rule_keys = set()
        messages = []
        overall_correct = True
        transaction_count = max(1, len(self.transactions))

        def add_message(message):
            if message and message not in messages:
                messages.append(message)

        def format_rule_label(rule):
            return f"{format_itemset(rule['lhs'])}⇒{format_itemset(rule['rhs'])}"

        def expected_probability_or_count(probability, support_count):
            return f"{format_probability(probability)} oder σ={int(support_count)}"

        def rule_payload(rule):
            numerator_probability = float(rule["support_xy"]) / float(transaction_count)
            denominator_probability = float(rule["support_x"]) / float(transaction_count)
            return {
                "target": format_itemset(rule["target"]),
                "lhs": format_itemset(rule["lhs"]),
                "rhs": format_itemset(rule["rhs"]),
                "label": format_rule_label(rule),
                "numerator": format_probability(numerator_probability),
                "denominator": format_probability(denominator_probability),
                "supportXY": str(rule["support_xy"]),
                "supportX": str(rule["support_x"]),
                "confidence": format_probability(rule["confidence"]),
                "accepted": str(bool(rule["accepted"])),
            }

        def set_field(field_id, correct, expected, **extra_payload):
            payload = {
                "correct": bool(correct),
                "expected": expected,
            }
            payload.update(extra_payload)
            field_results[field_id] = payload
            # Keep the old flat structure as a compatibility fallback.
            results[field_id] = payload
            return payload

        def set_rule(base_key, *, correct, message=None, expected_rule=None, actual_rule=None, field_ids=None, **flags):
            payload = {
                "correct": bool(correct),
                "field_ids": field_ids or {},
            }
            payload.update(flags)
            if message:
                payload["message"] = message
            if expected_rule is not None:
                expected_payload = rule_payload(expected_rule)
                payload["expected"] = expected_payload
                payload["expected_lhs"] = expected_payload["lhs"]
                payload["expected_rhs"] = expected_payload["rhs"]
            if actual_rule is not None:
                payload["actual"] = actual_rule
            rule_results[base_key] = payload
            return payload

        allowed_rules = ", ".join(format_rule_label(rule) for rule in self.target_rules)

        for group_idx, group in enumerate(groups):
            group = group if isinstance(group, dict) else {}
            rows = group.get("rows", [])
            rows = rows if isinstance(rows, list) else []

            for row_idx, row in enumerate(rows):
                row = row if isinstance(row, dict) else {}
                lhs_raw = str(row.get("lhs") or row.get("antecedent") or "").strip()
                rhs_raw = str(row.get("rhs") or row.get("consequent") or "").strip()
                numerator_raw = str(row.get("numerator") or row.get("supportXY") or "").strip()
                denominator_raw = str(row.get("denominator") or row.get("supportX") or "").strip()
                conf_raw = str(row.get("confidence") or "").strip()
                accepted_value = row.get("accepted")
                accepted_raw = self._bool_value(accepted_value)

                row_has_content = bool(lhs_raw or rhs_raw or numerator_raw or denominator_raw or conf_raw or accepted_raw)
                if not row_has_content:
                    continue

                base_key = f"{self.FIELD_ID}_g{group_idx}_r{row_idx}"
                lhs_key = f"{base_key}_lhs"
                rhs_key = f"{base_key}_rhs"
                numerator_key = f"{base_key}_numerator"
                denominator_key = f"{base_key}_denominator"
                confidence_key = f"{base_key}_confidence"
                accepted_key = f"{base_key}_accepted"
                field_ids = {
                    "lhs": lhs_key,
                    "rhs": rhs_key,
                    "numerator": numerator_key,
                    "denominator": denominator_key,
                    "confidence": confidence_key,
                    "accepted": accepted_key,
                }

                lhs = self.parse_itemset_text(lhs_raw)
                rhs = self.parse_itemset_text(rhs_raw)
                rule_key = self._rule_key(lhs, rhs) if lhs and rhs else ""
                actual_payload = {
                    "lhs": format_itemset(lhs) if lhs else lhs_raw,
                    "rhs": format_itemset(rhs) if rhs else rhs_raw,
                    "label": f"{format_itemset(lhs) if lhs else lhs_raw}⇒{format_itemset(rhs) if rhs else rhs_raw}",
                }

                group_target_raw = group.get("target") or ""
                if not group_target_raw and group_idx < len(self.target_itemsets):
                    group_target_raw = self._compact_itemset(self.target_itemsets[group_idx]["itemset"])
                group_target_key = self._compact_itemset(self.parse_itemset_text(group_target_raw))
                expected_rules_for_group = expected_by_target.get(group_target_key, {}).get("rules", all_expected_rules)
                expected_rule = expected_rules_for_group.get(rule_key)
                allowed_rules_for_group = ", ".join(
                    format_rule_label(rule) for rule in expected_rules_for_group.values()
                ) or allowed_rules

                is_duplicate = bool(rule_key and rule_key in seen_rule_keys)
                if rule_key:
                    seen_rule_keys.add(rule_key)

                if not lhs or not rhs:
                    overall_correct = False
                    set_field(lhs_key, False, "Antezedens erforderlich")
                    set_field(rhs_key, False, "Konsequenz erforderlich")
                    set_field(numerator_key, False, "P(A∩B) erforderlich")
                    set_field(denominator_key, False, "P(A) erforderlich")
                    set_field(confidence_key, False, "Konfidenz erforderlich")
                    set_field(accepted_key, False, "Entscheidung erforderlich")
                    set_rule(
                        base_key,
                        correct=False,
                        message="Regel unvollständig.",
                        actual_rule=actual_payload,
                        field_ids=field_ids,
                        lhs_correct=False,
                        rhs_correct=False,
                        numerator_correct=False,
                        denominator_correct=False,
                        confidence_correct=False,
                        accepted_correct=False,
                    )
                    add_message("Mindestens eine Regel hat kein vollständiges Antezedens/Konsequenz.")
                    extra.append({
                        "group": group_idx,
                        "row": row_idx,
                        "lhs": actual_payload["lhs"],
                        "rhs": actual_payload["rhs"],
                        "label": actual_payload["label"],
                        "message": "incomplete rule",
                    })
                    continue

                rule_ok = expected_rule is not None and not is_duplicate
                if not rule_ok:
                    overall_correct = False
                    expected_text = (
                        "Duplikat: Regel bereits eingetragen"
                        if is_duplicate
                        else f"Erlaubte Regeln für dieses FIS: {allowed_rules_for_group}"
                    )
                    set_field(lhs_key, False, expected_text)
                    set_field(rhs_key, False, expected_text)
                    set_field(numerator_key, False, "P(A∩B) zu einer erlaubten Regel")
                    set_field(denominator_key, False, "P(A) zu einer erlaubten Regel")
                    set_field(confidence_key, False, "Konfidenz zu einer erlaubten Regel")
                    set_field(accepted_key, False, "Entscheidung zu einer erlaubten Regel")
                    set_rule(
                        base_key,
                        correct=False,
                        message="Doppelte oder nicht erlaubte Regel.",
                        actual_rule=actual_payload,
                        field_ids=field_ids,
                        lhs_correct=False,
                        rhs_correct=False,
                        numerator_correct=False,
                        denominator_correct=False,
                        confidence_correct=False,
                        accepted_correct=False,
                    )
                    add_message("Es wurden doppelte oder nicht erlaubte Regeln eingetragen.")
                    extra.append({
                        "group": group_idx,
                        "row": row_idx,
                        "lhs": actual_payload["lhs"],
                        "rhs": actual_payload["rhs"],
                        "label": actual_payload["label"],
                        "message": "duplicate rule" if is_duplicate else "not an allowed rule for this target itemset",
                    })
                    continue

                matched_rule_keys.add(rule_key)
                numerator_raw_value = row.get("numerator") or row.get("supportXY")
                denominator_raw_value = row.get("denominator") or row.get("supportX")
                numerator_probability = parse_probability(numerator_raw_value)
                denominator_probability = parse_probability(denominator_raw_value)
                numerator_count = self._int_value(numerator_raw_value)
                denominator_count = self._int_value(denominator_raw_value)
                confidence = parse_probability(row.get("confidence"))

                expected_numerator_probability = float(expected_rule["support_xy"]) / float(transaction_count)
                expected_denominator_probability = float(expected_rule["support_x"]) / float(transaction_count)
                numerator_ok = (
                    self._confidence_matches(numerator_probability, expected_numerator_probability)
                    or numerator_count == int(expected_rule["support_xy"])
                )
                denominator_ok = (
                    self._confidence_matches(denominator_probability, expected_denominator_probability)
                    or denominator_count == int(expected_rule["support_x"])
                )
                confidence_ok = self._confidence_matches(confidence, expected_rule["confidence"])
                accepted_ok = accepted_raw == bool(expected_rule["accepted"])
                rule_correct = bool(numerator_ok and denominator_ok and confidence_ok and accepted_ok)

                set_field(lhs_key, True, format_itemset(expected_rule["lhs"]))
                set_field(rhs_key, True, format_itemset(expected_rule["rhs"]))
                set_field(
                    numerator_key,
                    numerator_ok,
                    expected_probability_or_count(expected_numerator_probability, expected_rule["support_xy"]),
                    expected_probability=format_probability(expected_numerator_probability),
                    expected_support=str(expected_rule["support_xy"]),
                )
                set_field(
                    denominator_key,
                    denominator_ok,
                    expected_probability_or_count(expected_denominator_probability, expected_rule["support_x"]),
                    expected_probability=format_probability(expected_denominator_probability),
                    expected_support=str(expected_rule["support_x"]),
                )
                set_field(confidence_key, confidence_ok, format_probability(expected_rule["confidence"]))
                set_field(accepted_key, accepted_ok, str(bool(expected_rule["accepted"])))
                set_rule(
                    base_key,
                    correct=rule_correct,
                    expected_rule=expected_rule,
                    actual_rule=actual_payload,
                    field_ids=field_ids,
                    lhs_correct=True,
                    rhs_correct=True,
                    numerator_correct=bool(numerator_ok),
                    denominator_correct=bool(denominator_ok),
                    confidence_correct=bool(confidence_ok),
                    accepted_correct=bool(accepted_ok),
                )

                if not rule_correct:
                    overall_correct = False
                if not numerator_ok:
                    add_message("Mindestens ein Wert P(A∩B) ist falsch.")
                if not denominator_ok:
                    add_message("Mindestens ein Wert P(A) ist falsch.")
                if not confidence_ok:
                    add_message("Mindestens eine Konfidenz ist falsch berechnet.")
                if not accepted_ok:
                    add_message("Mindestens eine conf ≥ d Entscheidung ist falsch.")

        missing_keys = sorted(set(all_expected_rules.keys()) - matched_rule_keys)
        if missing_keys:
            overall_correct = False
            missing_rules = [all_expected_rules[key] for key in missing_keys]
            missing.extend(rule_payload(rule) for rule in missing_rules)
            add_message(
                "Fehlende Regeln: "
                + ", ".join(format_rule_label(rule) for rule in missing_rules)
            )

            # Synthetic entries are useful if the user adds more rows after
            # evaluation; the same id pattern will immediately receive feedback.
            group_lengths = {
                idx: len((groups[idx] if idx < len(groups) and isinstance(groups[idx], dict) else {}).get("rows", []) or [])
                for idx in range(max(len(groups), len(self.target_itemsets)))
            }
            for rule in missing_rules:
                target_key = self._compact_itemset(rule["target"])
                target_idx = expected_by_target.get(target_key, {}).get("target_idx", 0)
                row_idx = group_lengths.get(target_idx, 0)
                group_lengths[target_idx] = row_idx + 1
                base_key = f"{self.FIELD_ID}_g{target_idx}_r{row_idx}"
                lhs_key = f"{base_key}_lhs"
                rhs_key = f"{base_key}_rhs"
                numerator_key = f"{base_key}_numerator"
                denominator_key = f"{base_key}_denominator"
                confidence_key = f"{base_key}_confidence"
                accepted_key = f"{base_key}_accepted"
                expected_numerator_probability = float(rule["support_xy"]) / float(transaction_count)
                expected_denominator_probability = float(rule["support_x"]) / float(transaction_count)
                set_field(lhs_key, False, format_itemset(rule["lhs"]))
                set_field(rhs_key, False, format_itemset(rule["rhs"]))
                set_field(numerator_key, False, expected_probability_or_count(expected_numerator_probability, rule["support_xy"]))
                set_field(denominator_key, False, expected_probability_or_count(expected_denominator_probability, rule["support_x"]))
                set_field(confidence_key, False, format_probability(rule["confidence"]))
                set_field(accepted_key, False, str(bool(rule["accepted"])))

        summary = (
            "Alle Regeln inkl. Formelwerte und Entscheidung korrekt."
            if overall_correct
            else " | ".join(messages) or "Nicht korrekt."
        )
        results[self.FIELD_ID] = {
            "correct": bool(overall_correct),
            "expected": self._solution_payload(summary),
            "field_results": field_results,
            "rule_results": rule_results,
            "missing": missing,
            "extra": extra,
            "message": summary,
        }
        return results

    def evaluate(self, user_input):
        groups = self._parse_builder_payload(user_input)
        if groups is None:
            return {
                self.FIELD_ID: {
                    "correct": False,
                    "expected": self._solution_payload("Ungültige Builder-Daten. Bitte Eingaben im Builder vornehmen."),
                    "field_results": {},
                    "rule_results": {},
                    "missing": [],
                    "extra": [],
                    "message": "Ungültige Builder-Daten. Bitte Eingaben im Builder vornehmen.",
                }
            }
        return self._grade_rows(groups)

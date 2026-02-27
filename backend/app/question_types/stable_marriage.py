import random
import re

from app.resources.synonyms import synonym_pairs


DIFFICULTY_SETTINGS = {
    "easy": {"n_choices": [3], "step_count_range": [3, 5]},
    "medium": {"n_choices": [3, 4], "step_count_range": [4, 6]},
    "hard": {"n_choices": [4], "step_count_range": [5, 12]},
}


class StableMarriageQuestion:
    def __init__(self, seed=None, difficulty="easy", mode="steps"):
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])
        self.n_choices = list(config.get("n_choices", [3]))
        step_range = config.get("step_count_range", [0, 999999])
        self.step_count_min = int(step_range[0])
        self.step_count_max = int(step_range[1])

        self.mode = (mode or "steps").lower()
        if self.mode not in {"steps", "exam"}:
            self.mode = "steps"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.n = 0
        self.pairs = []
        self.schema_a = []
        self.schema_b = []
        self.schema_a_pref = {}
        self.schema_b_pref = {}
        self.expected_matching = {}
        self.matching_history = []

        self._initialize_instance_for_difficulty()

    def _create_preference_lists(self, schema_a, schema_b, rng=None):
        rng = rng or self.rng
        schema_a_pref = {
            a: rng.sample(schema_b, len(schema_b))
            for a in schema_a
        }
        schema_b_pref = {
            b: rng.sample(schema_a, len(schema_a))
            for b in schema_b
        }
        return schema_a_pref, schema_b_pref

    def _initialize_instance_for_difficulty(self):
        max_attempts = 300
        first_candidate = None

        for attempt in range(max_attempts):
            attempt_rng = random.Random(self.seed + attempt)
            n = attempt_rng.choice(self.n_choices)

            pairs = attempt_rng.sample(synonym_pairs, n)
            schema_a = [a for a, _ in pairs]
            schema_b = [b for _, b in pairs]
            attempt_rng.shuffle(schema_a)
            attempt_rng.shuffle(schema_b)

            schema_a_pref, schema_b_pref = self._create_preference_lists(schema_a, schema_b, rng=attempt_rng)
            expected_matching, matching_history = self._solve_stable_marriage(schema_a_pref, schema_b_pref)

            candidate = {
                "n": n,
                "pairs": pairs,
                "schema_a": schema_a,
                "schema_b": schema_b,
                "schema_a_pref": schema_a_pref,
                "schema_b_pref": schema_b_pref,
                "expected_matching": expected_matching,
                "matching_history": matching_history,
            }

            if first_candidate is None:
                first_candidate = candidate

            steps = len(matching_history)
            if self.step_count_min <= steps <= self.step_count_max:
                first_candidate = candidate
                break

        if first_candidate is None:
            raise ValueError("Failed to initialize stable marriage instance")

        self.n = first_candidate["n"]
        self.pairs = first_candidate["pairs"]
        self.schema_a = first_candidate["schema_a"]
        self.schema_b = first_candidate["schema_b"]
        self.schema_a_pref = first_candidate["schema_a_pref"]
        self.schema_b_pref = first_candidate["schema_b_pref"]
        self.expected_matching = first_candidate["expected_matching"]
        self.matching_history = first_candidate["matching_history"]

    def _solve_stable_marriage(self, schema_a_pref, schema_b_pref):
        free_a = list(schema_a_pref.keys())
        next_choice_idx = {a: 0 for a in schema_a_pref}
        partner_of_b = {}
        history = []
        rank_in_b = {
            b: {a: idx for idx, a in enumerate(pref_list)}
            for b, pref_list in schema_b_pref.items()
        }

        while free_a:
            a = free_a.pop(0)
            k = next_choice_idx[a]
            potential_partner = schema_a_pref[a][k]
            next_choice_idx[a] += 1

            current_partner = partner_of_b.get(potential_partner)
            if current_partner is None:
                partner_of_b[potential_partner] = a
                decision = "agrees"
                left_a = None
            elif rank_in_b[potential_partner][a] < rank_in_b[potential_partner][current_partner]:
                partner_of_b[potential_partner] = a
                free_a.append(current_partner)
                decision = "agrees_and_leaves"
                left_a = current_partner
            else:
                free_a.append(a)
                decision = "declines"
                left_a = None

            pairs_snapshot = sorted(
                [(a_curr, b_curr) for b_curr, a_curr in partner_of_b.items()],
                key=lambda t: t[0],
            )
            history.append(
                {
                    "a": a,
                    "b": potential_partner,
                    "decision": decision,
                    "left_a": left_a,
                    "pairs": pairs_snapshot,
                }
            )

        matching = {a: b for b, a in partner_of_b.items()}
        return matching, history

    def _proposal_text(self, step):
        return f"{step['a']} proposes to {step['b']}"

    def _decision_text(self, step):
        if step["decision"] == "agrees":
            return f"{step['b']} agrees"
        if step["decision"] == "declines":
            return f"{step['b']} declines"
        return f"{step['b']} agrees and leaves {step['left_a']}"

    def _pairs_text(self, pairs):
        if not pairs:
            return "-"
        return ", ".join([f"({a}, {b})" for a, b in pairs])

    def _normalize_text(self, value):
        text = str(value or "").strip().lower()
        parts = [" ".join(part.split()) for part in text.replace("\n", ";").split(";")]
        parts = [p for p in parts if p]
        return ";".join(parts)

    def _normalize_pairs_text(self, value):
        text = str(value or "").strip().lower()
        if not text or text == "-":
            return "-"

        pairs = re.findall(r"\(([^,()]+),([^()]+)\)", text)
        if not pairs:
            return self._normalize_text(text)

        canonical = sorted(
            [(a.strip(), b.strip()) for a, b in pairs],
            key=lambda t: (t[0], t[1]),
        )
        return ";".join([f"({a},{b})" for a, b in canonical])

    def _step_row_layout(self, index):
        return [
            {
                "type": "Text",
                "content": f"Schritt {index}",
            },
            {
                "type": "layout_table",
                "title": "Eingabe für diesen Schritt",
                "rows": 1,
                "cols": 3,
                "cells": [[
                    {
                        "type": "TextInput",
                        "id": f"sm_step_{index}_proposal",
                        "label": "Vorschlag",
                    },
                    {
                        "type": "TextInput",
                        "id": f"sm_step_{index}_decision",
                        "label": "Entscheidung",
                    },
                    {
                        "type": "TextInput",
                        "id": f"sm_step_{index}_pairs",
                        "label": "Resultierende Paare",
                    },
                ]],
            },
        ]

    def _generate_steps_layout(self):
        base = {}

        base["view1"] = [
            {
                "type": "layout_table",
                "title": "Schemata",
                "rows": 1,
                "cols": 2,
                "cells": [[
                    {
                        "type": "Table",
                        "title": "Schema A",
                        "columns": ["Element"],
                        "rows": [[a] for a in self.schema_a],
                    },
                    {
                        "type": "Table",
                        "title": "Schema B",
                        "columns": ["Element"],
                        "rows": [[b] for b in self.schema_b],
                    },
                ]],
            },
            {
                "type": "Text",
                "content": (
                    "Aufgabe: Führe den Stable-Marriage-Algorithmus schrittweise aus. "
                    "Verwende die gezeigten Präferenzlisten. Die Elemente aus Schema A werden in Reihenfolge verarbeitet. "
                    "Wenn ein Vorschlag abgelehnt wird, bleibt das Element aus Schema A zunächst frei und der Algorithmus setzt mit dem nächsten Element fort.\n\n"
                    "Erwartete Eingaben pro Schritt:\n"
                    "- Vorschlag: z. B. a1 proposes to b1\n"
                    "- Entscheidung: b1 agrees | b1 agrees and leaves a2 | b1 declines\n"
                    "- Paare: z. B. (a1, b1), (a3, b2)"
                ),
            },
            {
                "type": "layout_table",
                "title": "Präferenzlisten",
                "rows": 1,
                "cols": 2,
                "cells": [[
                    {
                        "type": "Table",
                        "title": "Präferenzen von Schema A",
                        "columns": ["Element"] + [f"Rang {i + 1}" for i in range(self.n)],
                        "rows": [[a] + self.schema_a_pref[a] for a in self.schema_a],
                    },
                    {
                        "type": "Table",
                        "title": "Präferenzen von Schema B",
                        "columns": ["Element"] + [f"Rang {i + 1}" for i in range(self.n)],
                        "rows": [[b] + self.schema_b_pref[b] for b in self.schema_b],
                    },
                ]],
            },
        ] + self._step_row_layout(1)

        for idx in range(2, len(self.matching_history) + 1):
            base[f"view{idx}"] = self._step_row_layout(idx)

        base["lastView"] = [
            {
                "type": "Text",
                "content": "Algorithmus abgeschlossen.",
            },
            {
                "type": "Table",
                "title": "Finales stabiles Matching",
                "columns": ["Schema A", "Schema B"],
                "rows": [[a, self.expected_matching[a]] for a in sorted(self.expected_matching.keys())],
            },
        ]

        return base

    def _generate_exam_layout(self):
        return {
            "view1": [
                {
                    "type": "layout_table",
                    "title": "Schemata",
                    "rows": 1,
                    "cols": 2,
                    "cells": [[
                        {
                            "type": "Table",
                            "title": "Schema A",
                            "columns": ["Element"],
                            "rows": [[a] for a in self.schema_a],
                        },
                        {
                            "type": "Table",
                            "title": "Schema B",
                            "columns": ["Element"],
                            "rows": [[b] for b in self.schema_b],
                        },
                    ]],
                },
                {
                    "type": "Text",
                    "content": (
                        "Aufgabe: Führe den Stable-Marriage-Algorithmus schrittweise aus. "
                        "Verwende die gezeigten Präferenzlisten. Die Elemente aus Schema A werden in Reihenfolge verarbeitet. "
                        "Wenn ein Vorschlag abgelehnt wird, bleibt das Element aus Schema A zunächst frei und der Algorithmus setzt mit dem nächsten Element fort.\n\n"
                        "Exam-Modus: Gib den vollständigen Ablauf ein. Du kannst mit Enter neue Zeilen erzeugen. Trenne mehrere Einträge mit ';'.\n\n"
                        "Erwartete Form:\n"
                        "- Vorschläge: a1 proposes to b1; a2 proposes to b3\n"
                        "- Entscheidungen: b1 agrees; b3 declines; b2 agrees and leaves a1\n"
                        "- Paare: (a1, b1); (a3, b2)"
                    ),
                },
                {
                    "type": "layout_table",
                    "title": "Präferenzlisten",
                    "rows": 1,
                    "cols": 2,
                    "cells": [[
                        {
                            "type": "Table",
                            "title": "Präferenzen von Schema A",
                            "columns": ["Element"] + [f"Rang {i + 1}" for i in range(self.n)],
                            "rows": [[a] + self.schema_a_pref[a] for a in self.schema_a],
                        },
                        {
                            "type": "Table",
                            "title": "Präferenzen von Schema B",
                            "columns": ["Element"] + [f"Rang {i + 1}" for i in range(self.n)],
                            "rows": [[b] + self.schema_b_pref[b] for b in self.schema_b],
                        },
                    ]],
                },
                {
                    "type": "layout_table",
                    "title": "Gesamtablauf (Schritte mit ';' trennen!)",
                    "rows": 1,
                    "cols": 3,
                    "cells": [[
                        {
                            "type": "TextInput",
                            "id": "sm_exam_proposals",
                            "label": "Vorschläge",
                            "rows": 7,
                        },
                        {
                            "type": "TextInput",
                            "id": "sm_exam_decisions",
                            "label": "Entscheidungen",
                            "rows": 7,
                        },
                        {
                            "type": "TextInput",
                            "id": "sm_exam_pairs",
                            "label": "Zwischenpaare",
                            "rows": 7,
                        },
                    ]],
                },
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": "Bewertung abgeschlossen.",
                }
            ],
        }

    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        results = {}

        for idx, step in enumerate(self.matching_history, start=1):
            proposal_id = f"sm_step_{idx}_proposal"
            decision_id = f"sm_step_{idx}_decision"
            pairs_id = f"sm_step_{idx}_pairs"

            expected_proposal = self._proposal_text(step)
            expected_decision = self._decision_text(step)
            expected_pairs = self._pairs_text(step["pairs"])

            results[proposal_id] = {
                "correct": self._normalize_text(user_input.get(proposal_id, ""))
                == self._normalize_text(expected_proposal),
                "expected": expected_proposal,
            }
            results[decision_id] = {
                "correct": self._normalize_text(user_input.get(decision_id, ""))
                == self._normalize_text(expected_decision),
                "expected": expected_decision,
            }
            results[pairs_id] = {
                "correct": self._normalize_pairs_text(user_input.get(pairs_id, ""))
                == self._normalize_pairs_text(expected_pairs),
                "expected": expected_pairs,
            }

        return results

    def _evaluate_exam(self, user_input):
        proposals = [self._proposal_text(step) for step in self.matching_history]
        decisions = [self._decision_text(step) for step in self.matching_history]
        pairs = [self._pairs_text(step["pairs"]) for step in self.matching_history]

        expected_proposals = "; ".join(proposals)
        expected_decisions = "; ".join(decisions)
        expected_pairs = "; ".join(pairs)

        return {
            "sm_exam_proposals": {
                "correct": self._normalize_text(user_input.get("sm_exam_proposals", ""))
                == self._normalize_text(expected_proposals),
                "expected": expected_proposals,
            },
            "sm_exam_decisions": {
                "correct": self._normalize_text(user_input.get("sm_exam_decisions", ""))
                == self._normalize_text(expected_decisions),
                "expected": expected_decisions,
            },
            "sm_exam_pairs": {
                "correct": self._normalize_pairs_text(user_input.get("sm_exam_pairs", ""))
                == self._normalize_pairs_text(expected_pairs),
                "expected": expected_pairs,
            },
        }

    def evaluate(self, user_input):
        if self.mode == "exam":
            return self._evaluate_exam(user_input)
        return self._evaluate_steps(user_input)

import json
import random
import re
from pathlib import Path

from app.common import *

path = Path(__file__).resolve().parent.parent / "resources" / "ir_documents.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

DIFFICULTY_SETTINGS = {
    "easy":   {"docs_per_topic": 1, "query_terms": 2},
    "medium": {"docs_per_topic": 1, "query_terms": 3},
    "hard":   {"docs_per_topic": 2, "query_terms": 4},
}


class IRMeasuresJaccard:
    def __init__(self, seed=None, difficulty="easy", mode="steps", **kwargs):
        self.rounding = 3
        self.difficulty = str(difficulty).lower() if str(difficulty).lower() in DIFFICULTY_SETTINGS else "easy"
        self.mode = str(mode).lower()
        self.measure = "jaccard"
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.docs_per_topic = settings["docs_per_topic"]
        self.query_terms = settings["query_terms"]

        self.expected = {"jaccard": {}}
        self.expected_sets = {}

        self._solve()

    def _solve(self):
        self.corpus = {
            block["Thema"]: [
                {"topic": block["Thema"], "nr": d["Nr"], "tokens": list(d["content"])}
                for d in block["Docs"]
            ]
            for block in raw
        }

        self.selected_docs = []
        for topic, docs in self.corpus.items():
            if len(docs) < self.docs_per_topic:
                raise ValueError(f"Not enough docs in topic '{topic}' for docs_per_topic={self.docs_per_topic}")
            self.selected_docs.extend(self.rng.sample(docs, k=self.docs_per_topic))
        self.rng.shuffle(self.selected_docs)

        pool = [t for d in self.selected_docs for t in d["tokens"]]
        unique_pool = list(dict.fromkeys(pool))
        self.query = (
            self.rng.sample(unique_pool, k=self.query_terms)
            if len(unique_pool) >= self.query_terms
            else self.rng.choices(pool, k=self.query_terms)
        )

        self.selected_docs.sort(key=lambda d: int(re.search(r"\d+", d["nr"]).group(0)))
        self.query_set = set(self.query)
        self.query_terms_unique = sorted(self.query_set)

        for d in self.selected_docs:
            doc_set = set(d["tokens"])
            inter = self.query_set & doc_set
            union = self.query_set | doc_set
            score = 0.0 if not union else round(len(inter) / len(union), self.rounding)

            self.expected_sets[d["nr"]] = {
                "query_terms": sorted(self.query_set),
                "doc_terms": sorted(doc_set),
                "intersection_terms": sorted(inter),
                "union_terms": sorted(union),
                "intersection_size": len(inter),
                "union_size": len(union),
            }
            self.expected["jaccard"][d["nr"]] = score

    def _generate_steps_layout(self):
        docs = self.selected_docs
        base = {}

        view1 = [
            {
                "type": "Table",
                "title": "Ausgewählte Dokumente (Korpus)",
                "columns": ["Thema", "Nr", "Tokens"],
                "rows": [[d["topic"], d["nr"], ", ".join(d["tokens"])] for d in docs],
            },
            {
                "type": "Text",
                "content": (
                    "### Aufgabe (Steps): Jaccard Similarity\n\n"
                    f"Query: **{' '.join(self.query)}**\n\n"
                    "#### Teil 1: Mengen betrachten\n"
                    "Für Jaccard arbeiten wir mit **Mengen**, also nur mit **einzigartigen Termen**.\n\n"
                    "Doppelte Wörter zählen nicht mehrfach.\n"
                    "Unten sind die Mengen für Query und Dokumente bereits angegeben."
                    "**Hinweis:** Runde alle berechneten Werte auf **2 Nachkommastellen**.\n"
                ),
            },
            {
                "type": "Table",
                "title": "Query-Menge Q",
                "columns": ["Terme in Q"],
                "rows": [[t] for t in self.query_terms_unique],
            },
        ]

        for d in docs:
            view1.append({
                "type": "Table",
                "title": f"Dokumentmenge {d['nr']}",
                "columns": [f"Terme in {d['nr']}"],
                "rows": [[t] for t in self.expected_sets[d["nr"]]["doc_terms"]],
            })

        view2 = [
            {
                "type": "Text",
                "content": (
                    "#### Teil 2: Schnittmenge und Vereinigungsmenge\n\n"
                    "Berechne für jedes Dokument:\n\n"
                    "- **Schnittmenge**: $$Q \\cap D$$\n"
                    "- **Vereinigungsmenge**: $$Q \\cup D$$\n\n"
                    "Gib die Terme jeweils in **einem Textfeld** ein, getrennt durch Kommas.\n"
                    "Die **Reihenfolge ist egal**.\n\n"
                    "Beispiel:\n"
                    "`Katze, Hund, Wasser`"
                ),
            }
        ]

        for d in docs:
            nr = d["nr"]
            view2 += [
                {"type": "Text", "content": f"#### {nr}: Mengen eingeben"},
                {
                    "type": "TextInput",
                    "label": f"Schnittmenge Q ∩ {nr}",
                    "id": f"intersection_{nr}",
                    "rows": 2,
                },
                {
                    "type": "TextInput",
                    "label": f"Vereinigungsmenge Q ∪ {nr}",
                    "id": f"union_{nr}",
                    "rows": 3,
                },
            ]

        view3 = [
            {
                "type": "Text",
                "content": (
                    "#### Teil 3: Kardinalitäten und Jaccard-Wert\n\n"
                    "Jetzt bestimme:\n"
                    "- $$|Q \\cap D|$$\n"
                    "- $$|Q \\cup D|$$\n\n"
                    "und berechne dann:\n\n"
                    "$$J(Q,D) = \\frac{|Q \\cap D|}{|Q \\cup D|}$$"
                ),
            }
        ]

        cells = [[
            {"type": "text", "value": "**Dokument**"},
            {"type": "text", "value": "**|Q ∩ D|**"},
            {"type": "text", "value": "**|Q ∪ D|**"},
            {"type": "text", "value": "**Jaccard**"},
        ]]

        for d in docs:
            nr = d["nr"]
            cells.append([
                {"type": "text", "value": nr},
                {"type": "TextInput", "id": f"intersection_size_{nr}"},
                {"type": "TextInput", "id": f"union_size_{nr}"},
                {"type": "TextInput", "id": f"score_{nr}"},
            ])

        view3.append({
            "type": "layout_table",
            "rows": len(cells),
            "cols": 4,
            "cells": cells,
        })
        base["lastView"] = [{
            "type": "Text",
            "content": (
                "### Hinweis zur Praxis:\n\n"
                "Die Jaccard-Ähnlichkeit misst die Überschneidung zwischen zwei Mengen.\n\n"
                "**Idee:**\n"
                "Verglichen wird, wie viele gemeinsame Elemente zwei Mengen haben "
                "im Verhältnis zur Gesamtanzahl unterschiedlicher Elemente.\n\n"
                "**Vorteile:**\n"
                "- Einfach zu berechnen und zu interpretieren\n"
                "- Gut geeignet für Mengenvergleiche (z. B. Dokumente als Token-Mengen)\n"
                "- Robust gegenüber unterschiedlicher Dokumentlänge\n\n"
                "**Einschränkung:**\n"
                "Berücksichtigt keine Gewichtung oder Häufigkeit von Begriffen, sondern nur deren Vorkommen."
            ),
        }]
        base["view1"] = view1 + view2
        base["view2"] = view3
        #base["view3"] = view3
        return base

    def _generate_exam_layout(self):
        return {
            "view1": [
                {
                    "type": "Table",
                    "title": "Ausgewählte Dokumente",
                    "columns": ["Thema", "Nr", "Tokens"],
                    "rows": [[d["topic"], d["nr"], ", ".join(d["tokens"])] for d in self.selected_docs],
                },
                {
                    "type": "Text",
                    "content": (
                        "### Prüfungsaufgabe: Dokument-Ähnlichkeit (Jaccard)\n\n"
                        f"Query: **{' '.join(self.query)}**\n\n"
                        "Berechne die Jaccard Similarity der Query zu **jedem** Dokument.\n\n"
                        "Verwende Mengen, also **nur einzigartige Terme**:\n"
                        "$$J(Q,D) = \\frac{|Q \\cap D|}{|Q \\cup D|}$$\n\n"
                        "#### Abgabeformat\n"
                        "Gib deine Ergebnisse genau in dieser Form an:\n"
                        "- `D1: <wert>`\n"
                        "- `D2: <wert>`\n"
                        "- ...\n"
                    ),
                },
                {
                    "type": "TextInput",
                    "label": "Antworten Jaccard (z.B. D1: 0.5)",
                    "id": "answers_jaccard",
                    "rows": 10,
                },
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": (
                        "### Hinweis zur Praxis:\n\n"
                        "Die Jaccard-Ähnlichkeit misst die Überschneidung zwischen zwei Mengen.\n\n"
                        "**Idee:**\n"
                        "Verglichen wird, wie viele gemeinsame Elemente zwei Mengen haben "
                        "im Verhältnis zur Gesamtanzahl unterschiedlicher Elemente.\n\n"
                        "**Vorteile:**\n"
                        "- Einfach zu berechnen und zu interpretieren\n"
                        "- Gut geeignet für Mengenvergleiche (z. B. Dokumente als Token-Mengen)\n"
                        "- Robust gegenüber unterschiedlicher Dokumentlänge\n\n"
                        "**Einschränkung:**\n"
                        "Berücksichtigt keine Gewichtung oder Häufigkeit von Begriffen, sondern nur deren Vorkommen."
                    ),
                }]
        }

    def generate(self):
        return self._generate_exam_layout() if self.mode == "exam" else self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}
        sets_ok = True
        sizes_ok = True
        scores_ok = True

        def parse_term_list(text):
            text = "" if text is None else str(text)
            parts = [p.strip().lower() for p in text.split(",")]
            return {p for p in parts if p}

        for d in self.selected_docs:
            nr = d["nr"]
            exp = self.expected_sets[nr]

            intersection_id = f"intersection_{nr}"
            union_id = f"union_{nr}"
            intersection_size_id = f"intersection_size_{nr}"
            union_size_id = f"union_size_{nr}"
            score_id = f"score_{nr}"

            expected_intersection = {t.lower() for t in exp["intersection_terms"]}
            expected_union = {t.lower() for t in exp["union_terms"]}

            found_intersection = parse_term_list(user_input.get(intersection_id))
            found_union = parse_term_list(user_input.get(union_id))

            ok_intersection = found_intersection == expected_intersection
            ok_union = found_union == expected_union

            results[intersection_id] = {
                "correct": ok_intersection,
                "expected": ", ".join(exp["intersection_terms"]) if exp["intersection_terms"] else "∅",
            }
            results[union_id] = {
                "correct": ok_union,
                "expected": ", ".join(exp["union_terms"]),
            }

            sets_ok &= ok_intersection and ok_union

            exp_intersection_size = exp["intersection_size"]
            exp_union_size = exp["union_size"]
            exp_score = self.expected["jaccard"][nr]

            ok_intersection_size = (
                str(normalize_number(user_input.get(intersection_size_id)))
                == str(normalize_number(exp_intersection_size))
            )
            ok_union_size = (
                str(normalize_number(user_input.get(union_size_id)))
                == str(normalize_number(exp_union_size))
            )
            ok_score = (
                str(normalize_number(user_input.get(score_id)))
                == str(normalize_number(exp_score))
            )

            results[intersection_size_id] = {
                "correct": ok_intersection_size,
                "expected": str(normalize_number(exp_intersection_size)),
            }
            results[union_size_id] = {
                "correct": ok_union_size,
                "expected": str(normalize_number(exp_union_size)),
            }
            results[score_id] = {
                "correct": ok_score,
                "expected": str(normalize_number(exp_score)),
            }

            sizes_ok &= ok_intersection_size and ok_union_size
            scores_ok &= ok_score

        results["sets"] = {
            "correct": sets_ok,
            "expected": "Alle Schnitt- und Vereinigungsmengen korrekt.",
        }
        results["sizes"] = {
            "correct": sizes_ok,
            "expected": "Alle Kardinalitäten korrekt.",
        }
        results["scores"] = {
            "correct": scores_ok,
            "expected": "\n".join(
                f"{d['nr']}: {normalize_number(self.expected['jaccard'][d['nr']])}"
                for d in self.selected_docs
            ),
        }
        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        text = str(user_input.get("answers_jaccard", "") or "")
        parsed = {
            docid.upper(): val
            for docid, val in re.findall(r"(?im)\b(D\d+)\b\s*[:=]?\s*([-+]?\d+(?:[.,]\d+)?)", text)
        }

        expected_lines = []
        all_correct = True
        for d in self.selected_docs:
            nr = d["nr"].upper()
            exp = self.expected["jaccard"][d["nr"]]
            if str(normalize_number(parsed.get(nr))) != str(normalize_number(exp)):
                all_correct = False
            expected_lines.append(f"{nr}: {normalize_number(exp)}")

        return {
            "answers_jaccard": {
                "correct": all_correct,
                "expected": "\n".join(expected_lines),
            }
        }

    def evaluate(self, user_input):
        return self._evaluate_exam(user_input) if self.mode == "exam" else self._evaluate_steps(user_input)

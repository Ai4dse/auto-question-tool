from collections import Counter
from app.common import *
from pathlib import Path
import json

path = Path(__file__).resolve().parent.parent / "resources" / "ir_documents.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

DIFFICULTY_SETTINGS = {
    "easy":   {"doc_num": 2},
    "medium": {"doc_num": 3},
    "hard":   {"doc_num": 4},
}


class InvertedIndex:
    def __init__(self, seed=None, difficulty="easy", **kwargs):
        self.difficulty = str(difficulty).lower() if str(difficulty).lower() in DIFFICULTY_SETTINGS else "easy"
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.docs_per_topic = self.settings["doc_num"]

        block = self.rng.choice(raw)
        sampled_docs = self.rng.sample(block["Docs"], self.docs_per_topic)

        self.docs = [
            {
                "nr": f"Doc{i+1}",
                "tokens": list(d["content"])
            }
            for i, d in enumerate(sampled_docs)
        ]

        self.terms = sorted({
            term
            for doc in self.docs
            for term in doc["tokens"]
        })

        self._solve()

    def _solve(self):
        self.solution = {
            f"id_term_{term}": ", ".join(
                doc["nr"]
                for doc in self.docs
                if term in doc["tokens"]
            )
            for term in self.terms
        }

    def _generate_steps_layout(self):
        base = {}

        cells = []
        cells.append([
            {"type": "text", "value": "**Term**"},
            {"type": "text", "value": "**Dokumente**"}
        ])

        for term in self.terms:
            cells.append([
                {"type": "text", "value": f"*{term}*"},
                {"type": "text_input", "id": f"id_term_{term}"}
            ])

        view1 = [
            {
                "type": "Text",
                "content": (
                    "### Inverted Index\n\n"
                    "Betrachte die folgenden Dokumente:\n"
                    + "\n".join(
                        f"- **{doc['nr']}**: {' '.join(doc['tokens'])}"
                        for doc in self.docs
                    )
                    + "\n\n"
                    "### Aufgabe\n\n"
                    "Erstelle einen **Inverted Index** für die gegebenen Dokumente.\n\n"
                    "Für jeden Term soll angegeben werden, in welchen Dokumenten er vorkommt.\n\n"
                    "**Vorgehen:**\n"
                    "- Jede Zeile entspricht einem Term\n"
                    "- Trage alle passenden Dokumente ein, z. B. `Doc1, Doc3`\n"
                    "- Verwende nur die Bezeichnungen `Doc1`, `Doc2`, ...\n"
                    "- Gib die Dokumente in **aufsteigender Reihenfolge** an\n\n"
                    "**Hinweis:**\n"
                    "Wenn ein Term nur in einem Dokument vorkommt, trage nur dieses Dokument ein."
                ),
            },
            {
                "type": "layout_table",
                "rows": len(self.terms) + 1,
                "cols": 2,
                "cells": cells
            }
        ]
        base["view1"] = view1

        base["lastView"] = [{
            "type": "Text",
            "content": (
                "### Hinweis zur Praxis\n\n"
                "Der Inverted Index ist eine zentrale Datenstruktur in Suchmaschinen.\n\n"
                "**Vorteile gegenüber der Term-Document-Incidence-Matrix:**\n"
                "- Es werden nur tatsächlich vorkommende Einträge gespeichert\n"
                "- Es gibt keine große Matrix mit fast nur Nullen\n"
                "- Suchanfragen können sehr effizient verarbeitet werden\n\n"
                "**Idee:**\n"
                "Zu jedem Term wird direkt gespeichert, in welchen Dokumenten er vorkommt.\n\n"
                "Dadurch ist die Darstellung kompakter und in der Praxis deutlich besser geeignet."
            ),
        }]

        return base

    def generate(self):
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}

        for term in self.terms:
            key = f"id_term_{term}"

            expected = normalize_list_string(self.solution[key])
            user_val = normalize_list_string(user_input.get(key))

            results[key] = {
                "correct": user_val == expected,
                "expected": ", ".join(expected) if isinstance(expected, tuple) else expected
            }

        return results

    def evaluate(self, user_input):
        return self._evaluate_steps(user_input)
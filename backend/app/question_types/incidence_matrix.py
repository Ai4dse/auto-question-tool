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


class IncidenceMatrix:
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
            f"id_{doc['nr']}_{term}": (term in doc["tokens"])
            for doc in self.docs
            for term in self.terms
        }

    def _generate_steps_layout(self):
        base = {}

        cells = []

        header = [{"type": "text", "value": "**Term**"}] + [
            {"type": "text", "value": f"**{doc['nr']}**"}
            for doc in self.docs
        ]
        cells.append(header)

        for term in self.terms:
            row = [{"type": "text", "value": f"*{term}*"}] + [
                {"type": "text_input", "id": f"id_{doc['nr']}_{term}"}
                for doc in self.docs
            ]
            cells.append(row)
        view1 = [
            {
                "type": "Text",
                "content": (
                    "### Term-Document-Incidence-Matrix\n\n"
                    "Betrachte die folgenden Dokumente:\n"
                    + "\n".join(
                        f"- **{doc['nr']}**: {' '.join(doc['tokens'])}"
                        for doc in self.docs
                    )
                    + "\n\n"
                    "### Aufgabe\n\n"
                    "Fülle die bereitgestellte Tabelle (Term-Document-Incidence-Matrix) aus.\n\n"
                ),
            },
            {"type": "layout_table", "rows": len(self.terms)+1, "cols": len(self.docs)+1, "cells": cells}
        ]
        base["view1"] = view1
        base["lastView"] = [{
            "type": "Text",
            "content": (
                "### Hinweis zur Praxis\n\n"
                "Die Term-Document-Incidence-Matrix wird in der Praxis selten direkt verwendet.\n\n"
                "**Grund:**\n"
                "- In großen Dokumentkollektionen gibt es **sehr viele unterschiedliche Terme**\n"
                "- Jedes einzelne Dokument enthält jedoch nur **wenige dieser Terme**\n\n"
                "→ Die Matrix ist daher **dünnbesetzt (sparse)**, d. h. sie enthält fast nur Nullen.\n\n"
                "**Folge:**\n"
                "- Sehr hoher Speicherbedarf\n"
                "- Ineffiziente Verarbeitung\n\n"
                "Deshalb verwendet man in der Praxis kompaktere Darstellungen (z. B. invertierte Indizes)."
            ),
        }]
        return base

    def generate(self):
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}
        for term in self.terms:
            for doc in self.docs:
                key = f"id_{doc['nr']}_{term}"

                expected = self.solution[key]
                user_val = user_input.get(key)

                results[key] = {
                    "correct": str(user_val) == ("1" if expected else "0"),
                    "expected": "1" if expected else "0"
                }
        print(self.terms)
        print("####################################")
        print(results)
        return results

    def evaluate(self, user_input):
        return self._evaluate_steps(user_input)

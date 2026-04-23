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


class PositionalIndex:
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
        self._generate_queries()

    def _has_proximity_match(self, a, b, n):

        matching_docs = []

        for doc in self.docs:
            pos_a = [i for i, token in enumerate(doc["tokens"], start=1) if token == a]
            pos_b = [i for i, token in enumerate(doc["tokens"], start=1) if token == b]

            found = False
            for pa in pos_a:
                for pb in pos_b:
                    if pb > pa and (pb - pa) <= n:
                        found = True
                        break
                if found:
                    break

            if found:
                matching_docs.append(doc["nr"])

        return matching_docs


    def _generate_queries(self):
        """
        Erzeugt 2 zufällige Proximity-Anfragen, die mindestens ein Match haben.
        Bevorzugt Anfragen, die in mehr als einem Dokument matchen.
        """
        candidates = []

        for a in self.terms:
            for b in self.terms:
                if a == b:
                    continue
                for n in [1, 2, 3]:
                    matches = self._has_proximity_match(a, b, n)
                    if matches:
                        candidates.append({
                            "a": a,
                            "b": b,
                            "n": n,
                            "query": f"{a} /{n} {b}",
                            "matches": matches
                        })

        if not candidates:
            self.queries = []
            return

        multi_doc = [q for q in candidates if len(q["matches"]) > 1]
        pool = multi_doc if len(multi_doc) >= 2 else candidates

        if len(pool) >= 2:
            self.queries = self.rng.sample(pool, 2)
        else:
            self.queries = pool
        self.query_solution = {
            f"id_query_{i+1}": ", ".join(q["matches"]) if q["matches"] else "-"
            for i, q in enumerate(self.queries)
        }

    def _solve(self):
        self.solution = {}

        for term in self.terms:
            entries = []

            for doc in self.docs:
                positions = [
                    idx
                    for idx, token in enumerate(doc["tokens"], start=1)
                    if token == term
                ]

                if positions:
                    pos_str = ", ".join(str(p) for p in positions)
                    entries.append(f"{doc['nr']}: [{pos_str}]")

            self.solution[f"id_term_{term}"] = "; ".join(entries)

    def _generate_steps_layout(self):
        base = {}

        cells = []
        cells.append([
            {"type": "text", "value": "**Term**"},
            {"type": "text", "value": "**Dokumente mit Positionen**"}
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
                    "### Positional Index\n\n"
                    "Betrachte die folgenden Dokumente:\n"
                    + "\n".join(
                        f"- **{doc['nr']}**: {' '.join(doc['tokens'])}"
                        for doc in self.docs
                    )
                    + "\n\n"
                    "### Aufgabe\n\n"
                    "Erstelle einen **Positional Index** für die gegebenen Dokumente.\n\n"
                    "Für jeden Term soll angegeben werden,\n"
                    "- in welchen Dokumenten er vorkommt und\n"
                    "- an welchen **Positionen** im jeweiligen Dokument.\n\n"
                    "**Verwende dieses Format:**\n"
                    "- `Doc1: [1, 4]; Doc2: [2]`\n\n"
                    "**Hinweise:**\n"
                    "- Die Positionen beginnen bei **1**\n"
                    "- Die Dokumente sollen in aufsteigender Reihenfolge angegeben werden\n"
                    "- Die Positionen innerhalb eines Dokuments sollen ebenfalls aufsteigend angegeben werden\n"
                    "- Wenn ein Term nur in einem Dokument vorkommt, genügt ein einzelner Eintrag"
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
        view2 = [
            {
                "type": "Text",
                "content": (
                    "### Proximity-Anfragen\n\n"
                    "Bearbeite die folgenden Anfragen:\n"
                    + "\n".join(
                        f"- **{q['query']}**"
                        for q in self.queries
                    )
                    + "\n\n"
                    "### Aufgabe\n\n"
                    "Gib für jede Anfrage alle Dokumente an, in denen die Anfrage ein Match hat.\n\n"
                    "**Bedeutung:**\n"
                    "- `a /n b` bedeutet: Zwischen `a` und `b` liegen **höchstens n-1 Wörter**\n"
                    "- `/1` bedeutet also: `a` und `b` stehen **direkt hintereinander**\n"
                    "- Die Reihenfolge ist wichtig: zuerst `a`, danach `b`\n\n"
                    "**Beispiel:**\n"
                    "- `home /1 sales` matcht nur `home sales`\n"
                    "- `sales /2 july` matcht neben `sales july` auch `sales x july`\n"
                    "- `sales /2 july` ≠ `july /2 sales`\n\n"
                    "**Antwortformat:**\n"
                    "- Trage die passenden Dokumente als Liste ein, z. B. `Doc1, Doc3`\n"
                    "- Wenn keine Übereinstimmung existiert, trage `-` ein"
                ),
            }
        ]

        for i, q in enumerate(self.queries, start=1):
            view2.append({
                "type": "text_input",
                "id": f"id_query_{i}",
                "label": f"{q['query']}"
            })

        base["view2"] = view2

        base["lastView"] = [{
            "type": "Text",
            "content": (
                "### Hinweis zur Praxis\n\n"
                "Ein Positional Index erweitert den Inverted Index um die genauen Positionen der Terme in den Dokumenten.\n\n"
                "**Vorteile:**\n"
                "- Suchanfragen mit Wortabständen können beantwortet werden\n"
                "- Phrasensuche wird möglich\n"
                "- Die Positionen liefern zusätzliche Strukturinformationen\n\n"
                "**Beispiel:**\n"
                "Für eine Anfrage wie `new home` kann geprüft werden, ob beide Wörter direkt hintereinander im selben Dokument vorkommen.\n\n"
                "Deshalb ist der Positional Index besonders wichtig für Suchmaschinen und Information Retrieval."
            ),
        }]

        return base

    def generate(self):
        return self._generate_steps_layout()

    def _normalize_positional_string(self, value):
        """
        Normalize positional index strings into a comparable canonical form.

        Accepts variants like:
        - Doc1: [1, 4]; Doc2: [2]
        - doc2:[2] | doc1:[4,1]
        - Doc1 [1 4], Doc2 [2]

        Returns:
            tuple of normalized document-position entries, e.g.
            ('doc1:[1,4]', 'doc2:[2]')
        """
        if value is None:
            return ""

        s = str(value).strip()
        if s == "" or s == "-":
            return ""

        matches = re.findall(r'(Doc\d+)\s*:?\s*\[([^\]]*)\]', s, flags=re.IGNORECASE)

        if not matches:
            return normalize_list_string(s)

        normalized_entries = []

        for doc, positions_raw in matches:
            positions = re.findall(r'\d+', positions_raw)
            positions = sorted({int(p) for p in positions})
            pos_str = ",".join(str(p) for p in positions)
            normalized_entries.append((doc.lower(), f"{doc.lower()}:[{pos_str}]"))

        normalized_entries = sorted(set(normalized_entries), key=lambda x: int(re.search(r'\d+', x[0]).group()))
        return tuple(entry for _, entry in normalized_entries)

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}

        for term in self.terms:
            key = f"id_term_{term}"

            expected = self._normalize_positional_string(self.solution[key])
            user_val = self._normalize_positional_string(user_input.get(key))

            if isinstance(expected, tuple):
                expected_display = "; ".join(expected)
            else:
                expected_display = expected

            results[key] = {
                "correct": user_val == expected,
                "expected": expected_display
            }
        for i, q in enumerate(self.queries, start=1):
            key = f"id_query_{i}"
            expected = normalize_list_string(self.query_solution[key])
            user_val = normalize_list_string(user_input.get(key))

            results[key] = {
                "correct": user_val == expected,
                "expected": self.query_solution[key]
            }

        return results

    def evaluate(self, user_input):
        return self._evaluate_steps(user_input)
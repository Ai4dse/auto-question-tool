import random
import re
from pathlib import Path
import json
from collections import defaultdict

from app.common import *

DIFFICULTY_SETTINGS = {
    "easy": {},
    "medium": {},
    "hard": {},
}

path = Path(__file__).resolve().parent.parent / "resources" / "er_diagrams.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

class ERSchema:

    def __init__(self, seed=None, difficulty="easy", mode="steps", question="random", **kwargs):
        print(kwargs)
        self.question = str(question).lower()
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = mode.lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        if self.question == "random":
            self.task = self.rng.choice(raw)
        else:
            self.task = next(t for t in raw if self.question == t["id"])
        self.nodes = self.task["cardinality"]["nodes"]
        self.edges = self.task["cardinality"]["edges"]


    def _generate_steps_layout(self):
        self.entity_names = [n["data"]["label"] for n in self.nodes if n["type"] == "entity"]
        self.relationship_names = [n["data"]["label"] for n in self.nodes if n["type"] in ["relationship", "relation"]]
        self.max_final_relations = len(self.entity_names) + len(self.relationship_names)
        base = {}

        view1 = [
            {
                "type": "Text",
                "content": (
                    "### Aufgabe (Steps): ER-Diagramm in relationales Schema überführen\n\n"
                    "Gegeben ist ein vollständiges ER-Diagramm. "
                    "Überführe es **schrittweise** in ein relationales Schema.\n\n"
                    "#### Teil 1: Entitäten in Relationen überführen\n\n"
                    "Erzeuge zunächst für jede **Entität** aus dem ER-Diagramm genau **eine Relation**.\n"
                    "Trage pro Entität den **Relationsnamen** und alle zugehörigen **Attribute** ein.\n\n"
                    "Achte darauf:\n"
                    "- Beziehungen werden in diesem Schritt **noch nicht** übertragen\n"
                    "- Verwende die Namen aus dem ER-Diagramm\n"
                    "- Attribute sollen **atomar** notiert werden\n"
                    "- Primärschlüssel und Fremdschlüssel werden in **eigenen Feldern** eingetragen\n\n"
                    "### Hinweise\n"
                    "- Falls Attributnamen mehrfach vorkommen und dadurch mehrdeutig werden, benenne sie eindeutig um,\n"
                    "  z. B. als $$Entitaet.Attribut$$ oder $$Beziehung.Attribut$$\n"
                    "- Achte auf eine konsistente Benennung über alle Schritte hinweg\n"
                ),
            },
            {
                "type": "ER_Diagram_Builder",
                "id": "free_er_builder",
                "title": "Gegebenes ER-Diagramm",
                "initial_diagram": {
                    "nodes": self.nodes,
                    "edges": self.edges,
                }
            },
        ]

        entity_cells = [[
            {"type": "text", "value": "**Relation**"},
            {"type": "text", "value": "**Attribute**"},
            {"type": "text", "value": "**Primärschlüssel (PK)**"},
        ]]

        for i in range(len(self.entity_names)):
            entity_cells.append([
                {"type": "TextInput", "id": f"v1_relation_{i}"},
                {"type": "TextInput", "id": f"v1_attributes_{i}"},
                {"type": "TextInput", "id": f"v1_pk_{i}"},
            ])

        view1 += [
            {
                "type": "Text",
                "content": (
                    "#### Entitätsrelationen\n"
                    "Trage für jede Entität eine Relation, ihre Attribute und den Primärschlüssel ein."
                ),
            },
            {
                "type": "layout_table",
                "rows": len(entity_cells),
                "cols": 3,
                "cells": entity_cells,
            },
        ]

        base["view1"] = view1


        view2 = [
            {
                "type": "Text",
                "content": (
                    "#### Teil 2: Beziehungen zunächst als eigene Relationen überführen\n\n"
                    "Überführe nun **alle Beziehungen** aus dem ER-Diagramm zunächst in **eigene Relationen**.\n"
                    "Gehe also in diesem Schritt noch **nicht optimierend** vor.\n\n"
                    "Achte darauf:\n"
                    "- Jede Beziehung wird zuerst als eigene Relation notiert\n"
                    "- Übernimm die Schlüssel der beteiligten Entitäten als Attribute in diese Relation\n"
                    "- Vorhandene Beziehungsattribute gehören ebenfalls in diese Relation\n"
                    "- Trage Primärschlüssel und Fremdschlüssel wieder in die vorgesehenen Felder ein\n"
                ),
            },
        ]

        relationship_cells = [[
            {"type": "text", "value": "**Beziehungsrelation**"},
            {"type": "text", "value": "**Attribute**"},
            {"type": "text", "value": "**Primärschlüssel (PK)**"},
            {"type": "text", "value": "**Fremdschlüssel (FK)**"},
        ]]

        for i in range(len(self.relationship_names)):
            relationship_cells.append([
                {"type": "TextInput", "id": f"v2_relation_{i}"},
                {"type": "TextInput", "id": f"v2_attributes_{i}"},
                {"type": "TextInput", "id": f"v2_pk_{i}"},
                {"type": "TextInput", "id": f"v2_fk_{i}"},
            ])

        view2 += [
            {
                "type": "Text",
                "content": (
                    "#### Beziehungsrelationen\n"
                    "Trage hier alle Beziehungen zunächst als eigene Relationen ein."
                ),
            },
            {
                "type": "layout_table",
                "rows": len(relationship_cells),
                "cols": 4,
                "cells": relationship_cells,
            },
        ]

        base["view2"] = view2


        view3 = [
            {
                "type": "Text",
                "content": (
                    "#### Teil 3: 1..1- und 1..*-Beziehungen optimieren\n\n"
                    "Prüfe nun, welche der in Teil 2 erzeugten Beziehungsrelationen bei $$1..1$$- oder $$1..*$$-Beziehungen "
                    "nicht als eigene Relation bestehen bleiben müssen.\n"
                    "Integriere diese stattdessen, wo möglich, über geeignete **Fremdschlüssel** in die passenden Entitätsrelationen.\n\n"
                    "Achte darauf:\n"
                    "- $$M..N$$-Beziehungen bleiben in der Regel als eigene Relation bestehen\n"
                    "- $$1..1$$- und $$1..*$$-Beziehungen können oft in Entitätsrelationen integriert werden\n"
                    "- Trage pro Entitätsrelation nur die **neu hinzukommenden Fremdschlüssel** ein\n"
                    "- Entferne in Gedanken die entsprechenden Beziehungsrelationen, wenn sie vollständig ersetzt wurden\n"
                ),
            },
        ]

        opt_cells = [[
            {"type": "text", "value": "**Entitätsrelation**"},
            {"type": "text", "value": "**Zusätzliche Fremdschlüssel nach Optimierung**"},
        ]]

        for i in range(len(self.entity_names)):
            opt_cells.append([
                {"type": "text", "value": self.entity_names[i]},
                {"type": "TextInput", "id": f"v3_fk_{i}"},
            ])

        view3 += [
            {
                "type": "Text",
                "content": (
                    "#### Optimierte Fremdschlüssel\n"
                    "Trage die Fremdschlüssel ein, die nach der Optimierung in Entitätsrelationen aufgenommen werden."
                ),
            },
            {
                "type": "layout_table",
                "rows": len(opt_cells),
                "cols": 2,
                "cells": opt_cells,
            },
        ]
        base["view3"] = view3


        view4 = [
            {
                "type": "Text",
                "content": (
                    "#### Teil 4: Vollständiges relationales Schema\n\n"
                    "Führe nun alle bisherigen Zwischenschritte zu einem vollständigen relationalen Schema zusammen.\n\n"
                    "Achte darauf:\n"
                    "- Alle Entitäten wurden in Relationen überführt\n"
                    "- Alle Primärschlüssel sind korrekt gesetzt\n"
                    "- Alle nötigen Fremdschlüssel sind enthalten\n"
                    "- Beziehungen aus $$M..N$$ bleiben als eigene Relationen bestehen\n"
                    "- Beziehungen aus $$1..1$$ und $$1..*$$ wurden, falls möglich, sinnvoll integriert\n"
                ),
            },
        ]

        final_cells = [[
            {"type": "text", "value": "**Relation**"},
            {"type": "text", "value": "**Attribute**"},
            {"type": "text", "value": "**Primärschlüssel (PK)**"},
            {"type": "text", "value": "**Fremdschlüssel (FK)**"},
        ]]

        for i in range(self.max_final_relations):
            final_cells.append([
                {"type": "TextInput", "id": f"v4_relation_{i}"},
                {"type": "TextInput", "id": f"v4_attributes_{i}"},
                {"type": "TextInput", "id": f"v4_pk_{i}"},
                {"type": "TextInput", "id": f"v4_fk_{i}"},
            ])

        view4 += [
            {
                "type": "Text",
                "content": "#### Vollständiges relationales Schema",
            },
            {
                "type": "layout_table",
                "rows": len(final_cells),
                "cols": 4,
                "cells": final_cells,
            },
        ]

        base["view4"] = view4

        return base

    def _generate_exam_layout(self):
        base = {}
        view1 = [
            {
                "type": "Text",
                "content": (
                    "### Prüfungsaufgabe: ER-Diagramm → Relationales Schema\n\n"
                    "Gegeben ist ein **ER-Diagramm**. Leite daraus ein **relational optimiertes Schema** ab.\n\n"
                    "Achte dabei insbesondere auf:\n"
                    "- **Primärschlüssel (PK)** korrekt bestimmen\n"
                    "- **Fremdschlüssel (FK)** aus Beziehungen ableiten\n"
                    "- **n:m-Beziehungen** in eigene Relationen überführen\n"
                    "- **1:n-Beziehungen** durch Fremdschlüssel modellieren\n"
                    "- Nur **optimierte Relationen** angeben (keine redundanten Zwischentabellen)\n\n"
                    "#### Abgabeformat\n"
                    "Gib dein Ergebnis **als Text** im folgenden Format an:\n\n"
                    "- **Eine Relation pro Zeile**\n"
                    "- Format: `Relation(Attribut1,Attribut2,...)`\n"
                    "- Attribute werden durch **Kommas getrennt**\n\n"
                    "#### Schlüsselkennzeichnung\n"
                    "- Primärschlüssel: `(PK)`\n"
                    "- Fremdschlüssel: `(FK)`\n"
                    "- Kombination möglich: `(PK)(FK)`\n\n"
                    "Die Markierungen können **vor oder nach dem Attributnamen** stehen.\n\n"
                    "#### Beispiele für gültige Attribute\n"
                    "- `(PK)id`\n"
                    "- `id(PK)`\n"
                    "- `(FK)kunden_id`\n"
                    "- `(PK)(FK)bestell_id`\n\n"
                    "#### Beispiel für eine vollständige Lösung\n"
                    "```\n"
                    "Kunde((PK)KID,Name,Adresse)\n"
                    "Bestellung((PK)BID,Datum,(FK)KID)\n"
                    "Produkt((PK)PID,Bezeichnung,Preis)\n"
                    "enthaelt((PK)(FK)BID,(PK)(FK)PID,Menge)\n"
                    "```\n\n"
                    "#### Hinweise\n"
                    "- Reihenfolge der Relationen ist beliebig\n"
                    "- Reihenfolge der Attribute ist beliebig\n"
                    "- Groß-/Kleinschreibung ist relevant (falls nicht anders angegeben)\n"
                    "- Verwende **keine zusätzlichen Zeichen oder Kommentare**\n"
                ),
            },
            {
                "type": "ER_Diagram_Builder",
                "id": "free_er_builder",
                "title": "Gegebenes ER-Diagramm",
                "initial_diagram": {
                    "nodes": self.nodes,
                    "edges": self.edges,
                }
            },
            {
                "type": "TextInput",
                "label": "Relationales Schema",
                "id": "er_schema",
                "rows": 7,
            },
        ]
        base["view1"]= view1
        return base


    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        print(user_input)
        def parse_key(key):
            m = re.match(r"^(v\d+)_(.+)_(\d+)$", key)
            if not m:
                return None
            return m.group(1), m.group(2), int(m.group(3))

        def build_rows(data):
            rows = defaultdict(lambda: defaultdict(dict))
            for key, value in data.items():
                parsed = parse_key(key)
                if not parsed:
                    continue
                prefix, field, row_id = parsed
                rows[prefix][row_id][field] = value
            return rows

        def get_anchor_field(fields):
            if "relation" in fields:
                return "relation"
            return sorted(fields)[0] if fields else None

        results = {}
        solution_rows = build_rows(self.task["relational_schema_solution"])
        user_rows = build_rows(user_input)

        all_prefixes = set(solution_rows.keys()) | set(user_rows.keys())

        for prefix in all_prefixes:
            solution_prefix_rows = solution_rows.get(prefix, {})
            user_prefix_rows = user_rows.get(prefix, {})

            if not solution_prefix_rows:
                continue

            all_fields = set()
            for row in solution_prefix_rows.values():
                all_fields.update(row.keys())
            for row in user_prefix_rows.values():
                all_fields.update(row.keys())

            max_solution_row_id = max(solution_prefix_rows.keys(), default=-1)
            row_ids = list(range(max_solution_row_id + 1))

            # v3: fixed row order, no swapping
            if prefix == "v3":
                for row_id in row_ids:
                    user_row = user_prefix_rows.get(row_id, {})
                    solution_row = solution_prefix_rows.get(row_id, {})

                    for field in all_fields:
                        key = f"{prefix}_{field}_{row_id}"
                        given = user_row.get(field, "")
                        expected = solution_row.get(field, "")
                        results[key] = {
                            "correct": normalize_list_string(given) == normalize_list_string(expected),
                            "expected": expected
                        }
                continue

            anchor_field = get_anchor_field(all_fields)

            # anchor -> queue of still-available solution row ids
            solution_anchor_map = defaultdict(list)
            for sol_row_id in sorted(solution_prefix_rows.keys()):
                sol_row = solution_prefix_rows[sol_row_id]
                anchor_value = normalize_list_string(sol_row.get(anchor_field, ""))
                solution_anchor_map[anchor_value].append(sol_row_id)

            matched_solution_row_ids = set()
            unmatched_user_row_ids = []

            # first pass: match by anchor, consuming each solution row at most once
            for user_row_id in row_ids:
                user_row = user_prefix_rows.get(user_row_id, {})
                user_anchor = normalize_list_string(user_row.get(anchor_field, ""))

                available_solution_rows = solution_anchor_map.get(user_anchor, [])

                if available_solution_rows:
                    matched_sol_row_id = available_solution_rows.pop(0)
                    matched_solution_row_ids.add(matched_sol_row_id)

                    expected_row = solution_prefix_rows[matched_sol_row_id]
                    for field in all_fields:
                        key = f"{prefix}_{field}_{user_row_id}"
                        given = user_row.get(field, "")
                        expected = expected_row.get(field, "")
                        results[key] = {
                            "correct": normalize_list_string(given) == normalize_list_string(expected),
                            "expected": expected
                        }
                else:
                    unmatched_user_row_ids.append(user_row_id)

            # second pass: assign remaining solution rows to unmatched user rows
            # so missing / duplicate / invalid rows get the correct expected values
            remaining_solution_row_ids = [
                sol_row_id
                for sol_row_id in sorted(solution_prefix_rows.keys())
                if sol_row_id not in matched_solution_row_ids
            ]

            for user_row_id, sol_row_id in zip(unmatched_user_row_ids, remaining_solution_row_ids):
                user_row = user_prefix_rows.get(user_row_id, {})
                expected_row = solution_prefix_rows[sol_row_id]

                for field in all_fields:
                    key = f"{prefix}_{field}_{user_row_id}"
                    given = user_row.get(field, "")
                    expected = expected_row.get(field, "")
                    results[key] = {
                        "correct": normalize_list_string(given) == normalize_list_string(expected),
                        "expected": expected
                    }

            # if there are more unmatched user rows than remaining solution rows,
            # those rows are just wrong against empty expected values
            for user_row_id in unmatched_user_row_ids[len(remaining_solution_row_ids):]:
                user_row = user_prefix_rows.get(user_row_id, {})
                for field in all_fields:
                    key = f"{prefix}_{field}_{user_row_id}"
                    given = user_row.get(field, "")
                    results[key] = {
                        "correct": normalize_list_string(given) == normalize_list_string(""),
                        "expected": ""
                    }

        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        print(user_input)
        user_input.get("er_schema")


        def split_csv(value):
            value = (value or "").strip()
            if value in ("", "-"):
                return []
            return [x.strip() for x in value.split(",") if x.strip()]


        def parse_expected_relations(solution_dict):
            grouped = {}

            for key, value in solution_dict.items():
                if not key.startswith("v4_"):
                    continue

                m = re.match(r"^v4_(relation|attributes|pk|fk)_(\d+)$", key)
                if not m:
                    continue

                field, idx = m.group(1), int(m.group(2))
                grouped.setdefault(idx, {})[field] = value

            relations = {}

            for idx in sorted(grouped.keys()):
                entry = grouped[idx]
                relation_name = (entry.get("relation") or "").strip()
                if relation_name in ("", "-"):
                    continue

                attributes = split_csv(entry.get("attributes"))
                pk_attrs = set(split_csv(entry.get("pk")))
                fk_attrs = set(split_csv(entry.get("fk")))

                relations[relation_name] = {
                    attr: {
                        "pk": attr in pk_attrs,
                        "fk": attr in fk_attrs,
                    }
                    for attr in attributes
                }

            return relations


        def parse_user_relations(user_schema):
            relations = {}

            if not user_schema:
                return relations

            lines = [line.strip() for line in user_schema.split("\n") if line.strip()]

            for line in lines:
                m = re.match(r"^([A-Za-zÄÖÜäöüß_][A-Za-z0-9_ÄÖÜäöüß-]*)\s*\((.*)\)\s*$", line)
                if not m:
                    continue

                relation_name = m.group(1).strip()
                raw_attr_part = m.group(2).strip()

                attrs = {}
                if raw_attr_part:
                    raw_attributes = [a.strip() for a in raw_attr_part.split(",") if a.strip()]

                    for raw_attr in raw_attributes:
                        is_pk = bool(re.search(r"\(PK\)", raw_attr, flags=re.IGNORECASE))
                        is_fk = bool(re.search(r"\(FK\)", raw_attr, flags=re.IGNORECASE))

                        attr_name = re.sub(r"\((PK|FK)\)", "", raw_attr, flags=re.IGNORECASE).strip()
                        if not attr_name:
                            continue

                        attrs[attr_name] = {
                            "pk": is_pk,
                            "fk": is_fk,
                        }

                relations[relation_name] = attrs

            return relations


        def relation_to_string(relation_name, attributes):
            parts = []
            for attr_name, flags in attributes.items():
                prefix = ""
                if flags["pk"]:
                    prefix += "(PK)"
                if flags["fk"]:
                    prefix += "(FK)"
                parts.append(f"{prefix}{attr_name}")
            return f"{relation_name}({','.join(parts)})"


        def expected_relations_to_string(expected_relations):
            return "\n".join(
                relation_to_string(relation_name, attributes)
                for relation_name, attributes in expected_relations.items()
            )


        def compare_relations(expected_relations, user_relations):
            if set(expected_relations.keys()) != set(user_relations.keys()):
                return False

            for relation_name, expected_attrs in expected_relations.items():
                user_attrs = user_relations.get(relation_name, {})

                if set(expected_attrs.keys()) != set(user_attrs.keys()):
                    return False

                for attr_name, expected_flags in expected_attrs.items():
                    user_flags = user_attrs.get(attr_name)
                    if user_flags != expected_flags:
                        return False

            return True
        solution_dict = self.task["relational_schema_solution"]
        user_schema = user_input.get("er_schema", "")

        expected_relations = parse_expected_relations(solution_dict)
        user_relations = parse_user_relations(user_schema)

        correct = compare_relations(expected_relations, user_relations)
        expected_string = expected_relations_to_string(expected_relations)

        return {
            "er_schema": {
                "correct": correct,
                "expected": expected_string,
            }
        }

    def evaluate(self, user_input):
        if self.mode == "exam":
            return self._evaluate_exam(user_input)
        return self._evaluate_steps(user_input)

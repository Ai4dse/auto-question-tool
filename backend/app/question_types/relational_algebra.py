import random
from pathlib import Path
import numpy as np
import pandas as pd
import json
from app.question_types.relational_algebra_helper import load_schema, execute_relational_algebra

APP_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = APP_DIR / "resources"

DIFFICULTY_SETTINGS = {
    "easy": {"min": 1, "max": 10 },
    "medium": {"min": 10, "max": 100 },
    "hard": {"min": 100, "max": 10000 },
}

class RelationalAlgebra:
    def __init__(self, seed=None, difficulty="easy", exercise_name=None):
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.exercise_name = str(exercise_name) if exercise_name is not None else None
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)

        #Aufgabenauswahl
        exercises_path = RESOURCES_DIR / "relational_algebra_exercises" / "exercises.json"
        with open(exercises_path, "r", encoding="utf-8") as f:
            exercises = json.load(f)["exercises"]
        
        filtered = [ex for ex in exercises if ex["difficulty"] == self.difficulty]
        if not filtered:
            raise ValueError(f"No relational algebra exercises found for difficulty '{self.difficulty}'.")

        if self.exercise_name:
            match = next((ex for ex in filtered if str(ex.get("name")) == self.exercise_name), None)
            if match is None:
                raise ValueError(
                    f"Unknown relational algebra exercise '{self.exercise_name}' for difficulty '{self.difficulty}'."
                )
            self.exercise = match
        else:
            self.exercise = self.rng.choice(filtered)

        schema_path = RESOURCES_DIR / "schemas" / self.exercise["schema"]
        _, dfs = load_schema(str(schema_path))
        self.dfs = dfs
        result_path = RESOURCES_DIR / "relational_algebra_exercises" / self.exercise["result_path"]
        df = pd.read_csv(result_path, index_col=0)
        self.exercise_res = df

    def generate(self):
        base = {}

        schema = [
            {
                "type": "SchemaGrid",
                "tables": [
                    {
                        "title": name,
                        "columns": [c.split(".", 1)[1] for c in df.columns],
                        "rows": df.values.tolist()[:2],  # nur erste 2 Zeilen
                    }
                    for name, df in self.dfs.items()
                ],
            }
        ]
            
        view0 = [
            {
            "type": "Dropdown",
            "title": "Hinweise zur Aufgabe",
            "defaultOpen": False,
            "children": [
                {
                "type": "Text",
                "content": (
                    "### Relationale Algebra: Kurzanleitung\n\n"
                    "#### Überblick\n"
                    "- Zu jeder Aufgabe sehen Sie das Datenbankschema mit Beispiel-Tupeln.\n"
                    "- Geben Sie Ihren Ausdruck im Eingabefeld ein.\n"
                    "- Das System zeigt live die Ergebnisrelation und den Operatorbaum.\n\n"
                    "#### Wichtige Regeln\n"
                    "- Attribute immer voll qualifizieren, z. B. `Vorlesungen.VorlNr` statt nur `VorlNr`.\n"
                    "- Klammern sauber setzen, besonders bei komplexen Bedingungen.\n"
                    "- Logische Operatoren: `AND`, `OR`, `NOT`. Vergleichsoperatoren: `=`, `!=`, `<`, `>`, `<=`, `>=`.\n\n"
                    "#### Schreibweise (wichtig)\n"
                    "- Verwenden Sie die Backslash-Notation: `\\proj`, `\\sel`, `\\join`, `\\diff`, `\\rename`.\n"
                    "- Das Tool wandelt diese automatisch in Symbole um: `π{}`, `σ{}`, `⋈{}`, `−{}`, `ρ{}`.\n"
                    "- Sie müssen Sonderzeichen nicht manuell eingeben.\n\n"
                    "#### Unterstützte Operatoren\n"
                    "- `\\join`\n"
                    "- `\\diff`\n"
                    "- `\\proj`\n"
                    "- `\\sel`\n"
                    "- `\\rename`\n\n"
                    "#### Syntax und Beispiele\n"
                    "**JOIN**\n"
                    "- Syntax: `Relation1 \\join{Prädikat}(Relation2)`\n"
                    "- Beispiel: `hoeren \\join{hoeren.MatrNr = Studierende.MatrNr}(Studierende)`\n\n"
                    "**DIFFERENCE**\n"
                    "- Syntax: `Relation1 \\diff{}(Relation2)`\n"
                    "- Beispiel: `hoeren \\diff{}(hoeren)`\n"
                    "- Hinweis: Beide Relationen müssen dieselben Attributnamen besitzen.\n\n"
                    "**PROJECTION**\n"
                    "- Syntax: `\\proj{Attribut1, Attribut2, ...}(Relation)`\n"
                    "- Beispiel: `\\proj{Vorlesungen.VorlNr, Vorlesungen.Titel}(Vorlesungen)`\n"
                    "- Wirkung: Wählt Attribute aus und entfernt Duplikate.\n\n"
                    "**SELECTION**\n"
                    "- Syntax: `\\sel{Bedingung}(Relation)`\n"
                    "- Beispiel: `\\sel{(Studierende.MatrNr != 24002) AND (Studierende.Semester > 3)}(Studierende)`\n\n"
                    "**RENAME**\n"
                    "- Relation umbenennen: `\\rename{NeuerName}(Relation)`\n"
                    "- Attribut umbenennen: `\\rename{AltesAttribut, NeuesAttribut}(Relation)`\n"
                    "- Beispiel: `\\rename{Vorlesungen.VorlNr, Vorlesungen.Vorlesungsnummer}(Vorlesungen)`\n"
                    "- Hinweis: Das Tool erkennt automatisch, ob eine Relation oder ein Attribut umbenannt wird.\n\n"
                    "#### Typische Fehler\n"
                    "- Fehlende oder falsch gesetzte Klammern\n"
                    "- Nicht existierende Relationen- oder Attributnamen\n"
                    "- Attribute ohne Tabellenpräfix\n"
                    "- Beispiele 1:1 kopieren und dann bearbeiten: führt zu Klammerfehlern nach der Symbol-Umwandlung (z. B. `\\proj{...}` wird zu `π{}{...}` )\n"
                    "- Empfehlung: Beispiele als Orientierung nutzen und den Ausdruck selbst neu tippen.\n"
                )
                },
            ]
            },
            {
            "type": "Dropdown",
            "title": "Datenbankschema",
            "defaultOpen": False,
            "children": schema
            }
        ]
        
        base["view1"] = view0 + [
            {
                "type": "Text",
                "content": '### Relationale Algebra\n\nAufgabe: ' + self.exercise['text'],
            },
            {
            "type": "ExpressionInput",
            "id": "0",
            "label": "Antwort in Relationaler Algebra:",
            "rows": 5
            },
            {
                "type": "ReactiveTable",
                "id": "relalg_preview",
                "label": "Live Ergebnisse",
                "listenTo": "0",
            },
            { 
                "type": "ReactiveTree", 
                "label": "Ausführungsbaum", 
                "listenTo": "0" },
        ]

        base["lastView"] = [
            {
            "type": "ExpressionInput",
            "id": "0",
            "label": "Musterlösung",
            "rows": 5,
            "default": self.exercise['answer']
            }
        ]

        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        results = {}
        statement = user_input.get('0')
        try:
            res_df, execution_string= execute_relational_algebra(self.dfs, statement)
        except:
            results['0'] = {"correct": False, "expected": self.exercise['answer']}
            return results

        def df_equal_unordered(a, b):
            if set(a.columns) != set(b.columns):
                return False
            cols = sorted(a.columns)
            a2 = a[cols].sort_values(by=cols).reset_index(drop=True)
            b2 = b[cols].sort_values(by=cols).reset_index(drop=True)
            return a2.equals(b2)
    
        is_identical = df_equal_unordered(res_df, self.exercise_res)

        results['0'] = {"correct": is_identical, "expected": self.exercise['answer']}
        return results

    def preview(self, statement: str):
        statement = (statement or "").strip()
        if not statement:
            return {
                "columns": [],
                "rows": [],
                "tree": None,
                "error": None
            }

        try:
            res_df, tree = execute_relational_algebra(self.dfs, statement)

            preview_rows = res_df.head(10).values.tolist() if res_df is not None else []

            return {
                "columns": list(res_df.columns) if res_df is not None else [],
                "rows": preview_rows,
                "tree": tree,
                "error": None
            }

        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "tree": None,
                "error": str(e)
            }

import random
import numpy as np
import pandas as pd
from app.question_types.relational_algebra_helper import load_schema, execute_relational_algebra

DIFFICULTY_SETTINGS = {
    "easy": {"min": 1, "max": 10 },
    "medium": {"min": 10, "max": 100 },
    "hard": {"min": 100, "max": 10000 },
}

class RelationalAlgebra:
    def __init__(self, seed=None, difficulty="easy"):
        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        _, dfs = load_schema('./app/resources/schemas/university')
        
        self.dfs = dfs
        print('initialized')
        self.live_df = pd.DataFrame()

        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        np.random.seed(self.seed)

    def generate(self):
        base = {}

        view0 = [
            {
            "type": "Text",
            "content": "Relationale Algebra – Kurzanleitung zur Nutzung der Engine\n==========================================================\n1. Allgemeines\n--------------\nZu jeder Aufgabe wird das vollständige Datenbankschema einschließlich Beispiel-Tupeln angezeigt.\nIm Eingabefeld können Sie Ausdrücke der Relationalen Algebra eingeben.\nDie folgenden Operationen stehen zur Verfügung:\n- JOIN\n- DIFFERENCE\n- PROJECTION\n- RENAME\n- SELECTION\n\nAlle Operationen werden über Backslash-Notation angegeben, z.B. \\join, \\proj usw.\nDie Engine ersetzt diese automatisch durch die entsprechenden mathematischen Symbole.\n\n2. Allgemeine Hinweise\n----------------------\n• Attribute müssen stets vollständig qualifiziert sein: z.B. Vorlesungen.VorlNr (nicht nur \"VorlNr\").\n• Klammern sind besonders bei komplexen logischen Ausdrücken wichtig: (A != B) AND ((C > D) OR (E = F)).\n• Falls keine Ausgabe erscheint, liegt vermutlich ein Syntaxfehler vor.\n\nZu jeder Anfrage werden ausgegeben:\n1. Die resultierende Tabelle\n2. Der Operatorbaum\n\n3. JOIN\n-------\nSyntax:\n  Relation1 \\join{Praedikat}(Relation2)\n\nBeispiel:\n  hoeren \\join{hoeren.MatrNr = Studierende.MatrNr}(Studierende)\n\nBeschreibung:\n  Führt einen Join basierend auf dem angegebenen Prädikat aus.\n\n4. DIFFERENCE\n-------------\nSyntax:\n  Relation1 \\diff{}(Relation2)\n\nBeispiel:\n  hoeren \\diff{} hoeren\n\nHinweis:\n  Beide Relationen müssen identische Attributnamen besitzen.\n\n5. PROJECTION\n--------------\nSyntax:\n  \\proj{Attribut1, Attribut2, ...}(Relation)\n\nBeispiel:\n  \\proj{Vorlesungen.VorlNr, Vorlesungen.Titel}(Vorlesungen)\n\nBeschreibung:\n  Wählt bestimmte Attribute aus und entfernt automatisch Duplikate.\n\n6. SELECTION\n------------\nSyntax:\n  \\sel{Bedingung}(Relation)\n\nBeispiel:\n  \\sel{(Studierende.Alter != 0) AND (Studierende.Semester > 3)}(Studierende)\n\nUnterstützte Operatoren:\n  =, !=, <, >, <=, >=, AND, OR, NOT\n\nWichtig:\n  Logische Ausdrücke müssen korrekt geklammert sein:\n  \\sel{(A != B) AND ((C > 3) OR NOT(A = 0))}(R)\n\n7. RENAME\n---------\nVariante 1: Rename der gesamten Relation:\n  \\rename{NeuerName}AlteRelation\nBeispiel:\n  \\rename{V1}Vorlesungen\nVariante 2: Rename einzelner Attribute:\n  \\rename{Alter_Name, Neuer_Name}(Relation)\nBeispiel:\n  \\rename{Vorlesungen.VorlNr, Vorlesungen.Nummer}(Vorlesungen)\n\n8. Ausgabe\n----------\nNach der erfolgreichen Auswertung werden angezeigt:\n• Die Ergebnisrelation (als Tabelle)\n• Der Operatorbaum\nFalls nichts ausgegeben wird, liegt meist ein Syntaxfehler vor. \n\nDatenbankschema:"
            }
        ]

        for name, df in self.dfs.items():
            view0.append({
                "type": "Table",
                "title": name,
                "columns": list(df.columns),
                "rows": df.values.tolist()[:2],
        })
        
        base["view1"] = view0 + [
            {
                "type": "Text",
                "content": "Enter a relational algebra expression HIER KOMMT DIE AUFGABE HIN:",
            },
            {
                "type": "TextInput",
                "id": "0",
                "label": "Antwort in Relationaler Algebra",
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
                "type": "Text",
                "content": f"Bye",    
            },
        ]

        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        results = {}
        statement = user_input.get('0')
        res_df, execution_string= execute_relational_algebra(self.dfs, statement)

        self.live_df = res_df
        print(self.live_df)

        results['0'] = {"correct": 1 == 1, "expected": 1}
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
            print(f'Statement: {statement}')
            res_df, tree = execute_relational_algebra(self.dfs, statement)
            print(tree)
            # Assuming you change execute_relational_algebra to return 3 things

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
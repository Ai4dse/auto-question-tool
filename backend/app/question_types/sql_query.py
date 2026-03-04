import csv
import json
import os
import random

from app.question_types.sql_query_helper import (
    execute_for_compare,
    execute_read_only_query,
)


EXERCISES_PATH = "./app/resources/sql/exercises.json"
EXERCISE_RESULTS_DIR = "./app/resources/sql"


class SqlQueryQuestion:
    def __init__(self, seed=None, difficulty="easy"):
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.difficulty = str(difficulty).lower()
        random.seed(self.seed)

        with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
            exercises = json.load(f).get("exercises", [])

        filtered = [e for e in exercises if str(e.get("difficulty", "easy")).lower() == self.difficulty]

        self.exercise = random.choice(filtered)
        self.expected_column_count, self.expected_rows = self._load_expected_result(self.exercise["result_path"])

    def _load_expected_result(self, result_path: str):
        csv_path = os.path.join(EXERCISE_RESULTS_DIR, result_path)
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return 0, []

        header = rows[0]
        data_rows = [tuple(row) for row in rows[1:]]
        data_rows.sort()
        return len(header), data_rows

    def generate(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Verwenden Sie die bereitgestellte SQL-Datenbank und formulieren Sie eine passende Abfrage. In [ ] ist die Anzahl der Lösungstupel angegeben.\n"
                    ),
                },
                {
                    "type": "PdfViewer",
                    "title": "Relationen-Schema (PDF)",
                    "src": "/resources/sql/mondial-abh.pdf",
                    "height": 700,
                },
                {
                    "type": "Text",
                    "content": f"Aufgabe: {self.exercise['text']}",
                },
                {
                    "type": "TextInput",
                    "id": "0",
                    "label": "Deine SQL-Abfrage",
                    "rows": 6,
                },
                {
                    "type": "ReactiveTable",
                    "id": "sql_preview",
                    "label": "Live-Ergebnis",
                    "listenTo": "0",
                }
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": (
                        f"Musterlösung: \n\n {self.exercise["answer"]}"
                    ),
                }
            ],
        }

    def evaluate(self, user_input):
        statement = (user_input or {}).get("0", "")
        try:
            user_cols, user_rows = execute_for_compare(statement)
            normalized_user_rows = [
                tuple("" if value is None else str(value) for value in row)
                for row in user_rows
            ]
            normalized_user_rows.sort()

            correct = (
                len(user_cols) == self.expected_column_count
                and normalized_user_rows == self.expected_rows
            )
        except Exception:
            correct = False

        return {
            "0": {
                "correct": correct,
                "expected": self.exercise["answer"],
            }
        }

    def preview(self, statement: str):
        statement = (statement or "").strip()
        if not statement:
            return {
                "columns": [],
                "rows": [],
                "error": None,
            }

        try:
            result = execute_read_only_query(statement)
            return {
                "columns": result["columns"],
                "rows": result["rows"],
                "total_rows": result.get("total_rows", len(result["rows"])),
                "error": None,
            }
        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "total_rows": 0,
                "error": str(e),
            }

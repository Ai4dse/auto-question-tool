import json
import random
from pathlib import Path


EXERCISES_PATH = Path(__file__).resolve().parents[1] / "resources" / "regex" / "exercises.json"


class RegexQuestion:
    def __init__(self, seed=None, difficulty="easy", exercise_name=None):
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.difficulty = str(difficulty).lower()
        self.exercise_name = str(exercise_name) if exercise_name is not None else None
        self.rng = random.Random(self.seed)

        with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
            exercises = json.load(f).get("exercises", [])

        filtered = [
            e
            for e in exercises
            if str(e.get("difficulty", "easy")).lower() == self.difficulty
        ]

        if not filtered:
            raise ValueError(f"No regex exercises found for difficulty '{self.difficulty}'.")

        if self.exercise_name:
            match = next(
                (e for e in filtered if str(e.get("name")) == self.exercise_name),
                None,
            )
            if match is None:
                raise ValueError(
                    f"Unknown regex exercise '{self.exercise_name}' for difficulty '{self.difficulty}'."
                )
            self.exercise = match
        else:
            self.exercise = self.rng.choice(filtered)

    def _format_solution(self):
        solution = self.exercise.get("solution", "")
        if isinstance(solution, dict):
            find_value = str(solution.get("find", ""))
            replace_value = str(solution.get("replace", ""))
            return (
                "FIND:\n"
                f"```regex\n{find_value}\n```\n\n"
                "REPLACE:\n"
                f"```text\n{replace_value}\n```"
            )
        return f"```regex\n{str(solution)}\n```"

    def generate(self):
        link = str(self.exercise.get("link") or "").strip()
        link_text = f"[Regex101 Link]({link})"

        base_view = [
            {
                "type": "Text",
                "content": (
                    "Diese Aufgabe wird hier erklärt, aber auf Regex101 gelöst. "
                    "Falls es beim Lösen Probleme gibt, können Sie auf diese Seite zurückkommen "
                    "und mit `Abgeben` die Musterlösung ansehen. \n"
                    "Hinweis: Mehrere Lösungen sind möglich. Alle regulären Ausdrücke, "
                    "die das Gefragte korrekt markieren oder ersetzen, sind richtig. "
                    "Um 'Replace' in Regex101 darzustellen, klicken Sie auf der linken Seite unter 'Function' auf 'Substitution' und geben Sie dort Ihren Replace-Ausdruck ein.\n\n"
                ),
            },
            {
                "type": "Text",
                "content": (
                    f'- {self.exercise["question"]}\n\n'
                    f'```text\n{self.exercise["content"]}\n```'
                ),
            },
            {
                "type": "Text",
                "content": link_text,
            },
        ]

        return {
            "view1": base_view,
            "lastView": [
                {
                    "type": "Text",
                    "content": f"Musterlösung:\n\n{self._format_solution()}",
                }
            ],
        }

    def evaluate(self, user_input):
        return {}

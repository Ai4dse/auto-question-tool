import json
import random


EXERCISES_PATH = "./app/resources/xpath_xquery/exercises.json"


class XPathXQueryQuestion:
    def __init__(self, seed=None, difficulty="easy", mode="xpath", exercise_name=None):
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.difficulty = str(difficulty).lower()
        self.mode = str(mode).lower()
        self.exercise_name = str(exercise_name) if exercise_name is not None else None
        self.rng = random.Random(self.seed)

        if self.mode not in {"xpath", "xquery"}:
            raise ValueError("Mode must be either 'xpath' or 'xquery'.")

        with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
            exercises = json.load(f).get("exercises", [])

        filtered = [
            e
            for e in exercises
            if str(e.get("difficulty", "easy")).lower() == self.difficulty
            and str(e.get("mode", "xpath")).lower() == self.mode
        ]

        if not filtered:
            raise ValueError(
                f"No {self.mode} exercises found for difficulty '{self.difficulty}'."
            )

        if self.exercise_name:
            match = next(
                (e for e in filtered if str(e.get("name")) == self.exercise_name),
                None,
            )
            if match is None:
                raise ValueError(
                    f"Unknown {self.mode} exercise '{self.exercise_name}' for difficulty '{self.difficulty}'."
                )
            self.exercise = match
        else:
            self.exercise = self.rng.choice(filtered)

    def _format_solution(self):
        solution = str(self.exercise.get("solution", ""))
        code_lang = "xpath" if self.mode == "xpath" else "xquery"
        return f"```{code_lang}\n{solution}\n```"

    def generate(self):
        link = str(self.exercise.get("link") or "").strip()
        link_label = "XPath Tool" if self.mode == "xpath" else "XQuery Tool"

        base_view = [
            {
                "type": "Text",
                "content": (
                    "Diese Aufgabe wird hier erklärt, aber auf einer externen Seite gelöst. "
                    "Falls es beim Lösen Probleme gibt, können Sie auf diese Seite zurückkommen "
                    "und mit `Abgeben` die Musterlösung ansehen.\n"
                    "Hinweis: Mehrere Lösungen können korrekt sein, solange die Abfrage "
                    "das gewünschte Ergebnis liefert."
                ),
            },
            {
                "type": "Text",
                "content": (
                    f'- {self.exercise["question"]}\n\n'
                    f'```xml\n{self.exercise["content"]}\n```'
                ),
            },
            {
                "type": "Text",
                "content": f"[{link_label}]({link})",
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

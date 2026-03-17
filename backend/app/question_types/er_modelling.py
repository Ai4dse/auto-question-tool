import random
import re
from pathlib import Path
import json

from app.common import *

DIFFICULTY_SETTINGS = {
    "easy": {},
    "medium": {},
    "hard": {},
}

path = Path(__file__).resolve().parent.parent / "resources" / "er_diagrams.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

class ERModelling:

    def __init__(self, seed=None, difficulty="easy", mode="steps", card_type="min_max", **kwargs):
        print(kwargs)

        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = mode.lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        random.seed(self.seed)

        self.card_type = card_type
        self.tasks = []

        self.tasks = [task for task in raw if task["difficulty"] == self.difficulty]
        self.task = random.choice(self.tasks)

    def _generate_steps_layout(self):
        base = {}
        base["view1"] = [
                {
                    "type": "Text",
                    "content": f"{self.task["descriptive_text"]}",
                },
                {
                    "type": "ER_Diagram",
                },
                {
                    "type": "ER_Diagram_Builder",
                    "id": "free_er_builder",
                    "title": "Build your own ER diagram",
                    "card_type": "min_max",   # or "cardinality"
                    "height": 750,
                },
        ]
        return base

    def _generate_exam_layout(self):
        base = {}
        return base


    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        print(user_input)
        results = {}
        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        results = {}
        return results

    def evaluate(self, user_input):
        if self.mode == "exam":
            return self._evaluate_exam(user_input)
        return self._evaluate_steps(user_input)

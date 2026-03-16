import random
import re

from app.common import *

DIFFICULTY_SETTINGS = {
    "easy": {"num_points": 10, "dimensions": 1},
    "medium": {"num_points": 13, "dimensions": 1},
    "hard": {"num_points": 10, "dimensions": 2},
}

class DummyQ:

    def __init__(self, seed=None, difficulty="easy", mode="steps", **kwargs):
        print(kwargs)
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = mode.lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        random.seed(self.seed)

        self._dummy_solver()

    def _dummy_solver(self):
        pass

    def _generate_steps_layout(self):
        base = {}
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

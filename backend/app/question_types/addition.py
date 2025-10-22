import random

class AdditionQuestion:
    def __init__(self, min=1, max=10):
        self.min = min
        self.max = max

    def generate(self):
        a = random.randint(self.min, self.max)
        b = random.randint(self.min, self.max)
        return {
            "type": "addition",
            "question": f"What is {a} + {b}?",
            "answer": a + b
        }

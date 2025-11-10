import random
import numpy as np

DIFFICULTY_SETTINGS = {
    "easy": {"min": 1, "max": 10 },
    "medium": {"min": 10, "max": 100 },
    "hard": {"min": 100, "max": 10000 },
}


class AdditionQuestion:
    def __init__(self, seed=None, difficulty="easy"):
        
        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])
        
        self.min = config["min"]
        self.max = config["max"]

        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        np.random.seed(self.seed)
        self.addition_data = []
        self.a = random.randint(self.min, self.max)
        self.b = random.randint(self.min, self.max)
        self._run_addition()
        
    def _run_addition(self):
        sumx = self.a+self.b
        self.addition_data.append({"sumx": sumx})

    def generate(self):
        base = {}

        view0 = [
            {
                "type": "Text",
                "content": f"Solve this simple Addition with values from {self.min} up to {self.max}",    
            },
        ]
        
        base["view1"] = [
            {
                "type": "Text",
                "content": f"What is {self.a} + {self.b}?",    
            },
            {
              "type": "TextInput",
              "id": "5",  
            },
        ]

        base["lastView"] = [
            {
                "type": "Text",
                "content": f"Bye",    
            },
        ]

        base["view1"] = view0 + base["view1"]
        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        results = {}
        id="5"
        results[id] = {"correct": user_input.get(id) == str(self.addition_data[0]["sumx"]),
                    "expected": str(self.addition_data[0]["sumx"])}
        return results


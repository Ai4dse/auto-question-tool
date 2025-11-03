# app/question_types/dbscan.py

import random
import numpy as np
from sklearn.cluster import KMeans
from app.ui_layout import Point
from app.layouts.kmeans_layout import KMeansLayout
import math


DIFFICULTY_SETTINGS = {
    "easy": {"num_points": 5},
    "medium": {"num_points": 6},
    "hard": {"num_points": 7},
}


class DBSCANQuestion:

    def __init__(self, seed=None, difficulty="easy"):
        
        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.num_points = config["num_points"]

        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        np.random.seed(self.seed)

        self.points = [
            Point(f"P{i}", random.randint(0, 10), random.randint(0, 10))
            for i in range(self.num_points)
        ]
        self._run_dbscan()

    # ---------------------------------------------------------------------
    # Internal DBSCAN computation
    # ---------------------------------------------------------------------
    def _run_dbscan(self):
        pass

    # ---------------------------------------------------------------------
    # Layout builder
    # ---------------------------------------------------------------------
    def generate(self):
        base = {}
        points = self.points

        view0 = [
            {
                "type": "Text",
                "content": f"",    
            },
            {
                "type": "Table",
                "title": "Points",
                "columns": ["Label", "X", "Y"],
                "rows": [[p.label, p.x, p.y] for p in points],
            },
        ]
        base["view1"] = [
            {
                "type": "Text",
                "content": f"not implemented yet",    
            },
        ]

        base["lastView"] = [
            {
                "type": "CoordinatePlot",
                "points_blue": [[p.label, p.x, p.y] for p in points],
            },
            {
                "type": "Text",
                "content": f"",    
            },
        ]

        base["view1"] = view0 + base["view1"]
        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        return None

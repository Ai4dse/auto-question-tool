# app/question_types/agnes.py

import random
import numpy as np
from app.ui_layout import Point

DIFFICULTY_SETTINGS = {
    "easy": {"num_points": 5},
    "medium": {"num_points": 6},
    "hard": {"num_points": 8},
}


class AGNESQuestion:

    def __init__(self, seed=None, difficulty="easy", linkage_method = "single", **kwargs):

        print(kwargs)

        self.linkage = linkage_method

        EUCLIDEAN = "euclidean"
        MANHATTAN = "manhattan"
        self.dist = MANHATTAN

        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.num_points = config["num_points"]

        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        np.random.seed(self.seed)

        coords = set()
        while len(coords) < self.num_points:
            coords.add((random.randint(0, 10), random.randint(0, 10)))
        self.points = [Point(f"P{i}", x, y) for i, (x, y) in enumerate(coords)]

        self._run_agnes()

    def _distance_matrix(self, X):

        if self.dist == "euclidean":
            return np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))

        elif self.dist == "manhattan":
            return np.abs(X[:, None, :] - X[None, :, :]).sum(axis=2)

        else:
            raise ValueError(f"Unknown distance metric: {self.dist}")

    # ---------------------------------------------------------------------
    # Internal DBSCAN computation
    # ---------------------------------------------------------------------
    def _run_agnes(self):

        X = np.array([(p.x, p.y) for p in self.points], dtype=float)
        D = self._distance_matrix(X)
        self.cluster = [0] * self.num_points

    # ---------------------------------------------------------------------
    # Layout builder
    # ---------------------------------------------------------------------
    def generate(self):
        base = {}
        points = self.points
        view0 = [
            {
                "type": "Text",
                "content": f"{self.linkage} In the following {self.num_points} are given and ploted. ",
            },
            {
                "type": "Table",
                "title": "Points",
                "columns": ["Label", "X", "Y"],
                "rows": [[p.label, p.x, p.y] for p in points],
            },
            {
                "type": "CoordinatePlot",
                "points_blue": [[p.label, p.x, p.y] for p in points],
            },
        ]
        base["view1"] = [

        ]
        points_black = [
            [f"{p.label}", p.x, p.y]
            for i, p in enumerate(points)
            if self.cluster[i] == 0
        ]
        points_blue = [
            [
                f"{p.label}",
                p.x,
                p.y,
            ]
            for i, p in enumerate(points)
            if self.cluster[i] == 1
        ]

        points_green = [
            [
                f"{p.label}",
                p.x,
                p.y,
            ]
            for i, p in enumerate(points)
            if self.cluster[i] >= 2
        ]

        base["lastView"] = [
            {
                "type": "var_coordinates_plot",
                "title": "DBSCAN result",
                "series": [
                    {"name": "cluster 2", "color": "green", "points": points_green, "symbol": "triangle-up", "size": 8},
                    {"name": "cluster 1", "color": "blue",  "points": points_blue,  "symbol": "circle",      "size": 8},
                    {"name": "noise",     "color": "black", "points": points_black, "symbol": "x",           "size": 8},
                ]
            },
        ]

        base["view1"] = view0 + base["view1"]
        print(base)
        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        print(user_input)
        results = {}
        return results

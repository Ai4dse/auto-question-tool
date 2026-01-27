# app/question_types/dbscan.py

import random
import numpy as np
from sklearn.cluster import KMeans
from app.ui_layout import Point

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
        self.min_pts = random.randint(2, 4)

        self._run_dbscan()


    def average_kth_neighbor_distance(points, k):
        X = np.array([(p.x, p.y) for p in points], dtype=float)

        n = len(X)
        if n <= k:
            raise ValueError("k must be smaller than number of points")

        # Pairwise distances
        D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))
        np.fill_diagonal(D, np.inf)

        # k-th nearest neighbor distance for each point
        kth_distances = np.partition(D, k-1, axis=1)[:, k-1]

        # Average
        return float(kth_distances.mean())
    
    # ---------------------------------------------------------------------
    # Internal DBSCAN computation
    # ---------------------------------------------------------------------
    def _run_dbscan(self):
        k = random.randint(2, self.num_points)
        self.dist = average_kth_neighbor_distance(self.points,k)
        X = np.array([(p.x, p.y) for p in self.points], dtype=float)
        D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))

        # Neighborhood matrix: within dist
        within = (D <= self.dist)

        # Count neighbors including self
        neighbor_counts = within.sum(axis=1)

        # Core points
        core_mask = neighbor_counts >= self.min_pts

        # Border points: not core, but in eps-neighborhood of some core
        # For each point i, check if there exists a core point j with within[i, j] == True
        border_mask = (~core_mask) & (within[:, core_mask].any(axis=1))

        # Noise: neither
        noise_mask = ~(core_mask | border_mask)

        print(core_mask, border_mask, noise_mask)
        
        

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
            {
                "type": "CoordinatePlot",
                "points_blue": [[p.label, p.x, p.y] for p in points],
            },
        ]
        base["view1"] = [
            {
                "type": "Text",
                "content": f"not implemented yet",
            },
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

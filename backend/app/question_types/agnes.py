# app/question_types/agnes.py

from app.common import *
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

    def build_dendrogram_merges(self):

        n = self.D.shape[0]
        assert self.D.shape == (n, n)

        clusters = {f"L:{i}": [i] for i in range(n)}
        self.merges = []
        self.merge_dists = []
        next_merge_idx = 0

        def cluster_distance(a_key, b_key):
            A = clusters[a_key]
            B = clusters[b_key]
            # all pairwise distances between members
            block = self.D[np.ix_(A, B)]
            if self.linkage == "single":
                return float(np.min(block))
            elif self.linkage == "complete":
                return float(np.max(block))
            elif self.linkage == "average":
                return float(np.mean(block))

        while len(clusters) > 1:
            keys = sorted(clusters.keys())  # for deterministic tie-breaking
            best = None  # (dist, a_key, b_key)

            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    a, b = keys[i], keys[j]
                    dist = cluster_distance(a, b)
                    cand = (dist, a, b)
                    if best is None or cand < best:   # tuple ordering = distance, then name tie-break
                        best = cand

            dist, a, b = best
            # record merge exactly in the format you want
            self.merges.append(f"{a}|{b}")
            self.merge_dists.append(dist)

            # create new merged cluster
            new_key = f"M:{next_merge_idx}"
            next_merge_idx += 1
            clusters[new_key] = clusters[a] + clusters[b]
            del clusters[a]
            del clusters[b]

        print(self.merges)
        print(self.merge_dists)
    # ---------------------------------------------------------------------
    # Internal DBSCAN computation
    # ---------------------------------------------------------------------
    def _run_agnes(self):

        X = np.array([(p.x, p.y) for p in self.points], dtype=float)
        self.D = self._distance_matrix(X)
        self.cluster = [0] * self.num_points
        self.build_dendrogram_merges()

    # ---------------------------------------------------------------------
    # Layout builder
    # ---------------------------------------------------------------------
    def generate(self):
        base = {}
        points = self.points
        cells = []
        cells.append([{"type": "text", "value": ""}]+[{"type": "text", "value": f"P{i}"} for i in range(self.num_points)])
        for i in range(self.num_points):
            row = (
                [{"type": "text", "value": f"P{i}"}] +
                [{"type": "TextInput", "id": f"D1_{i}_{j}"} for j in range(self.num_points)]
            )
            cells.append(row)


        view0 = [
            {
                "type": "Text",
                "content": f"In this exercise you need to solf the clustering task using AGNES. Use the {self.linkage} linkage method and {self.dist} distance as distance measure. In the following {self.num_points} Points are given and ploted.",
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
                "content": "Lets calculate the distance matrix First",
                },
                {
                "type": "layout_table",
                "title":"Distance Matrix",
                "rows": self.num_points+1,
                "cols": self.num_points+1,
                "cells": cells
                }
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

        base["view2"] = [
                {
                "type": "Text",
                "content": f"Lets Dendogram for {self.linkage} linkage next.",
                },
                {
                    "type": "DendrogramBuilder",
                    "id": "dendo",
                    "title": "Build the dendrogram",
                    "points": [f"P{i}" for i in range(self.num_points)]
                }

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
        results = {}
        #distance matrix eval
        for i in range(self.num_points):
            for j in range(self.num_points):
                id = f"D1_{i}_{j}"
                results[id] = { "correct": user_input.get(id) == str(self.D[i][j]),
                                "expected": f"{self.D[i][j]}"}
                continue
        #dendogram eval
        for i in range(len(self.merges)):
            id_merge = f"dendo:merge:{i}:children"
            id_dist = f"dendo:merge_dist:{i}"
            results[id_merge] = { "correct": user_input.get(id_merge) == str(normalize_number(self.merges[i])),
                                "expected": f"{self.merges[i]}"}
            results[id_dist] = { "correct": user_input.get(id_dist) == str(normalize_number(self.merge_dists[i])) and user_input.get(id_merge) == str(normalize_number(self.merges[i])),
                                "expected": f"{self.merge_dists[i]}, {str(self.merges[i])}"}
        print(user_input)
        print(results)
        return results

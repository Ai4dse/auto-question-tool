# app/question_types/dbscan.py

import random
import numpy as np
from sklearn.cluster import KMeans
from app.ui_layout import Point

DIFFICULTY_SETTINGS = {
    "easy": {"num_points": 5},
    "medium": {"num_points": 6},
    "hard": {"num_points": 8},
}


class DBSCANQuestion:

    def __init__(self, seed=None, difficulty="easy"):

        EUCLIDEAN = "euclidean"
        MANHATTAN = "manhattan"
        self.dist = MANHATTAN

        self.noise_label = "NP"
        self.border_label = "BP"
        self.core_label = "CP"

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

        self.min_pts = random.randint(2, int(self.num_points/2))
        self.average_kth_neighbor_distance()
        self._run_dbscan()

    def average_kth_neighbor_distance(self):
        k = random.randint(2, self.num_points)
        k=2
        points = self.points
        X = np.array([(p.x, p.y) for p in points], dtype=float)

        n = len(X)
        if n <= k:
            raise ValueError("k must be smaller than number of points")

        # Pairwise distances
        D = self._distance_matrix(X)
        np.fill_diagonal(D, np.inf)

        # k-th nearest neighbor distance for each point
        kth_distances = np.partition(D, k-1, axis=1)[:, k-1]

        # Average
        self.cluster_range = int(kth_distances.mean())

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
    def _run_dbscan(self):

        X = np.array([(p.x, p.y) for p in self.points], dtype=float)
        D = self._distance_matrix(X)

        within = (D <= self.cluster_range)

        # Count neighbors including self
        neighbor_counts = within.sum(axis=1)

        # Core points
        self.core_mask = neighbor_counts >= self.min_pts

        # For each point i, check if there exists a core point j with within[i, j] == True
        self.border_mask = (~self.core_mask) & (within[:, self.core_mask].any(axis=1))

        self.noise_mask = ~(self.core_mask | self.border_mask)
        visited = [False]*self.num_points
        self.cluster = [0]*self.num_points
        idx = 0
        for idx in range(len(self.core_mask)):
            cluster_label = 0

            if (not self.core_mask[idx]) or visited[idx]:
                print("check")
                continue
            visited[idx] = True
            neigh_mask = D[idx] <= self.cluster_range
            neigh_idx  = np.flatnonzero(neigh_mask)
            print(neigh_idx)
            for k in neigh_idx:
                if (self.core_mask[k] == True) and (self.cluster[k] != 0):
                    cluster_label =  self.cluster[k]
            if cluster_label == 0:
                cluster_label = max(self.cluster)+1
                self.cluster[idx] = cluster_label
            for k in neigh_idx:
                 self.cluster[k] = cluster_label

            idx += 1
        print(self.cluster)


    # ---------------------------------------------------------------------
    # Layout builder
    # ---------------------------------------------------------------------
    def generate(self):
        base = {}
        points = self.points
        table_header = []
        dropdown_body = []
        for i in range(0,self.num_points):
            table_header.append({ "type": "text", "value": f"P{i}" })
            dropdown_body.append({
                "type": "DropdownInput",
                "id": i,
                "placeholder": "Please select…",
                "options": [self.core_label,self.border_label,self.noise_label]
                })
        view0 = [
            {
                "type": "Text",
                "content": f"In the following {self.num_points} are given and ploted. Use the DBSCAN algorithm do find cluster and Noise Points. To execute the DBSCAN algorithm use {self.dist}distance as distance measure. Furthermore the parameters min_pts = {self.min_pts}\n and e = {self.cluster_range} are given",
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
            "type": "layout_table",
            "title": f"Select the type for each point. ({self.core_label}=Core Point, {self.border_label}=Border Point, {self.noise_label}=Noise Point)",
            "rows": 2,
            "cols": self.num_points,
            "cells": [
                table_header,
                dropdown_body
            ]
            }
        ]
        points_black = [
            [f"{p.label}({self.noise_label})", p.x, p.y]
            for i, p in enumerate(points)
            if self.cluster[i] == 0
        ]
        points_blue = [
            [
                f"{p.label}({self.core_label})" if self.core_mask[i] else f"{p.label}({self.border_label})",
                p.x,
                p.y,
            ]
            for i, p in enumerate(points)
            if self.cluster[i] == 1
        ]

        points_green = [
            [
                f"{p.label}({self.core_label})" if self.core_mask[i] else f"{p.label}({self.border_label})",
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
        for id in range(0,self.num_points):
            value = False
            match user_input.get(str(id)):
                case self.core_label:
                    value = self.core_mask[id]
                case self.border_label:
                    value = self.border_mask[id]
                case self.noise_label:
                    value = self.noise_mask[id]
            if self.core_mask[id]: expected = self.core_label
            elif self.border_mask[id]: expected = self.border_label
            elif self.noise_mask[id]: expected = self.noise_label
            else:
                print(f"invalid input on field{id}: {user_input.get(id)}")
                expected = "Undefined"
            results[id] = {"correct": bool(value),
                        "expected": expected}
        print(results)
        return results

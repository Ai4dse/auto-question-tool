# app/question_types/kmeans.py

import random
import numpy as np
from sklearn.cluster import KMeans
from app.ui_layout import Point
from app.layouts.kmeans_layout import KMeansLayout
import math


DIFFICULTY_SETTINGS = {
    "easy": {"num_points": 5, "num_centroids": 2, "max_iter": 2},
    "medium": {"num_points": 6, "num_centroids": 3, "max_iter": 3},
    "hard": {"num_points": 7, "num_centroids": 3, "max_iter": 4},
}


class KMeansQuestion:

    def __init__(self, num_points=None, num_centroids=None, max_iter=None, seed=None, difficulty="easy"):
        
        self.difficulty = difficulty.lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.num_points = num_points or config["num_points"]
        self.num_centroids = num_centroids or config["num_centroids"]
        self.iterations = max_iter or config["max_iter"]

        self.seed = seed or random.randint(1, 999999)
        random.seed(self.seed)
        np.random.seed(self.seed)

        self.points = [
            Point(f"P{i}", random.randint(0, 10), random.randint(0, 10))
            for i in range(self.num_points)
        ]
        self.initial_centroids = [
            Point(f"C{j}", random.randint(0, 10), random.randint(0, 10))
            for j in range(self.num_centroids)
        ]

        self.iteration_data = []

        self._run_kmeans()

    # ---------------------------------------------------------------------
    # Internal KMeans computation
    # ---------------------------------------------------------------------
    def _run_kmeans(self):
        
        while True:
            # --- Reset everything for a fresh run ---
            points = [(p.x, p.y) for p in self.points]
            centroids = [(c.x, c.y) for c in self.initial_centroids]
            self.iteration_data = []
            prev_assignments = None
            iteration = 0

            # --- Run K-Means iterations ---
            while True:
                assignments = []
                distances = []

                for (px, py) in points:
                    point_distances = []
                    min_dist = float("inf")
                    min_idx = 0

                    for j, (cx, cy) in enumerate(centroids):
                        
                        dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
                        
                        point_distances.append(f"{dist:.2f}".rstrip("0").rstrip("."))

                        if dist < min_dist or (math.isclose(dist, min_dist) and j < min_idx):
                            min_dist = dist
                            min_idx = j

                    distances.append(point_distances)
                    assignments.append(min_idx)

                #Check for convergence
                if assignments == prev_assignments:
                    stable_clusters = True
                    break
                elif iteration >= self.iterations:
                    stable_clusters = False
                    break
                prev_assignments = assignments[:]
                
                # Step 3: Recompute centroids
                new_centroids = []
                for k in range(self.num_centroids):
                    cluster_points = [points[i] for i, a in enumerate(assignments) if a == k]
                    if cluster_points:
                        avg_x = sum(p[0] for p in cluster_points) / len(cluster_points)
                        avg_y = sum(p[1] for p in cluster_points) / len(cluster_points)
                        new_centroids.append((avg_x, avg_y))
                    else:
                        # Empty cluster → keep same centroid
                        new_centroids.append(centroids[k])

                centroids = new_centroids

                # Save iteration data as formatted strings cuz only display and eval purpose from here
                current_centroids = [
                    Point(
                        f"C{j}",
                        f"{cx:.2f}".rstrip("0").rstrip("."),
                        f"{cy:.2f}".rstrip("0").rstrip(".")
                    )
                    for j, (cx, cy) in enumerate(centroids)
                ]

                self.iteration_data.append({
                    "centroids": current_centroids,
                    "assignments": assignments[:],
                    "distances": distances,
                })

                iteration += 1

            # --- Check if we reached max_iter ---
            if len(self.iteration_data) == self.iterations and stable_clusters:
                break
            else:
                # Rerun K-means with new random centroids
                self.initial_centroids = [
                    Point(f"C{j}", random.randint(0, 10), random.randint(0, 10))
                    for j in range(self.num_centroids)
                ]



    # ---------------------------------------------------------------------
    # Layout builder
    # ---------------------------------------------------------------------
    def generate(self):
        base = {}
        points = self.points

        view0 = [
            {
                "type": "Text",
                "content": f"In this task you have to solve {self.iterations} Kmeans iterations.\n Use euclidean Distance for Point Distances. \n If a Point has the same Distance to 2 centroids choose the first (choose C0 over C1 if they have equal distance to a point). \n If a Centroid isnt the closest centroid to any point it stays in its position",    
            },
            {
                "type": "Table",
                "title": "Points",
                "columns": ["Label", "X", "Y"],
                "rows": [[p.label, p.x, p.y] for p in points],
            },
        ]

        for iter_idx in range(len(self.iteration_data)):
            if iter_idx > 0: 
                iter_centroids = self.iteration_data[iter_idx-1]["centroids"]
                
            else: 
                iter_centroids = self.initial_centroids
            
            iter_num = iter_idx + 1

            # Each iteration view gets its own ID (iter1, iter2, etc.)
            view_key = f"view{iter_num}"
            iter_views = []

            if iter_idx > 0:
                iter_views.append({"type": "Text", "value": f"Iteration {iter_num}"})

            iter_views.append({
                "type": "Table",
                "title": "Centroids",
                "columns": ["Label", "X", "Y"],
                "rows": [[c.label, c.x, c.y] for c in iter_centroids], 
            })
            
            iter_views.append({
                "type": "CoordinatePlot",
                "points_blue": [[p.label, p.x, p.y] for p in points],
                "points_green": [[c.label, c.x, c.y] for c in iter_centroids],
            })
            
            iter_views.append({
                "type": "TableInput",
                "label": "Point Distances",
                "columns": ["Point to Centroid distance"]+[f"C{i}" for i in range(self.num_centroids)],
                "rows": [
                    {"id": f"iter{iter_num}_P{j}_dist", "fields": [f"P{j}"]+[ "" for i in range(self.num_centroids)]}
                    for j in range(self.num_points)
                ]
            })
            
            iter_views.append({
                "type": "TableInput",
                "label": "Point Allocation and resulting Centroid coordinates for next Iteration",
                "columns": ["Centroid", "X", "Y", "Cluster Points"],
                "rows": [
                    {"id": f"iter{iter_num}_c{j}", "fields": [f"C{j}", "", "", ""]}
                    for j in range(self.num_centroids)
                ],
            })
            

            base[view_key] = iter_views
            base["lastView"] = [
            {
                "type": "CoordinatePlot",
                "points_blue": [[p.label, p.x, p.y] for p in points],
                "points_green": [[c.label, c.x, c.y] for c in self.iteration_data[len(self.iteration_data)-1]["centroids"]],
            },
            {
                "type": "Text",
                "content": f"Kmeans ends at this point because a stable cluster asignment has been found. Running further Kmeans iterations results in the same clusters.",    
            },
        ]

        base["view1"] = view0 + base["view1"]
        return base

    # ---------------------------------------------------------------------
    # Evaluation
    # ---------------------------------------------------------------------
    def evaluate(self, user_input):
        print(user_input)
        results = {}

        for iter_idx, iteration in enumerate(self.iteration_data):
            centroids = iteration["centroids"]
            assignments = iteration["assignments"]
            distances = iteration["distances"]

            for j,valuesPoints in enumerate(distances):
                for i,valuesCentroids in enumerate(valuesPoints):
                    id = f"iter{iter_idx+1}_P{j}_dist_{i+1}"
                    results[id] = {
                    "correct": user_input.get(id) == valuesCentroids,
                    "expected": valuesCentroids
                }
                    
            cluster_points = {
                i: [p.label for j, p in enumerate(self.points) if assignments[j] == i]
                for i in range(self.num_centroids)
            }

            for c_idx, centroid in enumerate(centroids):
                row_id = f"iter{iter_idx+1}_c{c_idx}"

                expected_x = str(centroid.x)
                expected_y = str(centroid.y)
                expected_cluster = ",".join(sorted(cluster_points[c_idx]))

                x_field = f"{row_id}_1"
                y_field = f"{row_id}_2"
                cluster_field = f"{row_id}_3"

                results[x_field] = {
                    "correct": user_input.get(x_field) == expected_x,
                    "expected": expected_x
                }
                results[y_field] = {
                    "correct": user_input.get(y_field) == expected_y,
                    "expected": expected_y
                }
                results[cluster_field] = {
                    "correct": user_input.get(cluster_field, "").replace(" ", "") == expected_cluster,
                    "expected": expected_cluster
                }
        print(results)
        return results

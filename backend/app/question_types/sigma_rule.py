import random
import re

from app.common import *

DIFFICULTY_SETTINGS = {
    "easy": {"num_points": 10, "dimensions": 1},
    "medium": {"num_points": 13, "dimensions": 1},
    "hard": {"num_points": 10, "dimensions": 2},
}

class SigmaRule:

    def __init__(self, seed=None, difficulty="easy", mode="steps", dimensions = "random", num_points = "random", **kwargs):
        print(kwargs)
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = mode.lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)

        self.dimensions = int(dimensions) if dimensions != "random" else DIFFICULTY_SETTINGS[self.difficulty]["dimensions"]
        self.num_points = int(num_points) if num_points != "random" else DIFFICULTY_SETTINGS[self.difficulty]["num_points"]
        min_c = -1 * self.num_points
        max_c = 2 * self.num_points
        coords = set()
        while len(coords) < self.num_points:
            coords.add((random.randint(min_c, max_c), random.randint(min_c, max_c)))
        self.points = [Point(f"P{i}", x, y) for i, (x, y) in enumerate(coords)]
        self.sorted_points_x = sorted(self.points, key=lambda p: p.x)
        self.sorted_points_y = sorted(self.points, key=lambda p: p.y)
        self.alpha = round(random.uniform(0.2, 1.0), 1)


    def _generate_steps_layout(self):
        base = {}
        if self.dimensions > 1:
            point_display = [
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X", "Y"],
                    "rows": [[p.label, p.x, p.y] for p in self.points],
                },
                {
                    "type": "var_coordinates_plot",
                    "title": "DBSCAN result",
                    "series": [
                        {"name": "Points", "color": "blue",  "points": [[p.label, p.x, p.y] for p in self.points],  "symbol": "circle", "size": 8},
                    ]
                },
                {
                "type": "Text",
                "content": "Starten wir mit dimension X.\nDie Standardabweichung ist:\n\n$$\\sigma = \\sqrt{\\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}(p_i-\\mu)^2}$$"
                }

            ]
        else:
            point_display = [
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X"],
                    "rows": [[p.label, p.x] for p in self.points],
                },
                {
                "type": "Text",
                "content": f"Die Punkte werden zur Vereinfachung Sortiert:{[p.label for p in self.sorted_points_x]}",
                },
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X"],
                    "rows": [[p.label, p.x] for p in self.sorted_points_x],
                },
                {
                "type": "Text",
                "content": "Starten wir mit dder Berechnung der Standartabweichung X.\nDie Standardabweichung ist:\n\n$$\\sigma = \\sqrt{\\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}(p_i-\\mu)^2}$$",
                },
                {
                "type": "Text",
                "content": "Dabei wird der Mittelwert $$\\mu$$ benötigt der sich wie folgt errechnet: \n\n$$\\mu = \\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}p_i$$",
                },
                {
                "type": "layout_table",
                "rows": 2,
                "cols": 2,
                "cells": [[{"type": "text", "value": "##### Mittelwert",},{"type": "TextInput","id": "Mittelwert",}],[{"type": "text", "value": "##### Standartabweichung",},{"type": "TextInput","id": "Standartabweichung",}]]
                }
            ]

        base["view1"] = point_display
        base["view2"] = [
            {
                "type": "Text",
                "content": "Jetzt sind wir bereit die ober und untergrenzen zu berechnen \n dafür ist ein $$ \\alpha = "+ str(self.alpha) +"$$ gegeben \n Dabei ist zu beachten das\nObergrenze: $$\\mu + \\alpha * \\sigma$$\n\nUntergrenze: $$\\mu - \\alpha * \\sigma$$",
            },
            {
                "type": "layout_table",
                "rows": 2,
                "cols": 2,
                "cells": [[{"type": "text", "value": "##### Obergrenze",},{"type": "TextInput","id": "Obergrenze",}],[{"type": "text", "value": "##### Untergrenze",},{"type": "TextInput","id": "Untergrenze",}]]
            }
        ]
        base["view3"] = [
            {
                "type": "Text",
                "content": "Durch die Berechneten Grenzen können wir Punkte als Outlier Ausschlließen",
            },
            {"type": "TextInput","label": "Outlier:" ,"id": "Outlier",}
        ]
        base["last_view"] = []
        return base

    def _generate_exam_layout(self):
        return

    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        pass
    def _evaluate_exam(self, user_input):
        pass
    def evaluate(self, user_input):
        pass

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
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = mode.lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.dimensions = int(dimensions) if dimensions != "random" else DIFFICULTY_SETTINGS[self.difficulty]["dimensions"]
        self.num_points = int(num_points) if num_points != "random" else DIFFICULTY_SETTINGS[self.difficulty]["num_points"]
        min_c = -1 * self.num_points
        max_c = 2 * self.num_points
        coords = set()
        while len(coords) < self.num_points:
            coords.add((self.rng.randint(min_c, max_c), self.rng.randint(min_c, max_c)))
        coords_list = sorted(coords)  # e.g. sort by x then y
        self.points = [Point(f"P{i}", x, y) for i, (x, y) in enumerate(coords_list)]

        self.sorted_points_x = sorted(self.points, key=lambda p: p.x)
        self.sorted_points_y = sorted(self.points, key=lambda p: p.y)
        self.alpha = round(self.rng.uniform(0.2, 1.0), 1)
        self.results_x = {
        "mean_x" : 0,
        "stddev_x" : 0,
        "upper_x": 0,
        "lower_x": 0,
        }
        self.results_y = {
        "mean_y": 0,
        "stddev_y": 0,
        "upper_y": 0,
        "lower_y": 0
        }
        self._detect_outliers_sigma()

    def _detect_outliers_sigma(self):
        """
        Detect outliers using the sigma rule.
        - If self.dimensions == 1: use x only.
        - If self.dimensions == 2: use x and y; outlier if flagged in either dimension.
        Updates:
        self.outl: list of outlier Points
        self.inl:  list of inlier Points
        """

        def mean(vals):
            return sum(vals) / len(vals) if vals else 0.0

        def stddev(vals):
            n = len(vals)
            if n == 0:
                return 0.0
            mu = mean(vals)
            var = sum((v - mu) ** 2 for v in vals) / n
            return math.sqrt(var)

        def flagged(points, attr):
            vals = [getattr(p, attr) for p in points]
            mu = mean(vals)
            sd = stddev(vals)

            if sd == 0:
                return set()

            lower = mu - sd * self.alpha
            upper = mu + sd * self.alpha
            if attr == "x":
                self.results_x[f"stddev_x"] = sd
                self.results_x[f"mean_x"] = mu
                self.results_x[f"lower_x"] = lower
                self.results_x[f"upper_x"] = upper
            elif attr == "y":
                self.results_y[f"stddev_y"] = sd
                self.results_y[f"mean_y"] = mu
                self.results_y[f"lower_y"] = lower
                self.results_y[f"upper_y"] = upper

            return {p for p in points if getattr(p, attr) < lower or getattr(p, attr) > upper}

        pts = list(self.points)

        outliers = set()
        outliers |= flagged(pts, "x")

        if int(self.dimensions) >= 2:
            outliers |= flagged(pts, "y")

        self.outl = [p for p in pts if p in outliers]
        self.inl  = [p for p in pts if p not in outliers]

    def _generate_steps_layout(self):
        base = {}
        if self.dimensions > 1:
            # -------- 2 dimensions UI --------

            base["view1"] = [
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X", "Y"],
                    "rows": [[p.label, p.x, p.y] for p in self.points],
                },
                {
                    "type": "var_coordinates_plot",
                    "title": "Points",
                    "series": [
                        {"name": "Points", "color": "blue", "points": [[p.label, p.x, p.y] for p in self.points], "symbol": "circle", "size": 8},
                    ],
                },
                {
                    "type": "Text",
                    "content": (
                        "Starten wir mit Dimension **X**.\n"
                        "Dafür benötigen wir Mittelwert und Standardabweichung.\n\n"
                        "$$\\sigma = \\sqrt{\\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}(p_i-\\mu)^2}$$\n\n"
                        "Der Mittelwert ist:\n\n"
                        "$$\\mu = \\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}p_i$$"
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        [
                            {"type": "text", "value": "##### Mittelwert (X)"},
                            {"type": "TextInput", "id": "mean_x"},
                        ],
                        [
                            {"type": "text", "value": "##### Standardabweichung (X)"},
                            {"type": "TextInput", "id": "stddev_x"},
                        ],
                    ],
                },
            ]

            base["view2"] = [
                {
                    "type": "Text",
                    "content": (
                        "Jetzt berechnen wir die Ober- und Untergrenze für **X**.\n"
                        "Gegeben ist $$\\alpha = " + str(self.alpha) + "$$.\n\n"
                        "Obergrenze: $$\\mu + \\alpha \\cdot \\sigma$$\n\n"
                        "Untergrenze: $$\\mu - \\alpha \\cdot \\sigma$$"
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        [
                            {"type": "text", "value": "##### Obergrenze (X)"},
                            {"type": "TextInput", "id": "upper_x"},
                        ],
                        [
                            {"type": "text", "value": "##### Untergrenze (X)"},
                            {"type": "TextInput", "id": "lower_x"},
                        ],
                    ],
                },
            ]

            base["view3"] = [
                {
                    "type": "Text",
                    "content": (
                        "Jetzt wiederholen wir das Gleiche für Dimension **Y**.\n"
                        "Wir berechnen Mittelwert und Standardabweichung für Y.\n\n"
                        "$$\\sigma = \\sqrt{\\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}(p_i-\\mu)^2}$$\n\n"
                        "Der Mittelwert ist:\n\n"
                        "$$\\mu = \\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}p_i$$"
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        [
                            {"type": "text", "value": "##### Mittelwert (Y)"},
                            {"type": "TextInput", "id": "mean_y"},
                        ],
                        [
                            {"type": "text", "value": "##### Standardabweichung (Y)"},
                            {"type": "TextInput", "id": "stddev_y"},
                        ],
                    ],
                },
            ]

            base["view4"] = [
                {
                    "type": "Text",
                    "content": (
                        "Jetzt berechnen wir die Ober- und Untergrenze für **Y**.\n"
                        "Gegeben ist $$\\alpha = " + str(self.alpha) + "$$.\n\n"
                        "Obergrenze: $$\\mu + \\alpha \\cdot \\sigma$$\n\n"
                        "Untergrenze: $$\\mu - \\alpha \\cdot \\sigma$$"
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        [
                            {"type": "text", "value": "##### Obergrenze (Y)"},
                            {"type": "TextInput", "id": "upper_y"},
                        ],
                        [
                            {"type": "text", "value": "##### Untergrenze (Y)"},
                            {"type": "TextInput", "id": "lower_y"},
                        ],
                    ],
                },
            ]

            base["view5"] = [
                {
                    "type": "Text",
                    "content": (
                        "Jetzt haben wir die Grenzen für **X** und **Y** berechnet.\n"
                        "Ein Punkt ist ein Outlier, wenn er in **X oder Y** außerhalb seiner Grenzen liegt.\n"
                        "Gib die Outlier als Labels an (z.B. `P1, P5, P9`)."
                    ),
                },
                {"type": "TextInput", "label": "Outlier:", "id": "outliers"},
            ]

            base["lastView"] = [
                {
                    "type": "var_coordinates_plot",
                    "title": "Sigma Rule Result",
                    "series": [
                        {"name": "Inlier", "color": "blue", "points": [[p.label, p.x, p.y] for p in self.inl], "symbol": "circle", "size": 8},
                        {"name": "Outlier", "color": "greenblack", "points": [[p.label, p.x, p.y] for p in self.outl], "symbol": "x", "size": 8},
                    ],
                },
            ]


        else:
            # -------- 1 dimension UI (stylistically aligned with 2D) --------

            base["view1"] = [
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X"],
                    "rows": [[p.label, p.x] for p in self.points],
                },
                {
                    "type": "var_coordinates_plot",
                    "title": "Points",
                    "series": [
                        {"name": "Points", "color": "blue", "points": [[p.label, p.x, 0] for p in self.points], "symbol": "circle", "size": 8},
                    ],
                },
                {
                    "type": "Text",
                    "content": (
                        "Starten wir mit Dimension **X**.\n"
                        "Dafür benötigen wir Mittelwert und Standardabweichung.\n\n"
                        "$$\\sigma = \\sqrt{\\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}(p_i-\\mu)^2}$$\n\n"
                        "Der Mittelwert ist:\n\n"
                        "$$\\mu = \\frac{1}{" + str(self.num_points) + "}\\sum_{i=1}^{" + str(self.num_points) + "}p_i$$"
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        [
                            {"type": "text", "value": "##### Mittelwert (X)"},
                            {"type": "TextInput", "id": "mean_x"},
                        ],
                        [
                            {"type": "text", "value": "##### Standardabweichung (X)"},
                            {"type": "TextInput", "id": "stddev_x"},
                        ],
                    ],
                },
            ]

            base["view2"] = [
                {
                    "type": "Text",
                    "content": (
                        "Jetzt berechnen wir die Ober- und Untergrenze für **X**.\n"
                        "Gegeben ist $$\\alpha = " + str(self.alpha) + "$$.\n\n"
                        "Obergrenze: $$\\mu + \\alpha \\cdot \\sigma$$\n\n"
                        "Untergrenze: $$\\mu - \\alpha \\cdot \\sigma$$"
                    ),
                },
                {
                    "type": "layout_table",
                    "rows": 2,
                    "cols": 2,
                    "cells": [
                        [
                            {"type": "text", "value": "##### Obergrenze (X)"},
                            {"type": "TextInput", "id": "upper_x"},
                        ],
                        [
                            {"type": "text", "value": "##### Untergrenze (X)"},
                            {"type": "TextInput", "id": "lower_x"},
                        ],
                    ],
                },
            ]

            base["view3"] = [
                {
                    "type": "Text",
                    "content": (
                        "Jetzt haben wir die Grenzen für **X** berechnet.\n"
                        "Ein Punkt ist ein Outlier, wenn er außerhalb der Grenzen liegt.\n"
                        "Gib die Outlier als Labels an (z.B. `P1, P5, P9`)."
                    ),
                },
                {"type": "TextInput", "label": "Outlier:", "id": "outliers"},
            ]

            base["lastView"] = [
                {
                    "type": "var_coordinates_plot",
                    "title": "Sigma Rule Result",
                    "series": [
                        {"name": "Inlier", "color": "blue", "points": [[p.label, p.x, 0] for p in self.inl], "symbol": "circle", "size": 8},
                        {"name": "Outlier", "color": "greenblack", "points": [[p.label, p.x, 0] for p in self.outl], "symbol": "x", "size": 8},
                    ],
                },
            ]


        return base

    def _generate_exam_layout(self):
        base = {}

        if self.dimensions > 1:
            # -------- 2D Exam UI --------
            base["view1"] = [
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X", "Y"],
                    "rows": [[p.label, p.x, p.y] for p in self.points],
                },
                {
                    "type": "var_coordinates_plot",
                    "title": "Points",
                    "series": [
                        {"name": "Points", "color": "blue", "points": [[p.label, p.x, p.y] for p in self.points], "symbol": "circle", "size": 8},
                    ],
                },
                {
                    "type": "Text",
                    "content": (
                        "### Prüfungsaufgabe: Sigma-Regel (2D)\n\n"
                        "Bestimme für **X** und **Y** jeweils den **Mittelwert (μ)** und die **Standardabweichung (σ)**.\n"
                        f"Es gilt: **α = {self.alpha}**.\n\n"
                        "Berechne anschließend für jede Dimension die Grenzen:\n"
                        "- `Upper = μ + α · σ`\n"
                        "- `Lower = μ − α · σ`\n\n"
                        "#### Abgabeformat\n"
                        "Gib deine Ergebnisse **genau in dieser Form** an (jede Angabe in einer neuen Zeile):\n\n"
                        "**Für X (im Feld „Antworten X“):**\n"
                        "- `Mean: <zahl>`\n"
                        "- `Stddev: <zahl>`\n"
                        "- `Lower: <zahl>`\n"
                        "- `Upper: <zahl>`\n\n"
                        "**Für Y (im Feld „Antworten Y“):**\n"
                        "- `Mean: <zahl>`\n"
                        "- `Stddev: <zahl>`\n"
                        "- `Lower: <zahl>`\n"
                        "- `Upper: <zahl>`\n\n"
                        "**Outlier (separates Feld):**\n"
                        "- `Outliers: P1, P5, ...` (oder `Outliers: None`)\n"
                    ),
                },
                {
                    "type": "TextInput",
                    "label": "Antworten X (Mean/Stddev/Lower/Upper)",
                    "id": "answers_x",
                    "rows": 7,
                },
                {
                    "type": "TextInput",
                    "label": "Antworten Y (Mean/Stddev/Lower/Upper)",
                    "id": "answers_y",
                    "rows": 7,
                },
                {
                    "type": "TextInput",
                    "label": "Outliers",
                    "id": "outliers",
                },
            ]

            base["lastView"] = [
                {
                    "type": "var_coordinates_plot",
                    "title": "Sigma Rule Result",
                    "series": [
                        {"name": "Inlier", "color": "blue", "points": [[p.label, p.x, p.y] for p in self.inl], "symbol": "circle", "size": 8},
                        {"name": "Outlier", "color": "greenblack", "points": [[p.label, p.x, p.y] for p in self.outl], "symbol": "x", "size": 8},
                    ],
                },
            ]

        else:
            # -------- 1D Exam UI --------
            base["view1"] = [
                {
                    "type": "Table",
                    "title": "Points",
                    "columns": ["Label", "X"],
                    "rows": [[p.label, p.x] for p in self.points],
                },
                {
                    "type": "var_coordinates_plot",
                    "title": "Points",
                    "series": [
                        {"name": "Points", "color": "blue", "points": [[p.label, p.x, 0] for p in self.points], "symbol": "circle", "size": 8},
                    ],
                },
                {
                    "type": "Text",
                    "content": (
                        "### Prüfungsaufgabe: Sigma-Regel (1D)\n\n"
                        "Bestimme für **X** den **Mittelwert (μ)** und die **Standardabweichung (σ)**.\n"
                        f"Es gilt: **α = {self.alpha}**.\n\n"
                        "Berechne anschließend die Grenzen:\n"
                        "- `Upper = μ + α · σ`\n"
                        "- `Lower = μ − α · σ`\n\n"
                        "#### Abgabeformat\n"
                        "Gib deine Ergebnisse **genau in dieser Form** an (jede Angabe in einer neuen Zeile):\n"
                        "- `Mean: <zahl>`\n"
                        "- `Stddev: <zahl>`\n"
                        "- `Lower: <zahl>`\n"
                        "- `Upper: <zahl>`\n\n"
                        "Outlier in einem separaten Feld:\n"
                        "- `Outliers: P1, P5, ...` (oder `Outliers: None`)\n"
                    ),
                },
                {
                    "type": "TextInput",
                    "label": "Antworten (Mean/Stddev/Lower/Upper)",
                    "id": "answers_x",
                    "rows": 7,
                },
                {
                    "type": "TextInput",
                    "label": "Outliers",
                    "id": "outliers",
                },
            ]

            base["lastView"] = [
                {
                    "type": "var_coordinates_plot",
                    "title": "Sigma Rule Result",
                    "series": [
                        {"name": "Inlier", "color": "blue", "points": [[p.label, p.x, 0] for p in self.inl], "symbol": "circle", "size": 8},
                        {"name": "Outlier", "color": "greenblack", "points": [[p.label, p.x, 0] for p in self.outl], "symbol": "x", "size": 8},
                    ],
                },
            ]

        return base


    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}

        def process_dimension(results_dict):
            for key, expected_value in results_dict.items():
                results[key] = {
                    "correct": str(normalize_number(user_input.get(key))) == str(normalize_number(expected_value)),
                    "expected": str(normalize_number(expected_value)),
                }

        process_dimension(self.results_x)

        if int(self.dimensions) >= 2:
            process_dimension(self.results_y)

        user_outlier_input = user_input.get("outliers", "")
        user_outlier_input = str(user_outlier_input).lower()

        expected_labels = [p.label.lower() for p in self.outl]

        # Extract tokens like P1, P2, P10 etc.
        found_labels = re.findall(r"[a-zA-Z]+\d+", user_outlier_input)

        found_labels = [label.lower() for label in found_labels]

        correct = set(found_labels) == set(expected_labels)

        results["outliers"] = {
            "correct": correct,
            "expected": ", ".join(p.label for p in self.outl) if self.outl else "None",
        }
        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        results = {}

        def extract_value(text, key):
            """
            Extrahiert eine Zahl zu einem Key aus Freitext.
            Akzeptiert z.B.:
            - "Mean: 7"
            - "Stddev = 2.5"
            - "lower -1"
            """
            text = "" if text is None else str(text)

            num = r"([-+]?\d+(?:[.,]\d+)?)"
            pattern = rf"(?im)\b{re.escape(key)}\b\s*[:=]?\s*{num}"
            m = re.search(pattern, text)
            return m.group(1) if m else None

        def check_dimension(text, expected_map, key_prefix):
            """
            Prüft alle erwarteten Werte in einem Textfeld (answers_x / answers_y).
            correct = True nur wenn alle Werte stimmen.
            expected = zusammengefasster Erwartungsstring.
            """
            exam_to_expected = {
                "Mean": f"mean_{key_prefix}",
                "Stddev": f"stddev_{key_prefix}",
                "Lower": f"lower_{key_prefix}",
                "Upper": f"upper_{key_prefix}",
            }

            all_correct = True
            expected_parts = []

            for exam_key, exp_key in exam_to_expected.items():
                expected_value = expected_map.get(exp_key)
                found = extract_value(text, exam_key)

                if str(normalize_number(found)) != str(normalize_number(expected_value)):
                    all_correct = False

                expected_parts.append(f"{exam_key}: {normalize_number(expected_value)}")

            results[f"answers_{key_prefix}"] = {
                "correct": all_correct,
                "expected": "\n".join(expected_parts),
            }

        # --- X ---
        answers_x = user_input.get("answers_x", "")
        check_dimension(answers_x, self.results_x, "x")

        # --- Y (optional) ---
        if int(self.dimensions) >= 2:
            answers_y = user_input.get("answers_y", "")
            check_dimension(answers_y, self.results_y, "y")

        # --- Outliers (wie in steps) ---
        user_outlier_input = user_input.get("outliers", "")
        user_outlier_input = str(user_outlier_input).lower()

        expected_labels = [p.label.lower() for p in self.outl]

        found_labels = re.findall(r"[a-zA-Z]+\d+", user_outlier_input)
        found_labels = [label.lower() for label in found_labels]

        if ("none" in user_outlier_input or "kein" in user_outlier_input) and len(expected_labels) == 0:
            correct = True
        else:
            correct = set(found_labels) == set(expected_labels)

        results["outliers"] = {
            "correct": correct,
            "expected": ", ".join(p.label for p in self.outl) if self.outl else "None",
        }

        return results

    def evaluate(self, user_input):
        if self.mode == "exam":
            return self._evaluate_exam(user_input)
        return self._evaluate_steps(user_input)

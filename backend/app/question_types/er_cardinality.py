import random
import copy
import re
from pathlib import Path
import json
from collections import defaultdict

from app.common import *

DIFFICULTY_SETTINGS = {
    "easy": {},
    "medium": {},
    "hard": {},
}

path = Path(__file__).resolve().parent.parent / "resources" / "er_diagrams.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

class ERCardinality:

    def __init__(self, seed=None, card_type="min_max", question="random", **kwargs):

        self.question = str(question).lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.card_type = str(card_type).lower()
        if self.question == "random":
            self.task = self.rng.choice(raw)
        else:
            self.task = next(t for t in raw if self.question == t["id"])
        self.nodes = self.task[self.card_type]["nodes"]
        self.edges = self.task[self.card_type]["edges"]
        self.edges_altered = self.remove_cardinality_values()

    def remove_cardinality_values(self):
        altered = copy.deepcopy(self.edges)

        for edge in altered:
            if "data" in edge and "value" in edge["data"]:
                edge["data"]["value"] = ""

        return altered
    def _generate_steps_layout(self):
        base = {}

        min_max = (
            "### Aufgabe: Kardinalitäten ergänzen (Min-Max-Notation)\n"
            "Im gegebenen ER-Diagramm fehlen die Kardinalitäten an den Beziehungen.\n"
            "Ergänze für jede Beziehung die minimale und maximale Teilnahme der beteiligten Entitäten.\n\n"
            "### Min-Max-Notation\n"
            "Verwende pro Seite einer Beziehung genau einen Wert der Form $$min..max$$.\n"
            "Typische Werte sind zum Beispiel:\n"
            "- $$0..1$$\n"
            "- $$1..1$$\n"
            "- $$0..*$$\n"
            "- $$1..*$$\n\n"
            "Die erste Zahl gibt an, wie oft eine Entität **mindestens** an der Beziehung teilnimmt.\n"
            "Die zweite Zahl beschreibt, wie oft sie **höchstens** an der Beziehung teilnehmen kann.\n\n"
            "### Deine Aufgabe\n"
            "Trage für **jede Seite jeder Beziehung** den passenden $$min..max$$-Wert ein.\n\n"
            "### Hinweise\n"
            "- Betrachte jede Seite einer Beziehung separat\n"
            "- Orientiere dich an der Bedeutung der Beziehung im Text\n"
            "- Jede Beziehung muss an **allen beteiligten Seiten** eine vollständige Min-Max-Angabe erhalten\n"
        )

        cardinality = (
            "### Aufgabe: Kardinalitäten ergänzen\n"
            "Im gegebenen ER-Diagramm fehlen die Kardinalitäten an den Beziehungen.\n"
            "Ergänze für jede Beziehung die passende Kardinalität.\n\n"
            "### Mögliche Kardinalitäten\n"
            "- $$1:1$$\n"
            "- $$1:N$$\n"
            "- $$M:N$$\n\n"
            "### Deine Aufgabe\n"
            "Trage die passende Kardinalität an den Beziehungen ein.\n\n"
            "### Hinweise\n"
            "- Orientiere dich an der Bedeutung der Beziehung im Text\n"
            "- Prüfe für jede Beziehung, wie viele Objekte einer Entität mit Objekten der anderen Entität verbunden sein können\n"
            "- Jede Beziehung soll vollständig beschriftet werden\n"
        )

        if self.card_type == "min_max":
            text = min_max
        else:
            text = cardinality

        base["view1"] = [
            {
                "type": "Text",
                "content": text
            },
            {
                "type": "Text",
                "content": self.task["descriptive_text"]
            },
            {
                "type": "ER_Diagram_Builder",
                "id": "free_er_builder",
                "title": "Kardinalitäten ergänzen",
                "initial_diagram": {
                    "nodes": self.nodes,
                    "edges": self.edges_altered,
                }
            },
        ]
        base["lastView"] = [{
                "type": "ER_Diagram_Builder",
                "id": "free_er_builder2",
                "title": "Musterlösung:",
                "initial_diagram": {
                    "nodes": self.nodes,
                    "edges": self.edges,
                }
            }]
        return base

    def _generate_exam_layout(self):
        base = {}
        return base


    def generate(self):
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}
        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        results = {}
        return results

    def evaluate(self, user_input):
        return self._evaluate_steps(user_input)

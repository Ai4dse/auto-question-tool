import random
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

class ERModelling:

    def __init__(self, seed=None, difficulty="easy", mode="steps", card_type="min_max", question="random", **kwargs):
        self.difficulty = str(difficulty).lower()
        config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.question = str(question).lower()
        self.mode = mode.lower()
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.card_type = str(card_type).lower()
        if self.question == "random":
            self.task = self.rng.choice(raw)
        else:
            self.task = next(t for t in raw if self.question == t["id"])
        self.nodes = self.task[self.card_type]["nodes"]
        self.edges = self.task[self.card_type]["edges"]
        self.nodes_altered = []
        self.edges_altered = []
        if self.difficulty == "easy":
            self.build_random_incomplete_er_diagram(0.7, 0.6,2)
        elif self.difficulty == "medium":
            self.build_random_incomplete_er_diagram(0.3, 0.2,1)

    def build_random_incomplete_er_diagram(
        self,
        keep_core_ratio: float = 0.7,
        keep_attribute_ratio: float = 0.6,
        min_core_nodes: int = 2,
    ):
        """
        Build a random incomplete but still valid ER subdiagram.

        Uses:
            self.nodes
            self.edges

        Sets:
            self.nodes_altered
            self.edges_altered

        Rules:
        - only keep a connected subgraph of entity/relation nodes
        - only keep attributes whose owner is still present
        - randomly remove some remaining attributes
        - no dangling attributes
        - no disconnected remaining entity/relation components
        """
        nodes = list(self.nodes)
        edges = list(self.edges)

        node_by_id = {n["id"]: n for n in nodes}

        entity_relation_nodes = [
            n for n in nodes if n.get("type") in {"entity", "relation"}
        ]
        attribute_nodes = [
            n for n in nodes if n.get("type") == "attribute"
        ]

        # Split edges into:
        # - core edges: relation -> entity
        # - attribute edges: attribute -> entity/relation
        core_edges = []
        attribute_edges = []

        for e in edges:
            source = node_by_id.get(e["source"])
            target = node_by_id.get(e["target"])
            if not source or not target:
                continue

            s_type = source.get("type")
            t_type = target.get("type")

            if s_type == "relation" and t_type == "entity":
                core_edges.append(e)
            elif s_type == "attribute" and t_type in {"entity", "relation"}:
                attribute_edges.append(e)

        # Build undirected adjacency for the core graph
        adjacency = defaultdict(set)
        for e in core_edges:
            s = e["source"]
            t = e["target"]
            adjacency[s].add(t)
            adjacency[t].add(s)

        core_ids = [n["id"] for n in entity_relation_nodes]

        # Handle trivial cases
        if not core_ids:
            self.nodes_altered = []
            self.edges_altered = []
            return

        if len(core_ids) == 1:
            kept_core_ids = {core_ids[0]}
        else:
            # If the original core graph has isolated nodes, they cannot be part of a
            # connected multi-node result. Prefer starting from a node with neighbors.
            possible_starts = [nid for nid in core_ids if adjacency[nid]]
            start = self.rng.choice(possible_starts if possible_starts else core_ids)

            target_count = max(
                min_core_nodes,
                min(len(core_ids), round(len(core_ids) * keep_core_ratio))
            )

            # Grow a connected random subset
            kept_core_ids = {start}
            frontier = set(adjacency[start])

            while len(kept_core_ids) < target_count and frontier:
                nxt = self.rng.choice(sorted(frontier))
                kept_core_ids.add(nxt)

                frontier.discard(nxt)
                for nb in adjacency[nxt]:
                    if nb not in kept_core_ids:
                        frontier.add(nb)

            # If we couldn't reach target_count because graph is sparse/disconnected,
            # we keep the connected component we managed to build.
            # This still satisfies the "remaining nodes are connected" requirement.

        # Keep only core edges entirely inside kept_core_ids
        kept_core_edges = [
            e for e in core_edges
            if e["source"] in kept_core_ids and e["target"] in kept_core_ids
        ]

        # Optional cleanup:
        # remove isolated core nodes that may have slipped in
        # (important if start node was isolated or if target_count == 1)
        if len(kept_core_ids) > 1:
            used_core_ids = set()
            for e in kept_core_edges:
                used_core_ids.add(e["source"])
                used_core_ids.add(e["target"])
            kept_core_ids = used_core_ids

        # Now keep attributes whose owner is still present
        possible_attribute_edges = [
            e for e in attribute_edges
            if e["target"] in kept_core_ids
        ]

        # Randomly keep some of those attribute edges
        kept_attribute_edges = []
        for e in possible_attribute_edges:
            if self.rng.random() < keep_attribute_ratio:
                kept_attribute_edges.append(e)

        # Attribute nodes must only exist if their edge exists
        kept_attribute_ids = {e["source"] for e in kept_attribute_edges}

        # Build final node list
        kept_node_ids = kept_core_ids | kept_attribute_ids

        nodes_altered = [
            n for n in nodes
            if n["id"] in kept_node_ids
        ]

        edges_altered = kept_core_edges + kept_attribute_edges

        self.nodes_altered = nodes_altered
        self.edges_altered = edges_altered

    def _generate_steps_layout(self):
        base = {}
        min_max =   (
                    "### Schritt 4: Kardinalitäten (Min-Max-Notation)\n"
                    "Bestimme für jede Beziehung die minimale und maximale Teilnahme jeder Entität:\n"
                    "- Notation: $$min..max$$\n"
                    "- Beispiel: $$0..1$$, $$1..1$$, $$0..*$$, $$1..*$$\n\n"
                    "Die erste Zahl gibt an, wie oft eine Entität **mindestens** an der Beziehung teilnimmt,\n"
                    "die zweite Zahl beschreibt die **maximale** Anzahl an Teilnahmen.\n\n"
                    "Trage die entsprechenden $$min..max$$-Werte an beiden Seiten der Beziehung ein.\n\n"
                    )
        cardinality = (
                    "### Schritt 4: Kardinalitäten\n"
                    "Bestimme für jede Beziehung die Kardinalität:\n"
                    "- $$1:1$$\n"
                    "- $$1:N$$\n"
                    "- $$M:N$$\n\n"
                    "Trage die Kardinalitäten an beiden Seiten der Beziehung ein.\n\n"
                    )
        if self.card_type == "min_max":
            text = min_max
        else:
            text = cardinality
        base["view1"] = [
                {
                    "type": "Text",
                    "content": (
                        "### Aufgabe: ER-Diagramm erstellen\n"
                        "Erstelle ein Entity-Relationship-Diagramm aus dem gegebenen Text.\n\n"
                        "### Schritt 1: Entitäten\n"
                        "Definiere sinnvolle Entitäten (z. B. Student, Kurs, Dozent).\n"
                        "Bennene Entitäten wie im gegebenen Text.\n"
                        "Jede Entität sollte Attribute besitzen.\n\n"
                        "Achte darauf:\n"
                        "- Jede Entität benötigt einen **Primärschlüssel** $$PK$$\n"
                        "- Attribute sollen **atomar** und eindeutig sein\n\n"
                        "### Schritt 2: Attribute und Schlüssel\n"
                        "Ergänze alle Attribute für die Entitäten.\n"
                        "Markiere den jeweiligen Primärschlüssel $$PK$$ klar durch einen Doppelclick auf das jeweilige Attribut.\n\n"
                        "### Schritt 3: Beziehungen\n"
                        "Erstelle Beziehungen zwischen den Entitäten.\n\n"
                        "Achte darauf:\n"
                        "- Jede Beziehung verbindet minimal **zwei** und maximal **drei** Entitäten\n"
                        "- Jede Entität kann an beliebig vielen unterschiedlichen Relationen Teilnehmen\n"
                        "- Eine Relation kann bis zu **zweimal** mit der selben entität verbunden werden\n"
                        "- Verwende sinnvolle **Beziehungsnamen (Verben)**\n\n"
                        f"{text}"
                        "### Schritt 5: Beziehungsattribute\n"
                        "Beziehungen können ebenfalls eigene Attribute besitzen (z. B. Datum, Rolle).\n\n"
                        "### Hinweise\n"
                        "- Vermeide doppelte oder unnötige Attribute oder Entitäten\n"
                        "- Achte auf eine klare und übersichtliche Struktur im Diagramm\n"
                    )
                },
                {
                    "type": "Text",
                    "content": self.task["descriptive_text"]
                },
                {
                    "type": "ER_Diagram_Builder",
                    "id": "free_er_builder",
                    "title": "Build your own ER diagram",
                    "initial_diagram": {
                        "nodes": self.nodes_altered,
                        "edges": self.edges_altered,
                    }
                },

        ]
        base["lastView"] = [
                {
                    "type": "Text",
                    "content": "### Musterlösung:\n\n",
                },
                {
                    "type": "ER_Diagram_Builder",
                    "id": "free_er_builder",
                    "title": "Build your own ER diagram",
                    "initial_diagram": {
                        "nodes": self.nodes,
                        "edges": self.edges,
                    }
                },
        ]
        return base

    def _generate_exam_layout(self):
        base = {}
        return base


    def generate(self):
        if self.mode == "exam":
            return self._generate_exam_layout()
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
        if self.mode == "exam":
            return self._evaluate_exam(user_input)
        return self._evaluate_steps(user_input)

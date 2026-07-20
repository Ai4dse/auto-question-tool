import math
import random
import re
from itertools import combinations

DIFFICULTY_SETTINGS = {
    "easy": {"min_gap": 0.20, "max_gap": 1.01},
    "medium": {"min_gap": 0.09, "max_gap": 0.20},
    "hard": {"min_gap": 0.02, "max_gap": 0.09},
}

WORD_TRIPLES = [
    ("statistics", "statistic", "statistical"),
    ("integration", "integrating", "iteration"),
    ("customer", "costumer", "consumer"),
    ("address", "adress", "addressee"),
    ("engineering", "engineer", "engaging"),
    ("relation", "relational", "rotation"),
    ("database", "databases", "data"),
    ("algorithm", "algorithms", "logarithm"),
    ("matching", "mapping", "patching"),
    ("similarity", "similarly", "simplicity"),
    ("information", "informational", "formation"),
    ("analysis", "analyst", "analogy"),
    ("schema", "schemas", "scheme"),
    ("cluster", "clustering", "clutter"),
    ("projection", "protection", "production"),
    ("normalization", "normalisation", "nomination"),
    ("dependency", "dependencies", "independency"),
    ("duplicate", "duplication", "replicate"),
    ("representation", "presentation", "repetition"),
    ("searching", "matching", "marching"),
    ("semantic", "semantics", "systematic"),
    ("tokenization", "normalization", "localization"),
    ("stemming", "streaming", "steaming"),
    ("distance", "instance", "resistance"),
    ("similar", "similarity", "simulator"),
    ("record", "records", "recorder"),
    ("classification", "classifier", "clarification"),
    ("regression", "progression", "digression"),
    ("aggregation", "aggregating", "aggravation"),
    ("evaluation", "evaluating", "valuation"),
    ("extraction", "extracting", "traction"),
    ("retrieval", "retrieving", "revival"),
    ("indexing", "indexes", "inducing"),
    ("ranking", "rankings", "banking"),
    ("sorting", "sorted", "sporting"),
    ("filtering", "filtered", "faltering"),
    ("querying", "queries", "queuing"),
    ("transaction", "transactions", "translation"),
    ("consistency", "consistent", "constituency"),
    ("concurrency", "concurrent", "currency"),
    ("partition", "partitioning", "position"),
    ("distribution", "distributed", "distortion"),
    ("optimization", "optimisation", "organization"),
    ("validation", "validating", "valuation"),
    ("verification", "verified", "variation"),
    ("correlation", "correlated", "correction"),
    ("probability", "probabilistic", "profitability"),
    ("prediction", "predictive", "protection"),
    ("precision", "precise", "provision"),
    ("recall", "recalled", "record"),
    ("measurement", "measurements", "management"),
    ("performance", "performing", "preference"),
    ("experiment", "experimental", "experience"),
    ("parameter", "parameters", "perimeter"),
    ("variable", "variables", "valuable"),
    ("attribute", "attributes", "attitude"),
    ("entity", "entities", "identity"),
    ("document", "documents", "dominant"),
    ("collection", "collections", "correction"),
    ("corpus", "corpora", "purpose"),
    ("sentence", "sentences", "sequence"),
    ("language", "languages", "luggage"),
    ("lexical", "lexicon", "logical"),
    ("embedding", "embeddings", "emerging"),
    ("encoder", "encoders", "enclosure"),
    ("decoder", "decoders", "decorator"),
    ("transformer", "transformers", "transformation"),
    ("attention", "attentive", "intention"),
    ("training", "trained", "trailing"),
    ("learning", "learner", "leaving"),
    ("inference", "inferential", "interference"),
    ("generation", "generating", "generalization"),
    ("completion", "completing", "compilation"),
    ("instruction", "instructions", "construction"),
    ("response", "responses", "responsible"),
    ("question", "questions", "quotation"),
    ("answer", "answers", "ancestor"),
    ("benchmark", "benchmarks", "birthmark"),
    ("dataset", "datasets", "datagram"),
    ("metadata", "metadatas", "metaphor"),
    ("annotation", "annotations", "notation"),
    ("labeling", "labelled", "leveling"),
    ("feature", "features", "feather"),
    ("vector", "vectors", "victor"),
    ("matrix", "matrices", "metrics"),
    ("dimension", "dimensions", "division"),
    ("sampling", "samples", "stamping"),
    ("threshold", "thresholds", "household"),
    ("frequency", "frequencies", "fluency"),
    ("sequence", "sequences", "consequence"),
    ("structure", "structured", "stricture"),
    ("architecture", "architectural", "agriculture"),
    ("component", "components", "complement"),
    ("interface", "interfaces", "interlace"),
    ("implementation", "implementing", "implication"),
    ("configuration", "configurations", "confirmation"),
    ("application", "applications", "appellation"),
    ("processing", "processor", "progressing"),
    ("computation", "computational", "communication"),
    ("storage", "stored", "shortage"),
    ("memory", "memories", "mercury"),
    ("network", "networks", "noteworthy"),
    ("protocol", "protocols", "portfolio"),
    ("connection", "connections", "collection"),
    ("synchronization", "synchronisation", "symbolization"),
    ("serialization", "serializing", "specialization"),
    ("encoding", "encoded", "enclosing"),
    ("compression", "compressed", "comparison"),
    ("encryption", "encrypted", "description"),
    ("authentication", "authenticated", "authorization"),
    ("permission", "permissions", "permutation"),
    ("security", "secure", "severity"),
    ("privacy", "private", "priority"),
    ("repository", "repositories", "repetitory"),
    ("version", "versions", "conversion"),
    ("revision", "revisions", "decision"),
    ("deployment", "deploying", "employment"),
    ("container", "containers", "contention"),
    ("virtualization", "virtualisation", "visualization"),
    ("monitoring", "monitored", "mentoring"),
    ("logging", "logger", "lodging"),
    ("debugging", "debugger", "degrading"),
    ("exception", "exceptions", "execution"),
    ("failure", "failures", "feature"),
    ("recovery", "recovering", "discovery"),
    ("availability", "available", "variability"),
    ("scalability", "scalable", "stability"),
    ("reliability", "reliable", "relatability"),
    ("efficiency", "efficient", "sufficiency"),
    ("latency", "latencies", "vacancy"),
    ("throughput", "throughputs", "throughout"),
]


class NGramSimilarityQuestion:

    PAIR_INDICES = ((0, 1), (0, 2), (1, 2))

    def __init__(self, seed=None, difficulty="easy", Mode="bigram"):
        self.difficulty = str(difficulty or "easy").strip().lower()
        if self.difficulty not in DIFFICULTY_SETTINGS:
            self.difficulty = "easy"

        self.a = self._normalize_ngram_mode(Mode)
        self.n = 2 if self.a == "bigram" else 3

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.words = []
        self.word_ngrams = []
        self.pair_results = {}
        self.best_pair = None

        self._initialize_instance()

    @staticmethod
    def _normalize_ngram_mode(value):
        text = str(value or "bigram").strip().lower().replace("-", "")
        if text in {"trigram", "trigrams", "tri", "3", "3gram", "3grams"}:
            return "trigram"
        return "bigram"

    @staticmethod
    def _normalize_word(word):

        return re.sub(r"[^0-9a-zäöüß]", "", str(word or "").lower())

    def _ngrams_in_order(self, word):
        """Return unique n-grams in first-occurrence order."""
        normalized = self._normalize_word(word)
        padding = "_" * (self.n - 1)
        padded = padding + normalized + padding

        grams = []
        seen = set()
        for index in range(len(padded) - self.n + 1):
            gram = padded[index:index + self.n]
            if gram not in seen:
                grams.append(gram)
                seen.add(gram)
        return grams

    @staticmethod
    def _dice_similarity(grams_a, grams_b):
        set_a = set(grams_a)
        set_b = set(grams_b)
        denominator = len(set_a) + len(set_b)
        if denominator == 0:
            return 1.0
        return (2.0 * len(set_a & set_b)) / denominator

    def _analyze_words(self, words):
        ngram_lists = [self._ngrams_in_order(word) for word in words]
        pair_results = {}

        for left, right in self.PAIR_INDICES:
            left_set = set(ngram_lists[left])
            right_set = set(ngram_lists[right])

            # Preserve the order from the left word for readable solutions.
            shared = [gram for gram in ngram_lists[left] if gram in right_set]
            similarity = self._dice_similarity(ngram_lists[left], ngram_lists[right])

            pair_results[(left, right)] = {
                "shared": shared,
                "similarity": similarity,
                "left_count": len(left_set),
                "right_count": len(right_set),
                "shared_count": len(left_set & right_set),
            }

        ranked = sorted(
            pair_results.items(),
            key=lambda item: item[1]["similarity"],
            reverse=True,
        )
        best_pair, best_result = ranked[0]
        second_result = ranked[1][1]
        gap = best_result["similarity"] - second_result["similarity"]

        return ngram_lists, pair_results, best_pair, gap

    def _initialize_instance(self):
        config = DIFFICULTY_SETTINGS[self.difficulty]
        candidates = []

        for triple in WORD_TRIPLES:
            ngram_lists, pair_results, best_pair, gap = self._analyze_words(triple)
            ranked_scores = sorted(
                (result["similarity"] for result in pair_results.values()),
                reverse=True,
            )

            if math.isclose(ranked_scores[0], ranked_scores[1], abs_tol=1e-12):
                continue

            if config["min_gap"] <= gap < config["max_gap"]:
                candidates.append(triple)

        if not candidates:
            raise ValueError(
                f"No {self.a} word triple available for difficulty "
                f"'{self.difficulty}'."
            )

        selected = list(self.rng.choice(candidates))
        self.rng.shuffle(selected)

        self.words = selected
        (
            self.word_ngrams,
            self.pair_results,
            self.best_pair,
            _,
        ) = self._analyze_words(self.words)

    @property
    def gram_label(self):
        return "Bigramme" if self.n == 2 else "Trigramme"

    @staticmethod
    def _format_grams(grams):
        return ", ".join(grams) if grams else "-"

    @staticmethod
    def _format_similarity(value):
        return f"{value:.3f}"

    def _pair_title(self, left, right):
        return f"Wort {left + 1} und Wort {right + 1}"

    def _pair_expected_text(self, left, right):
        return (
            f"{self._pair_title(left, right)} "
            f"({self.words[left]}, {self.words[right]})"
        )

    def generate(self):
        ngram_examples = (
            'Beispiel: `abc` → `_a`, `ab`, `bc`, `c_`'
            if self.n == 2
            else 'Beispiel: `abc` → `__a`, `_ab`, `abc`, `bc_`, `c__`'
        )

        gram_cells = []
        for index, word in enumerate(self.words, start=1):
            gram_cells.append([
                {
                    "type": "TextInput",
                    "id": f"ng_word_{index}_grams",
                    "label": f'{self.gram_label} von Wort {index} ("{word}")',
                }
            ])

        pair_cells = []
        for left, right in self.PAIR_INDICES:
            pair_slug = f"{left + 1}_{right + 1}"
            pair_cells.append([
                {
                    "type": "TextInput",
                    "id": f"ng_pair_{pair_slug}_shared",
                    "label": f"Gemeinsame {self.gram_label}: {self._pair_title(left, right)}",
                },
                {
                    "type": "TextInput",
                    "id": f"ng_pair_{pair_slug}_similarity",
                    "label": f"Dice-Ähnlichkeit: {self._pair_title(left, right)}",
                },
            ])

        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        f"Aufgabe: Berechne für die drei Wörter die eindeutigen "
                        f"{self.gram_label} und anschließend für jedes Wortpaar die "
                        "Dice-Ähnlichkeit. Entscheide danach, welches Wortpaar am "
                        "ähnlichsten ist.\n\n"
                        "Verwende führende und nachgestellte Leerzeichen als Padding "
                        f"und stelle sie mit '_' dar. {ngram_examples}\n\n"
                        "Die Reihenfolge der eingegebenen N-Gramme ist egal; doppelte "
                        "N-Gramme werden nur einmal gezählt.\n\n"
                        "Formel: S(A,B) = 2 * |A ∩ B| / (|A| + |B|). "
                        "Ähnlichkeitswerte dürfen als Dezimalzahl oder Prozentwert "
                        "eingegeben werden."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Zu vergleichende Wörter",
                    "columns": ["Nummer", "Wort"],
                    "rows": [
                        [str(index), word]
                        for index, word in enumerate(self.words, start=1)
                    ],
                },
                {
                    "type": "layout_table",
                    "title": f"1. Eindeutige {self.gram_label}",
                    "rows": 3,
                    "cols": 1,
                    "cells": gram_cells,
                },
                {
                    "type": "layout_table",
                    "title": "2. Paarweise Ähnlichkeiten",
                    "rows": 3,
                    "cols": 2,
                    "cells": pair_cells,
                },
                {
                    "type": "TextInput",
                    "id": "ng_most_similar_pair",
                    "label": "Ähnlichstes Wortpaar (z. B. '1-2' oder die beiden Wörter)",
                },
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": "Bewertung abgeschlossen.",
                },
                {
                    "type": "Table",
                    "title": "Lösung: Paarweise Dice-Ähnlichkeit",
                    "columns": [
                        "Wortpaar",
                        f"Gemeinsame {self.gram_label}",
                        "Ähnlichkeit",
                    ],
                    "rows": [
                        [
                            self._pair_expected_text(left, right),
                            self._format_grams(self.pair_results[(left, right)]["shared"]),
                            self._format_similarity(
                                self.pair_results[(left, right)]["similarity"]
                            ),
                        ]
                        for left, right in self.PAIR_INDICES
                    ],
                },
                {
                    "type": "Text",
                    "content": (
                        "Ähnlichstes Paar: "
                        + self._pair_expected_text(*self.best_pair)
                    ),
                },
            ],
        }

    @staticmethod
    def _parse_gram_collection(value):
        if isinstance(value, (list, tuple, set)):
            raw_parts = [str(item) for item in value]
        else:
            text = str(value or "").strip().lower()
            if not text or text == "-":
                return set()

            text = re.sub(r"[\[\]{}()]", " ", text)
            raw_parts = re.split(r"[,;|\s]+", text)

        return {
            part.strip().lower()
            for part in raw_parts
            if part and part.strip() and part.strip() != "-"
        }

    @staticmethod
    def _parse_similarity(value):
        text = str(value or "").strip().lower().replace(" ", "")
        if not text:
            return None

        is_percent = text.endswith("%")
        if is_percent:
            text = text[:-1]

        text = text.replace(",", ".")
        try:
            number = float(text)
        except (TypeError, ValueError):
            return None

        if is_percent or number > 1.0:
            number /= 100.0
        return number

    def _parse_pair(self, value):
        text = str(value or "").strip().lower()
        if not text:
            return None

        numbers = [int(number) for number in re.findall(r"[1-3]", text)]
        unique_numbers = []
        for number in numbers:
            if number not in unique_numbers:
                unique_numbers.append(number)
        if len(unique_numbers) == 2:
            return tuple(sorted((unique_numbers[0] - 1, unique_numbers[1] - 1)))

        supplied_tokens = re.findall(r"[0-9a-zäöüß]+", text)
        word_to_index = {
            self._normalize_word(word): index
            for index, word in enumerate(self.words)
        }
        matched_indices = []
        for token in supplied_tokens:
            index = word_to_index.get(self._normalize_word(token))
            if index is not None and index not in matched_indices:
                matched_indices.append(index)

        if len(matched_indices) == 2:
            return tuple(sorted(matched_indices))
        return None

    def evaluate(self, user_input):
        user_input = user_input or {}
        results = {}

        for index, expected_grams in enumerate(self.word_ngrams, start=1):
            field_id = f"ng_word_{index}_grams"
            actual = self._parse_gram_collection(user_input.get(field_id, ""))
            expected = set(expected_grams)
            results[field_id] = {
                "correct": actual == expected,
                "expected": self._format_grams(expected_grams),
            }

        for left, right in self.PAIR_INDICES:
            pair_slug = f"{left + 1}_{right + 1}"
            shared_id = f"ng_pair_{pair_slug}_shared"
            similarity_id = f"ng_pair_{pair_slug}_similarity"
            expected_result = self.pair_results[(left, right)]

            actual_shared = self._parse_gram_collection(
                user_input.get(shared_id, "")
            )
            expected_shared = set(expected_result["shared"])
            results[shared_id] = {
                "correct": actual_shared == expected_shared,
                "expected": self._format_grams(expected_result["shared"]),
            }

            actual_similarity = self._parse_similarity(
                user_input.get(similarity_id, "")
            )
            expected_similarity = expected_result["similarity"]
            results[similarity_id] = {
                "correct": (
                    actual_similarity is not None
                    and math.isclose(
                        actual_similarity,
                        expected_similarity,
                        rel_tol=0.0,
                        abs_tol=0.005,
                    )
                ),
                "expected": self._format_similarity(expected_similarity),
            }

        pair_id = "ng_most_similar_pair"
        actual_pair = self._parse_pair(user_input.get(pair_id, ""))
        results[pair_id] = {
            "correct": actual_pair == tuple(sorted(self.best_pair)),
            "expected": self._pair_expected_text(*self.best_pair),
        }

        return results

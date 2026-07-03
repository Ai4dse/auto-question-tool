import itertools
import json
import math
import random
import re

from app.question_types.frequent_itemset_helper import (
    format_itemset,
    format_probability,
    generate_transaction_dataset,
    parse_itemset_text,
    parse_probability,
)
from app.question_types.fp_tree_eval_helpers import (
    evaluate_fp_tree,
    parse_fp_tree_payload,
    tree_from_path_count_rows,
)



DIFFICULTY_SETTINGS = {
    "easy": {
        "num_items": 4,
        "num_transactions": 8,
        "min_items": 2,
        "max_items": 4,
        "minsup_range": (0.35, 0.50),
        "min_frequent_items": 3,
        "min_conditional_paths": 1,
        "min_frequent_itemsets": 5,
    },
    "medium": {
        "num_items": 5,
        "num_transactions": 9,
        "min_items": 2,
        "max_items": 4,
        "minsup_range": (0.30, 0.45),
        "min_frequent_items": 3,
        "min_conditional_paths": 2,
        "min_frequent_itemsets": 6,
    },
    "hard": {
        "num_items": 6,
        "num_transactions": 10,
        "min_items": 2,
        "max_items": 5,
        "minsup_range": (0.25, 0.40),
        "min_frequent_items": 4,
        "min_conditional_paths": 3,
        "min_frequent_itemsets": 8,
    },
}


class _FPNode:
    def __init__(self, item=None, parent=None):
        self.item = item
        self.count = 0
        self.parent = parent
        self.children = {}

    def child(self, item):
        if item not in self.children:
            self.children[item] = _FPNode(item=item, parent=self)
        return self.children[item]


class FPGrowthAlgorithmQuestion:
    """
    FP-growth task matching the AprioriAlgorithmQuestion pattern.

    Expected frontend payloads:
    - fp_sorted_transactions: {"rows": [{"tid": "T1", "items": "A, B"}, ...]}
    - fp_main_tree: {"rows": [{"path": "A, B", "count": "3"}, ...]}
    - fp_relational_paths: {"rows": [{"item": "C", "path": "A, B", "count": "2"}, ...]}
    - fp_relational_trees: {"rows": [{"item": "C", "path": "A, B", "count": "2"}, ...]}
    - fp_frequent_itemsets: {"rows": [{"item": "C", "itemset": "A, C", "support": "2", "probability": "0.25"}, ...]}

    Empty path rows are not required. If a conditional/relational tree is empty, no rows are expected for it.
    """

    def __init__(self, seed=None, difficulty="easy", mode="steps"):
        self.difficulty = str(difficulty).lower()
        self.config = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS["easy"])

        self.mode = str(mode or "steps").lower()
        if self.mode not in {"steps", "exam"}:
            self.mode = "steps"

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.minsup = round(self.rng.uniform(*self.config["minsup_range"]), 2)
        self.base_items = []
        self.transactions = []
        self.minsup_count = 1
        self.solution = {}
        self._initialize_instance()

    def _initialize_instance(self):
        chosen = None
        for attempt in range(120):
            local_rng = random.Random(self.seed + attempt)
            base_items, transactions = generate_transaction_dataset(
                local_rng,
                self.config["num_items"],
                self.config["num_transactions"],
                self.config["min_items"],
                self.config["max_items"],
            )

            minsup_count = max(1, int(math.ceil(self.minsup * len(transactions))))

            # wichtig: _run_fp_growth und Unterfunktionen nutzen self.minsup_count
            self.minsup_count = minsup_count

            solution = self._run_fp_growth(transactions, base_items, minsup_count)

            if self._is_interesting_solution(solution):
                chosen = (base_items, transactions, minsup_count, solution)
                break
            if chosen is None:
                chosen = (base_items, transactions, minsup_count, solution)

        if not chosen:
            raise ValueError("Failed to generate FP-growth instance.")
        self.base_items, self.transactions, self.minsup_count, self.solution = chosen

    def _is_interesting_solution(self, solution):
        return (
            len(solution["frequent_items"]) >= self.config["min_frequent_items"]
            and len(solution["relational_paths"]) >= self.config["min_conditional_paths"]
            and len(solution["frequent_itemsets"]) >= self.config["min_frequent_itemsets"]
        )

    def _parse_path_items(self, raw):
        """
        Parse item/path text flexibly.

        Accepted examples for single-letter items:
        - A,B
        - A B
        - A;B
        - A/B
        - A->B
        - AB
        - ab

        Returns a tuple in the entered order, using canonical item names.
        """
        text = str(raw or "").strip()
        if not text or text in {"-", "∅", "{}"}:
            return tuple()

        canonical_items = {str(item).lower(): str(item) for item in self.base_items}
        single_char_items = all(len(str(item)) == 1 for item in self.base_items)
        single_char_lookup = {
            str(item).lower(): str(item)
            for item in self.base_items
            if len(str(item)) == 1
        }

        text = text.replace("[", " ").replace("]", " ")
        text = text.replace("(", " ").replace(")", " ")
        text = text.replace("{", " ").replace("}", " ")
        text = text.replace("->", ",").replace("→", ",").replace("/", ",")
        text = text.replace("|", ",")
        text = text.strip(" ,;|\n\t")

        if not text:
            return tuple()

        if any(sep in text for sep in [",", ";", " ", "\t", "\n"]):
            parts = [p.strip() for p in re.split(r"[,;\s]+", text) if p.strip()]
        elif single_char_items and all(ch.lower() in single_char_lookup for ch in text):
            parts = [single_char_lookup[ch.lower()] for ch in text]
        else:
            parts = [text]

        return tuple(
            canonical_items.get(str(part).lower(), str(part))
            for part in parts
        )

    @staticmethod
    def _itemset_slug(itemset):
        return "_".join(itemset)

    @staticmethod
    def _format_path(path):
        return ", ".join(path) if path else "-"

    @staticmethod
    def _bool_value(value):
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on"}

    @staticmethod
    def _int_value(value):
        raw = "" if value is None else str(value).strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def _prob_matches(actual, expected):
        return actual is not None and abs(actual - expected) <= 0.005

    def _parse_ordered_items(self, raw):
        return self._parse_path_items(raw)

    def _frequency_order_key(self, item, frequencies):
        return (-frequencies.get(item, 0), item)

    def _count_frequencies(self, transactions, base_items):
        counts = {item: 0 for item in base_items}
        for tx in transactions:
            for item in tx:
                counts[item] = counts.get(item, 0) + 1
        return counts

    def _sort_transaction(self, tx, frequencies, minsup_count):
        frequent = [item for item in tx if frequencies.get(item, 0) >= minsup_count]
        return tuple(sorted(frequent, key=lambda item: self._frequency_order_key(item, frequencies)))

    def _insert_tree_path(self, root, items, count=1):
        node = root
        for item in items:
            node = node.child(item)
            node.count += count

    def _build_tree(self, weighted_paths):
        root = _FPNode()
        for path, count in weighted_paths:
            if path and count > 0:
                self._insert_tree_path(root, path, count)
        return root

    def _tree_rows(self, root):
        rows = []

        def visit(node, prefix):
            for item in sorted(node.children, key=lambda child: (-node.children[child].count, child)):
                child = node.children[item]
                path = prefix + (item,)
                rows.append({"path": path, "count": int(child.count)})
                visit(child, path)

        visit(root, tuple())
        return rows

    def _node_occurrences(self, root):
        occurrences = []

        def visit(node, prefix):
            for item, child in node.children.items():
                path = prefix + (item,)
                occurrences.append({"item": item, "prefix": prefix, "path": path, "count": int(child.count)})
                visit(child, path)

        visit(root, tuple())
        return occurrences

    def _conditional_pattern_base(self, root, mining_items):
        occ = self._node_occurrences(root)
        paths = []
        for item in mining_items:
            for node in occ:
                if node["item"] == item and node["prefix"]:
                    paths.append({"item": item, "path": node["prefix"], "count": int(node["count"])})
        return paths

    def _conditional_item_counts(self, paths_for_item):
        counts = {}
        for entry in paths_for_item:
            for item in entry["path"]:
                counts[item] = counts.get(item, 0) + int(entry["count"])
        return counts

    def _conditional_sorted_paths(self, paths_for_item):
        counts = self._conditional_item_counts(paths_for_item)
        tree_paths = []
        for entry in paths_for_item:
            # Important: a conditional FP-tree is built from the prefix paths
            # produced in Step 3. Do not re-sort a path by local frequency here.
            # Otherwise a path like C,B,D,E can incorrectly become B,C,E,D.
            path = tuple(entry["path"])
            if path:
                tree_paths.append((path, int(entry["count"])))
        return tree_paths, counts

    def _frequent_itemsets_for_suffix(
        self,
        suffix_item,
        paths_for_item,
        suffix_support,
        num_transactions,
    ):
        sorted_paths, counts = self._conditional_sorted_paths(paths_for_item)
        conditional_frequent_items = sorted(
            item for item, count in counts.items()
            if count >= self.minsup_count
        )

        itemsets = [
            {
                "item": suffix_item,
                "itemset": tuple(sorted((suffix_item,))),
                "support": int(suffix_support),
                "probability": suffix_support / num_transactions,
            }
        ]

        for size in range(1, len(conditional_frequent_items) + 1):
            for combo in itertools.combinations(conditional_frequent_items, size):
                combo_set = set(combo)
                support = sum(
                    count
                    for path, count in sorted_paths
                    if combo_set.issubset(set(path))
                )

                if support >= self.minsup_count:
                    full_itemset = tuple(sorted(combo + (suffix_item,)))
                    itemsets.append(
                        {
                            "item": suffix_item,
                            "itemset": full_itemset,
                            "support": int(support),
                            "probability": support / num_transactions,
                        }
                    )
        return itemsets

    def _run_fp_growth(self, transactions, base_items, minsup_count):
        frequencies = self._count_frequencies(transactions, base_items)
        frequent_items = sorted(
            [item for item in base_items if frequencies.get(item, 0) >= minsup_count],
            key=lambda item: self._frequency_order_key(item, frequencies),
        )
        mining_items = sorted(frequent_items, key=lambda item: (frequencies[item], item))

        sorted_transactions = [self._sort_transaction(tx, frequencies, minsup_count) for tx in transactions]
        main_tree = self._build_tree([(tx, 1) for tx in sorted_transactions if tx])
        main_tree_rows = self._tree_rows(main_tree)

        relational_paths = self._conditional_pattern_base(main_tree, mining_items)
        relational_trees = []
        frequent_itemsets = []
        num_transactions = len(transactions)

        paths_by_item = {item: [] for item in mining_items}
        for entry in relational_paths:
            paths_by_item.setdefault(entry["item"], []).append(entry)

        for item in mining_items:
            paths_for_item = paths_by_item.get(item, [])
            sorted_paths, _ = self._conditional_sorted_paths(paths_for_item)
            conditional_tree = self._build_tree(sorted_paths)
            for tree_row in self._tree_rows(conditional_tree):
                relational_trees.append({"item": item, "path": tree_row["path"], "count": tree_row["count"]})

            frequent_itemsets.extend(
                self._frequent_itemsets_for_suffix(item, paths_for_item, frequencies[item], num_transactions)
            )

        # Remove duplicates defensively. In normal suffix-order mining every itemset is produced once.
        dedup = {}
        for entry in frequent_itemsets:
            dedup[(entry["item"], entry["itemset"])] = entry
        frequent_itemsets = list(dedup.values())

        return {
            "frequencies": frequencies,
            "frequent_items": frequent_items,
            "mining_items": mining_items,
            "sorted_transactions": sorted_transactions,
            "main_tree_rows": main_tree_rows,
            "relational_paths": relational_paths,
            "relational_trees": relational_trees,
            "frequent_itemsets": frequent_itemsets,
        }
    
    @staticmethod
    def _set_tree_root_count(tree, root_count):
        """Set the root count on the expected FP-tree object returned by the helper.

        The helper can return either a dict-like tree or a small node object,
        depending on the frontend/evaluation implementation. This keeps the
        conditional-tree root-count patch local.
        """
        if root_count is None or tree is None:
            return tree

        root_count = int(root_count)

        if isinstance(tree, dict):
            if "root" in tree:
                if isinstance(tree.get("root"), dict):
                    tree["root"]["count"] = root_count
                elif tree.get("root") is not None and hasattr(tree.get("root"), "count"):
                    setattr(tree["root"], "count", root_count)
            else:
                tree["count"] = root_count
            return tree

        if hasattr(tree, "count"):
            setattr(tree, "count", root_count)
        elif hasattr(tree, "root") and hasattr(tree.root, "count"):
            setattr(tree.root, "count", root_count)

        return tree

    def _grade_fp_tree(self, user_input, key, expected_rows, expected_root_count=None):
        expected_tree = tree_from_path_count_rows(expected_rows)
        expected_tree = self._set_tree_root_count(expected_tree, expected_root_count)

        try:
            actual_tree = parse_fp_tree_payload((user_input or {}).get(key))
        except (json.JSONDecodeError, TypeError, ValueError):
            return {
                key: {
                    "correct": False,
                    "expected": expected_tree,
                    "node_results": {},
                    "missing": [],
                    "extra": [],
                    "message": "Invalid FP-tree JSON payload.",
                }
            }

        evaluation = evaluate_fp_tree(actual_tree, expected_tree)

        return {
            key: {
                "correct": evaluation["correct"],
                "expected": evaluation["expected_tree"],
                "node_results": evaluation["node_results"],
                "missing": evaluation["missing"],
                "extra": evaluation["extra"],
            }
        }


    def _transaction_rows(self):
        return [[f"T{i + 1}", ", ".join(sorted(list(tx)))] for i, tx in enumerate(self.transactions)]

    def _frequency_rows(self):
        frequencies = self.solution["frequencies"]
        rows = []
        for item in sorted(self.base_items, key=lambda x: (-frequencies.get(x, 0), x)):
            rows.append([
                item,
                str(frequencies.get(item, 0)),
                str(frequencies.get(item, 0) >= self.minsup_count),
            ])
        return rows

    def _prefilled_sorted_transaction_rows(self):
        rows = []
        for idx, _tx in enumerate(self.transactions):
            rows.append(
                {
                    "id": f"fp_sort_t{idx + 1}",
                    "fields": [
                        f"T{idx + 1}",
                        {"kind": "input", "id": f"fp_sort_t{idx + 1}_items"},
                    ],
                }
            )
        return rows

    def _prefilled_conditional_path_rows(self):
        rows = []

        # One row per frequent item in mining order. This is the same outer-to-inner
        # order used for the conditional pattern bases.
        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))

            rows.append(
                {
                    "id": f"conditional_path_{safe_item}",
                    "fields": [
                        str(item),
                        {"kind": "input", "id": f"conditional_path_{safe_item}_paths"},
                    ],
                }
            )

        return rows

    def _prefilled_frequent_itemset_rows(self):
        rows = []

        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))
            rows.append(
                {
                    "id": f"fp_itemsets_{safe_item}",
                    "fields": [
                        str(item),
                        {"kind": "input", "id": f"fp_itemsets_{safe_item}_sets"},
                    ],
                }
            )

        return rows

    def _prefilled_frequency_rows(self):
        rows = []
        frequencies = self.solution["frequencies"]
        for item in sorted(self.base_items, key=lambda x: (-frequencies.get(x, 0), x)):
            rows.append(
                {
                    "id": f"fp_freq_{item}",
                    "fields": [
                        item,
                        {"kind": "input", "id": f"fp_freq_{item}_count"},
                    ],
                }
            )
        return rows

    def _conditional_tree_builder_elements(self):
        elements = [
            {
                "type": "Text",
                "content": (
                    "### Schritt 4\n"
                    "Baue für jedes Item den relationalen/conditional FP-tree direkt aus den "
                    "Conditional Paths aus Schritt 3. Die Reihenfolge innerhalb eines Prefix-Pfads "
                    "bleibt unverändert. Für jeden Conditional Tree kann derselbe Tree-Builder "
                    "wie beim normalen FP-tree verwendet werden. "
                    "Der Root-Count des Conditional Trees entspricht dem Support des Items, "
                    "für das der Tree gebaut wird."
                ),
            }
        ]

        expected_paths_by_item = self._conditional_paths_by_item()
        frequencies = self.solution.get("frequencies", {})

        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))
            conditional_paths = expected_paths_by_item.get(item, [])
            root_count = int(frequencies.get(item, 0))
            path_rows = [
                [self._format_path(path), str(count)]
                for path, count in conditional_paths
            ] or [["-", "-"]]

            elements.extend([
                {
                    "type": "Table",
                    "title": f"Conditional Paths für {item}",
                    "columns": ["Pfad", "Count"],
                    "rows": path_rows,
                },
                {
                    "type": "FPTreeBuilder",
                    "id": f"fp_conditional_tree_{safe_item}",
                    "label": f"Conditional FP-tree für {item}",
                    "available_items": [x for x in self.solution.get("frequent_items", []) if x != item],
                    "root_count": root_count,
                    "rootCount": root_count,
                },
            ])

        return elements


    def _solution_tables(self):
        solution_elements = [
            {"type": "Text", "content": "Referenzlösung (FP-growth):"},
            {
                "type": "Table",
                "title": "1. Häufigkeiten",
                "columns": ["Item", "Support", "frequent?"],
                "rows": self._frequency_rows(),
            },
            {
                "type": "Table",
                "title": "1. Sortierte Transaktionen",
                "columns": ["Tid", "sortierte frequent Items"],
                "rows": [
                    [f"T{i + 1}", self._format_path(path)]
                    for i, path in enumerate(self.solution["sorted_transactions"])
                ],
            },
            {
                "type": "Table",
                "title": "2. FP-tree als Pfade",
                "columns": ["Pfad", "Count"],
                "rows": [[self._format_path(r["path"]), str(r["count"])] for r in self.solution["main_tree_rows"]] or [["-", "-"]],
            },
            {
                "type": "Table",
                "title": "3. Relationale Pfade / Conditional Pattern Bases",
                "columns": ["Item", "Pfad", "Count"],
                "rows": [
                    [r["item"], self._format_path(r["path"]), str(r["count"])]
                    for r in self.solution["relational_paths"]
                ] or [["-", "-", "-"]],
            },
            {
                "type": "Table",
                "title": "4. Relationale / Conditional FP-trees",
                "columns": ["Item", "Pfad", "Count"],
                "rows": [
                    [r["item"], self._format_path(r["path"]), str(r["count"])]
                    for r in self.solution["relational_trees"]
                ] or [["-", "-", "-"]],
            },
            {
                "type": "Table",
                "title": "5. Frequent Itemsets aus den relationalen Trees",
                "columns": ["Tree/Item", "Itemset", "Support", "P"],
                "rows": [
                    [
                        r["item"],
                        format_itemset(r["itemset"]),
                        str(r["support"]),
                        format_probability(float(r["probability"])),
                    ]
                    for r in self.solution["frequent_itemsets"]
                ] or [["-", "-", "-", "-"]],
            },
        ]
        return solution_elements

    def _generate_steps_layout(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Führe den FP-growth-Algorithmus Schritt für Schritt aus.\n"
                        f"- Grundmenge: {', '.join(self.base_items)}\n"
                        f"- minsup = {self.minsup} ({self.minsup_count} von {len(self.transactions)} Transaktionen)\n"
                        "- Sortiere Items pro Transaktion zuerst nach globaler Häufigkeit absteigend und bei Gleichstand alphabetisch.\n"
                        "- Entferne Items, die nicht frequent sind, bevor der FP-tree aufgebaut wird.\n"
                        "- Für Bäume genügt die Pfad-Darstellung: ein Knoten wird als Pfad vom Root bis zum Knoten mit Count eingetragen."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Transaktionen",
                    "columns": ["Tid", "Items"],
                    "rows": self._transaction_rows(),
                },
                {
                    "type": "Text",
                    "content": "### Schritt 1\nBestimme die globale Häufigkeit und trage die sortierten frequent Items jeder Transaktion ein.",
                },
                {
                    "type": "TableInput",
                    "label": "Item-Häufigkeiten",
                    "columns": ["Item", "Häufigkeit"],
                    "rows": self._prefilled_frequency_rows(),
                },
                {
                    "type": "TableInput",
                    "label": "Sortierte Transaktionen",
                    "columns": ["Tid", "sortierte frequent Items"],
                    "rows": self._prefilled_sorted_transaction_rows(),
                },
            ],
            "view2": [
                {
                    "type": "Text",
                    "content": (
                        "### Schritt 2\n"
                        "Nutze die nach minsup-Eliminierung gefilterten und nach globaler Häufigkeit "
                        "sortierten Transaktionen als Eingabe für den FP-tree."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Sortierte Transaktionen nach minsup-Eliminierung",
                    "columns": ["Tid", "frequent Items in FP-order"],
                    "rows": [
                        [f"T{i + 1}", self._format_path(path)]
                        for i, path in enumerate(self.solution["sorted_transactions"])
                    ],
                },
                {
                    "type": "Text",
                    "content": (
                        "Baue aus diesen sortierten Transaktionen den FP-tree. "
                        "Trage jeden Knoten als Pfad vom Root zum Knoten mit Count ein."
                    ),
                },
                {
                    "type": "FPTreeBuilder",
                    "id": "fp_main_tree",
                    "label": "FP-tree",
                    "available_items": self.base_items,
                }
            ],
            "view3": [
                {
                    "type": "Text",
                    "content": "### Schritt 3\nBilde für jedes Item die relationalen Pfade, also die Prefix-Pfade im FP-tree mit dem Count des jeweiligen Item-Knotens.",
                },
                {
                    "type": "TableInput",
                    "label": "Conditional Paths / Relationale Pfade",
                    "columns": ["Item", "Pfade vom Root zum Item-Knoten + Count"],
                    "rows": self._prefilled_conditional_path_rows(),
                },
            ],
            "view4": self._conditional_tree_builder_elements(),
            "view5": [
                {
                    "type": "Text",
                    "content": (
                        "### Schritt 5\n"
                        "Leite pro Item die frequent Itemsets aus den Conditional Paths ab. "
                        "Das einzelne Item ist immer ein frequent Itemset mit seinem globalen Support. "
                        "Weitere Itemsets entstehen aus den Items, die in den Conditional Paths "
                        "mindestens minsup-mal gemeinsam mit diesem Item vorkommen.\n\n"
                        "**Format:** `D:5, DC:5, DB:3, DCB:3`"
                    ),
                },
                {
                    "type": "TableInput",
                    "label": "Frequent Itemsets aus den Conditional Paths",
                    "columns": ["Item", "Frequent Itemsets + Support"],
                    "rows": self._prefilled_frequent_itemset_rows(),
                },
            ],
            "lastView": self._solution_tables(),
        }

    def _conditional_tree_builder_inputs_only(self):
        elements = []
        frequencies = self.solution.get("frequencies", {})

        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))
            root_count = int(frequencies.get(item, 0))
            elements.append(
                {
                    "type": "FPTreeBuilder",
                    "id": f"fp_conditional_tree_{safe_item}",
                    "label": f"Conditional FP-tree für {item}",
                    "available_items": [x for x in self.solution.get("frequent_items", []) if x != item],
                    "root_count": root_count,
                    "rootCount": root_count,
                }
            )

        return elements

    def _generate_exam_layout(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Exam-Modus: FP-growth\n"
                        f"minsup = {self.minsup} ({self.minsup_count} von {len(self.transactions)} Transaktionen)."
                    ),
                },
                {
                    "type": "Table",
                    "title": "Transaktionen",
                    "columns": ["Tid", "Items"],
                    "rows": self._transaction_rows(),
                },
                {
                    "type": "FPTreeBuilder",
                    "id": "fp_main_tree",
                    "label": "FP-tree",
                    "available_items": self.base_items,
                },
                *self._conditional_tree_builder_inputs_only(),
                {
                    "type": "TableInput",
                    "label": "Frequent Itemsets aus den Conditional Paths",
                    "columns": ["Item", "Frequent Itemsets + Support"],
                    "rows": self._prefilled_frequent_itemset_rows(),
                },
            ],
            "lastView": self._solution_tables(),
        }

    def generate(self):
        return self._generate_exam_layout() if self.mode == "exam" else self._generate_steps_layout()

    def _solution_payload(self, message):
        return {
            "message": message,
            "frequencies": self.solution["frequencies"],
            "sorted_transactions": [self._format_path(p) for p in self.solution["sorted_transactions"]],
            "main_tree_rows": [
                {"path": self._format_path(r["path"]), "count": str(r["count"])}
                for r in self.solution["main_tree_rows"]
            ],
            "relational_paths": [
                {"item": r["item"], "path": self._format_path(r["path"]), "count": str(r["count"])}
                for r in self.solution["relational_paths"]
            ],
            "relational_trees": [
                {"item": r["item"], "path": self._format_path(r["path"]), "count": str(r["count"])}
                for r in self.solution["relational_trees"]
            ],
            "frequent_itemsets": [
                {
                    "item": r["item"],
                    "itemset": format_itemset(r["itemset"]),
                    "support": str(r["support"]),
                    "probability": format_probability(float(r["probability"])),
                }
                for r in self.solution["frequent_itemsets"]
            ],
        }

    def _grade_sorted_transactions(self, user_input):
        results = {}
        expected = self.solution["sorted_transactions"]
        all_correct = True

        for idx, exp_path in enumerate(expected):
            key = f"fp_sort_t{idx + 1}_items"
            actual_path = self._parse_ordered_items((user_input or {}).get(key))
            ok = actual_path == exp_path
            all_correct = all_correct and ok
            results[key] = {"correct": ok, "expected": self._format_path(exp_path)}

        results["fp_sorted_transactions"] = {
            "correct": all_correct,
            "expected": self._solution_payload("Referenzlösung für sortierte Transaktionen"),
        }
        return results

    def _grade_frequency_rows(self, user_input):
        results = {}
        expected = self.solution["frequencies"]
        all_correct = True

        for item, exp_count in expected.items():
            key = f"fp_freq_{item}_count"
            actual_count = self._int_value((user_input or {}).get(key))
            ok = actual_count == exp_count
            all_correct = all_correct and ok
            results[key] = {"correct": ok, "expected": str(exp_count)}

        results["fp_frequencies"] = {
            "correct": all_correct,
            "expected": self._solution_payload("Referenzlösung für Frequenzen"),
        }
        return results

    def _read_rows_payload(self, user_input, key):
        raw = (user_input or {}).get(key, "")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            rows = parsed.get("rows", [])
        elif isinstance(parsed, list):
            rows = parsed
        else:
            rows = []
        return rows if isinstance(rows, list) else []

    def _grade_path_count_rows(self, rows_list, expected_rows, key, include_item=False):
        results = {}
        expected_canon = []
        for row in expected_rows:
            item = row.get("item") if include_item else None
            expected_canon.append((item, tuple(row["path"]), int(row["count"])))
        expected_canon = sorted(expected_canon, key=lambda x: (x[0] or "", x[1], x[2]))
        expected_map = {(item, path): count for item, path, count in expected_canon}

        seen = set()
        actual_canon = []
        duplicate = False

        for row_idx, row in enumerate(rows_list or []):
            row = row or {}
            item = str(row.get("item") or row.get("baseItem") or "").strip() if include_item else None
            path = self._parse_ordered_items(row.get("path"))
            count = self._int_value(row.get("count"))
            row_has_content = bool((item or "") or path or str(row.get("count") or "").strip())

            item_key = f"{key}_r{row_idx}_item"
            path_key = f"{key}_r{row_idx}_path"
            count_key = f"{key}_r{row_idx}_count"

            if not row_has_content:
                continue

            canon_key = (item, path)
            exp_count = expected_map.get(canon_key)
            is_duplicate = canon_key in seen
            seen.add(canon_key)
            duplicate = duplicate or is_duplicate

            row_ok = exp_count is not None and count == exp_count and not is_duplicate
            if include_item:
                results[item_key] = {
                    "correct": bool(item) and exp_count is not None and not is_duplicate,
                    "expected": item if exp_count is not None else "Item mit passendem relationalem Pfad",
                }
            results[path_key] = {
                "correct": exp_count is not None and not is_duplicate,
                "expected": self._format_path(path) if exp_count is not None else "Pfad aus der Referenzlösung",
            }
            results[count_key] = {
                "correct": row_ok,
                "expected": str(exp_count) if exp_count is not None else "Count zum Referenzpfad",
            }
            if exp_count is not None and not is_duplicate:
                actual_canon.append((item, path, count))

        actual_canon = sorted(actual_canon, key=lambda x: (x[0] or "", x[1], x[2]))
        missing = [row for row in expected_canon if (row[0], row[1]) not in {(a[0], a[1]) for a in actual_canon}]
        is_correct = (not duplicate) and actual_canon == expected_canon

        for miss_idx, miss in enumerate(missing):
            item, path, count = miss
            offset = len(rows_list or []) + miss_idx
            if include_item:
                results[f"{key}_r{offset}_item"] = {"correct": False, "expected": item}
            results[f"{key}_r{offset}_path"] = {"correct": False, "expected": self._format_path(path)}
            results[f"{key}_r{offset}_count"] = {"correct": False, "expected": str(count)}

        results[key] = {
            "correct": is_correct,
            "expected": self._solution_payload(f"Referenzlösung für {key}"),
        }
        return results

    def _conditional_paths_by_item(self):
        grouped = {item: [] for item in self.solution.get("mining_items", [])}
        for row in self.solution.get("relational_paths", []):
            item = str(row.get("item", ""))
            path = tuple(row.get("path", ()))
            count = int(row.get("count", 0))
            if path and count > 0:
                grouped.setdefault(item, []).append((path, count))

        # Merge duplicate prefix paths defensively. Usually the FP-tree already
        # stores each prefix/item-node combination uniquely, but this keeps the
        # evaluator stable if equal paths appear more than once.
        merged = {}
        for item, entries in grouped.items():
            path_counts = {}
            for path, count in entries:
                path_counts[path] = path_counts.get(path, 0) + count
            merged[item] = sorted(path_counts.items(), key=lambda x: (x[0], x[1]))
        return merged

    def _format_conditional_paths_compact(self, entries):
        if not entries:
            return "-"
        return ", ".join(f"{''.join(path)}:{count}" for path, count in entries)

    def _parse_conditional_path_text(self, raw):
        text = str(raw or "").strip()
        if not text or text in {"-", "∅", "{}"}:
            return {}

        canonical_items = {str(item).lower(): str(item) for item in self.base_items}
        single_char_items = all(len(str(item)) == 1 for item in self.base_items)
        single_char_lookup = {str(item).lower(): str(item) for item in self.base_items if len(str(item)) == 1}

        parsed = {}
        last_end = 0
        for match in re.finditer(r":\s*(-?\d+)", text):
            path_raw = text[last_end:match.start()].strip(" ,;|\n\t")
            count = self._int_value(match.group(1))
            last_end = match.end()
            if not path_raw or count is None:
                continue

            path = self._parse_path_items(path_raw)
            if path:
                parsed[path] = parsed.get(path, 0) + count

        return parsed

    def _grade_conditional_path_inputs(self, user_input):
        results = {}
        expected_by_item = self._conditional_paths_by_item()
        all_correct = True

        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))
            key = f"conditional_path_{safe_item}_paths"
            expected_entries = expected_by_item.get(item, [])
            expected_map = {path: int(count) for path, count in expected_entries}
            actual_map = self._parse_conditional_path_text((user_input or {}).get(key))

            ok = actual_map == expected_map
            all_correct = all_correct and ok
            results[key] = {
                "correct": ok,
                "expected": self._format_conditional_paths_compact(expected_entries),
            }

        results["fp_conditional_paths"] = {
            "correct": all_correct,
            "expected": self._solution_payload("Referenzlösung für Conditional Paths / relationale Pfade"),
        }
        return results

    def _relational_tree_rows_by_item(self):
        grouped = {item: [] for item in self.solution.get("mining_items", [])}

        for row in self.solution.get("relational_trees", []):
            item = str(row.get("item", ""))
            path = tuple(row.get("path", ()))
            count = int(row.get("count", 0))
            if path and count > 0:
                grouped.setdefault(item, []).append({"path": path, "count": count})

        return grouped

    def _grade_conditional_tree_builders(self, user_input):
        results = {}
        expected_by_item = self._relational_tree_rows_by_item()
        frequencies = self.solution.get("frequencies", {})
        all_correct = True

        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))
            key = f"fp_conditional_tree_{safe_item}"
            expected_rows = expected_by_item.get(item, [])
            expected_root_count = int(frequencies.get(item, 0))

            partial = self._grade_fp_tree(
                user_input,
                key,
                expected_rows,
                expected_root_count=expected_root_count,
            )
            results.update(partial)
            all_correct = all_correct and bool(partial.get(key, {}).get("correct"))

        results["fp_relational_trees"] = {
            "correct": all_correct,
            "expected": self._solution_payload("Referenzlösung für relationale / conditional FP-trees"),
        }
        return results


    def _frequent_itemsets_by_item(self):
        grouped = {item: [] for item in self.solution.get("mining_items", [])}

        for row in self.solution.get("frequent_itemsets", []):
            item = str(row.get("item", ""))
            itemset = tuple(row.get("itemset", ()))
            support = int(row.get("support", 0))
            if itemset and support > 0:
                grouped.setdefault(item, []).append((itemset, support))

        for item, entries in grouped.items():
            # Defensive merge: same itemset should only occur once in the suffix-mining order.
            # Compare by membership so inputs like DC and CD are both accepted.
            merged = {}
            for itemset, support in entries:
                key = frozenset(itemset)
                if key not in merged:
                    merged[key] = (itemset, support)
                else:
                    kept_itemset, kept_support = merged[key]
                    merged[key] = (kept_itemset, max(kept_support, support))
            grouped[item] = sorted(
                merged.values(),
                key=lambda x: (len(x[0]), tuple(str(part) for part in x[0])),
            )

        return grouped

    def _format_itemset_compact(self, itemset):
        if not itemset:
            return "-"
        if all(len(str(item)) == 1 for item in self.base_items):
            return "".join(str(item) for item in itemset)
        return ",".join(str(item) for item in itemset)

    def _format_itemsets_compact(self, entries):
        if not entries:
            return "-"
        return ", ".join(
            f"{self._format_itemset_compact(itemset)}:{support}"
            for itemset, support in entries
        )

    def _parse_itemset_support_text(self, raw):
        text = str(raw or "").strip()
        if not text or text in {"-", "∅", "{}"}:
            return {}

        canonical_items = {str(item).lower(): str(item) for item in self.base_items}
        single_char_items = all(len(str(item)) == 1 for item in self.base_items)
        single_char_lookup = {
            str(item).lower(): str(item)
            for item in self.base_items
            if len(str(item)) == 1
        }

        parsed = {}
        last_end = 0
        for match in re.finditer(r":\s*(-?\d+)", text):
            itemset_raw = text[last_end:match.start()].strip(" ,;|\n\t")
            support = self._int_value(match.group(1))
            last_end = match.end()
            if not itemset_raw or support is None:
                continue

            itemset = frozenset(self._parse_path_items(itemset_raw))
            if itemset:
                parsed[itemset] = parsed.get(itemset, 0) + support

        return parsed

    def _grade_frequent_itemset_inputs(self, user_input):
        results = {}
        expected_by_item = self._frequent_itemsets_by_item()
        all_correct = True

        for item in self.solution.get("mining_items", []):
            safe_item = re.sub(r"[^a-zA-Z0-9_]+", "_", str(item))
            key = f"fp_itemsets_{safe_item}_sets"
            expected_entries = expected_by_item.get(item, [])
            expected_map = {frozenset(itemset): int(support) for itemset, support in expected_entries}
            actual_map = self._parse_itemset_support_text((user_input or {}).get(key))

            ok = actual_map == expected_map
            all_correct = all_correct and ok
            results[key] = {
                "correct": ok,
                "expected": self._format_itemsets_compact(expected_entries),
            }

        results["fp_frequent_itemsets"] = {
            "correct": all_correct,
            "expected": self._solution_payload("Referenzlösung für frequent Itemsets"),
        }
        return results


    def _grade_frequent_itemsets(self, rows_list, key):
        expected = []
        for row in self.solution["frequent_itemsets"]:
            expected.append(
                (
                    row["item"],
                    tuple(row["itemset"]),
                    int(row["support"]),
                    format_probability(float(row["probability"])),
                )
            )
        expected = sorted(expected, key=lambda x: (x[0], x[1]))
        expected_map = {(item, itemset): (support, prob) for item, itemset, support, prob in expected}

        results = {}
        seen = set()
        actual = []
        duplicate = False

        for row_idx, row in enumerate(rows_list or []):
            row = row or {}
            item = str(row.get("item") or row.get("baseItem") or "").strip()
            item_raw = str(row.get("itemset") or "").strip()
            support_raw = str(row.get("support") or "").strip()
            prob_raw = str(row.get("probability") or "").strip()
            row_has_content = bool(item or item_raw or support_raw or prob_raw)
            if not row_has_content:
                continue

            itemset = parse_itemset_text(item_raw)
            support = self._int_value(row.get("support"))
            prob = parse_probability(row.get("probability"))
            canon_key = (item, itemset)
            exp = expected_map.get(canon_key)
            is_duplicate = canon_key in seen
            seen.add(canon_key)
            duplicate = duplicate or is_duplicate

            item_ok = exp is not None and not is_duplicate
            support_ok = item_ok and support == exp[0]
            prob_ok = item_ok and self._prob_matches(prob, float(exp[1]))

            results[f"{key}_r{row_idx}_item"] = {
                "correct": item_ok,
                "expected": item if exp is not None else "Tree/Item aus der Referenzlösung",
            }
            results[f"{key}_r{row_idx}_itemset"] = {
                "correct": item_ok,
                "expected": format_itemset(itemset) if exp is not None else "Itemset aus der Referenzlösung",
            }
            results[f"{key}_r{row_idx}_support"] = {
                "correct": support_ok,
                "expected": str(exp[0]) if exp is not None else "Support zum Itemset",
            }
            results[f"{key}_r{row_idx}_probability"] = {
                "correct": prob_ok,
                "expected": exp[1] if exp is not None else "P zum Itemset",
            }

            if item_ok:
                actual.append((item, itemset, support, None if prob is None else format_probability(prob)))

        actual = sorted(actual, key=lambda x: (x[0], x[1]))
        actual_keys = {(a[0], a[1]) for a in actual}
        missing = [row for row in expected if (row[0], row[1]) not in actual_keys]
        is_correct = (not duplicate) and actual == expected

        for miss_idx, miss in enumerate(missing):
            offset = len(rows_list or []) + miss_idx
            item, itemset, support, prob = miss
            results[f"{key}_r{offset}_item"] = {"correct": False, "expected": item}
            results[f"{key}_r{offset}_itemset"] = {"correct": False, "expected": format_itemset(itemset)}
            results[f"{key}_r{offset}_support"] = {"correct": False, "expected": str(support)}
            results[f"{key}_r{offset}_probability"] = {"correct": False, "expected": prob}

        results[key] = {
            "correct": is_correct,
            "expected": self._solution_payload("Referenzlösung für frequent Itemsets"),
        }
        return results

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}
        results.update(self._grade_sorted_transactions(user_input))
        results.update(self._grade_frequency_rows(user_input))

        results.update(
            self._grade_fp_tree(
                user_input,
                "fp_main_tree",
                self.solution["main_tree_rows"],
            )
        )

        if "fp_relational_paths" in user_input:
            relational_path_rows = self._read_rows_payload(user_input, "fp_relational_paths")
            results.update(
                self._grade_path_count_rows(
                    relational_path_rows,
                    self.solution["relational_paths"],
                    "fp_relational_paths",
                    include_item=True,
                )
            )
        else:
            results.update(self._grade_conditional_path_inputs(user_input))

        if "fp_relational_trees" in user_input:
            relational_tree_rows = self._read_rows_payload(user_input, "fp_relational_trees")
            results.update(
                self._grade_path_count_rows(
                    relational_tree_rows,
                    self.solution["relational_trees"],
                    "fp_relational_trees",
                    include_item=True,
                )
            )
        else:
            results.update(self._grade_conditional_tree_builders(user_input))

        if "fp_frequent_itemsets" in user_input:
            itemset_rows = self._read_rows_payload(user_input, "fp_frequent_itemsets")
            results.update(self._grade_frequent_itemsets(itemset_rows, "fp_frequent_itemsets"))
        else:
            results.update(self._grade_frequent_itemset_inputs(user_input))
        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        results = {}

        results.update(
            self._grade_fp_tree(
                user_input,
                "fp_main_tree",
                self.solution["main_tree_rows"],
            )
        )

        results.update(self._grade_conditional_tree_builders(user_input))
        results.update(self._grade_frequent_itemset_inputs(user_input))

        section_keys = ["fp_main_tree", "fp_relational_trees", "fp_frequent_itemsets"]
        overall = all(results.get(key, {}).get("correct") for key in section_keys)
        results["fp_growth_exam"] = {
            "correct": overall,
            "expected": self._solution_payload(
                "Alle FP-growth Exam-Eingaben korrekt."
                if overall
                else "Mindestens eine FP-growth Exam-Eingabe ist fehlerhaft."
            ),
        }
        return results

    def evaluate(self, user_input):
        return self._evaluate_exam(user_input) if self.mode == "exam" else self._evaluate_steps(user_input)

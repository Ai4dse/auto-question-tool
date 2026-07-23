import itertools
import random
import re

from app.question_types.fp_tree_eval_helpers import (
    evaluate_fp_tree,
    parse_fp_tree_payload,
    tree_from_path_count_rows,
)


DIFFICULTY_SETTINGS = {
    "easy": {
        "num_columns": 3,
        "num_rows": 3,
        "max_values_per_column": 2,
        "max_ucc_size": 2,
        "max_ucc_count": 3,
        "max_non_unique_count": 3,
    },
    "medium": {
        "num_columns": 4,
        "num_rows": 5,
        "max_values_per_column": 3,
        "max_ucc_size": 3,
        "max_ucc_count": 4,
        "max_non_unique_count": 6,
    },
    "hard": {
        "num_columns": 5,
        "num_rows": 5,
        "max_values_per_column": 4,
        "max_ucc_size": 4,
        "max_ucc_count": 6,
        "max_non_unique_count": 8,
    },
}


class UCCDiscoveryQuestion:
    """Discover minimal UCCs with three alternative algorithms.

    Supported modes:
    - ``agree_sets``: agree sets, complements/difference sets, minimal hitting sets
    - ``apriori``: bottom-up traversal of the column-combination lattice
    - ``gordian``: GORDIAN-style prefix trees built from column values

    All modes use the same generated relation for the same seed and difficulty.
    Different seeds generate randomized equality distributions, while rejection
    checks guarantee at least one minimal UCC and one non-empty maximal agree set.
    """

    ATTRIBUTE_POOL = ("A", "B", "C", "D", "E")

    MODE_ALIASES = {
        "agree": "agree_sets",
        "agree_set": "agree_sets",
        "agree_sets": "agree_sets",
        "difference_sets": "agree_sets",
        "apriori": "apriori",
        "lattice": "apriori",
        "gordian": "gordian",
        "fp_tree": "gordian",
        "fptree": "gordian",
        "fp_growth": "gordian",
        "fpgrowth": "gordian",
    }

    def __init__(self, seed=None, difficulty="easy", mode="agree_sets", Mode=None):
        self.difficulty = str(difficulty or "easy").strip().lower()
        self.config = DIFFICULTY_SETTINGS.get(
            self.difficulty,
            DIFFICULTY_SETTINGS["easy"],
        )

        requested_mode = Mode if Mode is not None else mode
        normalized_mode = str(requested_mode or "agree_sets").strip().lower().replace("-", "_")
        self.mode = self.MODE_ALIASES.get(normalized_mode, "agree_sets")

        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.attributes = []
        self.rows = []
        self.agree_sets = {}
        self.maximal_agree_sets = []
        self.difference_sets = []
        self.minimal_uccs = []
        self.apriori_levels = []
        self.main_tree_rows = []

        self._initialize_instance()

    # ------------------------------------------------------------------
    # Instance generation and core algorithms
    # ------------------------------------------------------------------

    def _initialize_instance(self):
        self.attributes = list(
            self.ATTRIBUTE_POOL[: self.config["num_columns"]]
        )

        structural_rows = self._generate_structural_relation()
        self.rows = self._format_structural_rows(structural_rows)

        self.agree_sets = {
            (left, right): self._agree_set(left, right)
            for left, right in itertools.combinations(range(len(self.rows)), 2)
        }
        self.maximal_agree_sets = self._maximal_sets(self.agree_sets.values())
        self.difference_sets = sorted(
            {
                tuple(attr for attr in self.attributes if attr not in agree_set)
                for agree_set in self.maximal_agree_sets
            },
            key=lambda itemset: (len(itemset), itemset),
        )
        self.minimal_uccs = self._discover_minimal_uccs()
        self.apriori_levels = self._build_apriori_levels()
        self.main_tree_rows = self._tree_rows(self.attributes)

        # Defensive validation: all three derivations must describe the same
        # search problem, and the full relation must not contain duplicate rows.
        maximal_non_unique = self._maximal_non_unique_combinations()
        if set(maximal_non_unique) != set(self.maximal_agree_sets):
            raise ValueError("Generated relation has inconsistent maximal non-unique sets.")
        if not self._is_unique(self.attributes):
            raise ValueError("Generated relation contains duplicate full rows.")
        if not self.minimal_uccs:
            raise ValueError("Generated relation has no minimal UCC.")
        if not self.maximal_agree_sets:
            raise ValueError("Generated relation has no maximal agree set.")
        if not any(len(agree_set) > 0 for agree_set in self.maximal_agree_sets):
            raise ValueError("Generated relation has no non-empty maximal agree set.")

    def _generate_structural_relation(self):
        """Generate a genuinely new equality pattern for the selected difficulty.

        The seed keeps the result reproducible, but unlike the old implementation
        the generator does not start from one fixed matrix. Candidates are drawn
        randomly and retained only when they form a useful UCC exercise.
        """
        num_columns = int(self.config["num_columns"])
        num_rows = int(self.config["num_rows"])
        max_values = min(
            int(self.config["max_values_per_column"]),
            num_rows - 1,
        )

        for _attempt in range(2000):
            columns = []

            for _column_index in range(num_columns):
                domain_size = self.rng.randint(2, max_values)
                raw_values = [
                    self.rng.randrange(domain_size)
                    for _ in range(num_rows)
                ]

                distinct_values = set(raw_values)
                # Every column should provide information, but no singleton
                # column should already be a UCC.
                if len(distinct_values) < 2 or len(distinct_values) == num_rows:
                    break

                # Canonicalize the structural labels. Their names are randomized
                # separately after a valid equality pattern has been selected.
                canonical_map = {}
                canonical_column = []
                for value in raw_values:
                    if value not in canonical_map:
                        canonical_map[value] = len(canonical_map) + 1
                    canonical_column.append(canonical_map[value])
                columns.append(canonical_column)

            if len(columns) != num_columns:
                continue

            candidate_rows = [
                tuple(columns[column][row] for column in range(num_columns))
                for row in range(num_rows)
            ]

            if len(set(candidate_rows)) != num_rows:
                continue

            minimal_uccs = self._matrix_minimal_uccs(candidate_rows)
            if not minimal_uccs:
                continue
            if any(len(itemset) == 1 for itemset in minimal_uccs):
                continue
            if max(len(itemset) for itemset in minimal_uccs) > self.config["max_ucc_size"]:
                continue
            if len(minimal_uccs) > self.config["max_ucc_count"]:
                continue

            maximal_agree_sets = self._matrix_maximal_agree_sets(candidate_rows)
            if not maximal_agree_sets:
                continue
            if not any(len(agree_set) > 0 for agree_set in maximal_agree_sets):
                continue

            maximal_non_unique = self._matrix_maximal_non_unique(candidate_rows)
            if not maximal_non_unique:
                continue
            if len(maximal_non_unique) > self.config["max_non_unique_count"]:
                continue

            # For a relation without duplicate full tuples, maximal agree sets
            # and maximal non-unique column combinations describe the same
            # structural boundary and must therefore coincide.
            if set(maximal_agree_sets) != set(maximal_non_unique):
                continue

            return candidate_rows

        raise ValueError(
            f"Could not generate a valid {self.difficulty} UCC relation after 2000 attempts."
        )

    def _format_structural_rows(self, structural_rows):
        """Shuffle display order and map structural values to column-specific labels."""
        matrix_rows = list(structural_rows)
        self.rng.shuffle(matrix_rows)

        value_maps = {}
        for column_index, attribute in enumerate(self.attributes):
            structural_values = sorted({row[column_index] for row in matrix_rows})
            displayed_values = list(range(1, len(structural_values) + 1))
            self.rng.shuffle(displayed_values)
            value_maps[attribute] = dict(zip(structural_values, displayed_values))

        rows = []
        for matrix_row in matrix_rows:
            row = {}
            for column_index, attribute in enumerate(self.attributes):
                displayed_value = value_maps[attribute][matrix_row[column_index]]
                row[attribute] = f"{attribute.lower()}{displayed_value}"
            rows.append(row)
        return rows

    def _matrix_projection_counts(self, matrix_rows, column_indices):
        counts = {}
        for row in matrix_rows:
            key = tuple(row[index] for index in column_indices)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _matrix_is_unique(self, matrix_rows, column_indices):
        counts = self._matrix_projection_counts(matrix_rows, column_indices)
        return max(counts.values(), default=0) <= 1

    def _matrix_minimal_uccs(self, matrix_rows):
        result = []
        num_columns = len(matrix_rows[0]) if matrix_rows else 0
        for size in range(1, num_columns + 1):
            for candidate in itertools.combinations(range(num_columns), size):
                candidate_set = set(candidate)
                if any(set(ucc).issubset(candidate_set) for ucc in result):
                    continue
                if self._matrix_is_unique(matrix_rows, candidate):
                    result.append(candidate)
        return result

    def _matrix_maximal_non_unique(self, matrix_rows):
        non_unique = []
        num_columns = len(matrix_rows[0]) if matrix_rows else 0
        for size in range(1, num_columns + 1):
            for candidate in itertools.combinations(range(num_columns), size):
                if not self._matrix_is_unique(matrix_rows, candidate):
                    non_unique.append(candidate)
        return self._maximal_sets(non_unique)

    def _matrix_maximal_agree_sets(self, matrix_rows):
        """Return maximal agree sets for the structural integer matrix.

        A column index belongs to the agree set of two rows when both rows have
        the same value in that column. At least one non-empty maximal agree set
        is required so the agree-set and GORDIAN modes have a meaningful
        non-unique pattern to discover.
        """
        if not matrix_rows:
            return []

        agree_sets = []
        num_columns = len(matrix_rows[0])
        for left, right in itertools.combinations(range(len(matrix_rows)), 2):
            agree_sets.append(tuple(
                column_index
                for column_index in range(num_columns)
                if matrix_rows[left][column_index] == matrix_rows[right][column_index]
            ))

        return self._maximal_sets(agree_sets)

    def _agree_set(self, left_index, right_index):
        left = self.rows[left_index]
        right = self.rows[right_index]
        return tuple(
            attr for attr in self.attributes
            if left[attr] == right[attr]
        )

    @staticmethod
    def _maximal_sets(itemsets):
        unique_sets = {tuple(itemset) for itemset in itemsets}
        maximal = []
        for itemset in unique_sets:
            itemset_values = set(itemset)
            if not any(
                itemset_values < set(other)
                for other in unique_sets
            ):
                maximal.append(itemset)
        return sorted(maximal, key=lambda value: (len(value), value))

    def _projection_counts(self, columns):
        columns = tuple(columns)
        counts = {}
        for row in self.rows:
            key = tuple(row[column] for column in columns)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _distinct_count(self, columns):
        return len(self._projection_counts(columns))

    def _max_duplicate_count(self, columns):
        counts = self._projection_counts(columns)
        return max(counts.values(), default=0)

    def _is_unique(self, columns):
        return self._max_duplicate_count(columns) <= 1

    def _discover_minimal_uccs(self):
        result = []
        for size in range(1, len(self.attributes) + 1):
            for candidate in itertools.combinations(self.attributes, size):
                candidate_set = set(candidate)
                if any(set(ucc).issubset(candidate_set) for ucc in result):
                    continue
                if self._is_unique(candidate):
                    result.append(candidate)
        return sorted(result, key=lambda value: (len(value), value))

    def _maximal_non_unique_combinations(self):
        non_unique = []
        for size in range(1, len(self.attributes) + 1):
            for candidate in itertools.combinations(self.attributes, size):
                if not self._is_unique(candidate):
                    non_unique.append(candidate)
        return self._maximal_sets(non_unique)

    def _build_apriori_levels(self):
        levels = []
        known_uccs = []

        for size in range(1, len(self.attributes) + 1):
            tested = []
            pruned = []

            for candidate in itertools.combinations(self.attributes, size):
                candidate_set = set(candidate)
                containing_ucc = next(
                    (
                        ucc for ucc in known_uccs
                        if set(ucc).issubset(candidate_set)
                    ),
                    None,
                )
                if containing_ucc is not None:
                    pruned.append({
                        "itemset": candidate,
                        "reason": containing_ucc,
                    })
                    continue

                unique = self._is_unique(candidate)
                tested.append({
                    "itemset": candidate,
                    "distinct_count": self._distinct_count(candidate),
                    "max_duplicate_count": self._max_duplicate_count(candidate),
                    "unique": unique,
                })
                if unique:
                    known_uccs.append(candidate)

            if tested or pruned:
                levels.append({
                    "k": size,
                    "tested": tested,
                    "pruned": pruned,
                })

            if not tested:
                break

        return levels

    def _tree_rows(self, columns):
        """Return every prefix-tree node as ``{path, count}``.

        Paths contain the actual values from the selected table columns in the
        fixed left-to-right column order. Equal row prefixes share nodes.
        """
        columns = tuple(columns)
        root = {"children": {}}

        for row in self.rows:
            node = root
            for column in columns:
                value = row[column]
                children = node["children"]
                if value not in children:
                    children[value] = {"count": 0, "children": {}}
                node = children[value]
                node["count"] += 1

        result = []

        def visit(node, prefix):
            children = node.get("children", {})
            ordered = sorted(
                children.items(),
                key=lambda entry: (-entry[1]["count"], entry[0]),
            )
            for value, child in ordered:
                path = prefix + (value,)
                result.append({"path": path, "count": int(child["count"])})
                visit(child, path)

        visit(root, tuple())
        return result

    # ------------------------------------------------------------------
    # Formatting and parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _format_itemset(itemset):
        return "{" + ",".join(itemset) + "}" if itemset else "∅"

    @staticmethod
    def _format_compact(itemset):
        return "".join(itemset) if itemset else "∅"

    def _format_collection(self, itemsets):
        return "; ".join(self._format_compact(itemset) for itemset in itemsets) or "∅"

    @staticmethod
    def _itemset_slug(itemset):
        return "_".join(itemset) if itemset else "empty"

    @staticmethod
    def _bool_value(value):
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {
            "1", "true", "yes", "ja", "on", "unique", "eindeutig"
        }

    @staticmethod
    def _int_value(value):
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def _parse_itemset(self, value):
        text = str(value or "").upper()
        return tuple(
            attr for attr in self.attributes
            if re.search(rf"(?<![A-Z0-9]){re.escape(attr)}(?![A-Z0-9])", text)
            or attr in re.sub(r"[^A-Z]", "", text)
        )

    def _parse_itemset_collection(self, value):
        text = str(value or "").strip()
        if not text or text in {"-", "∅", "{}"}:
            return set()

        braced = re.findall(r"[\{\[]([^\}\]]+)[\}\]]", text)
        if braced:
            raw_groups = braced
        elif any(separator in text for separator in [";", "|", "\n"]):
            raw_groups = re.split(r"[;|\n]+", text)
        else:
            # Compact notation such as "AC, BD" or "AC BD".
            raw_groups = re.findall(r"[A-Za-z]+", text)

        parsed = set()
        for raw_group in raw_groups:
            itemset = self._parse_itemset(raw_group)
            if itemset:
                parsed.add(itemset)
        return parsed

    def _available_values(self, columns):
        values = []
        seen = set()
        for column in columns:
            for row in self.rows:
                value = row[column]
                if value not in seen:
                    seen.add(value)
                    values.append(value)
        return values

    def _relation_rows(self):
        return [
            [f"t{index + 1}"] + [row[attr] for attr in self.attributes]
            for index, row in enumerate(self.rows)
        ]

    def _common_relation_elements(self):
        return [
            {
                "type": "Table",
                "title": "Relation R",
                "columns": ["Tupel"] + self.attributes,
                "rows": self._relation_rows(),
            }
        ]

    # ------------------------------------------------------------------
    # Agree-set mode
    # ------------------------------------------------------------------

    def _agree_pair_rows(self):
        rows = []
        for left, right in itertools.combinations(range(len(self.rows)), 2):
            pair_slug = f"t{left + 1}_t{right + 1}"
            rows.append({
                "id": f"ucc_agree_{pair_slug}",
                "fields": [
                    f"t{left + 1}, t{right + 1}",
                    {"kind": "input", "id": f"ucc_agree_{pair_slug}_set"},
                    {"kind": "input", "id": f"ucc_agree_{pair_slug}_complement"},
                ],
            })
        return rows

    def _generate_agree_sets_layout(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Bestimme minimale Unique Column Combinations mit dem Agree-Set-Ansatz.\n\n"
                        "Für zwei Tupel gilt $$agree(t_i,t_j)=\\{A\\mid t_i[A]=t_j[A]\\}$$. "
                        "Das Komplement ist das zugehörige Difference Set. "
                        "Gib Attributmengen kompakt oder in Mengenklammern ein, z. B. `AC` oder `{A,C}`."
                    ),
                },
                *self._common_relation_elements(),
                {
                    "type": "TableInput",
                    "label": "Agree Sets und Komplemente",
                    "columns": ["Tupelpaar", "Agree Set", "Komplement / Difference Set"],
                    "rows": self._agree_pair_rows(),
                },
            ],
            "view2": [
                {
                    "type": "Text",
                    "content": (
                        "### Maximal relevante Agree Sets\n"
                        "Entferne alle Agree Sets, die echte Teilmengen eines anderen Agree Sets sind. "
                        "Bilde anschließend die Komplemente dieser maximalen Agree Sets.\n\n"
                        "Mehrere Mengen bitte mit Semikolon trennen, z. B. `AB; AD; BC`."
                    ),
                },
                {
                    "type": "TextInput",
                    "id": "ucc_agree_maximal_sets",
                    "label": "Maximale Agree Sets",
                },
                {
                    "type": "TextInput",
                    "id": "ucc_agree_difference_sets",
                    "label": "Komplemente / relevante Difference Sets",
                },
            ],
            "view3": [
                {
                    "type": "Text",
                    "content": (
                        "### Minimale UCCs\n"
                        "Bestimme die minimalen Hitting Sets der relevanten Difference Sets. "
                        "Diese minimalen Hitting Sets sind die minimalen UCCs."
                    ),
                },
                {
                    "type": "TextInput",
                    "id": "ucc_agree_final_uccs",
                    "label": "Minimale UCCs",
                },
            ],
            "lastView": self._agree_solution_elements(),
        }

    def _agree_solution_elements(self):
        pair_rows = []
        for (left, right), agree_set in sorted(self.agree_sets.items()):
            complement = tuple(attr for attr in self.attributes if attr not in agree_set)
            pair_rows.append([
                f"t{left + 1}, t{right + 1}",
                self._format_itemset(agree_set),
                self._format_itemset(complement),
            ])

        return [
            {"type": "Text", "content": "Referenzlösung: Agree-Set-Ansatz"},
            {
                "type": "Table",
                "title": "Agree Sets",
                "columns": ["Tupelpaar", "Agree Set", "Komplement"],
                "rows": pair_rows,
            },
            {
                "type": "Table",
                "title": "Maximale Agree Sets und relevante Difference Sets",
                "columns": ["Maximales Agree Set", "Komplement"],
                "rows": [
                    [
                        self._format_itemset(agree_set),
                        self._format_itemset(
                            tuple(attr for attr in self.attributes if attr not in agree_set)
                        ),
                    ]
                    for agree_set in self.maximal_agree_sets
                ],
            },
            {
                "type": "Text",
                "content": f"Minimale UCCs: **{self._format_collection(self.minimal_uccs)}**",
            },
        ]

    # ------------------------------------------------------------------
    # Apriori mode
    # ------------------------------------------------------------------

    def _apriori_level_rows(self, level):
        rows = []
        k = level["k"]
        for entry in level["tested"]:
            itemset = entry["itemset"]
            slug = self._itemset_slug(itemset)
            rows.append({
                "id": f"ucc_apr_l{k}_{slug}",
                "fields": [
                    self._format_itemset(itemset),
                    {"kind": "input", "id": f"ucc_apr_l{k}_{slug}_distinct"},
                    {"kind": "input", "id": f"ucc_apr_l{k}_{slug}_max_count"},
                    {"kind": "checkbox", "id": f"ucc_apr_l{k}_{slug}_unique"},
                ],
            })
        return rows

    def _generate_apriori_layout(self):
        layout = {}
        for view_index, level in enumerate(self.apriori_levels, start=1):
            k = level["k"]
            elements = []
            if view_index == 1:
                elements.extend([
                    {
                        "type": "Text",
                        "content": (
                            "Bestimme minimale UCCs durch eine Apriori-artige Traversierung des Attributgitters.\n\n"
                            "Eine Kombination ist eindeutig, wenn die Anzahl verschiedener Projektionen der "
                            "Anzahl der Tupel entspricht. Sobald eine minimale UCC gefunden wurde, werden alle "
                            "ihre Obermengen verworfen."
                        ),
                    },
                    *self._common_relation_elements(),
                ])

            elements.append({
                "type": "Text",
                "content": f"### Level {k}\nBewerte alle noch nicht durch eine bekannte UCC geprunten Kandidaten der Größe {k}.",
            })

            if level["tested"]:
                elements.append({
                    "type": "TableInput",
                    "label": f"C{k}: UCC-Kandidaten",
                    "columns": [
                        "Attributkombination",
                        "Anzahl verschiedener Projektionen",
                        "Maximale Gruppenhäufigkeit",
                        "eindeutig?",
                    ],
                    "rows": self._apriori_level_rows(level),
                })
            else:
                elements.append({
                    "type": "Text",
                    "content": "Alle Kandidaten dieses Levels werden durch bereits gefundene minimale UCCs geprunt.",
                })

            if level["pruned"]:
                elements.append({
                    "type": "TextInput",
                    "id": f"ucc_apr_l{k}_pruned",
                    "label": f"In Level {k} geprunte Kandidaten",
                })

            layout[f"view{view_index}"] = elements

        final_view = len(self.apriori_levels) + 1
        layout[f"view{final_view}"] = [
            {
                "type": "Text",
                "content": "Gib alle gefundenen minimalen UCCs an.",
            },
            {
                "type": "TextInput",
                "id": "ucc_apr_final_uccs",
                "label": "Minimale UCCs",
            },
        ]
        layout["lastView"] = self._apriori_solution_elements()
        return layout

    def _apriori_solution_elements(self):
        elements = [{"type": "Text", "content": "Referenzlösung: Apriori-artige UCC-Suche"}]
        for level in self.apriori_levels:
            rows = [
                [
                    self._format_itemset(entry["itemset"]),
                    str(entry["distinct_count"]),
                    str(entry["max_duplicate_count"]),
                    str(bool(entry["unique"])),
                ]
                for entry in level["tested"]
            ]
            elements.append({
                "type": "Table",
                "title": f"Level {level['k']}",
                "columns": ["Kandidat", "Distinct", "Max Count", "eindeutig?"],
                "rows": rows or [["-", "-", "-", "-"]],
            })
            if level["pruned"]:
                elements.append({
                    "type": "Text",
                    "content": (
                        f"Geprunt in Level {level['k']}: "
                        + self._format_collection(entry["itemset"] for entry in level["pruned"])
                    ),
                })
        elements.append({
            "type": "Text",
            "content": f"Minimale UCCs: **{self._format_collection(self.minimal_uccs)}**",
        })
        return elements

    # ------------------------------------------------------------------
    # GORDIAN mode
    # ------------------------------------------------------------------

    @staticmethod
    def _format_path(path):
        return ", ".join(path) if path else "-"

    @staticmethod
    def _set_tree_root_count(tree, root_count):
        if tree is None or root_count is None:
            return tree
        root_count = int(root_count)
        if isinstance(tree, dict):
            if "root" in tree:
                if isinstance(tree.get("root"), dict):
                    tree["root"]["count"] = root_count
                elif tree.get("root") is not None and hasattr(tree["root"], "count"):
                    setattr(tree["root"], "count", root_count)
            else:
                tree["count"] = root_count
            return tree
        if hasattr(tree, "count"):
            setattr(tree, "count", root_count)
        elif hasattr(tree, "root") and hasattr(tree.root, "count"):
            setattr(tree.root, "count", root_count)
        return tree

    def _generate_gordian_layout(self):
        return {
            "view1": [
                {
                    "type": "Text",
                    "content": (
                        "Bestimme minimale UCCs mit einem GORDIAN-artigen Prefix-Tree.\n\n"
                        f"Spaltenreihenfolge im Tree: **{' → '.join(self.attributes)}**. "
                        "Füge für jedes Tupel genau einen Pfad aus seinen tatsächlichen Spaltenwerten ein. "
                        "Gemeinsame Präfixe teilen sich Knoten; der Count eines Knotens entspricht der "
                        "Anzahl der Tupel mit diesem vollständigen Präfix.\n\n"
                        "Eine Attributkombination ist **nicht eindeutig**, wenn nach Projektion auf diese "
                        "Attribute mindestens zwei Tupel denselben Wertepfad besitzen. Im Prefix-Tree kann "
                        "dies durch gedankliches Auslassen nicht ausgewählter Spalten und Zusammenführen "
                        "gleicher verbleibender Pfade erkannt werden. Eine nicht-eindeutige Kombination ist "
                        "**maximal**, wenn jede echte Obermenge eindeutig ist."
                    ),
                },
                *self._common_relation_elements(),
                {
                    "type": "FPTreeBuilder",
                    "id": "ucc_gordian_main_tree",
                    "label": "GORDIAN Prefix-Tree der vollständigen Tupel",
                    "available_items": self._available_values(self.attributes),
                    "root_count": len(self.rows),
                    "rootCount": len(self.rows),
                },
            ],
            "view2": [
                {
                    "type": "Text",
                    "content": (
                        "Bestimme aus gemeinsamen Pfaden und durch gedankliche Projektion/Merging die "
                        "maximalen nicht-eindeutigen Attributkombinationen. Eine Kombination gehört genau "
                        "dann zur gesuchten Menge, wenn mindestens zwei Tupel auf ihr übereinstimmen und "
                        "jede echte Obermenge eindeutig ist.\n\n"
                        "Mehrere Mengen mit Semikolon trennen, z. B. `AB; CD`."
                    ),
                },
                {
                    "type": "TextInput",
                    "id": "ucc_gordian_max_non_unique",
                    "label": "Maximale nicht-eindeutige Kombinationen",
                },
            ],
            "view3": [
                {
                    "type": "Text",
                    "content": (
                        "Leite nun direkt aus den maximal nicht-eindeutigen Kombinationen die minimalen "
                        "UCCs ab. Bilde dazu die Komplemente "
                        "der maximal nicht-eindeutigen Kombinationen. Gesucht sind die minimalen Hitting "
                        "Sets dieser Komplemente: Jede UCC muss aus jeder Komplementmenge mindestens ein "
                        "Attribut enthalten. Minimal bedeutet, dass nach Entfernen eines Attributs nicht "
                        "mehr alle Komplementmengen getroffen werden.\n\n"
                        "Mehrere Mengen mit Semikolon trennen."
                    ),
                },
                {
                    "type": "TextInput",
                    "id": "ucc_gordian_final_uccs",
                    "label": "Minimale UCCs",
                },
            ],
            "lastView": self._gordian_solution_elements(),
        }

    def _gordian_solution_elements(self):
        return [
            {"type": "Text", "content": "Referenzlösung: GORDIAN-artige Prefix-Tree-Suche"},
            {
                "type": "Table",
                "title": "Vollständiger Prefix-Tree als Pfade",
                "columns": ["Pfad", "Count"],
                "rows": [
                    [self._format_path(entry["path"]), str(entry["count"])]
                    for entry in self.main_tree_rows
                ],
            },
            {
                "type": "Text",
                "content": (
                    "Maximale nicht-eindeutige Kombinationen: "
                    f"**{self._format_collection(self.maximal_agree_sets)}**"
                ),
            },
            {
                "type": "Text",
                "content": (
                    "Komplemente der maximal nicht-eindeutigen Kombinationen: "
                    f"**{self._format_collection(self.difference_sets)}**"
                ),
            },
            {
                "type": "Text",
                "content": f"Minimale UCCs: **{self._format_collection(self.minimal_uccs)}**",
            },
        ]

    # ------------------------------------------------------------------
    # Public generation API
    # ------------------------------------------------------------------

    def generate(self):
        if self.mode == "apriori":
            return self._generate_apriori_layout()
        if self.mode == "gordian":
            return self._generate_gordian_layout()
        return self._generate_agree_sets_layout()

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def _grade_itemset_field(self, user_input, key, expected):
        actual = self._parse_itemset((user_input or {}).get(key))
        return {
            key: {
                "correct": actual == tuple(expected),
                "expected": self._format_itemset(expected),
            }
        }

    def _grade_collection_field(self, user_input, key, expected):
        actual = self._parse_itemset_collection((user_input or {}).get(key))
        expected_set = {tuple(itemset) for itemset in expected}
        return {
            key: {
                "correct": actual == expected_set,
                "expected": self._format_collection(expected),
            }
        }

    def _evaluate_agree_sets(self, user_input):
        user_input = user_input or {}
        results = {}

        for (left, right), agree_set in self.agree_sets.items():
            pair_slug = f"t{left + 1}_t{right + 1}"
            agree_key = f"ucc_agree_{pair_slug}_set"
            complement_key = f"ucc_agree_{pair_slug}_complement"
            complement = tuple(attr for attr in self.attributes if attr not in agree_set)
            results.update(self._grade_itemset_field(user_input, agree_key, agree_set))
            results.update(self._grade_itemset_field(user_input, complement_key, complement))

        results.update(self._grade_collection_field(
            user_input,
            "ucc_agree_maximal_sets",
            self.maximal_agree_sets,
        ))
        results.update(self._grade_collection_field(
            user_input,
            "ucc_agree_difference_sets",
            self.difference_sets,
        ))
        results.update(self._grade_collection_field(
            user_input,
            "ucc_agree_final_uccs",
            self.minimal_uccs,
        ))
        return results

    def _evaluate_apriori(self, user_input):
        user_input = user_input or {}
        results = {}

        for level in self.apriori_levels:
            k = level["k"]
            for entry in level["tested"]:
                itemset = entry["itemset"]
                slug = self._itemset_slug(itemset)
                distinct_key = f"ucc_apr_l{k}_{slug}_distinct"
                max_count_key = f"ucc_apr_l{k}_{slug}_max_count"
                unique_key = f"ucc_apr_l{k}_{slug}_unique"

                results[distinct_key] = {
                    "correct": self._int_value(user_input.get(distinct_key)) == entry["distinct_count"],
                    "expected": str(entry["distinct_count"]),
                }
                results[max_count_key] = {
                    "correct": self._int_value(user_input.get(max_count_key)) == entry["max_duplicate_count"],
                    "expected": str(entry["max_duplicate_count"]),
                }
                results[unique_key] = {
                    "correct": self._bool_value(user_input.get(unique_key)) == bool(entry["unique"]),
                    "expected": str(bool(entry["unique"])),
                }

            if level["pruned"]:
                results.update(self._grade_collection_field(
                    user_input,
                    f"ucc_apr_l{k}_pruned",
                    [entry["itemset"] for entry in level["pruned"]],
                ))

        results.update(self._grade_collection_field(
            user_input,
            "ucc_apr_final_uccs",
            self.minimal_uccs,
        ))
        return results

    def _grade_fp_tree(self, user_input, key, expected_rows):
        expected_tree = tree_from_path_count_rows(expected_rows)
        expected_tree = self._set_tree_root_count(expected_tree, len(self.rows))

        try:
            actual_tree = parse_fp_tree_payload((user_input or {}).get(key))
        except (TypeError, ValueError):
            return {
                key: {
                    "correct": False,
                    "expected": expected_tree,
                    "node_results": {},
                    "missing": [],
                    "extra": [],
                    "message": "Invalid FP-tree payload.",
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

    def _evaluate_gordian(self, user_input):
        user_input = user_input or {}
        results = {}

        results.update(self._grade_fp_tree(
            user_input,
            "ucc_gordian_main_tree",
            self.main_tree_rows,
        ))
        results.update(self._grade_collection_field(
            user_input,
            "ucc_gordian_max_non_unique",
            self.maximal_agree_sets,
        ))

        results.update(self._grade_collection_field(
            user_input,
            "ucc_gordian_final_uccs",
            self.minimal_uccs,
        ))
        return results

    def evaluate(self, user_input):
        if self.mode == "apriori":
            return self._evaluate_apriori(user_input)
        if self.mode == "gordian":
            return self._evaluate_gordian(user_input)
        return self._evaluate_agree_sets(user_input)

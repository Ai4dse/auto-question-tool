from app.common import *
from pathlib import Path
import json

path = Path(__file__).resolve().parent.parent / "resources" / "ir_documents.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

DIFFICULTY_SETTINGS = {
    "easy": {
        "doc_num": 2,
        "query_num": 2,
        "query_operator_counts": [1, 1],
    },
    "medium": {
        "doc_num": 3,
        "query_num": 2,
        "query_operator_counts": [1, 2],
    },
    "hard": {
        "doc_num": 4,
        "query_num": 3,
        "query_operator_counts": [2,3],
    },
}


class BooleanRetrieval:
    def __init__(self, seed=None, difficulty="easy", **kwargs):
        self.difficulty = str(difficulty).lower() if str(difficulty).lower() in DIFFICULTY_SETTINGS else "easy"
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        self.settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.docs_per_topic = self.settings["doc_num"]
        self.query_num = self.settings["query_num"]
        self.query_operator_counts = self.settings["query_operator_counts"][:self.query_num]

        block = self.rng.choice(raw)
        sampled_docs = self.rng.sample(block["Docs"], self.docs_per_topic)

        self.docs = [
            {
                "nr": f"Doc{i+1}",
                "tokens": list(d["content"])
            }
            for i, d in enumerate(sampled_docs)
        ]

        self.terms = sorted({
            term
            for doc in self.docs
            for term in doc["tokens"]
        })

        self._generate_queries()

    def _docs_for_term(self, term):
        return {
            doc["nr"]
            for doc in self.docs
            if term in doc["tokens"]
        }

    def _all_doc_ids(self):
        return {doc["nr"] for doc in self.docs}

    def _format_docset(self, docset):
        if not docset:
            return "-"

        def sort_key(doc_id):
            if doc_id.startswith("Doc") and doc_id[3:].isdigit():
                return int(doc_id[3:])
            return float("inf")

        return ", ".join(sorted(docset, key=sort_key))

    def _eval_expr(self, expr):
        kind = expr[0]

        if kind == "TERM":
            return self._docs_for_term(expr[1])

        if kind == "NOT":
            return self._all_doc_ids() - self._eval_expr(expr[1])

        if kind == "AND":
            return self._eval_expr(expr[1]) & self._eval_expr(expr[2])

        if kind == "OR":
            return self._eval_expr(expr[1]) | self._eval_expr(expr[2])

        return set()

    def _expr_to_string(self, expr, top_level=True):
        kind = expr[0]

        if kind == "TERM":
            return expr[1]

        if kind == "NOT":
            inner = self._expr_to_string(expr[1], top_level=False)
            if expr[1][0] == "TERM":
                return f"NOT {inner}"
            return f"NOT ({inner})"

        if kind in {"AND", "OR"}:
            left = self._expr_to_string(expr[1], top_level=False)
            right = self._expr_to_string(expr[2], top_level=False)
            s = f"{left} {kind} {right}"
            return s if top_level else f"({s})"

        return ""

    def _wrap_term(self, term, rng):
        """
        NOT zählt nicht als Operator im Schwierigkeitsgrad.
        Es wird nur als Modifikator um einen Term gelegt.
        """
        if rng.random() < 0.35:
            return ("NOT", ("TERM", term))
        return ("TERM", term)

    def _count_binary_operators(self, expr):
        kind = expr[0]

        if kind == "TERM":
            return 0

        if kind == "NOT":
            return self._count_binary_operators(expr[1])

        if kind in {"AND", "OR"}:
            return 1 + self._count_binary_operators(expr[1]) + self._count_binary_operators(expr[2])

        return 0

    def _build_random_expr(self, op_count, rng):
        """
        Erzeugt einen zufälligen booleschen Ausdruck mit genau op_count
        binären Operatoren (AND / OR). NOT zählt nicht mit.
        """
        if not self.terms:
            return ("TERM", "")

        def pick_terms(k):
            if len(self.terms) >= k:
                return rng.sample(self.terms, k)
            return [rng.choice(self.terms) for _ in range(k)]

        if op_count == 0:
            return self._wrap_term(rng.choice(self.terms), rng)

        if op_count == 1:
            a, b = pick_terms(2)
            op = rng.choice(["AND", "OR"])
            expr = (
                op,
                self._wrap_term(a, rng),
                self._wrap_term(b, rng),
            )
            return expr

        if op_count == 2:
            a, b, c = pick_terms(3)

            patterns = [
                (
                    rng.choice(["AND", "OR"]),
                    (
                        rng.choice(["AND", "OR"]),
                        self._wrap_term(a, rng),
                        self._wrap_term(b, rng),
                    ),
                    self._wrap_term(c, rng),
                ),
                (
                    rng.choice(["AND", "OR"]),
                    self._wrap_term(a, rng),
                    (
                        rng.choice(["AND", "OR"]),
                        self._wrap_term(b, rng),
                        self._wrap_term(c, rng),
                    ),
                ),
            ]
            expr = rng.choice(patterns)
            return expr

        if op_count == 3:
            a, b, c, d = pick_terms(4)

            patterns = [
                (
                    rng.choice(["AND", "OR"]),
                    (
                        rng.choice(["AND", "OR"]),
                        (
                            rng.choice(["AND", "OR"]),
                            self._wrap_term(a, rng),
                            self._wrap_term(b, rng),
                        ),
                        self._wrap_term(c, rng),
                    ),
                    self._wrap_term(d, rng),
                ),
                (
                    rng.choice(["AND", "OR"]),
                    (
                        rng.choice(["AND", "OR"]),
                        self._wrap_term(a, rng),
                        self._wrap_term(b, rng),
                    ),
                    (
                        rng.choice(["AND", "OR"]),
                        self._wrap_term(c, rng),
                        self._wrap_term(d, rng),
                    ),
                ),
            ]
            expr = rng.choice(patterns)
            return expr

        terms = pick_terms(op_count + 1)
        expr = (
            rng.choice(["AND", "OR"]),
            self._wrap_term(terms[0], rng),
            self._wrap_term(terms[1], rng),
        )

        for term in terms[2:]:
            expr = (
                rng.choice(["AND", "OR"]),
                expr,
                self._wrap_term(term, rng),
            )

        return expr

    def _generate_single_query(self, op_count, query_index):
        """
        Versucht bis zu 20-mal, eine Query mit mindestens einem Treffer zu erzeugen.
        Falls das nicht gelingt, wird die letzte Query trotzdem übernommen.
        """
        last_query = None

        for attempt in range(20):
            trial_rng = random.Random(self.seed + query_index * 1000 + attempt)
            expr = self._build_random_expr(op_count, trial_rng)

            # Sicherheit: nur binäre Operatoren zählen
            if self._count_binary_operators(expr) != op_count:
                continue

            matches = self._eval_expr(expr)

            last_query = {
                "difficulty": op_count,
                "expr": expr,
                "query": self._expr_to_string(expr),
                "matches": matches,
            }

            if matches:
                return last_query

        return last_query

    def _generate_queries(self):
        self.queries = []

        for i, op_count in enumerate(self.query_operator_counts, start=1):
            q = self._generate_single_query(op_count, i)
            if q:
                self.queries.append(q)

        self.solution = {
            f"id_query_{i+1}": self._format_docset(q["matches"])
            for i, q in enumerate(self.queries)
        }

    def _generate_steps_layout(self):
        base = {}

        view1 = [
            {
                "type": "Text",
                "content": (
                    "### Boolesches Retrieval\n\n"
                    "Betrachte die folgenden Dokumente:\n"
                    + "\n".join(
                        f"- **{doc['nr']}**: {' '.join(doc['tokens'])}"
                        for doc in self.docs
                    )
                    + "\n\n"
                    "### Aufgabe\n\n"
                    "Bearbeite die folgenden booleschen Anfragen.\n\n"
                    "Gib für jede Anfrage alle Dokumente an, die die Anfrage erfüllen.\n\n"
                    "**Operatoren:**\n"
                    "- `A AND B`: beide Terme müssen vorkommen\n"
                    "- `A OR B`: mindestens einer der beiden Terme muss vorkommen\n"
                    "- `NOT A`: der Term darf nicht vorkommen\n\n"
                    "**Antwortformat:**\n"
                    "- Trage die passenden Dokumente ein, z. B. `Doc1, Doc3`\n"
                    "- Falls kein Dokument passt, kann das Feld leer gelassen werden\n\n"
                ),
            }
        ]

        for i, q in enumerate(self.queries, start=1):
            view1.append({
                "type": "text_input",
                "id": f"id_query_{i}",
                "label": q["query"]
            })

        base["view1"] = view1

        base["lastView"] = [{
            "type": "Text",
            "content": (
                "### Hinweis zur Praxis\n\n"
                "Boolesches Retrieval ist ein einfaches Modell zur Dokumentensuche.\n\n"
                "**Idee:**\n"
                "Dokumente werden danach gefiltert, ob bestimmte Terme vorkommen oder nicht vorkommen.\n\n"
                "**Vorteile:**\n"
                "- Einfach zu verstehen\n"
                "- Gut für exakte Filterbedingungen\n"
                "- Lässt sich effizient mit einem Inverted Index umsetzen\n\n"
                "**Einschränkung:**\n"
                "Es gibt keine Rangfolge der Treffer. Alle passenden Dokumente gelten zunächst als gleich relevant."
            ),
        }]

        return base

    def generate(self):
        return self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}

        for i, q in enumerate(self.queries, start=1):
            key = f"id_query_{i}"
            expected_raw = self.solution[key]
            user_raw = user_input.get(key, "")

            if expected_raw == "-":
                user_norm = str(user_raw).strip().lower()
                correct = user_norm in {"", "-", "no solution", "keine lösung", "none"}
                expected_display = "-"
            else:
                expected = normalize_list_string(expected_raw)
                user_val = normalize_list_string(user_raw)
                correct = user_val == expected
                expected_display = expected_raw

            results[key] = {
                "correct": correct,
                "expected": expected_display
            }

        return results

    def evaluate(self, user_input):
        return self._evaluate_steps(user_input)
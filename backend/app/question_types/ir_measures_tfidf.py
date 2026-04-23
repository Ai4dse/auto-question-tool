from collections import Counter
from app.common import *
from pathlib import Path
import json

path = Path(__file__).resolve().parent.parent / "resources" / "ir_documents.json"
with open(path, "r", encoding="utf-8") as f:
    raw = json.load(f)

DIFFICULTY_SETTINGS = {
    "easy":   {"docs_per_topic": 1, "query_terms": 2},
    "medium": {"docs_per_topic": 1, "query_terms": 3},
    "hard":   {"docs_per_topic": 2, "query_terms": 4},
}


class IRMeasuresTFIDF:
    def __init__(self, seed=None, difficulty="easy", mode="steps", **kwargs):
        self.rounding = 3
        self.difficulty = str(difficulty).lower() if str(difficulty).lower() in DIFFICULTY_SETTINGS else "easy"
        self.mode = str(mode).lower()
        self.measure = "tfidf"
        self.seed = int(seed) if seed is not None else random.randint(1, 999999)
        self.rng = random.Random(self.seed)

        settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.docs_per_topic = settings["docs_per_topic"]
        self.query_terms = settings["query_terms"]

        self.expected = {"tfidf": {}}
        self.expected_tf = {}
        self.expected_df = {}
        self.expected_tf_q = {}
        self.expected_tfidf = {}

        self._solve()

    def _solve(self):
        self.corpus = {
            block["Thema"]: [
                {"topic": block["Thema"], "nr": d["Nr"], "tokens": list(d["content"])}
                for d in block["Docs"]
            ]
            for block in raw
        }
        self.all_docs = [d for docs in self.corpus.values() for d in docs]

        self.selected_docs = []
        for topic, docs in self.corpus.items():
            if len(docs) < self.docs_per_topic:
                raise ValueError(f"Not enough docs in topic '{topic}' for docs_per_topic={self.docs_per_topic}")
            self.selected_docs.extend(self.rng.sample(docs, k=self.docs_per_topic))
        self.rng.shuffle(self.selected_docs)

        pool = [t for d in self.selected_docs for t in d["tokens"]]
        unique_pool = list(dict.fromkeys(pool))
        self.query = (
            self.rng.sample(unique_pool, k=self.query_terms)
            if len(unique_pool) >= self.query_terms
            else self.rng.choices(pool, k=self.query_terms)
        )

        self.selected_docs.sort(key=lambda d: int(re.search(r"\d+", d["nr"]).group(0)))
        query_terms = list(dict.fromkeys(self.query))

        df = Counter()
        for d in self.selected_docs:
            df.update(set(d["tokens"]))

        N = len(self.selected_docs)
        idf = {t: math.log((N + 1) / (c + 1)) + 1.0 for t, c in df.items()}

        self.vocab = sorted(set(self.query) | {t for d in self.selected_docs for t in d["tokens"]})
        self.expected_df = {t: int(df.get(t, 0)) for t in self.vocab}
        self.expected_tf_q = {t: self.query.count(t) for t in self.vocab}

        for d in self.selected_docs:
            counts = Counter(d["tokens"])
            self.expected_tf[d["nr"]] = {t: int(counts.get(t, 0)) for t in self.vocab}

        self.expected_tfidf["Q"] = {
            t: round(self.expected_tf_q[t] * idf.get(t, math.log(N + 1) + 1.0), self.rounding)
            for t in self.vocab
        }

        for d in self.selected_docs:
            nr = d["nr"]
            self.expected_tfidf[nr] = {
                t: round(self.expected_tf[nr][t] * idf.get(t, math.log(N + 1) + 1.0), self.rounding)
                for t in self.vocab
            }

        qv = self.expected_tfidf["Q"]
        qnorm = math.sqrt(sum(v * v for v in qv.values()))
        for d in self.selected_docs:
            dv = self.expected_tfidf[d["nr"]]
            dnorm = math.sqrt(sum(v * v for v in dv.values()))
            dot = sum(qv[t] * dv[t] for t in self.vocab)
            self.expected["tfidf"][d["nr"]] = round(
                0.0 if qnorm == 0.0 or dnorm == 0.0 else dot / (qnorm * dnorm),
                self.rounding
            )

        self.query_terms_unique = query_terms

    def _generate_steps_layout(self):
        docs = self.selected_docs
        base = {}

        view1 = [
            {
                "type": "Table",
                "title": "Ausgewählte Dokumente (Korpus)",
                "columns": ["Thema", "Nr", "Tokens"],
                "rows": [[d["topic"], d["nr"], ", ".join(d["tokens"])] for d in docs],
            },
            {
                "type": "Text",
                "content": (
                    "### Aufgabe (Steps): TF-IDF (Cosine)\n\n"
                    f"Query: **{' '.join(self.query)}**\n\n"
                    "#### Teil 1: TF und DF\n"
                    "**Korpus = nur die ausgewählten Dokumente**.\n\n"
                    "**TF(t,d)** = Anzahl, wie oft Term *t* im Dokument *d* vorkommt.\n"
                    "**DF(t)** = Anzahl der ausgewählten Dokumente, die Term *t* enthalten.\n\n"
                    f"N = {len(docs)}\n\n"
                    "**Hinweis:** Runde alle berechneten Werte auf **2 Nachkommastellen**.\n"
                ),
            },
        ]

        q_cells = [[
            {"type": "text", "value": "**Term**"},
            {"type": "text", "value": "**tf (Query)**"},
        ]]
        for term in self.query_terms_unique:
            tid = term.lower()
            q_cells.append([
                {"type": "text", "value": term},
                {"type": "TextInput", "id": f"tf_Q_{tid}"},
            ])
        view1 += [
            {"type": "Text", "content": "#### Query: TF "},
            {"type": "layout_table", "rows": len(q_cells), "cols": 2, "cells": q_cells},
        ]

        for d in docs:
            doc_terms = list(dict.fromkeys(d["tokens"]))
            cells = [[
                {"type": "text", "value": "**Term**"},
                {"type": "text", "value": f"**tf ({d['nr']})**"},
            ]]
            for term in doc_terms:
                tid = term.lower()
                cells.append([
                    {"type": "text", "value": term},
                    {"type": "TextInput", "id": f"tf_{d['nr']}_{tid}"},
                ])
            view1 += [
                {"type": "Text", "content": f"#### {d['nr']}: TF"},
                {"type": "layout_table", "rows": len(cells), "cols": 2, "cells": cells},
            ]

        df_cells = [[
            {"type": "text", "value": "**Term**"},
            {"type": "text", "value": "**df**"},
        ]]
        for term in self.vocab:
            tid = term.lower()
            df_cells.append([
                {"type": "text", "value": term},
                {"type": "TextInput", "id": f"df_{tid}"},
            ])
        view1 += [
            {"type": "Text", "content": "#### DF-Tabelle"},
            {"type": "layout_table", "rows": len(df_cells), "cols": 2, "cells": df_cells},
        ]

        view2 = [{
            "type": "Text",
            "content": (
                "#### Teil 2: TF-IDF\n\n"
                "$$idf(t) = \\log\\left(\\frac{N+1}{df(t)+1}\\right) + 1$$\n"
                "$$tfidf(t,d) = tf(t,d) \\cdot idf(t)$$\n\n"
                "Baue die TF-IDF Werte für Query und Dokumente.\n"
                "Du trägst weiterhin **nur Terme ein, die in Query/Dokument vorkommen**.\n"
                "Alle anderen hätten tf=0 und damit automatisch tfidf=0."
            ),
        }]

        q_cells = [[
            {"type": "text", "value": "**Term**"},
            {"type": "text", "value": "**tfidf (Query)**"},
        ]]
        for term in self.query_terms_unique:
            q_cells.append([
                {"type": "text", "value": term},
                {"type": "TextInput", "id": f"tfidf_Q_{term.lower()}"},
            ])
        view2 += [
            {"type": "Text", "content": "#### Query: TF-IDF (nur Query-Terme)"},
            {"type": "layout_table", "rows": len(q_cells), "cols": 2, "cells": q_cells},
        ]

        for d in docs:
            doc_terms = list(dict.fromkeys(d["tokens"]))
            cells = [[
                {"type": "text", "value": "**Term**"},
                {"type": "text", "value": f"**tfidf ({d['nr']})**"},
            ]]
            for term in doc_terms:
                cells.append([
                    {"type": "text", "value": term},
                    {"type": "TextInput", "id": f"tfidf_{d['nr']}_{term.lower()}"},
                ])
            view2 += [
                {"type": "Text", "content": f"#### {d['nr']}: TF-IDF (nur Terme aus dem Dokument)"},
                {"type": "layout_table", "rows": len(cells), "cols": 2, "cells": cells},
            ]

        view3 = [{
            "type": "Text",
            "content": (
                "#### Teil 3: Cosine Similarity\n\n"
                "Jetzt bauen wir den gemeinsamen Vektorraum:\n"
                "**Vokabular = alle Terme, die in mindestens einem ausgewählten Dokument "
                "oder in der Query vorkommen**.\n"
                "Terme, die in einem Dokument nicht vorkommen, haben **tfidf = 0**.\n\n"
                "Cosine Similarity:\n"
                "$$\\cos(\\vec{q},\\vec{d}) = \\frac{\\vec{q}\\cdot\\vec{d}}{\\|\\vec{q}\\|\\,\\|\\vec{d}\\|}$$\n\n"
                "Unten siehst du die TF-IDF Vektoren über das gesamte Vokabular."
            ),
        }]

        view3.append({
            "type": "Table",
            "title": "TF-IDF Matrix (Vektorraummodell)",
            "columns": ["Term", "Query"] + [d["nr"] for d in docs],
            "rows": [
                [t, str(self.expected_tfidf["Q"][t])] + [str(self.expected_tfidf[d["nr"]][t]) for d in docs]
                for t in self.vocab
            ],
        })

        score_cells = [[
            {"type": "text", "value": "**Dokument**"},
            {"type": "text", "value": "**Cosine Similarity**"},
        ]] + [
            [
                {"type": "text", "value": d["nr"]},
                {"type": "TextInput", "id": f"score_{d['nr']}"},
            ]
            for d in docs
        ]

        view3.append({
            "type": "layout_table",
            "rows": len(score_cells),
            "cols": 2,
            "cells": score_cells,
        })

        base["lastView"] = [
        {
            "type": "Text",
            "content": (
                "### Hinweis zur Praxis:\n\n"
                "TF-IDF ist ein wichtiges Verfahren zur Gewichtung von Begriffen in Dokumenten.\n\n"
                "**Idee:**\n"
                "Wörter werden danach bewertet, wie häufig sie in einem Dokument vorkommen (TF) "
                "und wie selten sie im gesamten Korpus sind (IDF).\n\n"
                "**Vorteile:**\n"
                "- Hebt wichtige, charakteristische Begriffe hervor\n"
                "- Reduziert den Einfluss sehr häufiger Wörter (z. B. \"und\", \"der\")\n"
                "- Grundlage vieler Ranking-Verfahren (z. B. mit Cosine Similarity)\n\n"
                "**Einschränkung:**\n"
                "Berücksichtigt keine Bedeutung oder Reihenfolge von Wörtern, sondern nur deren Häufigkeit."
            ),
        }]
        base["view1"] = view1
        base["view2"] = view2
        base["view3"] = view3
        return base

    def _generate_exam_layout(self):
        return {
            "view1": [
                {
                    "type": "Table",
                    "title": "Ausgewählte Dokumente",
                    "columns": ["Thema", "Nr", "Tokens"],
                    "rows": [[d["topic"], d["nr"], ", ".join(d["tokens"])] for d in self.selected_docs],
                },
                {
                    "type": "Text",
                    "content": (
                        "### Prüfungsaufgabe: Dokument-Ähnlichkeit (TF-IDF Cosine)\n\n"
                        f"Query: **{' '.join(self.query)}**\n\n"
                        "Berechne die Cosine Similarity der Query zu **jedem** Dokument\n"
                        "mit **TF-IDF**.\n\n"
                        "#### Abgabeformat\n"
                        "Gib deine Ergebnisse genau in dieser Form an (jede Angabe in einer neuen Zeile):\n"
                        "- `D1: <wert>`\n"
                        "- `D2: <wert>`\n"
                        "- ...\n"
                    ),
                },
                {
                    "type": "TextInput",
                    "label": "Antworten TF-IDF (z.B. D1: 0.413)",
                    "id": "answers_tfidf",
                    "rows": 10,
                },
            ],
            "lastView": [
                {
                    "type": "Text",
                    "content": (
                        "### Hinweis zur Praxis:\n\n"
                        "TF-IDF ist ein wichtiges Verfahren zur Gewichtung von Begriffen in Dokumenten.\n\n"
                        "**Idee:**\n"
                        "Wörter werden danach bewertet, wie häufig sie in einem Dokument vorkommen (TF) "
                        "und wie selten sie im gesamten Korpus sind (IDF).\n\n"
                        "**Vorteile:**\n"
                        "- Hebt wichtige, charakteristische Begriffe hervor\n"
                        "- Reduziert den Einfluss sehr häufiger Wörter (z. B. \"und\", \"der\")\n"
                        "- Grundlage vieler Ranking-Verfahren (z. B. mit Cosine Similarity)\n\n"
                        "**Einschränkung:**\n"
                        "Berücksichtigt keine Bedeutung oder Reihenfolge von Wörtern, sondern nur deren Häufigkeit."
                    ),
                }]
        }

    def generate(self):
        return self._generate_exam_layout() if self.mode == "exam" else self._generate_steps_layout()

    def _evaluate_steps(self, user_input):
        user_input = user_input or {}
        results = {}
        tfdf_ok = tfidf_ok = score_ok = True
        tfdf_expected_lines = []
        tfidf_expected_lines = []
        score_expected_lines = []

        for term in self.query_terms_unique:
            tid = term.lower()
            key = f"tf_Q_{tid}"
            exp = self.expected_tf_q.get(term, 0)
            ok = str(normalize_number(user_input.get(key))) == str(normalize_number(exp))
            results[key] = {"correct": ok, "expected": str(normalize_number(exp))}
            tfdf_ok &= ok
            tfdf_expected_lines.append(
                f"Q {term} -> tf: {normalize_number(self.expected_tf_q.get(term, 0))}"
            )

            key = f"tfidf_Q_{tid}"
            exp = self.expected_tfidf["Q"].get(term, 0)
            ok = str(normalize_number(user_input.get(key))) == str(normalize_number(exp))
            results[key] = {"correct": ok, "expected": str(normalize_number(exp))}
            tfidf_ok &= ok
            tfidf_expected_lines.append(f"Q {term}: {normalize_number(exp)}")

        for term in self.vocab:
            tid = term.lower()
            key = f"df_{tid}"
            exp = self.expected_df.get(term, 0)
            ok = str(normalize_number(user_input.get(key))) == str(normalize_number(exp))
            results[key] = {"correct": ok, "expected": str(normalize_number(exp))}
            tfdf_ok &= ok
            tfdf_expected_lines.append(
                f"{term} -> df: {normalize_number(self.expected_df.get(term, 0))}"
            )

        for d in self.selected_docs:
            nr = d["nr"]
            for term in dict.fromkeys(d["tokens"]):
                tid = term.lower()

                key = f"tf_{nr}_{tid}"
                exp = self.expected_tf[nr].get(term, 0)
                ok = str(normalize_number(user_input.get(key))) == str(normalize_number(exp))
                results[key] = {"correct": ok, "expected": str(normalize_number(exp))}
                tfdf_ok &= ok
                tfdf_expected_lines.append(
                    f"{nr} {term} -> tf: {normalize_number(self.expected_tf[nr].get(term, 0))}"
                )

                key = f"tfidf_{nr}_{tid}"
                exp = self.expected_tfidf[nr].get(term, 0)
                ok = str(normalize_number(user_input.get(key))) == str(normalize_number(exp))
                results[key] = {"correct": ok, "expected": str(normalize_number(exp))}
                tfidf_ok &= ok
                tfidf_expected_lines.append(f"{nr} {term}: {normalize_number(exp)}")

            key = f"score_{nr}"
            exp = self.expected["tfidf"].get(nr, 0)
            ok = str(normalize_number(user_input.get(key))) == str(normalize_number(exp))
            results[key] = {"correct": ok, "expected": str(normalize_number(exp))}
            score_ok &= ok
            score_expected_lines.append(f"{nr}: {normalize_number(exp)}")

        results["tf_df"] = {"correct": tfdf_ok, "expected": "\n".join(tfdf_expected_lines)}
        results["tfidf_vectors"] = {"correct": tfidf_ok, "expected": "\n".join(tfidf_expected_lines)}
        results["scores"] = {"correct": score_ok, "expected": "\n".join(score_expected_lines)}
        return results

    def _evaluate_exam(self, user_input):
        user_input = user_input or {}
        text = str(user_input.get("answers_tfidf", "") or "")
        parsed = {
            docid.upper(): val
            for docid, val in re.findall(r"(?im)\b(D\d+)\b\s*[:=]?\s*([-+]?\d+(?:[.,]\d+)?)", text)
        }

        expected_lines = []
        all_correct = True
        for d in self.selected_docs:
            nr = d["nr"].upper()
            exp = self.expected["tfidf"][d["nr"]]
            if str(normalize_number(parsed.get(nr))) != str(normalize_number(exp)):
                all_correct = False
            expected_lines.append(f"{nr}: {normalize_number(exp)}")

        return {
            "answers_tfidf": {
                "correct": all_correct,
                "expected": "\n".join(expected_lines),
            }
        }

    def evaluate(self, user_input):
        return self._evaluate_exam(user_input) if self.mode == "exam" else self._evaluate_steps(user_input)

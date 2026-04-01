WEEK_CONFIG = {
    1: {
        "title": "Woche 1: Reguläre Ausdrücke",
        "start_date": "2025-03-01",
    },
    2: {
        "title": "Woche 2: Vektorraummodell",
        "start_date": "2025-03-15",
    },
    3: {
        "title": "Woche 3: ER-Diagramm",
        "start_date": "2025-03-29",
    },
    4: {
        "title": "Woche 4: Relationales Schema",
        "start_date": "2025-04-12",
    },
    5: {
        "title": "Woche 5: Relationale Algebra, SQL und XPath/XQuery",
        "start_date": "2025-04-26",
    },
    6: {
        "title": "Woche 6: Funktionale Abhängigkeiten und Normalformen",
        "start_date": "2025-05-10",
    },
    7: {
        "title": "Woche 7: Synthesealgorithmus und Star-/Snowflake-Schema",
        "start_date": "2025-05-24",
    },
    8: {
        "title": "Woche 8: Assoziationsregel-Extraktion",
        "start_date": "2025-06-07",
    },
    9: {
        "title": "Woche 9: Distanzmaße und Clustering",
        "start_date": "2025-06-21",
    },
    10: {
        "title": "Woche 10: Schema-Matching und Data Cleaning",
        "start_date": "2025-07-05",
    },
}

QUESTION_CONFIG = {
    "kmeans": {
        "class_path": "app.question_types.kmeans.KMeansQuestion",
        "metadata": {
            "title": "K-Means Clustering",
            "week": 9,
            "mode": ["steps", "exam"],
            "desc": "Gruppiere Datenpunkte mit dem K-Means-Algorithmus.",
            "tags": ["clustering", "unsupervised"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "agnes": {
        "class_path": "app.question_types.agnes.AGNESQuestion",
        "metadata": {
            "title": "AGNES",
            "week": 9,
            "mode": ["steps", "exam"],
            "desc": "Führe hierarchisches Clustering mit AGNES durch.",
            "tags": ["clustering", "unsupervised"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "label": "Difficulty",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "linkage_method": {
                    "kind": "select",
                    "visibility": "hidden",
                    "label": "Linkage Method",
                    "options": ["single", "complete", "average"],
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                    "label": "Random Seed",
                },
            },
        },
    },

    "dbscan": {
        "class_path": "app.question_types.dbscan.DBSCANQuestion",
        "metadata": {
            "title": "DBSCAN",
            "week": 9,
            "mode": ["steps", "exam"],
            "desc": "Erkenne Cluster und Ausreißer mit DBSCAN.",
            "tags": ["clustering", "unsupervised"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "hungarian_method": {
        "class_path": "app.question_types.hungarian_method.HungarianMethodQuestion",
        "metadata": {
            "title": "Ungarische Methode",
            "week": 10,
            "mode": ["steps", "exam"],
            "desc": "Löse Zuordnungsprobleme mit der ungarischen Methode.",
            "tags": ["arithmetic"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "relational_algebra": {
        "class_path": "app.question_types.relational_algebra.RelationalAlgebra",
        "metadata": {
            "title": "Relationale Algebra",
            "week": 5,
            "mode": ["steps", "exam"],
            "desc": "Übe relationale Algebra mit Tabellenoperationen.",
            "tags": ["arithmetic"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                }
            },
        },
    },

    "sql_query": {
        "class_path": "app.question_types.sql_query.SqlQueryQuestion",
        "metadata": {
            "title": "SQL Query",
            "week": 5,
            "desc": "Formuliere SQL-Abfragen auf einem realistischen Datensatz.",
            "tags": ["sql", "databases"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "regex": {
        "class_path": "app.question_types.regex.RegexQuestion",
        "metadata": {
            "title": "Regex",
            "week": 1,
            "desc": "Erstelle reguläre Ausdrücke für typische Textmuster.",
            "tags": ["regex", "text-processing"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "xpath_xquery": {
        "class_path": "app.question_types.xpath_xquery.XPathXQueryQuestion",
        "metadata": {
            "title": "XPath/XQuery",
            "week": 5,
            "desc": "Löse XPath- und XQuery-Aufgaben über externe Tools.",
            "tags": ["xml", "xpath", "xquery"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["xpath", "xquery"],
                    "default": "xpath",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "stable_marriage": {
        "class_path": "app.question_types.stable_marriage.StableMarriageQuestion",
        "metadata": {
            "title": "Stable Marriage",
            "week": 10,
            "desc": "Finde ein stabiles Matching aus Präferenzlisten.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },

    "sigma_rule": {
        "class_path": "app.question_types.sigma_rule.SigmaRule",
        "metadata": {
            "title": "Outlier Detection",
            "week": 9,
            "desc": "Identifiziere Ausreißer mit der Sigma-Regel.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
                "dimensions": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random","1","2"],
                    "default": "random",
                },
                "num_points": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20"],
                    "default": "random",
                },
            },
        },
    },

    "tukey_fences": {
        "class_path": "app.question_types.tukey_fences.TukeyFences",
        "metadata": {
            "title": "Outlier Detection2",
            "week": 10,
            "desc": "Identifiziere Ausreißer mit Tukey-Fences.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
                "dimensions": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random","1","2"],
                    "default": "random",
                },
                "num_points": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20"],
                    "default": "random",
                },
            },
        },
    },

    "apriori_algorithm": {
        "class_path": "app.question_types.apriori_algorithm.AprioriAlgorithmQuestion",
        "metadata": {
            "title": "Apriori Algorithm",
            "week": 8,
            "desc": "Bestimme frequent itemsets mit dem Apriori-Algorithmus.",
            "tags": ["data mining", "association rules"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "ir_measures_tfidf": {
        "class_path": "app.question_types.ir_measures_tfidf.IRMeasuresTFIDF",
        "metadata": {
            "title": "TF-IDF",
            "week": 2,
            "desc": "Berechne TF, DF und TF-IDF für Dokumente und Query.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "incidence_matrix": {
        "class_path": "app.question_types.incidence_matrix.IncidenceMatrix",
        "metadata": {
            "title": "Incidence Matrix",
            "week": 2,
            "desc": "Erstelle eine 0/1 Term-Dokument-Matrix.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "inverted_index": {
        "class_path": "app.question_types.inverted_index.InvertedIndex",
        "metadata": {
            "title": "Inverted Index",
            "week": 2,
            "desc": "Ordne jedem Term die passenden Dokumente zu.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "boolean_retrieval": {
        "class_path": "app.question_types.boolean_retrieval.BooleanRetrieval",
        "metadata": {
            "title": "Boolean Retrieval",
            "week": 2,
            "desc": "Finde passende Dokumente für AND, OR und NOT.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "positional_index": {
        "class_path": "app.question_types.positional_index.PositionalIndex",
        "metadata": {
            "title": "Positional Index",
            "week": 2,
            "desc": "Bestimme Dokumente und Positionen von Termen.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "levenshtein": {
        "class_path": "app.question_types.levenshtein.LevenshteinQuestion",
        "metadata": {
            "title": "Levenshtein",
            "week": 1,
            "desc": "Berechne die Edit-Distanz zwischen zwei Strings.",
            "tags": ["string", "distance", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy"
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden"
                }
            }
        }
    },
    "er_modelling": {
        "class_path": "app.question_types.er_modelling.ERModelling",
        "metadata": {
            "title": "ER-Modellierung",
            "week": 3,
            "desc": "Erstelle ein ER-Diagramm aus einem Text.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "question": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random", "universitäts_schema","firmen_schema(weak_entity)"],
                    "default": "random",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
                "card_type": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["min_max", "cardinality"],
                },
            },
        },
    },
    "er_schema": {
        "class_path": "app.question_types.er_schema.ERSchema",
        "metadata": {
            "title": "Relationales Schema",
            "week": 3,
            "desc": "Leite Tabellen aus einem ER-Diagramm ab.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "question": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random", "universitäts_schema","firmen_schema(weak_entity)"],
                    "default": "random",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "er_cardinality": {
        "class_path": "app.question_types.er_cardinality.ERCardinality",
        "metadata": {
            "title": "Cardinalitäten im Relationalen Schema",
            "week": 3,
            "desc": "Ergänze ein ER Diagramm mit den richtigen Cardinalitäten.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "card_type": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["min_max", "cardinality"],
                },
                "question": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random", "universitäts_schema","firmen_schema(weak_entity)"],
                    "default": "random",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "ir_measures_jaccard": {
        "class_path": "app.question_types.ir_measures_jaccard.IRMeasuresJaccard",
        "metadata": {
            "title": "Jaccard",
            "week": 2,
            "desc": "Berechne die Jaccard-Ähnlichkeit für Query und Dokumente.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["steps", "exam"],
                    "default": "steps",
                },
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "easy",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    }
}


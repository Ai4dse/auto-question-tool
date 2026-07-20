WEEK_CONFIG = {
    1: {
        "title": "Einfache Modelle für Text",
        "start_date": "2026-04-21",
    },
    2: {
        "title": "Vektorraummodell",
        "start_date": "2026-04-28",
    },
    3: {
        "title": "ER-Diagramm",
        "start_date": "2026-05-12",
    },
    4: {
        "title": "Relationale Algebra",
        "start_date": "2026-05-19",
    },
    5: {
        "title": "SQL und XPath/XQuery",
        "start_date": "2026-06-02",
    },
    6: {
        "title": "Funktionale Abhängigkeiten und Normalformen",
        "start_date": "2026-06-16",
    },
    7: {
        "title": "Transaktionen und Synchronisation",
        "start_date": "2026-06-23",
    },
    8: {
        "title": "Assoziationsregel-Extraktion",
        "start_date": "2026-07-01",
    },
    9: {
        "title": "Distanzmaße und Clustering",
        "start_date": "2026-07-07",
    },
    10: {
        "title": "Schema-Matching",
        "start_date": "2026-07-13",
    }
}

MISSING_TASKS = {
    'R 7. Star/Snowflakeschema': 'gegeben R + Datentypen --> transformieren Sie Relation in Schema',
    'R 8. Assoziationsregeln': 'gegeben häufige Itemsets',
    'R 8. FP-Growth:': 'gegeben Transaktionen (wie bei Apriori)',
    'R 9. Distanzen': 'Bigramm/Trigramm und vielleicht noch andere'
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
            "week": 4,
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

    "ngram_similarity": {
        "class_path": "app.question_types.ngram_similarity.NGramSimilarityQuestion",
        "metadata": {
            "title": "Bigramm- und Trigramm-Ähnlichkeit",
            "week": 10,
            "desc": (
                "Berechne die Bigramm- oder Trigramm-Ähnlichkeit von drei Wörtern "
                "und bestimme das ähnlichste Wortpaar."
            ),
            "tags": ["similarity", "ngrams", "dice"],
            "settings": {
                "Mode": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["bigram", "trigram"],
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
            "title": "Sigma-Regel",
            "week": 10,
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
            "title": "Tukey-Fences",
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
    "fp_grow": {
        "class_path": "app.question_types.fp_grow.FPGrowthAlgorithmQuestion",
        "metadata": {
            "title": "FP-Growth",
            "week": 8,
            "desc": "Bestimme frequent itemsets mit dem FP-Growth-Algorithmus.",
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
    "ass_rule_mining": {
        "class_path": "app.question_types.ass_rule_mining.AssociationRuleMiningQuestion",
        "metadata": {
            "title": "Association Rule Mining",
            "week": 8,
            "desc": "Bestimme association rules für ein Set häufiger Itemsets.",
            "tags": ["data mining", "association rules"],
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
            "desc": "Berechne die Levenshtein-Distanz zwischen zwei Strings.",
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
            "desc": "Vervollständige ein ER-Diagramm mithilfe eines Textes. Der Schwierigkeitsgrad gibt an wie viel des ER-Diagramms vorgegeben ist.",
            "tags": ["matching", "algorithms"],
            "settings": {
                "difficulty": {
                    "kind": "select",
                    "visibility": "open",
                    "options": ["easy", "medium", "hard"],
                    "default": "hard",
                },
                "question": {
                    "kind": "select",
                    "visibility": "hidden",
                    "options": ["random","universitäts_schema","firmen_schema(weak_entity)","supermarkt_schema"],
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
            "desc": "Leite ein Relationales Schema aus einem ER-Diagramm ab.",
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
                    "options": ["random", "universitäts_schema","firmen_schema(weak_entity)","supermarkt_schema"],
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
            "title": "Kardinalitäten im Relationalen Schema",
            "week": 3,
            "desc": "Ergänze die ER Diagramme aus der ER-Modellierungs Aufgabe mit den richtigen Kardinalitäten.",
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
                    "options": ["random", "universitäts_schema","firmen_schema(weak_entity)","supermarkt_schema"],
                    "default": "random",
                },
                "seed": {
                    "kind": "number",
                    "visibility": "hidden",
                },
            },
        },
    },
    "candidate_keys_fd": {
        "class_path": "app.question_types.candidate_keys_fd.CandidateKeysFDQuestion",
        "metadata": {
            "title": "Schlüsselsuche",
            "week": 6,
            "desc": "Bestimme Kandidatenschlüssel aus einer Relation und funktionalen Abhängigkeiten.",
            "tags": ["databases", "functional dependencies"],
            "suppress_final_view": True,
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
    "tuple_insertion_fd": {
        "class_path": "app.question_types.tuple_insertion_fd.TupleInsertionFDQuestion",
        "metadata": {
            "title": "Tupel einfügen (FD-Verletzung)",
            "week": 6,
            "desc": "Entscheide, ob Tupel in eine Relation eingefügt werden können, ohne funktionale Abhängigkeiten zu verletzen.",
            "tags": ["databases", "functional dependencies"],
            "suppress_final_view": True,
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
    "decomposition_fd": {
        "class_path": "app.question_types.decomposition_fd.DecompositionFDQuestion",
        "metadata": {
            "title": "Verlustfreiheit & Abhängigkeitsbewahrung",
            "week": 6,
            "desc": "Entscheide, ob eine Zerlegung einer Relation verlustfrei und abhängigkeitsbewahrend ist.",
            "tags": ["databases", "functional dependencies"],
            "suppress_final_view": True,
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
    "normal_forms_fd": {
        "class_path": "app.question_types.normal_forms_fd.NormalFormsFDQuestion",
        "metadata": {
            "title": "Normalform bestimmen",
            "week": 6,
            "desc": "Bestimme die höchste Normalform (1NF/2NF/3NF) einer Relation bezüglich funktionaler Abhängigkeiten.",
            "tags": ["databases", "functional dependencies"],
            "suppress_final_view": True,
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
    "synthesis_algorithm": {
        "class_path": "app.question_types.synthesis_algorithm.SynthesisAlgorithmQuestion",
        "metadata": {
            "title": "Synthesealgorithmus",
            "week": 6,
            "desc": "Führe den 3NF-Synthesealgorithmus schrittweise durch.",
            "tags": ["databases", "functional dependencies", "normalization"],
            "suppress_final_view": True,
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
    "wait_for_graph": {
        "class_path": "app.question_types.wait_for_graph.WaitForGraphQuestion",
        "metadata": {
            "title": "Wartegraph & Verklemmung",
            "week": 7,
            "desc": "Erkenne Verklemmungen mit dem Wartegraphen.",
            "tags": ["databases", "transactions", "deadlock", "2PL"],
            "suppress_final_view": True,
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
    "schedule_properties": {
        "class_path": "app.question_types.schedule_properties.SchedulePropertiesQuestion",
        "metadata": {
            "title": "Eigenschaften von Historien",
            "week": 7,
            "desc": "Bestimme die Eigenschaften einer Historie.",
            "tags": ["databases", "transactions", "serializability", "recoverability"],
            "suppress_final_view": True,
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

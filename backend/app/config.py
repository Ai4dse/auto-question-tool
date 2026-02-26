QUESTION_CONFIG = {
    "kmeans": {
        "class_path": "app.question_types.kmeans.KMeansQuestion",
        "metadata": {
            "title": "K-Means Clustering",
            "mode": ["steps", "exam"],
            "desc": "Cluster data points into groups.",
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
            "mode": ["steps", "exam"],
            "desc": "Practice the Agglomerative Nesting cluster algorithm.",
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
            "mode": ["steps", "exam"],
            "desc": "Practice the DBSCAN algorithm.",
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

    "addition": {
        "class_path": "app.question_types.addition.AdditionQuestion",
        "metadata": {
            "title": "Simple Addition",
            "mode": ["steps", "exam"],
            "desc": "Practice simple arithmetic.",
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

    "hungarian_method": {
        "class_path": "app.question_types.hungarian_method.HungarianMethodQuestion",
        "metadata": {
            "title": "Ungarische Methode",
            "mode": ["steps", "exam"],
            "desc": "Anwenden der ungarischen Methode.",
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
            "mode": ["steps", "exam"],
            "desc": "Übungen und Visualisierungen.",
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

    "stable_marriage": {
        "class_path": "app.question_types.stable_marriage.StableMarriageQuestion",
        "metadata": {
            "title": "Stable Marriage",
            "desc": "Finde ein stabiles Matching aus zwei Praeferenzlisten.",
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
}

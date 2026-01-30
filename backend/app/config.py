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
            "title": "Hungarian Method",
            "mode": ["steps", "exam"],
            "desc": "Practice the hungarian_method.",
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
            "title": "Relational Algebra",
            "mode": ["steps", "exam"],
            "desc": "Practice relational algebra.",
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
}

QUESTION_CONFIG = {
    "kmeans": {
        "class_path": "app.question_types.kmeans.KMeansQuestion",
        "metadata": {
            "title": "K-Means Clustering",
            "mode": ["steps", "exam"],
            "difficulty": ["easy", "medium", "hard"],
            "desc": "Cluster data points into groups.",
            "tags": ["clustering", "unsupervised"]
        }
    },
    
    "dbscan": {
        "class_path": "app.question_types.dbscan.DBSCANQuestion",
        "metadata": {
            "title": "DBSCAN",
            "mode": ["steps", "exam"],
            "difficulty": ["easy", "medium", "hard"],
            "desc": "Practice the DBSCAN algorithm.",
            "tags": ["clustering", "unsupervised"]
        }
    },
    
    "addition": {
        "class_path": "app.question_types.addition.AdditionQuestion",
        "metadata": {
            "title": "Simple Addition",
            "mode": ["steps", "exam"],
            "difficulty": ["easy", "medium", "hard"],
            "desc": "Practice simple arithmetic.",
            "tags": ["arithmetic"]
        }
    },

    "hungarian_method": {
        "class_path": "app.question_types.hungrian_method.HungarianMethodQuestion",
        "metadata": {
            "title": "Hungarian Method",
            "mode": ["steps", "exam"],
            "difficulty": ["easy", "medium", "hard"],
            "desc": "Practice the hungarian_method.",
            "tags": ["arithmetic"]
        }
    }
}

QUESTION_CONFIG = {
    "kmeans": {
        "class_path": "app.question_types.kmeans.KMeansQuestion",
        "metadata": {
            "title": "K-Means Clustering",
            "tags": ["clustering", "unsupervised"]
        }
    },
    
    "dbscan": {
        "class_path": "app.question_types.dbscan.DBSCANQuestion",
        "metadata": {
            "title": "DBSCAN",
            "tags": ["clustering", "unsupervised"]
        }
    },
    
    "addition": {
        "class_path": "app.question_types.addition.AdditionQuestion",
        "metadata": {
            "title": "Simple Addition",
            "tags": ["arithmetic"]
        }
    }
}

from app.ui_layout import *

class KMeansLayout(QuestionLayout):
    def __init__(self, points, centroids, iterations=2):
        self.points = points
        self.centroids = centroids
        self.iterations = iterations

    def build(self):
        return Layout(
            header=Text("K-Means Clustering"),
            body=[
                Table("Points", ["Label", "X", "Y"], [[p.label, p.x, p.y] for p in self.points]),
                CoordinatePlot(self.points, self.centroids)
            ],
            input=[
                TableInput(
                    label=f"Iteration {i+1}",
                    columns=["Centroid", "X", "Y", "Cluster Points"],
                    rows=[
                        TableRow(id=f"iter{i+1}_c{j}", fields=[f"C{j}", "", "", ""])
                        for j in range(len(self.centroids))
                    ]
                )
                for i in range(self.iterations)
            ]
        )

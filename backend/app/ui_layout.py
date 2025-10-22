class QuestionLayout:
    """Base class for all layouts."""
    def build(self):
        raise NotImplementedError("Subclasses must implement build()")

class Layout:
    def __init__(self, header=None, body=None, input=None):
        self.header = header
        self.body = body or []
        self.input = input or []

class UIElement:
    pass
class Text(UIElement):
    def __init__(self, content):
        self.type = "text"
        self.content = content

class Table(UIElement):
    def __init__(self, label, columns, rows):
        self.type = "table"
        self.label = label
        self.columns = columns
        self.rows = rows

class Point:
    def __init__(self, label, x, y):
        self.label = label
        self.x = x
        self.y = y

class CoordinatePlot(UIElement):
    def __init__(self, points, centroids=None):
        self.type = "coordinates_plot"
        self.points = points
        self.centroids = centroids or []
class InputElement:
    pass

class TableRow:
    def __init__(self, id, fields):
        self.id = id
        self.fields = fields

class TableInput(InputElement):
    def __init__(self, label, columns, rows):
        self.type = "table_input"
        self.label = label
        self.columns = columns
        self.rows = rows

class MultipleChoice(InputElement):
    def __init__(self, id, label, options):
        self.type = "multiple_choice"
        self.id = id
        self.label = label
        self.options = options  # list of {"label", "value"}

class TextInput(InputElement):
    def __init__(self, id, label):
        self.type = "text_input"
        self.id = id
        self.label = label

class GherkinDocument(object):
    def __init__(self):
        self.feature = None
        self.comments = []

    def set_feature(self, feature: 'Feature'):
        self.feature = feature

    def add_comment(self, comment: 'Comment'):
        self.comments.append(comment)


class Language(object):
    # TODO: must not be optional
    def __init__(self, language=None):
        self.language = language


class Comment(object):
    def __init__(self, text):
        self.text = text


class Description(object):
    def __init__(self, text):
        self.text = text


class Feature(object):
    def __init__(self):
        self.language = None
        self.keyword = None
        self.name = None
        self.description = None

        self.tags = []
        self.scenario_definitions = []

    def add_scenario_definition(self):
        self.scenario_definitions.append(ScenarioDefinition())

    def add_tag(self, tag: 'Tag'):
        self.tags.append(tag)


class ScenarioDefinition(object):
    def __init__(self, keyword, name, description):
        self.keyword = keyword
        self.name = name
        self.description = description


class Background(ScenarioDefinition):
    pass


class ScenarioOutline(ScenarioDefinition):
    pass


class Scenario(ScenarioDefinition):
    pass


class DocString(object):
    def __init__(self, text):
        self.text = text


class TableCell(object):
    def __init__(self, value):
        self.value = value


class TableRow(object):
    def __init__(self, cells=None):
        self.cells: [TableCell] = cells if cells is not None else []

    def get_value_at(self, index):
        return self.cells[index].value


class DataTable(object):
    def __init__(self, header, rows=None):
        self.header = header
        self.rows = rows if rows is not None else []


class Examples(object):
    def __init__(self, keyword, name, description):
        self.keyword = keyword
        self.name = name
        self.description = description


class Tag(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Tag: {}'.format(self.name)

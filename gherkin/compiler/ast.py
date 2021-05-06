class GherkinDocument(object):
    def __init__(self):
        self.feature = None
        self.comments = []

    def set_feature(self, feature: 'Feature'):
        self.feature = feature


class Language(object):
    # TODO: must not be optional
    def __init__(self, language=None):
        self.language = language


class Comment(object):
    def __init__(self, text):
        self.text = text


class Feature(object):
    def __init__(self, language, keyword, name, description):
        self.language = language
        self.keyword = keyword
        self.name = name
        self.description = description

        self.tags = []
        self.scenario_definitions = []

    def add_scenario_definition(self):
        self.scenario_definitions.append(ScenarioDefinition(feature=self))


class ScenarioDefinition(object):
    def __init__(self, keyword, name, description, feature):
        self.keyword = keyword
        self.name = name
        self.description = description
        self.feature = feature


class Background(ScenarioDefinition):
    pass


class ScenarioOutline(ScenarioDefinition):
    pass


class Scenario(ScenarioDefinition):
    pass


class Examples(object):
    def __init__(self, keyword, name, description):
        self.keyword = keyword
        self.name = name
        self.description = description


class Tag(object):
    pass

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
        self.scenario_definitions.append(ScenarioDefinition(feature=self))

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

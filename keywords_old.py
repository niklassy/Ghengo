from settings import Settings


class GherkinInputInvalid(Exception):
    pass


class GherkinKeyword(object):
    keyword_map = {}
    marked_by_column = False

    def __init__(self, string):
        if not self.string_indicates_this(string):
            raise GherkinInputInvalid('The input is not valid.')

    @property
    def keywords(self):
        if self.keyword_map.get('*') is not None:
            return self.keyword_map['*']

        return self.keyword_map[Settings.language]

    def string_indicates_this(self, string):
        """Returns if a given string indicates this keyword."""
        return any([string.startswith(keyword) for keyword in self.keywords])


class MarkedByColumnMixin(object):
    """For all keywords that are indicated by <Keyword>:"""
    @property
    def keywords(self):
        return ['{}:'.format(keyword) for keyword in super().keywords]


class Feature(MarkedByColumnMixin, GherkinKeyword):
    keyword_map = {
        'en': ['Feature']
    }
    marked_by_column = True

    comments = []

    _descendants = []

    # input should be parsed by a class in a way where the first line is referencing the feature and its tags
    def __init__(self, string):
        super().__init__(string)

        self.comments = []
        self._descendants = []

        for line in string.splitlines():

            # skip empty lines
            if not bool(line):
                continue

            try:
                self.comments.append(Comment(line))
                continue
            except GherkinInputInvalid:
                pass

            # try:
            #     self._descendants.append(Scenario(string))
            #     break
            # except GherkinInputInvalid:
            #     pass
            #
            # try:
            #     self._descendants.append(Example(string))
            #     break
            # except GherkinInputInvalid:
            #     pass

    def string_indicates_this(self, string: str):
        return any([string.startswith(keyword) for keyword in self.keywords])

    @property
    def descendants(self):
        return self._descendants

    @property
    def parent(self):
        return None


class Rule(GherkinKeyword):
    keyword_map = {
        'en': ['Rule']
    }


class Example(GherkinKeyword):
    pass


class Scenario(Example):
    """Is the same as an example"""
    pass


class Background(GherkinKeyword):
    pass


class ScenarioOutline(GherkinKeyword):
    pass


class ScenarioTemplate(GherkinKeyword):
    """Is the same as scenario outline"""
    pass


class Examples(GherkinKeyword):
    pass


class Scenarios(GherkinKeyword):
    """Is the same as examples"""
    pass


class Given(GherkinKeyword):
    pass


class When(GherkinKeyword):
    pass


class Then(GherkinKeyword):
    pass


class And(GherkinKeyword):
    pass


class Asteriks(GherkinKeyword):
    pass


class But(GherkinKeyword):
    pass


class DocString(GherkinKeyword):
    pass


class DataTable(GherkinKeyword):
    pass


class Tag(GherkinKeyword):
    pass


class Comment(GherkinKeyword):
    keyword_map = {
        '*': ['#']
    }

    def __init__(self, string):
        self.string = string.replace(self.keywords[0], '')

    def is_valid(self, string):
        for character in string:
            if character == ' ':
                continue

            return character == self.keywords[0]

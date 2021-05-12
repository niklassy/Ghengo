import re


class GherkinDocument(object):
    def __init__(self):
        self.feature = None
        self.comments = []

    def set_feature(self, feature: 'Feature'):
        self.feature = feature

    def add_comment(self, comment: 'Comment'):
        self.comments.append(comment)


class HasBackgroundMixin(object):
    def __init__(self, background=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background: 'Background' = background

    @property
    def steps(self):
        """Since a background has steps, the parent of the background should also have these steps defined."""
        return self.background.steps


class HasTagsMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tags = []
        self.parent = None

    @property
    def tags(self):
        """Returns all the tags of this object AND of its parents since Gherkin uses inheritance for tags."""
        tags = self._tags.copy()

        if self.parent:
            parent_tags = getattr(self.parent, 'tags', None)
            if parent_tags:
                tags += parent_tags.copy()

        return tags

    def add_tag(self, tag):
        self._tags.append(tag)


class Language(object):
    def __init__(self, language):
        self.language = language


class Comment(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return self.text


class Description(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return self.text


class Feature(HasBackgroundMixin, HasTagsMixin):
    def __init__(self, language, keyword, name, description, background=None):
        super().__init__(background=background)
        self.language = language
        self.keyword = keyword
        self.name = name
        self.description = description
        self._children = []

    def __repr__(self):
        return 'Feature - {} {}'.format(self.keyword, self.name)

    @property
    def children(self):
        return self._children

    def add_child(self, child):
        self._children.append(child)


class ScenarioDefinition(object):
    def __init__(self, keyword, name, description):
        self.keyword = keyword
        self.name = name
        self.description = description
        self._steps = []
        self.parent = None

    def __repr__(self):
        return '{} - {} {}'.format(self.__class__.__name__, self.keyword, self.name)

    @property
    def steps(self):
        """Returns all the steps of the scenario definition (the ones from Background included)"""
        steps = []

        # get parent steps (e.g. if the parent has a background)
        if self.parent:
            parent_steps = getattr(self.parent, 'steps', None)
            if parent_steps:
                steps += parent_steps.copy()

        # add own steps
        for step in self._steps.copy():
            steps.append(step)

            for sub_step in step.sub_steps:
                steps.append(sub_step)

        return steps

    def add_step(self, step):
        """Add a step to a specific step."""
        self._steps.append(step)


class ScenarioImplementation(HasTagsMixin, ScenarioDefinition):
    def __init__(self, keyword, name, description, background=None):
        super().__init__(keyword, name, description)
        self.background = background


class Background(ScenarioDefinition):
    pass


class ScenarioOutline(ScenarioImplementation):
    def __init__(self, keyword, name, description, background=None):
        super().__init__(keyword, name, description, background)
        self._examples = []

    @property
    def examples(self):
        return self._examples

    def add_example(self, example):
        self._examples.append(example)


class Scenario(ScenarioImplementation):
    pass


class StepArgument(object):
    pass


class DocString(StepArgument):
    def __init__(self, text):
        self.text = text


class TableCell(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class TableRow(object):
    def __init__(self, cells=None):
        self.cells: [TableCell] = cells if cells is not None else []

    def get_value_at(self, index):
        return self.cells[index].value

    def __repr__(self):
        return 'TableRow - {}'.format(' | '.join([str(c) for c in self.cells]))

    def __str__(self):
        return self.__repr__()


class DataTable(StepArgument):
    def __init__(self, header, rows=None):
        self.header: TableRow = header
        self.rows: [TableRow] = rows if rows is not None else []

    def __repr__(self):
        return 'DataTable - {}'.format(str(self.header))

    def get_row_at(self, index):
        """Returns a specific row (not the header)."""
        return self.rows[index]

    def get_values(self):
        """Returns all the values in the format: {<column_name_1>: [str], ...}"""
        output = {}
        names = [cell.value for cell in self.header.cells]

        for index, name in enumerate(names):
            values = []

            for row in self.rows:
                values.append(row.get_value_at(index))

            output[name] = values

        return output


class Examples(HasTagsMixin):
    def __init__(self, keyword, name, description, datatable):
        super().__init__()
        self.keyword = keyword
        self.name = name
        self.description = description
        self.datatable = datatable

    def __repr__(self):
        return 'Examples - {} {}'.format(self.keyword, self.name)


class Tag(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Tag - {}'.format(self.name)


class Rule(HasBackgroundMixin, HasTagsMixin):
    def __init__(self, keyword, name, description, background=None):
        super().__init__(background)
        self.keyword = keyword
        self.name = name
        self.description = description
        self._children = []

    def __repr__(self):
        return 'Rule - {} {}'.format(self.keyword, self.name)

    @property
    def children(self):
        return self._children

    def add_child(self, child):
        self._children.append(child)


class Step(object):
    type = None

    def __init__(self, keyword, text, argument=None):
        self.keyword = keyword
        self.text = text
        self.argument = argument
        self.argument_names = [name.replace(' ', '') for name in re.findall('{(.*?)}', self.text)]

    def __repr__(self):
        return '{} - {}{}'.format(self.__class__.__name__.upper(), self.keyword, self.text)


class ParentStep(Step):
    def __init__(self, keyword, text, argument=None):
        super().__init__(keyword, text, argument)
        self.__sub_steps = []

    @property
    def sub_steps(self):
        return self.__sub_steps

    def add_sub_step(self, step):
        self.__sub_steps.append(step)
        step.parent = self


class SubStep(Step):
    def __init__(self, keyword, text, argument=None):
        super().__init__(keyword, text, argument)
        self.parent = None


class Given(ParentStep):
    type = 'GIVEN'


class When(ParentStep):
    type = 'WHEN'


class Then(ParentStep):
    type = 'THEN'


class And(SubStep):
    type = 'AND'


class But(SubStep):
    type = 'BUT'

import re
from typing import Optional


class GherkinDocument(object):
    """Represents the whole gherkin document/ text."""
    def __init__(self):
        self.feature = None
        self.comments = []

    def set_feature(self, feature: Optional['Feature']):
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
    """A simple object that represents the language in the document/ feature."""
    def __init__(self, language):
        self.language = language


class Comment(object):
    """Represents a comment in a gherkin document. All comments are attached to the document."""
    def __init__(self, text: str):
        self.text: str = text

    def __repr__(self):
        return self.text


class Description(object):
    """Represents a description. The object is not attached directly to any other object. It is just a wrapper."""
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return self.text


class Feature(HasBackgroundMixin, HasTagsMixin):
    """
    A feature has:
        - language
        - name, description and keyword
        - an optional background (provided by `HasBackgroundMixin`)
        - optional tags (provided by `HasTagsMixin`)
        - children, which will either be a list of Rules or ScenarioDefinitions

    I will always be inside of a GherkinDocument.
    """
    def __init__(self, language, keyword, name, description, background=None):
        super().__init__(background=background)
        self.language = language
        self.keyword = keyword
        self.name = name
        self.description = description
        self._children = []
        self._rules_as_children = False

    def __repr__(self):
        return 'Feature - {} {}'.format(self.keyword, self.name)

    @property
    def children(self):
        """Represents all the children (can either bei Rule or ScenarioDefinition)"""
        return self._children

    def get_scenario_children(self):
        """
        Returns all scenario definitions. Since there might be Rules as direct children, extract the children from
        there as a nested loop.
        """
        if self._rules_as_children is False:
            return self.children

        children = []
        for rule in self.children:
            for sc_def in rule.scenario_definitions:
                children.append(sc_def)
        return children

    def add_child(self, child):
        if isinstance(child, Rule):
            assert not any([isinstance(c, (Scenario, ScenarioOutline)) for c in self.children])
            self._rules_as_children = True
        elif isinstance(child, (Scenario, ScenarioOutline)):
            assert not any([isinstance(c, Rule) for c in self.children])
            self._rules_as_children = False

        self._children.append(child)


class ScenarioDefinition(object):
    """
    A ScenarioDefinition is a base class for all types of Scenarios. They all have:
        - name, keyword and description
        - steps (GIVEN, AND, BUT, WHEN, THEN)
        - a parent (e.g. a feature or a rule)
    """
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

        # Rules and feature may have backgrounds. Backgrounds add steps that are executed before the steps of
        # the scenario definition
        if self.parent:
            parent_steps = getattr(self.parent, 'steps', None)
            if parent_steps:
                steps += parent_steps.copy()

        # add own steps
        for step in self._steps.copy():
            steps.append(step)

            sub_steps = getattr(step, 'sub_steps', [])
            for sub_step in sub_steps:
                steps.append(sub_step)

        return steps

    def add_step(self, step):
        """Add a step to a specific step."""
        if not isinstance(step, Step):
            raise ValueError('You must add a step instance!')

        self._steps.append(step)


class Background(ScenarioDefinition):
    """A Background only holds GIVEN steps. These steps will be passed to other scenarios/ scenario outlines."""
    pass


class ScenarioOutline(HasTagsMixin, ScenarioDefinition):
    """Scenario outlines use examples to be run multiple times. The examples will pass arguments to the steps."""
    def __init__(self, keyword, name, description):
        super().__init__(keyword, name, description)
        self._examples = []

    @property
    def examples(self):
        return self._examples

    def add_example(self, example):
        self._examples.append(example)


class Scenario(HasTagsMixin, ScenarioDefinition):
    """A Scenario is a simple ScenarioDefinition with steps."""
    pass


class StepArgument(object):
    """
    A StepArgument is passed to a single step. They are defined AFTER the step:

        Given foo and bar
            <Here comes the step argument for Given>
        When baz
    """
    pass


class DocString(StepArgument):
    """A doc string is a step argument to pass a very long string to it."""
    def __init__(self, text):
        self.text = text


class TableCell(object):
    """Represents a single cell in a TableRow. It holds a values (like a string)."""
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return str(self.value)

    def __str__(self):
        return str(self.value)


class TableRow(object):
    """
    Represents a row in a DataTable.
    """
    def __init__(self, cells=None):
        self.cells: [TableCell] = cells if cells is not None else []

    def get_value_at(self, index):
        return self.cells[index].value

    def get_values(self):
        return [cell.value for cell in self.cells]

    def __repr__(self):
        return 'TableRow - {}'.format(' | '.join([str(c) for c in self.cells]))

    def __str__(self):
        return self.__repr__()


class DataTable(StepArgument):
    """
    A DataTable is a step argument that holds data for steps. There is always a header and rows underneath it.
    The header defines the name of the variables. The rows define the data.

    DataTables can be passed as a StepArgument to a single Step.

    They are also used inside of Examples.
    """
    def __init__(self, header, rows=None):
        self.header: TableRow = header
        self.rows: [TableRow] = rows if rows is not None else []

    def __repr__(self):
        return 'DataTable - {}'.format(str(self.header))

    def get_column_names(self):
        return self.header.get_values()

    def get_row_at(self, index):
        """Returns a specific row (not the header)."""
        return self.rows[index]

    def get_values_as_list(self):
        output = []

        for row in self.rows:
            output.append(tuple(cell.value for cell in row.cells))

        return output

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
    """
    Examples are defined inside of ScenarioOutlines. They have:
        - keyword, name and description
        - a data table that holds data for the ScenarioOutline
    """
    def __init__(self, keyword, name, description, datatable):
        super().__init__()
        self.keyword = keyword
        self.name = name
        self.description = description
        self.datatable = datatable

    def __repr__(self):
        return 'Examples - {} {}'.format(self.keyword, self.name)


class Tag(object):
    """
    A Tag can be used on Rules, Features and ScenariosDefinitions (not Backgrounds though).

    They are used internally by Gherkin to determine which steps should be run. Tags work in an inherit-way.
    That means that parents pass their tags to the children as well (see `UsesTagsMixin` for more information).
    """
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Tag - {}'.format(self.name)


class Rule(HasBackgroundMixin, HasTagsMixin):
    """
    Rules were introduced in v6 of Gherkin. They group multiple ScenarioDefinitions. They have:
        - keyword, name and description
        - an optional background
        - optional tags
    """
    def __init__(self, keyword, name, description, background=None):
        super().__init__(background)
        self.keyword = keyword
        self.name = name
        self.description = description
        self._scenario_definitions = []

    def __repr__(self):
        return 'Rule - {} {}'.format(self.keyword, self.name)

    @property
    def scenario_definitions(self):
        return self._scenario_definitions

    def add_scenario_definition(self, child):
        if not isinstance(child, ScenarioDefinition):
            raise ValueError('You can only add ScenarioDefinitions.')

        self._scenario_definitions.append(child)


class Step(object):
    """
    A step is defined in a ScenarioDefinition and is a part of the scenario. It can receive arguments.
    """
    type = None

    def __init__(self, keyword, text, argument=None):
        if argument is not None and not isinstance(argument, StepArgument):
            raise ValueError('You may only pass a StepArgument to a Step.')

        self.keyword = keyword
        self.text = text
        self.argument = argument
        # all names are written in the format `<name>`
        if self.text:
            self.argument_names = [name.replace(' ', '') for name in re.findall('<(.*?)>', self.text)]
        else:
            self.argument_names = []

    @property
    def has_datatable(self):
        return bool(self.argument and isinstance(self.argument, DataTable))

    def get_parent_step(self):
        """This should return the step that is the parent of the current one."""
        raise NotImplementedError()

    def __repr__(self):
        return '{} - {}{}'.format(self.__class__.__name__.upper(), self.keyword, self.text)

    def __str__(self):
        return '{}{}'.format(self.keyword, self.text)


class ParentStep(Step):
    """
    A base class for GIVEN, THEN, WHEN.
    """
    def __init__(self, keyword, text, argument=None):
        super().__init__(keyword, text, argument)
        self.__sub_steps = []

    def get_parent_step(self):
        """Since this is a parent step, it is technically its own parent."""
        return self

    @property
    def sub_steps(self):
        return self.__sub_steps

    def add_sub_step(self, step):
        if not isinstance(step, SubStep):
            raise ValueError('You can only add a SubStep to a ParentStep.')

        self.__sub_steps.append(step)
        step.parent = self


class SubStep(Step):
    """A base class for AND and BUT."""
    def __init__(self, keyword, text, argument=None):
        super().__init__(keyword, text, argument)
        self.parent = None

    def get_parent_step(self):
        return self.parent


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

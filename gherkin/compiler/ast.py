import re


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
        self._steps = []

    @property
    def steps(self):
        steps = []
        for step in self._steps:
            steps.append(step)

            for sub_step in step.sub_steps:
                steps.append(sub_step)

        return steps

    def add_step(self, step):
        self._steps.append(step)


class Background(ScenarioDefinition):
    pass


class ScenarioOutline(ScenarioDefinition):
    pass


class Scenario(ScenarioDefinition):
    pass


class StepArgument(object):
    pass


class DocString(StepArgument):
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


class DataTable(StepArgument):
    def __init__(self, header, rows=None):
        self.header = header
        self.rows: [TableRow] = rows if rows is not None else []

    def get_row_at(self, index):
        return self.rows[index]

    def get_values(self):
        output = {}
        names = [cell.value for cell in self.header.cells]

        for index, name in enumerate(names):
            values = []

            for row in self.rows:
                values.append(row.get_value_at(index))

            output[name] = values

        return output


class Examples(object):
    def __init__(self, keyword, name, description, datatable):
        self.keyword = keyword
        self.name = name
        self.description = description
        self.datatable = datatable


class Tag(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Tag: {}'.format(self.name)


class Step(object):
    type = None

    def __init__(self, keyword, text):
        self.keyword = keyword
        self.text = text
        self._arguments = {}
        self.argument_names = [name.replace(' ', '') for name in re.findall('{(.*?)}', self.text)]
        self.doc_string = None

    def add_argument(self, argument: StepArgument):
        if isinstance(argument, DocString):
            self.doc_string = argument
        elif isinstance(argument, DataTable):
            datatable_values = argument.get_values()

            for key in datatable_values:
                if key in self.argument_names:
                    self._arguments[key] = datatable_values[key]
        else:
            raise ValueError('You can only pass a DocString or a DataTable to Step')

    @property
    def arguments(self):
        output = [self._arguments[key] for key in self._arguments]

        if self.doc_string:
            output.append(self.doc_string)

        return output

    def __repr__(self):
        return '{} - {}{}'.format(self.__class__.__name__.upper(), self.keyword, self.text)


class ParentStep(Step):
    def __init__(self, keyword, text):
        super().__init__(keyword, text)
        self._sub_steps = []

    @property
    def sub_steps(self):
        return self._sub_steps

    def add_sub_step(self, step):
        self._sub_steps.append(step)
        step.parent = self


class SubStep(Step):
    def __init__(self, keyword, text):
        super().__init__(keyword, text)
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

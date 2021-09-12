from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.replaceable import Replaceable
from nlp.generate.variable import Variable


class Statement(Replaceable, TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '{expression}{comment}'

    def __init__(self, expression, comment=None):
        super().__init__()
        self.expression = expression
        self.comment = comment

    def get_template_context(self, line_indent, indent):
        return {
            'expression': self.expression.to_template(line_indent),
            'comment': '   # {}'.format(self.comment) if self.comment else ''
        }

    def get_children(self):
        return [self.expression]

    def string_matches_variable(self, string, reference_string):
        return False

    def clean_up(self, test_case):
        """
        Can be used to clean up statements before everything is shipped.
        """
        pass


class AssignmentStatement(Statement):
    template = '{variable} = {expression}{comment}'

    def __init__(self, expression, variable):
        super().__init__(expression)
        assert isinstance(variable, Variable), 'You must pass a variable to an assignment statement.'
        self.variable = variable
        variable.set_value(self.expression)

    def get_children(self):
        references = super().get_children()
        references.append(self.variable)
        return references

    def clean_up(self, test_case):
        # if the variable here is not used anywhere, remove it
        if self.variable and not self.variable.is_referenced_in_tc:
            self.variable = None

    def string_matches_variable(self, string, reference_string=None):
        """
        Check if a string matches a the variable of this statement. If you don't pass the reference
        string, the check will be broader and not as precise.
        """
        if not self.variable:
            return False

        copy = self.variable.copy()
        copy.name_predetermined = string

        if reference_string:
            copy.reference_string = reference_string

        return copy == self.variable

    def generate_variable(self, test_case):
        """
        Generate a variable for this statement if there is none yet.
        """
        if not self.variable.name_predetermined:
            similar_statements = []

            for statement in test_case.statements:
                if not isinstance(statement, AssignmentStatement):
                    continue

                if self.variable.reference_strings_are_equal(statement.variable):
                    similar_statements.append(statement)

            self.variable.name_predetermined = str(len(similar_statements) + 1)

    def get_template(self):
        if self.variable:
            return self.template
        return '{expression}{comment}'

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, indent)
        context['variable'] = self.variable

        return context


class ModelFieldAssignmentStatement(Statement):
    template = '{variable_ref}.{field_name} = {expression}{comment}'

    def __init__(self, variable_ref, field_name, assigned_value):
        self.field_name = field_name
        self.variable_ref = variable_ref
        assert not isinstance(variable_ref, Variable)
        super().__init__(assigned_value)

    def get_children(self):
        children = super().get_children()
        children.append(self.variable_ref)
        return children

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, indent)
        context['variable_ref'] = self.variable_ref
        context['field_name'] = self.field_name
        return context


class PassStatement(Statement):
    template = 'pass'

    def __init__(self):
        # there is no expression in a pass statement
        super().__init__(None)

    def get_template_context(self, line_indent, indent):
        return {}


class AssertStatement(Statement):
    template = 'assert {expression}{comment}'


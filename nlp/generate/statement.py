from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin


class Statement(TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '{expression}'

    def __init__(self, expression):
        self.expression = expression
        self.test_case = None

    def get_template_context(self, indent):
        return {'expression': self.expression}

    def on_add_to_test_case(self, test_case):
        self.test_case = test_case

        if self.expression is not None:
            self.expression.on_add_to_test_case(test_case)

    def string_matches_variable(self, string):
        return False


class AssignmentStatement(Statement):
    template = '{variable} = {expression}'

    def __init__(self, expression, variable):
        super().__init__(expression)
        self.variable = variable
        variable.set_value(self.expression)

    def string_matches_variable(self, string):
        if not self.variable:
            return False

        return self.variable.string_matches_variable(string)

    def generate_variable(self, test_case):
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
        return '{expression}'

    def get_template_context(self, indent):
        context = super().get_template_context(indent)
        context['variable'] = self.variable

        return context


class PassStatement(Statement):
    template = 'pass'

    def __init__(self):
        # there is no expression in a pass statement
        super().__init__(None)


class AssertStatement(Statement):
    template = 'assert {expression}'


class RequestStatement(Statement):
    pass

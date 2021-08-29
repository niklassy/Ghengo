from nlp.generate.mixin import TemplateMixin, ReferencedVariablesMixin
from nlp.generate.replaceable import Replaceable
from nlp.generate.variable import VariableReference


class Attribute(ReferencedVariablesMixin, Replaceable, TemplateMixin):
    template = '{variable}.{attribute_name}'

    def __init__(self, variable, attribute_name):
        assert isinstance(variable, VariableReference), 'You may only use VariableReference in Attributes'
        self.variable = variable
        self.attribute_name = attribute_name

    def get_variable_reference_children(self):
        return [self.attribute_name, self.variable]

    def get_template_context(self, line_indent, indent):
        return {'variable': self.variable, 'attribute_name': self.attribute_name}

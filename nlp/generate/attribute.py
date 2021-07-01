from nlp.generate.mixin import TemplateMixin
from nlp.generate.replaceable import Replaceable


class Attribute(Replaceable, TemplateMixin):
    template = '{variable}.{attribute_name}'

    def __init__(self, variable, attribute_name):
        self.variable = variable
        self.attribute_name = attribute_name

    def get_template_context(self, line_indent, indent):
        return {'variable': self.variable, 'attribute_name': self.attribute_name}

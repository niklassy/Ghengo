from nlp.generate.mixin import TemplateMixin


class Index(TemplateMixin):
    template = '{variable}[{index}]'

    def __init__(self, variable, index):
        self.variable = variable
        self.index = index

    def get_template_context(self, line_indent, indent):
        return {'variable': self.variable, 'index': self.index}

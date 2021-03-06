from nlp.generate.mixin import TemplateMixin


class CustomTemplate(TemplateMixin):
    template = '{foo}{bar}'

    def get_template_context(self, line_indent, at_start_of_line):
        return {'foo': 123, 'bar': 'asd'}


def test_mixin_indent():
    mixin = CustomTemplate()
    assert mixin.get_template() == mixin.template
    assert mixin.to_template() == '123asd'
    assert mixin.to_template(5, True) == '     123asd'
    assert mixin.to_template(5, False) == '123asd'
    assert mixin.get_indent_string(5) == '     '

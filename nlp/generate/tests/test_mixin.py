from nlp.generate.mixin import TemplateMixin


class CustomTemplate(TemplateMixin):
    template = '{foo}{bar}'

    def get_template_context(self, parent_intend):
        return {'foo': 123, 'bar': 'asd'}


def test_mixin_indent():
    mixin = CustomTemplate()
    assert mixin.get_template() == mixin.template
    assert mixin.to_template() == '123asd'
    mixin.indent = 5
    assert mixin.to_template() == '     123asd'
    assert mixin.get_indent_string(5) == '     '

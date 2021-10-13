from gherkin.compiler_base.line import Line
from gherkin.compiler_base.token import Token


class CustomToken(Token):
    @classmethod
    def get_patterns(cls):
        return ['///', '?????']


def test_init():
    CustomToken(None, None)
    token = CustomToken('/// 123', Line('test', 1))
    assert token.text == '/// 123'
    assert token.matched_keyword == '///'


def test_string_fits():
    token = CustomToken('/// 123', Line('test', 1))
    assert token.string_contains_matching_pattern('819273') is False
    assert token.string_contains_matching_pattern('asdlkjasd') is False
    assert token.string_contains_matching_pattern('// qwe') is False
    assert token.string_contains_matching_pattern('/// qwe') is True   # <- is true since `///` is the keyword


def test_get_full_matching_text():
    token = CustomToken('/// 123', Line('test', 1))
    assert token.reduce_to_lexeme('12380') is ''
    assert token.reduce_to_lexeme('123qdasda') is ''
    assert token.reduce_to_lexeme('u918203') is ''
    assert token.reduce_to_lexeme('// 123 //') is ''
    assert token.reduce_to_lexeme('/// //') == '///'


def test_get_matching_keyword():
    token = CustomToken('/// 123', Line('test', 1))
    assert token.get_matching_pattern('123123') is None
    assert token.get_matching_pattern('lkjqwe91823') is None
    assert token.get_matching_pattern('//12 123') is None
    assert token.get_matching_pattern('/// 123123') == '///'
    assert token.get_matching_pattern('????? 123123') == '?????'

from gherkin.compiler_base.line import Line
from gherkin.compiler_base.token import Token


class TestToken(Token):
    @classmethod
    def get_keywords(cls):
        return ['///', '?????']


def test_init():
    TestToken(None, None)
    token = TestToken('/// 123', Line('test', 1))
    assert token.text == '/// 123'
    assert token.matched_keyword_full == '///'
    assert token.matched_keyword == '///'


def test_string_fits():
    token = TestToken('/// 123', Line('test', 1))
    assert token.string_contains_token('819273') is False
    assert token.string_contains_token('asdlkjasd') is False
    assert token.string_contains_token('// qwe') is False
    assert token.string_contains_token('/// qwe') is True   # <- is true since `///` is the keyword


def test_get_full_matching_text():
    token = TestToken('/// 123', Line('test', 1))
    assert token.reduce_to_belonging('12380') is ''
    assert token.reduce_to_belonging('123qdasda') is ''
    assert token.reduce_to_belonging('u918203') is ''
    assert token.reduce_to_belonging('// 123 //') is ''
    assert token.reduce_to_belonging('/// //') == '///'


def test_get_matching_keyword():
    token = TestToken('/// 123', Line('test', 1))
    assert token.get_matching_keyword('123123') is None
    assert token.get_matching_keyword('lkjqwe91823') is None
    assert token.get_matching_keyword('//12 123') is None
    assert token.get_matching_keyword('/// 123123') == '///'
    assert token.get_matching_keyword('????? 123123') == '?????'

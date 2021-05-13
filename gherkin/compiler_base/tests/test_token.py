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
    assert token.string_fits_token('819273') is False
    assert token.string_fits_token('asdlkjasd') is False
    assert token.string_fits_token('// qwe') is False
    assert token.string_fits_token('/// qwe') is True   # <- is true since `///` is the keyword


def test_get_full_matching_text():
    token = TestToken('/// 123', Line('test', 1))
    assert token.get_full_matching_text('12380') is None
    assert token.get_full_matching_text('123qdasda') is None
    assert token.get_full_matching_text('u918203') is None
    assert token.get_full_matching_text('// 123 //') is None
    assert token.get_full_matching_text('/// //') == '///'


def test_get_matching_keyword():
    token = TestToken('/// 123', Line('test', 1))
    assert token.get_matching_keyword('123123') is None
    assert token.get_matching_keyword('lkjqwe91823') is None
    assert token.get_matching_keyword('//12 123') is None
    assert token.get_matching_keyword('/// 123123') == '///'
    assert token.get_matching_keyword('????? 123123') == '?????'

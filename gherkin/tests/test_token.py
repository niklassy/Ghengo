import pytest

from gherkin.token import FeatureToken, DataTableToken, RuleToken, ScenarioToken, ScenarioOutlineToken, \
    BackgroundToken, ExamplesToken, GivenToken, WhenToken, ThenToken, AndToken, ButToken, TagsToken, TagToken, \
    CommentToken, LanguageToken, EmptyToken, DescriptionToken
from settings import Settings


@pytest.mark.parametrize(
    'token_cls, valid_string_en, valid_string_de, invalid_string_en, invalid_string_de',
    [
        (FeatureToken, 'Feature:', 'Funktionalität:', 'Feature', 'Feature:'),
        (RuleToken, 'Rule:', 'Regel:', 'Feature:', 'Feature:'),
        (ScenarioToken, 'Scenario:', 'Beispiel:', 'Beispiel:', 'Feature:'),
        (ScenarioToken, 'Example:', 'Szenario:', 'qweqwe:', 'Feature:'),
        (ScenarioOutlineToken, 'Scenario Outline:', 'Szenarien:', 'Scenario', 'Szenario:'),
        (ExamplesToken, 'Examples:', 'Beispiele:', 'Examples', 'Exampless:'),
        (BackgroundToken, 'Background:', 'Hintergrund:', 'Background aa:', 'Rule asd:'),
        (GivenToken, 'Given ', 'Angenommen ', 'given', 'Angenommen:'),
        (WhenToken, 'When ', 'Wenn ', 'Given ', 'Wenn:'),
        (ThenToken, 'Then ', 'Dann ', 'Feature: ', 'Then '),
        (AndToken, 'And ', 'Und ', 'And: ', 'Wenn '),
        (AndToken, '* ', '* ', '*: ', '*:'),
        (ButToken, 'But ', 'Aber ', 'But: ', 'Szenario '),
        (ButToken, '* ', '* ', '*: ', '*:'),
    ]
)
def test_basic_token_classes(token_cls, valid_string_en, valid_string_de, invalid_string_en, invalid_string_de):
    assert token_cls.string_contains_token('{} asdasd qwe asd yxc'.format(valid_string_en)) is True
    assert token_cls.string_contains_token('{} qwe q asd xy'.format(invalid_string_en)) is False
    assert token_cls.reduce_to_belonging('{} ab q a ooq'.format(valid_string_en)) == valid_string_en
    assert token_cls.reduce_to_belonging('{} qq a xc asd qwe'.format(invalid_string_en)) == ''
    Settings.language = 'de'
    assert token_cls.string_contains_token('{} asdasd qwe asd yxc'.format(invalid_string_de)) is False
    assert token_cls.reduce_to_belonging('{} ab q a ooq'.format(invalid_string_de)) == ''
    assert token_cls.string_contains_token('{} qwe akky asde'.format(valid_string_de)) is True
    assert token_cls.reduce_to_belonging('{} ab q a ooq'.format(valid_string_de)) == valid_string_de


@pytest.mark.parametrize(
    'token_cls, valid_string_en, valid_string_de, invalid_string_en, invalid_string_de',
    [
        (DataTableToken, '|a|b|', '|a|b|', 'asdasd', 'asdasd'),
        (DataTableToken, '|   a|b  |', '|  a|b  |', 'a|b', '|b|a'),
        (DataTableToken, '|   a|b | a |', '|  a|b |v |', 'a|b|', 'b|a|'),
        (TagsToken, '@qq', '@dd', '? asd', 'Funktionalität:'),
        (TagsToken, '@qq @tag1', '@dd @123', '@ qwe', '@qwe@qwe'),
        (TagToken, '@qq', '@dd', '@ qwe', '@qwe@qwe'),
        (CommentToken, '#asdasd', '# qweqwe', '/asd', 'Rule: asdasd'),
        (LanguageToken, '#language: de', '# language: en', '# language werwer', 'language de'),
        (LanguageToken, '#language: fr', '# language: es', '#language iquwekl', '#languagede'),
        (EmptyToken, '', '', '.', '.'),
        (EmptyToken, '    ', '  ', ' a  ', '     n'),
        (DescriptionToken, ' asd  a ', 'qq', None, None),
    ]
)
def test_full_line_token_classes(token_cls, valid_string_en, valid_string_de, invalid_string_en, invalid_string_de):
    assert token_cls.string_contains_token(valid_string_en) is True
    if invalid_string_en is not None:
        assert token_cls.reduce_to_belonging(invalid_string_en) == ''
        assert token_cls.string_contains_token(invalid_string_en) is False
    assert token_cls.reduce_to_belonging(valid_string_en) == valid_string_en
    Settings.language = 'de'
    assert token_cls.string_contains_token(valid_string_de) is True
    if invalid_string_de is not None:
        assert token_cls.string_contains_token(invalid_string_de) is False


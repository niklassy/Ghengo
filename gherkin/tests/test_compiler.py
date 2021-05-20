from gherkin.compiler import GherkinLexer, GherkinParser
from gherkin.compiler_base.line import Line
from gherkin.exception import GherkinInvalid
from gherkin.token import LanguageToken, EOFToken, EndOfLineToken, EmptyToken, CommentToken, RuleToken
from gherkin.ast import Comment
from settings import Settings
from test_utils import assert_callable_raises


def test_gherkin_lexer_language():
    """Check that the Gherkin lexer handles languages just as intended."""
    lexer = GherkinLexer(None)
    language = LanguageToken(text='# language de', line=Line('# language de', 3))
    assert_callable_raises(lexer.on_token_added, GherkinInvalid, args=[language])
    language = LanguageToken(text='# language de', line=Line('# language de', 0))
    lexer.on_token_added(language)
    assert Settings.language == 'de'


def test_gherkin_lexer_end_of_tokens():
    """Check that the lexer appends EndOfLine and EOF tokens."""
    lexer = GherkinLexer(None)
    tokens = lexer.tokenize('a\nb\nc')
    assert len(tokens) == 7
    assert isinstance(tokens[-1], EOFToken)
    assert isinstance(tokens[1], EndOfLineToken)
    assert isinstance(tokens[3], EndOfLineToken)
    assert isinstance(tokens[5], EndOfLineToken)


def test_parser_prepare_tokens():
    """Check that comments and empty lines are removed in preparation in parser."""
    parser = GherkinParser(None)
    tokens = [
        RuleToken(None, None),
        EndOfLineToken(None, None),
        EmptyToken(None, None),
        EndOfLineToken(None, None),
        CommentToken(None, None),
        RuleToken(None, None),   # <- normally invalid but it should be handled
        EOFToken(None, None)
    ]
    trimmed_tokens = parser.prepare_tokens(tokens)
    assert len(trimmed_tokens) == 4
    assert isinstance(trimmed_tokens[0], RuleToken)
    assert isinstance(trimmed_tokens[1], EndOfLineToken)
    assert isinstance(trimmed_tokens[2], RuleToken)
    assert isinstance(trimmed_tokens[3], EOFToken)


def test_parser_create_ast():
    """Check that all comments are added to the ast at the end of the creation."""
    class MockAst:
        def __init__(self):
            self.comments = []

        def add_comment(self, c):
            self.comments.append(c)

    parser = GherkinParser(None)
    parser._tokens = [
        RuleToken(None, None),
        EndOfLineToken(None, None),
        EmptyToken(None, None),
        EndOfLineToken(None, None),
        CommentToken(None, None),
    ]

    ast = parser.prepare_ast(MockAst())
    assert len(ast.comments) == 1
    assert isinstance(ast.comments[0], Comment)

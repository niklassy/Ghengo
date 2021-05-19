from gherkin.compiler import GherkinLexer, GherkinParser
from gherkin.compiler_base.line import Line
from gherkin.exception import GherkinInvalid
from gherkin.token import Language, EOF, EndOfLine, Empty, Comment, Rule
from gherkin.ast import Comment as ASTComment
from settings import Settings
from test_utils import assert_callable_raises


def test_gherkin_lexer_language():
    """Check that the Gherkin lexer handles languages just as intended."""
    lexer = GherkinLexer(None)
    language = Language(text='# language de', line=Line('de', 3))
    assert_callable_raises(lexer.on_token_added, GherkinInvalid, args=[language])
    language = Language(text='# language de', line=Line('de', 0))
    lexer.on_token_added(language)
    assert Settings.language == 'de'


def test_gherkin_lexer_end_of_tokens():
    """Check that the lexer appends EndOfLine and EOF tokens."""
    class MockCompiler:
        text = 'a\nb\nc'

    lexer = GherkinLexer(MockCompiler())
    tokens = lexer.tokenize()
    assert len(tokens) == 7
    assert isinstance(tokens[-1], EOF)
    assert isinstance(tokens[1], EndOfLine)
    assert isinstance(tokens[3], EndOfLine)
    assert isinstance(tokens[5], EndOfLine)


def test_parser_prepare_tokens():
    """Check that comments and empty lines are removed in preparation in parser."""
    parser = GherkinParser(None)
    tokens = [
        Rule(None, None),
        EndOfLine(None, None),
        Empty(None, None),
        EndOfLine(None, None),
        Comment(None, None),
        Rule(None, None),   # <- normally invalid but it should be handled
        EOF(None, None)
    ]
    trimmed_tokens = parser.prepare_tokens(tokens)
    assert len(trimmed_tokens) == 4
    assert isinstance(trimmed_tokens[0], Rule)
    assert isinstance(trimmed_tokens[1], EndOfLine)
    assert isinstance(trimmed_tokens[2], Rule)
    assert isinstance(trimmed_tokens[3], EOF)


def test_parser_create_ast():
    """Check that all comments are added to the ast at the end of the creation."""
    class MockAst:
        def __init__(self):
            self.comments = []

        def add_comment(self, c):
            self.comments.append(c)

    parser = GherkinParser(None)
    parser._tokens = [
        Rule(None, None),
        EndOfLine(None, None),
        Empty(None, None),
        EndOfLine(None, None),
        Comment(None, None),
    ]

    ast = parser.prepare_ast(MockAst())
    assert len(ast.comments) == 1
    assert isinstance(ast.comments[0], ASTComment)

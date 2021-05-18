from gherkin.compiler_base.compiler import Lexer
from gherkin.compiler_base.token import Token
from test_utils import assert_callable_raises


class TestToken(Token):
    @classmethod
    def get_keywords(cls):
        return ['ABCDE ', 'ABCDE']


class TestToken2(TestToken):
    @classmethod
    def get_keywords(cls):
        return ['12345']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string


def test_lexer_init():
    """Check that init of the lexer works."""
    lexer = Lexer('compiler')
    assert lexer.tokens == []
    assert lexer.compiler == 'compiler'


def test_lexer_token_fits_string():
    """Check that the default lexer checks tokens via its function."""
    lexer = Lexer(None)
    token = TestToken(None, None)
    assert lexer.token_fits_string(token, '123') is False
    assert lexer.token_fits_string(token, 'abcd') is False
    assert lexer.token_fits_string(token, 'ABCDE') is True


def test_lexer_get_fitting_token_cls():
    """Check that the lexer can extract the correct token class."""
    lexer = Lexer(None)
    lexer.token_classes = [TestToken, TestToken2]
    assert lexer.get_fitting_token_cls('123') is None
    assert lexer.get_fitting_token_cls('ABCDE') == TestToken
    assert lexer.get_fitting_token_cls('12345') == TestToken2


def test_lexer_init_and_add_token():
    """Check that the lexer can add tokens with init_and_add_token"""
    lexer = Lexer(None)
    add_token = lexer.init_and_add_token(TestToken, 'a', 'b')
    assert isinstance(add_token, TestToken)
    assert len(lexer.tokens) == 1
    assert lexer.tokens[0] == add_token


def test_lexer_tokenize():
    """Check that the tokenize of Lexer works as expected."""
    class MockCompiler:
        text = 'ABCDE\n12345 FOO\nABCDE 12345 778293'

    lexer = Lexer(MockCompiler())
    assert_callable_raises(lexer.tokenize, NotImplementedError)     # <- no token classes defined

    lexer.token_classes = [TestToken, TestToken2]
    tokens = lexer.tokenize()
    assert lexer.tokens == tokens
    assert isinstance(tokens[0], TestToken)
    assert tokens[0].text == 'ABCDE'
    assert isinstance(tokens[1], TestToken2)
    assert tokens[1].text == '12345 FOO'
    assert isinstance(tokens[2], TestToken)
    assert tokens[2].text == 'ABCDE '
    assert isinstance(tokens[3], TestToken2)
    assert tokens[3].text == '12345 778293'     # <-- TestToken2 matches till the end of the line


def test_custom_lexer():
    """Check that custom implementations of the lexer work."""
    class CustomLexer(Lexer):
        token_classes = [TestToken, TestToken2]
        on_token_added_calls = []
        on_end_of_line_calls = []
        on_end_of_doc_calls = 0

        def on_token_added(self, token):
            self.on_token_added_calls.append(token)

        def on_end_of_document(self):
            self.on_end_of_doc_calls += 1

        def on_end_of_line(self, line):
            self.on_end_of_line_calls.append(line)

    class MockCompiler:
        text = 'ABCDE\n12345 FOO\nABCDE 12345 778293'

    lexer = CustomLexer(MockCompiler())
    lexer.tokenize()
    assert lexer.on_end_of_doc_calls == 1
    assert len(lexer.on_end_of_line_calls) == 3
    assert len(lexer.on_token_added_calls) == 4


# TODO: test parser!!!

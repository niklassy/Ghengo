from gherkin.compiler_base.compiler import Lexer, Parser
from gherkin.compiler_base.grammar import Grammar
from gherkin.compiler_base.symbol.non_terminal import NonTerminal
from gherkin.compiler_base.rule.operator import Chain
from gherkin.compiler_base.token import Token
from test_utils import assert_callable_raises


class CustomToken(Token):
    @classmethod
    def get_patterns(cls):
        return ['ABCDE ', 'ABCDE']


class CustomToken2(CustomToken):
    @classmethod
    def get_patterns(cls):
        return ['12345']

    @classmethod
    def reduce_to_lexeme(cls, string: str):
        return string


def test_lexer_init():
    """Check that init of the lexer works."""
    lexer = Lexer('compiler')
    assert lexer.tokens == []
    assert lexer.compiler == 'compiler'


def test_lexer_token_fits_string():
    """Check that the default lexer checks tokens via its function."""
    lexer = Lexer(None)
    token = CustomToken(None, None)
    assert lexer.token_fits_string(token, '123') is False
    assert lexer.token_fits_string(token, 'abcd') is False
    assert lexer.token_fits_string(token, 'ABCDE') is True


def test_lexer_get_fitting_token_cls():
    """Check that the lexer can extract the correct token class."""
    lexer = Lexer(None)
    lexer.token_classes = [CustomToken, CustomToken2]
    assert lexer.get_fitting_token_cls('123') is None
    assert lexer.get_fitting_token_cls('ABCDE') == CustomToken
    assert lexer.get_fitting_token_cls('12345') == CustomToken2


def test_lexer_init_and_add_token():
    """Check that the lexer can add tokens with init_and_add_token"""
    lexer = Lexer(None)
    add_token = lexer.init_and_add_token(CustomToken, 'a', 'b')
    assert isinstance(add_token, CustomToken)
    assert len(lexer.tokens) == 1
    assert lexer.tokens[0] == add_token


def test_lexer_tokenize():
    """Check that the tokenize of Lexer works as expected."""
    text = 'ABCDE\n12345 FOO\nABCDE 12345 778293'

    lexer = Lexer(None)
    assert_callable_raises(lexer.tokenize, NotImplementedError, args=[text])     # <- no token classes defined

    lexer.token_classes = [CustomToken, CustomToken2]
    tokens = lexer.tokenize(text)
    assert lexer.tokens == tokens
    assert isinstance(tokens[0], CustomToken)
    assert tokens[0].lexeme == 'ABCDE'
    assert isinstance(tokens[1], CustomToken2)
    assert tokens[1].lexeme == '12345 FOO'
    assert isinstance(tokens[2], CustomToken)
    assert tokens[2].lexeme == 'ABCDE '
    assert isinstance(tokens[3], CustomToken2)
    assert tokens[3].lexeme == '12345 778293'     # <-- TestToken2 matches till the end of the line


def test_custom_lexer():
    """Check that custom implementations of the lexer work."""
    class CustomLexer(Lexer):
        token_classes = [CustomToken, CustomToken2]
        on_token_added_calls = []
        on_end_of_line_calls = []
        on_end_of_doc_calls = 0

        def on_token_added(self, token):
            self.on_token_added_calls.append(token)

        def on_end_of_document(self):
            self.on_end_of_doc_calls += 1

        def on_end_of_line(self, line):
            self.on_end_of_line_calls.append(line)

    lexer = CustomLexer(None)
    lexer.tokenize('ABCDE\n12345 FOO\nABCDE 12345 778293')
    assert lexer.on_end_of_doc_calls == 1
    assert len(lexer.on_end_of_line_calls) == 3
    assert len(lexer.on_token_added_calls) == 4


def test_parser_init():
    """Check that the init of the parser does everything we want."""
    parser = Parser('asd')
    assert parser.compiler == 'asd'
    assert parser.tokens == []


class CustomNonTerminal(NonTerminal):
    rule = Chain([])

    def convert(self, sequence):
        return 'I am done!'


def test_parser_parse_valid():
    """Check that parsing is possible."""
    class CustomGrammar(Grammar):
        start_non_terminal = CustomNonTerminal()

    class CustomParser(Parser):
        grammar = CustomGrammar

        def prepare_tokens(self, tokens):
            self.prepare_called = True
            return tokens

    parser = CustomParser(None)
    assert parser.parse([]) == 'I am done!'
    assert parser.prepare_called is True


def test_parser_invalid():
    """Check that invalid configurations for a parser are handled."""
    class GrammarMissingParser(Parser):
        pass

    assert_callable_raises(GrammarMissingParser(None).parse, ValueError, args=[[]])

    class InvalidRuleParser(Parser):
        token_wrapper_cls = 'asdasd'
        grammar = CustomNonTerminal

    assert_callable_raises(InvalidRuleParser(None).parse, ValueError, args=[[]])

    class InvalidGrammarParser(Parser):
        grammar = 'asdasd'

    assert_callable_raises(InvalidGrammarParser(None).parse, ValueError, args=[[]])

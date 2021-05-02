from gherkin.compiler.grammar import GherkinDocumentGrammar
from gherkin.compiler.rule import RuleToken
from gherkin.document import GherkinDocument
from gherkin.compiler.line import GherkinLine
from gherkin.compiler.token import Feature, Rule, Description, EOF, Background, Scenario, Comment, Given, Then, \
    When, Empty, And, But, Tags, Language, EndOfLine, Token
from settings import Settings


class Lexer(object):
    """Transforms a given text into tokens."""
    _token_classes = [
        Tags,
        Feature,
        Rule,
        Background,
        Scenario,
        Given,
        Then,
        When,
        And,
        But,

        Language,   # <- must stay before comment
        Comment,

        Empty,
        Description,  # <-- keep at the end as fallback
    ]

    def __init__(self, compiler):
        self.compiler = compiler
        self._tokens = []

    @property
    def tokens(self):
        return self._tokens

    def _get_token_for_string(self, string: str):
        for _token in self._token_classes:
            if _token.string_fits_token(string):
                return _token

        return None

    def _init_and_add_token(self, token_cls, text, line):
        """Initializes a token and adds it to the token list"""
        token = token_cls(text=text, line=line)

        # some token classes overwrite the __new__ and return a list of tokens instead, so catch them here
        if isinstance(token, list):
            self._tokens += token
        else:
            self._tokens.append(token)

        return token

    def tokenize(self):
        """
        Takes the text of the compiler and returns a list of tokens that represent entities in a Gherkin document.
        :return: list of Tokens
        """
        self._tokens = []
        text = self.compiler.gherkin_text

        for index, line_text in enumerate(text.splitlines()):
            line = GherkinLine(line_text, index)

            remaining_text = line.trimmed_text
            # loop must run at least once
            while True:

                # search for a token that fits
                token_cls = self._get_token_for_string(remaining_text)
                assert token_cls is not None

                # get the text that the token represents and create a token with it
                matching_text = token_cls.get_full_matching_text(remaining_text)
                token = self._init_and_add_token(token_cls, remaining_text, line)

                # if a language is found, overwrite it
                if isinstance(token, Language):
                    Settings.language = token.locale

                # strip the text that was found and continue with the remaining one
                remaining_text = remaining_text[len(matching_text):]

                # if nothing remains of the line, stop the loop
                if not bool(remaining_text):
                    break

            # add a EndOfLine after each line
            self._init_and_add_token(EndOfLine, line=line, text=None)

        # add EOF at the very end
        self._init_and_add_token(EOF, line=self.tokens[-1].line, text=None)

        return self._tokens


class Parser(object):
    """
    Checks that the tokens are valid aka if the syntax of the input is valid. It also generates an AST with the tokens.
    """
    def __init__(self, compiler):
        self.compiler = compiler
        self._tokens = []

    @property
    def tokens(self):
        return self._tokens

    def parse(self, tokens: [Token]):
        self._tokens = tokens
        self._validate()

        return self._create_ast()

    def _validate(self):
        tokens = self.tokens

        # remove any empty or comment lines
        to_remove = []
        for index, token in enumerate(tokens):
            if isinstance(token, Empty) or isinstance(token, Comment):
                to_remove.append(index)
                to_remove.append(index + 1)

        tokens_trimmed = tokens.copy()
        for index in sorted(to_remove, reverse=True):
            del tokens_trimmed[index]

        head_rule = GherkinDocumentGrammar.rule
        head_rule.validate_sequence([RuleToken(token=t) for t in tokens_trimmed])

    def _create_ast(self):
        pass


class CodeGenerator(object):
    """
    In a normal compiler, it would create code for the machine. In our case it will create an intermediate
    representation (IR). The IR is used later in other areas of the program. It is the internal structure of the code.
    """
    pass


class GherkinCompiler(object):
    """Will parse a gherkin text and analyze line by line in order for easy transformation to an AST."""
    def __init__(self, gherkin_text):
        self.gherkin_text = gherkin_text

    def compile(self):
        lexer = Lexer(compiler=self)
        tokens = lexer.tokenize()

        parser = Parser(self)
        parser.parse(tokens)


        lines = [GherkinLine(text, index) for index, text in enumerate(self.gherkin_text.splitlines())]
        self.gherkin_doc = GherkinDocument(lines)


from gherkin.compiler_base.rule import RuleToken
from gherkin.compiler_base.line import Line
from gherkin.compiler_base.token import Token


class Lexer(object):
    """Transforms a given text into tokens."""
    token_classes = []

    def __init__(self, compiler):
        self.compiler = compiler
        self._tokens: [Token] = []

    @property
    def tokens(self):
        return self._tokens

    def token_fits_string(self, token, string):
        return token.string_fits_token(string)

    def get_fitting_token_cls(self, string: str):
        for _token in self.token_classes:
            if self.token_fits_string(_token, string):
                return _token

        return None

    def init_and_add_token(self, token_cls, text, line):
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
        text = self.compiler.text

        for index, line_text in enumerate(text.splitlines()):
            line = Line(line_text, index)

            remaining_text = line.trimmed_text
            # loop must run at least once
            while True:

                # search for a token that fits
                token_cls = self.get_fitting_token_cls(remaining_text)
                assert token_cls is not None

                # get the text that the token represents and create a token with it
                matching_text = token_cls.get_full_matching_text(remaining_text)
                token = self.init_and_add_token(token_cls, remaining_text, line)

                self.on_token_added(token)

                # strip the text that was found and continue with the remaining one
                remaining_text = remaining_text[len(matching_text):]

                # if nothing remains of the line, stop the loop
                if not bool(remaining_text):
                    break

            self.on_end_of_line(line)

        self.on_end_of_document()

        return self._tokens

    def on_token_added(self, token):
        """Called after a token was added to the list of tokens that will be returned by `tokenize`."""
        pass

    def on_end_of_line(self, line):
        """Called after each line in the document that is used in `tokenize`."""
        pass

    def on_end_of_document(self):
        """Called after the whole document was processed that is used in `tokenize`."""
        pass


class Parser(object):
    """
    Checks that the tokens are valid aka if the syntax of the input is valid. It also generates an AST with the tokens.
    """
    grammar = None

    def __init__(self, compiler):
        self.compiler = compiler
        self._tokens = []

        assert self.grammar is not None

    @property
    def tokens(self):
        return self._tokens

    def parse(self, tokens: [Token]):
        self._tokens = tokens
        return self.validate_and_create_ast()

    def prepare_tokens(self, tokens):
        return tokens

    def validate_and_create_ast(self):
        tokens = self.tokens

        # remove any empty or comment lines
        prepared_tokens = self.prepare_tokens(tokens)

        # get the rule for the whole document and add wrapper around the objects
        wrapped_tokens = [RuleToken(token=t) for t in prepared_tokens]

        # convert also validates the tokens
        obj = self.grammar().convert(wrapped_tokens)

        return obj


class CodeGenerator(object):
    """
    In a normal compiler, it would create code for the machine. In our case it will create an intermediate
    representation (IR). The IR is used later in other areas of the program. It is the internal structure of the code.
    """
    pass


class Compiler(object):
    """Base class to create a compiler that will call a lexer, a parser and a code_generator."""
    lexer = None
    parser = None
    code_generator = None

    def __init__(self, text):
        self.text = text

    def compile(self):
        assert self.lexer
        lexer = self.lexer(compiler=self)
        tokens = lexer.tokenize()

        if self.parser is None:
            return tokens

        parser = self.parser(compiler=self)
        ast = parser.parse(tokens)

        if self.code_generator is None:
            return ast

        # TODO: code generator
        return None


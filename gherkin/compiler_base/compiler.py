import inspect

from gherkin.compiler_base.grammar import Grammar
from gherkin.compiler_base.rule import TokenWrapper
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

    def token_fits_string(self, token_cls, string):
        """A wrapper function to define how a token defines if given string fits it."""
        return token_cls.string_contains_token(string)

    def get_matching_text_for_token(self, token_cls, text) -> str:
        """
        Returns the text that belongs to a token. This is only called if the token class matches
        the text somehow.

        Example:
            A comment token would likely contain the whole line (Python `# asdasdasd` comment).
            In this case, this method should return `# asdasdasd`.

            If a token represents an if, it would only return `if` here, since the rest would
            be represented by a different token, even though it might be on the same line.
        """
        return token_cls.reduce_to_belonging(text)

    def get_fitting_token_cls(self, string: str):
        """Returns the first class in token_classes where token_fits_string returns true"""
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

    def tokenize(self, text):
        """
        Takes the text of the compiler and returns a list of tokens that represent entities in a Gherkin document.
        :return: list of Tokens
        """
        self._tokens = []

        self.on_start_tokenize()

        for index, line_text in enumerate(text.splitlines()):
            line = Line(line_text, index)

            remaining_text = line.trimmed_text
            # loop must run at least once
            while True:
                # search for a token that fits
                token_cls = self.get_fitting_token_cls(remaining_text)
                if token_cls is None:
                    raise NotImplementedError(
                        '`{}` in line {} did not result in a Token object. You should define a token for '
                        'every case.'.format(remaining_text, line.line_index + 1))

                # get the text that the token represents and create a token with it
                matching_text = self.get_matching_text_for_token(token_cls, remaining_text)
                token = self.init_and_add_token(token_cls, matching_text, line)

                self.on_token_added(token)

                # strip the text that was found and continue with the remaining one
                remaining_text = remaining_text[len(matching_text):]

                # if nothing remains of the line, stop the loop
                if not bool(remaining_text):
                    break

            self.on_end_of_line(line)

        self.on_end_of_document()

        return self._tokens

    def on_start_tokenize(self):
        """Is called before starting to tokenize the text input."""
        pass

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
    token_wrapper_cls = TokenWrapper

    def __init__(self, compiler):
        self.compiler = compiler
        self._tokens = []

    @property
    def tokens(self):
        """Returns all the tokens that this parser uses."""
        return self._tokens

    def parse(self, tokens: [Token]):
        """Parses the tokens - it will validate the input and create an AST."""
        if not isinstance(tokens, list):
            raise ValueError('You may only pass a list of tokens to `parse`.')

        self._tokens = tokens
        return self.validate_and_create_ast()

    def prepare_tokens(self, tokens):
        """Can be used by children to modify the tokens before validating them."""
        return tokens

    def get_grammar(self):
        """Returns an instance of the grammar for the parser."""
        return self.grammar()

    def _validate_parser(self):
        """Makes sure that the parser is set up correctly."""
        if not inspect.isclass(self.token_wrapper_cls) or not inspect.isclass(self.grammar):
            raise ValueError('Only use classes for `token_wrapper_cls` and `grammar`')

        if not issubclass(self.token_wrapper_cls, TokenWrapper) and self.token_wrapper_cls != TokenWrapper:
            raise ValueError('You must use a subclass of TokenWrapper for the Parser.')

        if self.grammar is None:
            raise ValueError('You must define a "head"-grammar for your parser that wraps everything else.')

        if not issubclass(self.grammar, Grammar):
            raise ValueError('You must use a subclass of Grammar in a parser.')

    def validate_and_create_ast(self):
        """Validate the tokens and create a AST with them."""
        # validate everything
        self._validate_parser()

        # prepare the tokens before validating them
        prepared_tokens = self.prepare_tokens(self.tokens)

        # wrap the tokens in RuleTokens because they will be used by Rules and Grammars in the validation
        wrapped_tokens = [self.token_wrapper_cls(token=t) for t in prepared_tokens]

        # convert also validates the tokens
        ast = self.get_grammar().convert(wrapped_tokens)

        return self.prepare_ast(ast)

    def prepare_ast(self, ast):
        """You can use this function to do anything to the ast before returning it the the compiler."""
        return ast


class CodeGenerator(object):
    """
    The code generator will perform operations to transform the tokens into some sort of code/ output.
    """
    file_extension = None

    def __init__(self, compiler):
        self.compiler = compiler

    def generate(self, ast):
        raise NotImplementedError()

    def get_file_extension(self):
        return self.file_extension

    def get_file_name(self, ast):
        return 'sample'

    def get_full_file_name(self, ast, output_directory):
        return '{}{}.{}'.format(output_directory, self.get_file_name(ast), self.get_file_extension())


class Compiler(object):
    """Base class to create a compiler that will call a lexer, a parser and a code_generator."""
    lexer_class = None
    parser_class = None
    code_generator_class = None

    def __init__(self):
        self._lexer = None
        self._parser = None
        self._code_generator = None
        self.ast = None

    @property
    def lexer(self):
        assert self.lexer_class is not None
        if self._lexer is None:
            self._lexer = self.lexer_class(self)
        return self._lexer

    @property
    def parser(self):
        assert self.parser_class is not None
        if self._parser is None:
            self._parser = self.parser_class(self)
        return self._parser

    @property
    def code_generator(self):
        assert self.code_generator_class is not None
        if self._code_generator is None:
            self._code_generator = self.code_generator_class(self)
        return self._code_generator

    @classmethod
    def read_file(cls, path):
        """Reads a the file at given path."""
        with open(path) as file:
            file_text = file.read()
        return file_text

    def use_lexer(self, text):
        return self.lexer.tokenize(text)

    def use_parser(self, tokens):
        return self.parser.parse(tokens)

    def compile_text(self, text):
        self.ast = None
        tokens = self.use_lexer(text)
        self.ast = self.use_parser(tokens)

        return self.ast

    def compile_file(self, path):
        file_text = self.read_file(path)
        return self.compile_text(file_text)

    def export_as_text(self, ast=None):
        if self.ast is None and ast is None:
            raise ValueError('You must call either compile_text or compile_file before exporting the AST.')

        ast = ast or self.ast
        return self.code_generator.generate(ast)

    def export_as_file(self, directory_path, ast=None):
        ast = ast or self.ast
        code = self.export_as_text(ast)

        file = open(self.code_generator.get_full_file_name(ast, directory_path), 'w')
        file.write(code)
        file.close()

        return file

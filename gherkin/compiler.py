from gherkin.compiler_base.compiler import Lexer, Compiler, Parser

from gherkin.ast import Comment as ASTComment
from gherkin.grammar import GherkinDocumentGrammar
from gherkin.token import Feature, Rule, Description, EOF, Background, Scenario, Comment, Given, Then, \
    When, Empty, And, But, Tags, Language, EndOfLine, ScenarioOutline, DocString, DataTable, Examples
from settings import Settings


class GherkinLexer(Lexer):
    token_classes = [
        Tags,
        Feature,
        Rule,
        Background,
        Examples,  # <-- must stay before scenario
        ScenarioOutline,  # <-- must stay before scenario
        Scenario,
        Given,
        Then,
        When,
        And,
        But,

        DataTable,
        DocString,
        Language,  # <- must stay before comment
        Comment,

        Empty,
        Description,  # <-- keep at the end as fallback
    ]

    def on_token_added(self, token):
        # if at any point a language is found, set it for the whole process
        if isinstance(token, Language):
            Settings.language = token.locale

    def on_end_of_line(self, line):
        self.init_and_add_token(EndOfLine, line=line, text=None)

    def on_end_of_document(self):
        self.init_and_add_token(EOF, line=self.tokens[-1].line, text=None)


class GherkinParser(Parser):
    grammar = GherkinDocumentGrammar

    def prepare_tokens(self, tokens):
        """Remove any empty lines or comments because they can be everywhere in the Grammar of Gherkin."""

        to_remove = []

        for index, token in enumerate(tokens):
            if isinstance(token, Empty) or isinstance(token, Comment):
                to_remove.append(index)
                # Comment and Empty are always followed by an EndOfLine
                to_remove.append(index + 1)

        tokens_trimmed = tokens.copy()
        for index in sorted(to_remove, reverse=True):
            del tokens_trimmed[index]

        return tokens_trimmed

    def validate_and_create_ast(self):
        ast = super().validate_and_create_ast()

        comments = [token for token in self.tokens if isinstance(token, Comment)]
        for c in comments:
            ast.add_comment(ASTComment(c.text))

        return ast


class GherkinCompiler(Compiler):
    """Will parse a gherkin text and analyze line by line in order for easy transformation to an AST."""
    lexer = GherkinLexer
    parser = GherkinParser

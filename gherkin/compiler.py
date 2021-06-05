from generate.suite import TestSuite, PyTestMarkDecorator
from generate.utils import to_function_name
from gherkin.compiler_base.compiler import Lexer, Compiler, Parser, CodeGenerator

from gherkin.ast import Comment as ASTComment, Scenario, ScenarioOutline, Rule
from gherkin.compiler_base.exception import RuleNotFulfilled, GrammarInvalid, GrammarNotUsed
from gherkin.compiler_base.line import Line
from gherkin.exception import GherkinInvalid
from gherkin.grammar import GherkinDocumentGrammar
from gherkin.token import FeatureToken, RuleToken, DescriptionToken, EOFToken, BackgroundToken, ScenarioToken, \
    CommentToken, GivenToken, ThenToken, WhenToken, EmptyToken, AndToken, ButToken, TagsToken, LanguageToken, \
    EndOfLineToken, ScenarioOutlineToken, DocStringToken, DataTableToken, ExamplesToken
from gherkin.settings import Settings


class GherkinLexer(Lexer):
    token_classes = [
        TagsToken,
        FeatureToken,
        RuleToken,
        BackgroundToken,
        ExamplesToken,  # <-- must stay before scenario
        ScenarioOutlineToken,  # <-- must stay before scenario
        ScenarioToken,
        AndToken,   # <-- must stay before given then when (because of * as a keyword in both of them)
        ButToken,   # <-- same as AND
        GivenToken,
        ThenToken,
        WhenToken,

        DataTableToken,
        DocStringToken,
        LanguageToken,  # <- must stay before comment
        CommentToken,

        EmptyToken,
        DescriptionToken,  # <-- keep at the end as fallback
    ]

    def on_start_tokenize(self):
        # in case this tokenizing is done multiple times, reset the value before starting again
        Settings.language = Settings.DEFAULT_LANGUAGE

    def on_token_added(self, token):
        # the first line may contain the language, so if it is found, set it
        if isinstance(token, LanguageToken):
            if token.line.line_index > 0:
                raise GherkinInvalid('You may only set the language in the first line of the document')

            Settings.language = token.locale

    def on_end_of_line(self, line):
        self.init_and_add_token(EndOfLineToken, line=line, text=None)

    def on_end_of_document(self):
        if len(self.tokens) > 0:
            line = self.tokens[-1].line
        else:
            line = Line('', 0)
        self.init_and_add_token(EOFToken, line=line, text=None)


class GherkinParser(Parser):
    grammar = GherkinDocumentGrammar

    def prepare_tokens(self, tokens):
        """Remove any empty lines or comments because they can be everywhere in the Grammar of Gherkin."""
        to_remove = []

        for index, token in enumerate(tokens):
            if isinstance(token, EmptyToken) or isinstance(token, CommentToken):
                to_remove.append(index)

                # Comment and Empty are always followed by an EndOfLine
                try:
                    next_token = tokens[index + 1]
                    previous_token = tokens[index - 1]
                except IndexError:
                    continue

                # remove the end of line token if the comment/ empty token is wrapped by EndOfLines
                if isinstance(next_token, EndOfLineToken) and isinstance(previous_token, EndOfLineToken):
                    to_remove.append(index + 1)

        tokens_trimmed = tokens.copy()
        for index in sorted(to_remove, reverse=True):
            del tokens_trimmed[index]

        return tokens_trimmed

    def prepare_ast(self, ast):
        """Add all comments to the ast."""
        comments = [token for token in self.tokens if isinstance(token, CommentToken)]
        for c in comments:
            ast.add_comment(ASTComment(c.text))

        return ast


class GherkinToPyTestCodeGenerator(CodeGenerator):
    file_extension = 'py'

    def scenario_to_test_case(self, scenario, suite):
        # TODO: handle scenario outline
        test_case = suite.create_and_add_test_case(scenario.name)

        for tag in scenario.tags:
            test_case.add_decorator(PyTestMarkDecorator(tag.name))

        # first phase: GIVEN clauses
        # TODO: implement
        # for step in scenario.steps:
        #     if isinstance(step, (When, Then)):
        #         break

        return test_case

    def get_file_name(self, ast):
        return 'test_{}'.format(to_function_name(ast.feature.name)) if ast.feature.name else 'test_generated'

    def generate(self, ast):
        if not ast.feature:
            return ''

        suite = TestSuite(ast.feature.name if ast.feature else '')
        for child in ast.feature.children:
            if isinstance(child, (Scenario, ScenarioOutline)):
                self.scenario_to_test_case(child, suite)
                continue

            if isinstance(child, Rule):
                for rule_child in child.scenario_definitions:
                    self.scenario_to_test_case(rule_child, suite)

        return suite.to_template()


class GherkinToPyTestCompiler(Compiler):
    """Will parse a gherkin text and analyze line by line in order for easy transformation to an AST."""
    lexer_class = GherkinLexer
    parser_class = GherkinParser
    code_generator_class = GherkinToPyTestCodeGenerator

    def use_parser(self, tokens):
        try:
            return super().use_parser(tokens)
        except (RuleNotFulfilled, GrammarInvalid, GrammarNotUsed) as e:
            raise GherkinInvalid(str(e))

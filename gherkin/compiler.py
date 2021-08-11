from core.constants import Languages
from django_meta.project import DjangoProject
from nlp.generate.pytest.decorator import PyTestMarkDecorator, PyTestParametrizeDecorator
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.translator import CacheTranslator
from settings import GenerationType
from nlp.generate.utils import to_function_name
from gherkin.compiler_base.compiler import Lexer, Compiler, Parser, CodeGenerator

from gherkin.ast import Comment as ASTComment, ScenarioOutline, Then, When
from gherkin.compiler_base.exception import GrammarInvalid, GrammarNotUsed
from gherkin.compiler_base.line import Line
from gherkin.exception import GherkinInvalid
from gherkin.grammar import GherkinDocumentGrammar, LanguageGrammar
from gherkin.token import FeatureToken, RuleToken, DescriptionToken, EOFToken, BackgroundToken, ScenarioToken, \
    CommentToken, GivenToken, ThenToken, WhenToken, EmptyToken, AndToken, ButToken, TagsToken, LanguageToken, \
    EndOfLineToken, ScenarioOutlineToken, DocStringToken, DataTableToken, ExamplesToken
from settings import Settings
from nlp.tiler import GivenTiler, WhenTiler, ThenTiler


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
        Settings.language = Settings.Defaults.LANGUAGE

    def on_token_added(self, token):
        # the first line may contain the language, so if it is found, set it
        if isinstance(token, LanguageToken):
            if not token.at_valid_position:
                raise GherkinInvalid(
                    'You may only set the language in the first line of the document',
                    grammar=LanguageGrammar(),
                    suggested_tokens=[],
                )

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

    def scenario_to_test_case(self, scenario, suite, project):
        if not scenario.name:
            test_case_name = str(len(suite.test_cases))
        else:
            test_case_name = CacheTranslator(
                src_language=Settings.language,
                target_language=Languages.EN
            ).translate(
                scenario.name.lstrip(),
            )
        test_case = suite.create_and_add_test_case(test_case_name)

        for tag in scenario.tags:
            try:
                test_case.add_decorator(PyTestMarkDecorator(tag.name))
            except test_case.DecoratorAlreadyPresent:
                pass

        # for a scenario outline, pytest offers the parametrize mark that we can add here to simplify everything
        if isinstance(scenario, ScenarioOutline):
            for example in scenario.examples:
                decorator = PyTestParametrizeDecorator(
                    example.datatable.header.get_values(),
                    example.datatable.get_values_as_list(),
                )
                try:
                    test_case.add_decorator(decorator)
                except test_case.DecoratorAlreadyPresent:
                    pass

        # first phase: GIVEN clauses
        in_given_steps = True
        in_when_steps = False
        in_then_steps = False

        for step in scenario.steps:
            tiler = None

            if isinstance(step, (When, Then)) and in_given_steps:
                in_given_steps = False
                in_when_steps = True

            if isinstance(step, Then) and (in_when_steps or in_given_steps):
                in_given_steps = False
                in_when_steps = False
                in_then_steps = True

            if in_given_steps:
                tiler = GivenTiler(
                    ast_object=step,
                    django_project=project,
                    language=Settings.language,
                    test_case=test_case,
                )

            if in_when_steps:
                tiler = WhenTiler(
                    ast_object=step,
                    django_project=project,
                    language=Settings.language,
                    test_case=test_case
                )

            if in_then_steps:
                tiler = ThenTiler(
                    ast_object=step,
                    django_project=project,
                    language=Settings.language,
                    test_case=test_case
                )

            if tiler is not None:
                tiler.add_statements_to_test_case()

        return test_case

    def get_file_name(self, ast):
        return 'test_{}'.format(to_function_name(ast.feature.name)) if ast.feature.name else 'test_generated'

    def generate(self, ast):
        if not ast.feature:
            return ''

        Settings.test_type = GenerationType.PY_TEST

        # TODO: extract django project path from input
        project = DjangoProject('django_sample_project.apps.config.settings')

        suite = PyTestTestSuite(ast.feature.name if ast.feature else '')

        for child in ast.feature.get_scenario_children():
            self.scenario_to_test_case(child, suite, project)

        suite.clean_up()

        Settings.generate_test_type = Settings.Defaults.GENERATE_TEST_TYPE

        return suite.to_template()


class GherkinToPyTestCompiler(Compiler):
    """Will parse a gherkin text and analyze line by line in order for easy transformation to an AST."""
    lexer_class = GherkinLexer
    parser_class = GherkinParser
    code_generator_class = GherkinToPyTestCodeGenerator

    def use_parser(self, tokens):
        try:
            return super().use_parser(tokens)
        except (GrammarInvalid, GrammarNotUsed) as e:
            raise GherkinInvalid(str(e), grammar=e.grammar, suggested_tokens=e.suggested_tokens)

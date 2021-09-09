from core.constants import Languages
from django_meta.project import DjangoProject
from gherkin.grammar import GherkinGrammar
from nlp.generate.pytest.decorator import PyTestMarkDecorator, PyTestParametrizeDecorator
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.translator import CacheTranslator
from settings import GenerationType
from nlp.generate.utils import to_function_name
from gherkin.compiler_base.compiler import Lexer, Compiler, Parser, CodeGenerator

from gherkin.ast import Comment as ASTComment, ScenarioOutline, Then, When, Given
from gherkin.compiler_base.exception import NonTerminalInvalid, NonTerminalNotUsed
from gherkin.compiler_base.line import Line
from gherkin.exception import GherkinInvalid
from gherkin.non_terminal import LanguageNonTerminal
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
                    grammar=LanguageNonTerminal(),
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
    grammar = GherkinGrammar

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

    STEP_TO_TILER = {
        Given: GivenTiler,
        When: WhenTiler,
        Then: ThenTiler,
    }

    def __init__(self, compiler):
        super().__init__(compiler)

        self._suite = None

    def get_test_case_name(self, scenario):
        """Returns the name for the test case of the scenario."""
        if not scenario.name:
            return str(len(self._suite.test_cases))

        translator = CacheTranslator(src_language=Settings.language, target_language=Languages.EN)
        return translator.translate(scenario.name.lstrip())

    def scenario_to_test_case(self, scenario, project):
        """
        Does everything to transform a scenario object into a test case object.
        """
        suite = self._suite

        test_case_name = self.get_test_case_name(scenario)
        test_case = suite.create_and_add_test_case(test_case_name)

        # handle tags
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

        for step in scenario.steps:
            # the parent step will always be given, when or then; if and or but are used, the parent is returned
            parent_step = step.get_parent_step()

            tiler_cls = self.STEP_TO_TILER[parent_step.__class__]
            tiler_instance = tiler_cls(
                ast_object=step,
                django_project=project,
                language=Settings.language,
                test_case=test_case,
            )
            tiler_instance.add_statements_to_test_case()

        return test_case

    def get_file_name(self, ast):
        return 'test_{}'.format(to_function_name(ast.feature.name)) if ast.feature.name else 'test_generated'

    def generate(self, ast):
        if not ast.feature:
            return ''

        # first set the test type and get the django project
        Settings.generate_test_type = GenerationType.PY_TEST
        project = DjangoProject(Settings.django_settings_path)

        # create a suite
        self._suite = PyTestTestSuite(ast.feature.name if ast.feature else '')

        # go through each scenario child and generate test cases
        for child in ast.feature.get_scenario_children():
            self.scenario_to_test_case(child, project)

        # clean up the test suite
        self._suite.clean_up()
        Settings.generate_test_type = Settings.Defaults.GENERATE_TEST_TYPE

        # return the suite as a template string
        return self._suite.to_template()


class GherkinToPyTestCompiler(Compiler):
    """Will parse a gherkin text and analyze line by line in order for easy transformation to an AST."""
    lexer_class = GherkinLexer
    parser_class = GherkinParser
    code_generator_class = GherkinToPyTestCodeGenerator

    def use_parser(self, tokens):
        try:
            return super().use_parser(tokens)
        except (NonTerminalInvalid, NonTerminalNotUsed) as e:
            raise GherkinInvalid(str(e), grammar=e.grammar, suggested_tokens=e.suggested_tokens)

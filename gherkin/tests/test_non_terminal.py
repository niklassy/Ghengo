import pytest

from core.constants import Languages
from gherkin.compiler_base.exception import NonTerminalNotUsed, NonTerminalInvalid
from gherkin.compiler_base.line import Line
from gherkin.compiler_base.symbol.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper
from gherkin.non_terminal import DescriptionNonTerminal, TagsNonTerminal, DocStringNonTerminal, DataTableNonTerminal, \
    AndNonTerminal, ButNonTerminal, \
    ExamplesNonTerminal, GivenNonTerminal, WhenNonTerminal, ThenNonTerminal, StepsNonTerminal, \
    ScenarioOutlineNonTerminal, ScenarioNonTerminal, \
    BackgroundNonTerminal, RuleNonTerminal, FeatureNonTerminal, LanguageNonTerminal, GherkinDocumentNonTerminal, \
    DescriptionChainNonTerminal
from gherkin.tests.valid_token_sequences import examples_sequence, given_sequence, when_sequence, then_sequence, \
    scenario_sequence, scenario_outline_sequence, background_sequence, feature_sequence
from gherkin.token import EOFToken, DescriptionToken, EndOfLineToken, RuleToken, TagToken, DocStringToken, \
    DataTableToken, AndToken, ButToken, ExamplesToken, GivenToken, WhenToken, ThenToken, ScenarioOutlineToken, \
    ScenarioToken, BackgroundToken, FeatureToken, LanguageToken
from gherkin.ast import Description, DataTable, DocString, And, But, Given, When, Then, Background
from settings import Settings
from test_utils import assert_callable_raises


class CustomTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        """In tests we simply pass None to the tokens, so simplify the place to search."""
        return ''


def append_eof_to_chain(chain):
    """Can be used to apply eof to a non_terminal. If you use it, remember to call remove_eof_from_chain."""
    chain.children.append(TerminalSymbol(EOFToken))


def remove_eof_from_chain(chain):
    """Can be used to remove eof of a non_terminal."""
    if chain.children[-1] == TerminalSymbol(EOFToken):
        chain.children = chain.children[:len(chain.children) - 1]
    return chain


def get_sequence(sequence, add_end_of=False):
    """Wraps a sequence of tokens in the TestTokenWrapper. That ways they can be used in the tests."""
    output = []

    for entry in sequence:
        output.append(CustomTokenWrapper(entry))

        if add_end_of:
            output.append(CustomTokenWrapper(EndOfLineToken(None, None)))

    if add_end_of:
        output.append(CustomTokenWrapper(EOFToken(None, None)))
    return output


def test_description_non_terminal_convert():
    """Check that the description non_terminal works as expected when converting."""
    non_terminal = DescriptionNonTerminal()
    append_eof_to_chain(non_terminal.rule)

    # check a valid sequence
    sequence = get_sequence([DescriptionToken(text='teasd', line=None)], add_end_of=True)
    output = non_terminal.convert(sequence=sequence)
    assert isinstance(output, Description)
    assert output.text == 'teasd'

    # check invalid sequences
    sequence = get_sequence([RuleToken(text='asd', line=None)], add_end_of=True)
    assert_callable_raises(non_terminal.convert, NonTerminalNotUsed, args=[sequence])
    sequence = get_sequence([DescriptionToken(text='asd', line=None), RuleToken(text='asd', line=None)])
    assert_callable_raises(non_terminal.convert, NonTerminalInvalid, args=[sequence])

    remove_eof_from_chain(non_terminal.rule)


def test_description_chain():
    """Check that DescriptionChainNonTerminal converts just as expected."""
    non_terminal = DescriptionChainNonTerminal()

    # valid 1
    sequence = get_sequence(
        [DescriptionToken('asd', None), EndOfLineToken(None, None)])
    name, description = non_terminal.convert(sequence)
    assert name == 'asd'
    assert description is None

    # valid 2
    sequence = get_sequence([
        DescriptionToken('asd', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ])
    name, description = non_terminal.convert(sequence)
    assert name == 'asd'
    assert description == 'desc'


def test_tags_non_terminal():
    """Check that TagsNonTerminal converts just as expected."""
    non_terminal = TagsNonTerminal()
    append_eof_to_chain(non_terminal.rule)

    # valid 1
    sequence = get_sequence(
        [TagToken(text='@tag1', line=None), TagToken(text='@tag2', line=None), EndOfLineToken(None, None), EOFToken(None, None)])
    output = non_terminal.convert(sequence)
    assert len(output) == 2
    assert output[0].name == 'tag1'
    assert output[1].name == 'tag2'

    # valid 2
    sequence = get_sequence([TagToken(text='@tag1', line=None), EndOfLineToken(None, None), EOFToken(None, None)])
    output = non_terminal.convert(sequence)
    assert len(output) == 1
    assert output[0].name == 'tag1'

    # invalid sequences
    assert_callable_raises(
        non_terminal.convert, NonTerminalNotUsed, args=[get_sequence([EndOfLineToken(None, None), EOFToken(None, None)])])
    assert_callable_raises(
        non_terminal.convert, NonTerminalInvalid, args=[get_sequence([TagToken('@tag1', None), EOFToken(None, None)])])
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([TagToken('tag1', None), RuleToken(None, None), EOFToken(None, None)])])

    remove_eof_from_chain(non_terminal.rule)


def test_doc_string_non_terminal():
    """Check that DocStrings work as expecting when converting."""
    non_terminal = DocStringNonTerminal()
    append_eof_to_chain(non_terminal.rule)

    # check valid input
    sequence = get_sequence(
        [DocStringToken(None, None), DescriptionToken('a', None), DescriptionToken('b', None), DocStringToken(None, None)], add_end_of=True)
    output = non_terminal.convert(sequence)
    assert output.text == 'a b'

    sequence = get_sequence([DocStringToken(None, None), DocStringToken(None, None)], add_end_of=True)
    output = non_terminal.convert(sequence)
    assert output.text == ''

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([DescriptionToken(None, None)], add_end_of=True)])
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([DocStringToken(None, None), DescriptionToken(None, None)], add_end_of=True)])
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,     # <- since description is at the beginning, DocString cant be identified.
        args=[get_sequence([DescriptionToken(None, None), DocStringToken(None, None)], add_end_of=True)])
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([DocStringToken(None, None), RuleToken(None, None)], add_end_of=True)])

    remove_eof_from_chain(non_terminal.rule)


def test_data_table():
    """Check that data tables are converted correctly."""
    non_terminal = DataTableNonTerminal()
    append_eof_to_chain(non_terminal.rule)

    # check a valid sequence
    sequence = get_sequence(
        [DataTableToken('| col1 | col2|    col3|', None), DataTableToken('| val1 | val2|val3', None)], add_end_of=True)
    output = non_terminal.convert(sequence)
    assert output.header.get_value_at(0) == 'col1'
    assert output.header.get_value_at(1) == 'col2'
    assert output.header.get_value_at(2) == 'col3'
    assert len(output.rows) == 1
    assert output.rows[0].get_value_at(0) == 'val1'
    assert output.rows[0].get_value_at(1) == 'val2'
    assert output.rows[0].get_value_at(2) == 'val3'

    # check that all entries must have the same amount of columns
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        message='All rows in a data table must have the same amount of columns. ',
        args=[get_sequence([DataTableToken('|a|b|c|', None), DataTableToken('|a|b|', None)], add_end_of=True)]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)], add_end_of=True)]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([DataTableToken(None, None)], add_end_of=True)]   # <- not enough columns
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([DataTableToken(None, None), RuleToken(None, None)], add_end_of=True)]
    )

    remove_eof_from_chain(non_terminal.rule)


@pytest.mark.parametrize(
    'non_terminal_cls, token_cls', [(AndNonTerminal, AndToken), (ButNonTerminal, ButToken)]
)
def test_and_but_non_terminal(non_terminal_cls, token_cls):
    """Check that the AND and BUT non_terminal work correctly and convert everything correctly."""
    non_terminal = non_terminal_cls()

    # check valid sequence without docstring or data table
    sequence = get_sequence([token_cls(None, None), DescriptionToken('123', None), EndOfLineToken(None, None)])
    output = non_terminal.convert(sequence)
    assert output.text == '123'
    assert output.keyword is None
    assert output.argument is None

    # check valid sequence with data table
    sequence = get_sequence([
        token_cls(None, None),
        DescriptionToken('543', None),
        EndOfLineToken(None, None),
        DataTableToken('|n|q|', None),
        EndOfLineToken(None, None),
        DataTableToken('|a|b|', None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.text == '543'
    assert output.keyword is None
    assert output.argument is not None
    assert isinstance(output.argument, DataTable)

    # check valid sequence with doc string
    sequence = get_sequence([
        token_cls(None, None),
        DescriptionToken('5435', None),
        EndOfLineToken(None, None),
        DocStringToken('"""', None),
        EndOfLineToken(None, None),
        DocStringToken('"""', None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.text == '5435'
    assert output.keyword is None
    assert output.argument is not None
    assert isinstance(output.argument, DocString)

    # check invalid sequences
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])],
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([DescriptionToken(None, None)])],
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([token_cls(None, None), EndOfLineToken(None, None)])],
    )


def test_examples_non_terminal_valid():
    """Check that the examples non_terminal converts the tokens correctly."""
    non_terminal = ExamplesNonTerminal()

    # check valid sequence without tags
    sequence = get_sequence([
        ExamplesToken(None, None),
        EndOfLineToken(None, None),
        DataTableToken('|n|q|', None),
        EndOfLineToken(None, None),
        DataTableToken('|a|b|', None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.name is None
    assert output.description is None
    assert isinstance(output.datatable, DataTable)
    assert output.tags == []

    # check valid sequence with tags
    sequence = get_sequence([
        TagToken('tag1', None),
        TagToken('tag2', None),
        EndOfLineToken(None, None),
        ExamplesToken(None, None),
        EndOfLineToken(None, None),
        DataTableToken('|n|q|', None),
        EndOfLineToken(None, None),
        DataTableToken('|a|b|', None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.name is None
    assert output.description is None
    assert isinstance(output.datatable, DataTable)
    assert len(output.tags) == 2

    # check valid with description
    sequence = get_sequence([
        ExamplesToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
        DataTableToken('|n|q|', None),
        EndOfLineToken(None, None),
        DataTableToken('|a|b|', None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert isinstance(output.datatable, DataTable)
    assert output.tags == []


def test_examples_non_terminal_invalid():
    """Check that the examples non_terminal handles invalid input correctly."""
    non_terminal = ExamplesNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ExamplesToken(None, None), DataTableToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ExamplesToken(None, None), TagToken(None, None)])]
    )


@pytest.mark.parametrize(
    'non_terminal_cls, token_cls', [
        (GivenNonTerminal, GivenToken),
        (WhenNonTerminal, WhenToken),
        (ThenNonTerminal, ThenToken),
    ]
)
def test_given_when_then_non_terminal_valid(non_terminal_cls, token_cls):
    """Check that step non_terminals handle valid input correctly."""
    non_terminal = non_terminal_cls()

    # check simple step
    sequence = get_sequence([token_cls(None, None), DescriptionToken('blub', None), EndOfLineToken(None, None)])
    output = non_terminal.convert(sequence)
    assert output.text == 'blub'
    assert output.argument is None
    assert output.sub_steps == []

    # check step with sub step
    sequence = get_sequence([
        token_cls(None, None),
        DescriptionToken('blub', None),
        EndOfLineToken(None, None),
        AndToken(None, None),
        DescriptionToken(None, None),
        EndOfLineToken(None, None),
        ButToken(None, None),
        DescriptionToken(None, None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.text == 'blub'
    assert output.argument is None
    assert len(output.sub_steps) == 2
    assert isinstance(output.sub_steps[0], And)
    assert isinstance(output.sub_steps[1], But)

    # check step with argument
    sequence = get_sequence([
        token_cls(None, None),
        DescriptionToken('blub', None),
        EndOfLineToken(None, None),
        DocStringToken(None, None),
        EndOfLineToken(None, None),
        DocStringToken(None, None),
        EndOfLineToken(None, None),
    ])
    output = non_terminal.convert(sequence)
    assert output.text == 'blub'
    assert isinstance(output.argument, DocString)
    assert len(output.sub_steps) == 0


@pytest.mark.parametrize(
    'non_terminal_cls, token_cls', [
        (GivenNonTerminal, GivenToken),
        (WhenNonTerminal, WhenToken),
        (ThenNonTerminal, ThenToken),
    ]
)
def test_given_when_then_non_terminal_invalid(non_terminal_cls, token_cls):
    """Check that steps handle invalid input correctly."""
    non_terminal = non_terminal_cls()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])],
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([token_cls(None, None), RuleToken(None, None)])],
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([token_cls(None, None), EndOfLineToken(None, None)])],
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([token_cls(None, None), AndToken(None, None)])],
    )


def test_steps_non_terminal_valid():
    """Check that the steps non_terminal converts valid input correctly."""
    non_terminal = StepsNonTerminal()

    sequence = get_sequence(given_sequence + when_sequence + then_sequence)
    output = non_terminal.convert(sequence)
    assert len(output) == 3
    assert all([isinstance(output[i], ast_cls) for i, ast_cls in enumerate([Given, When, Then])])

    sequence = get_sequence(when_sequence + then_sequence)
    output = non_terminal.convert(sequence)
    assert len(output) == 2
    assert all([isinstance(output[i], ast_cls) for i, ast_cls in enumerate([When, Then])])

    sequence = get_sequence(then_sequence + then_sequence)
    output = non_terminal.convert(sequence)
    assert len(output) == 2
    assert all([isinstance(output[i], ast_cls) for i, ast_cls in enumerate([Then, Then])])

    sequence = get_sequence(given_sequence + given_sequence + when_sequence + then_sequence)
    output = non_terminal.convert(sequence)
    assert len(output) == 4
    assert all([isinstance(output[i], ast_cls) for i, ast_cls in enumerate([Given, Given, When, Then])])

    sequence = get_sequence(
        given_sequence + given_sequence + when_sequence + when_sequence + then_sequence + then_sequence + then_sequence
    )
    output = non_terminal.convert(sequence)
    assert len(output) == 7
    assert all(
        [isinstance(output[i], ast_cls) for i, ast_cls in enumerate([Given, Given, When, When, Then, Then, Then])])


def test_steps_non_terminal_invalid():
    """Check that the steps non_terminal handles invalid input correctly."""
    non_terminal = StepsNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([RuleToken(None, None)])],
        message='You must use at least one Given, When or Then. '
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([GivenToken(None, None), RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([WhenToken(None, None), RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ThenToken(None, None), RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ThenToken(None, None), GivenToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ThenToken(None, None), WhenToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([WhenToken(None, None), GivenToken(None, None)])]
    )


def test_scenario_outline_non_terminal_valid():
    """Check that the scenario outline handles valid input correctly."""
    non_terminal = ScenarioOutlineNonTerminal()

    base_sequence = [
        ScenarioOutlineToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]

    # valid simple sequence
    sequence = get_sequence(base_sequence + given_sequence + examples_sequence)
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert len(output.tags) == 0
    assert len(output.examples) == 1
    assert output.examples[0].parent == output
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)

    # valid simple sequence with tags
    sequence = get_sequence(
        [TagToken('tag1', None), TagToken('tag2', None), EndOfLineToken(None, None)]
        + base_sequence
        + given_sequence
        + examples_sequence
    )
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert len(output.tags) == 2
    assert len(output.examples) == 1
    assert output.examples[0].parent == output
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)

    # multiple examples
    sequence = get_sequence(base_sequence + given_sequence + examples_sequence + examples_sequence + examples_sequence)
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert len(output.tags) == 0
    assert len(output.examples) == 3
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)

    for example in output.examples:
        assert example.parent == output


def test_scenario_outline_non_terminal_invalid():
    """Check that the scenario outline handles invalid input correctly."""
    non_terminal = ScenarioOutlineNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([TagToken(None, None), EndOfLineToken(None, None), RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ScenarioOutlineToken(None, None), ExamplesToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ScenarioOutlineToken(None, None), EndOfLineToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([])]
    )
    base_sequence = [
        ScenarioOutlineToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]
    # it not allowed to have multiple steps with the same text
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence(base_sequence + given_sequence + given_sequence + examples_sequence)]
    )


def test_scenario_non_terminal_valid():
    """Check that the scenario non_terminal converts valid input correctly."""
    non_terminal = ScenarioNonTerminal()

    base_sequence = [
        ScenarioToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]

    # basic sequence
    sequence = get_sequence(base_sequence + given_sequence)
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)

    # description but no name
    base_sequence_no_name = [
        ScenarioToken(None, None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]
    sequence = get_sequence(base_sequence_no_name + given_sequence)
    output = non_terminal.convert(sequence)
    assert output.name is None
    assert output.description == 'desc'
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)

    # not name and no description
    base_sequence_no_data = [
        ScenarioToken(None, None),
        EndOfLineToken(None, None),
    ]
    sequence = get_sequence(base_sequence_no_data + given_sequence)
    output = non_terminal.convert(sequence)
    assert output.name is None
    assert output.description is None
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)

    # with tags
    sequence = get_sequence([TagToken('tag1', None), EndOfLineToken(None, None)] + base_sequence + given_sequence)
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert len(output.tags) == 1
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)


def test_scenario_non_terminal_invalid():
    """Check that the scenario non_terminal handles invalid input correctly."""
    non_terminal = ScenarioNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([ScenarioOutlineToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ScenarioToken(None, None)] + given_sequence)]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([ScenarioToken(None, None), DescriptionToken(None, None)] + given_sequence)]
    )
    base_sequence = [
        ScenarioToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]
    # it not allowed to have multiple steps with the same text
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence(base_sequence + given_sequence + given_sequence + examples_sequence)]
    )


def test_background_non_terminal_valid():
    """Check that the background handles valid input correctly."""
    non_terminal = BackgroundNonTerminal()

    base_sequence = [
        BackgroundToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]
    sequence = get_sequence(base_sequence + given_sequence)
    output = non_terminal.convert(sequence)
    assert output.name == 'name'
    assert output.description == 'desc'
    assert len(output.steps) == 1
    assert isinstance(output.steps[0], Given)


def test_background_non_terminal_invalid():
    """Check that background non_terminal handles invalid input correctly."""
    non_terminal = BackgroundNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])]
    )
    # does not support tags
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([TagToken(None, None), BackgroundToken(None, None)])]
    )
    # steps missing
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([BackgroundToken(None, None), EndOfLineToken(None, None)])]
    )
    base_sequence = [
        BackgroundToken(None, None),
        DescriptionToken('name', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc', None),
        EndOfLineToken(None, None),
    ]
    # it not allowed to have multiple steps with the same text
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence(base_sequence + given_sequence + given_sequence + examples_sequence)]
    )


def test_rule_non_terminal_valid():
    """Check that rule non_terminal handles valid input correctly."""
    non_terminal = RuleNonTerminal()

    base_sequence = [
        RuleToken(None, None),
        DescriptionToken('name1', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc1', None),
        EndOfLineToken(None, None),
    ]

    # simple version
    output = non_terminal.convert(get_sequence(base_sequence + scenario_sequence))
    assert output.name == 'name1'
    assert output.description == 'desc1'
    assert output.background is None
    assert output.tags == []
    assert len(output.scenario_definitions) == 1

    # multiple scenario definitions
    output = non_terminal.convert(get_sequence(
        base_sequence
        + scenario_sequence
        + scenario_outline_sequence
        + scenario_outline_sequence
        + scenario_sequence
    ))
    assert output.name == 'name1'
    assert output.description == 'desc1'
    assert output.background is None
    assert output.tags == []
    assert len(output.scenario_definitions) == 4

    # tags
    output = non_terminal.convert(get_sequence(
        [TagToken('tag1', None), EndOfLineToken(None, None)] +
        base_sequence
        + scenario_sequence
        + scenario_outline_sequence
        + scenario_outline_sequence
        + scenario_sequence
    ))
    assert output.name == 'name1'
    assert output.description == 'desc1'
    assert output.background is None
    assert len(output.tags) == 1
    assert len(output.scenario_definitions) == 4

    # background
    output = non_terminal.convert(get_sequence(
        [TagToken('tag1', None), EndOfLineToken(None, None)] +
        base_sequence
        + background_sequence
        + scenario_outline_sequence
        + scenario_sequence
    ))
    assert output.name == 'name1'
    assert output.description == 'desc1'
    assert isinstance(output.background, Background)
    assert len(output.tags) == 1
    assert len(output.scenario_definitions) == 2


def test_rule_non_terminal_invalid():
    """Check that the rule non_terminal handles invalid input correctly."""
    non_terminal = RuleNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([DescriptionToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[[]]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([RuleToken(None, None), TagToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([RuleToken(None, None), EndOfLineToken(None, None), GivenToken(None, None)])]
    )


def test_feature_non_terminal_valid():
    """Check that feature non_terminal handles valid input correctly."""
    non_terminal = FeatureNonTerminal()

    base_sequence = [
        FeatureToken(None, None),
        DescriptionToken('name123', None),
        EndOfLineToken(None, None),
        DescriptionToken('desc123', None),
        EndOfLineToken(None, None),
    ]

    # with one scenario
    Settings.language = 'qweqweqwe'
    output = non_terminal.convert(get_sequence(base_sequence + scenario_sequence))
    assert output.name == 'name123'
    assert output.description == 'desc123'
    assert len(output.tags) == 0
    assert output.background is None
    assert len(output.children) == 1
    assert output.language == 'qweqweqwe'
    assert all([child.parent == output for child in output.children])

    # with background
    Settings.language = Settings.Defaults.LANGUAGE
    output = non_terminal.convert(get_sequence(base_sequence + background_sequence + scenario_sequence))
    assert output.name == 'name123'
    assert output.description == 'desc123'
    assert output.background is not None
    assert len(output.children) == 1
    assert output.language == Settings.Defaults.LANGUAGE
    assert all([child.parent == output for child in output.children])
    assert len(output.tags) == 0

    # multiple scenarios
    output = non_terminal.convert(get_sequence(
        base_sequence
        + background_sequence
        + scenario_sequence
        + scenario_outline_sequence
        + scenario_sequence
    ))
    assert len(output.tags) == 0
    assert output.name == 'name123'
    assert output.description == 'desc123'
    assert output.background is not None
    assert len(output.children) == 3
    assert all([child.parent == output for child in output.children])
    assert output.language == Settings.Defaults.LANGUAGE

    # with tags
    output = non_terminal.convert(get_sequence(
        [TagToken('tag1', None), EndOfLineToken(None, None)]
        + base_sequence
        + background_sequence
        + scenario_sequence
        + scenario_outline_sequence
        + scenario_sequence
    ))
    assert output.language == Settings.Defaults.LANGUAGE
    assert len(output.tags) == 1
    assert output.name == 'name123'
    assert output.description == 'desc123'
    assert output.background is not None
    assert len(output.children) == 3
    assert all([child.parent == output for child in output.children])


def test_feature_non_terminal_invalid():
    """Check that the feature non_terminal handles invalid input correctly."""
    non_terminal = FeatureNonTerminal()

    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[[]]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([TagToken(None, None), EndOfLineToken(None, None), RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([FeatureToken(None, None), EndOfLineToken(None, None), DescriptionToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([
            FeatureToken(None, None),
            BackgroundToken(None, None),
            EndOfLineToken(None, None),
            DescriptionToken(None, None)
        ])]
    )


def test_language_non_terminal():
    """Check that language non_terminal handles all forms of input correctly"""
    non_terminal = LanguageNonTerminal()

    # valid input
    output = non_terminal.convert(get_sequence([LanguageToken(None, Line('# language: en', 1)), EndOfLineToken(None, None)]))
    assert output.language == Languages.EN

    # invalid input
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([EndOfLineToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[[]]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalInvalid,
        args=[get_sequence([LanguageToken(None, Line('my text', 1)), DescriptionToken(None, None)])]
    )


def test_gherkin_doc_non_terminal_valid():
    """Check that Gherkin document handles all input correctly."""
    non_terminal = GherkinDocumentNonTerminal()

    # empty doc
    output = non_terminal.convert(get_sequence([EOFToken(None, None)]))
    assert output.feature is None

    # with language
    output = non_terminal.convert(
        get_sequence([LanguageToken(None, Line(Languages.DE, 1)), EndOfLineToken(None, None), EOFToken(None, None)]))
    assert output.feature is None

    # with feature
    output = non_terminal.convert(get_sequence(
        [LanguageToken(None, Line(Languages.DE, 1)), EndOfLineToken(None, None)]
        + feature_sequence
        + [EOFToken(None, None)]
    ))
    assert output.feature is not None
    assert output.feature.parent == output


def test_gherkin_doc_non_terminal_invalid():
    """Check that gherkin doc non_terminal handles invalid input."""
    non_terminal = GherkinDocumentNonTerminal()
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence([RuleToken(None, None)])]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[[]]
    )
    assert_callable_raises(
        non_terminal.convert,
        NonTerminalNotUsed,
        args=[get_sequence(feature_sequence + [RuleToken(None, None)])]
    )

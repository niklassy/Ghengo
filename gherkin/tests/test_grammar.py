from gherkin.compiler_base.exception import GrammarNotUsed, GrammarInvalid
from gherkin.compiler_base.wrapper import TokenWrapper, RuleAlias
from gherkin.grammar import DescriptionGrammar, TagsGrammar, DocStringGrammar, DataTableGrammar
from gherkin.token import EOFToken, DescriptionToken, EndOfLineToken, RuleToken, TagToken, DocStringToken, \
    DataTableToken
from gherkin.ast import Description
from test_utils import assert_callable_raises


class TestTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def append_eof_to_chain(chain):
    chain.child_rule.append(RuleAlias(EOFToken))


def remove_eof_from_chain(chain):
    if chain.child_rule[-1] == RuleAlias(EOFToken):
        chain.child_rule = chain.child_rule[:len(chain.child_rule) - 1]
    return chain


def get_sequence(sequence, add_end_of=False):
    output = []

    for entry in sequence:
        output.append(TestTokenWrapper(entry))

        if add_end_of:
            output.append(TestTokenWrapper(EndOfLineToken(None, None)))

    if add_end_of:
        output.append(TestTokenWrapper(EOFToken(None, None)))
    return output


def test_description_grammar_convert():
    """Check that the description grammar works as expected when converting."""
    grammar = DescriptionGrammar()
    append_eof_to_chain(grammar.rule)

    # check a valid sequence
    sequence = get_sequence([DescriptionToken(text='teasd', line=None)], add_end_of=True)
    output = grammar.convert(sequence=sequence)
    assert isinstance(output, Description)
    assert output.text == 'teasd'

    # check invalid sequences
    sequence = get_sequence([RuleToken(text='asd', line=None)], add_end_of=True)
    assert_callable_raises(grammar.convert, GrammarNotUsed, args=[sequence])
    sequence = get_sequence([DescriptionToken(text='asd', line=None), RuleToken(text='asd', line=None)])
    assert_callable_raises(grammar.convert, GrammarInvalid, args=[sequence])

    remove_eof_from_chain(grammar.rule)


def test_description_get_name_and_description():
    """Check that the DescriptionGrammar helps building the name and description of other grammars."""
    descriptions = [Description(text='val1'), Description(text='val2'), Description(text='val3')]

    name, description = DescriptionGrammar.get_name_and_description(descriptions)
    assert name == 'val1'
    assert description == 'val2 val3'


def test_tags_grammar():
    """Check that TagsGrammar converts just as expected."""
    grammar = TagsGrammar()
    append_eof_to_chain(grammar.rule)

    # valid 1
    sequence = get_sequence(
        [TagToken(text='tag1', line=None), TagToken(text='tag2', line=None), EndOfLineToken(None, None), EOFToken(None, None)])
    output = grammar.convert(sequence)
    assert len(output) == 2
    assert output[0].name == 'tag1'
    assert output[1].name == 'tag2'

    # valid 2
    sequence = get_sequence([TagToken(text='tag1', line=None), EndOfLineToken(None, None), EOFToken(None, None)])
    output = grammar.convert(sequence)
    assert len(output) == 1
    assert output[0].name == 'tag1'

    # invalid sequences
    assert_callable_raises(
        grammar.convert, GrammarNotUsed, args=[get_sequence([EndOfLineToken(None, None), EOFToken(None, None)])])
    assert_callable_raises(
        grammar.convert, GrammarInvalid, args=[get_sequence([TagToken('tag1', None), EOFToken(None, None)])])
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([TagToken('tag1', None), RuleToken(None, None), EOFToken(None, None)])])

    remove_eof_from_chain(grammar.rule)


def test_doc_string_grammar():
    """Check that DocStrings work as expecting when converting."""
    grammar = DocStringGrammar()
    append_eof_to_chain(grammar.rule)

    # check valid input
    sequence = get_sequence(
        [DocStringToken(None, None), DescriptionToken('a', None), DescriptionToken('b', None), DocStringToken(None, None)], add_end_of=True)
    output = grammar.convert(sequence)
    assert output.text == 'a b'

    sequence = get_sequence([DocStringToken(None, None), DocStringToken(None, None)], add_end_of=True)
    output = grammar.convert(sequence)
    assert output.text == ''

    assert_callable_raises(
        grammar.convert,
        GrammarNotUsed,
        args=[get_sequence([DescriptionToken(None, None)], add_end_of=True)])
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DocStringToken(None, None), DescriptionToken(None, None)], add_end_of=True)])
    assert_callable_raises(
        grammar.convert,
        GrammarNotUsed,     # <- since description is at the beginning, DocString cant be identified.
        args=[get_sequence([DescriptionToken(None, None), DocStringToken(None, None)], add_end_of=True)])
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DocStringToken(None, None), RuleToken(None, None)], add_end_of=True)])

    remove_eof_from_chain(grammar.rule)


def test_data_table():
    """Check that data tables are converted correctly."""
    grammar = DataTableGrammar()
    append_eof_to_chain(grammar.rule)

    # check a valid sequence
    sequence = get_sequence(
        [DataTableToken('| col1 | col2|    col3|', None), DataTableToken('| val1 | val2|val3', None)], add_end_of=True)
    output = grammar.convert(sequence)
    assert output.header.get_value_at(0) == 'col1'
    assert output.header.get_value_at(1) == 'col2'
    assert output.header.get_value_at(2) == 'col3'
    assert len(output.rows) == 1
    assert output.rows[0].get_value_at(0) == 'val1'
    assert output.rows[0].get_value_at(1) == 'val2'
    assert output.rows[0].get_value_at(2) == 'val3'

    # check that all entries must have the same amount of columns
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        message='All rows in a data table must have the same amount of columns. ',
        args=[get_sequence([DataTableToken('|a|b|c|', None), DataTableToken('|a|b|', None)], add_end_of=True)]
    )
    assert_callable_raises(
        grammar.convert,
        GrammarNotUsed,
        args=[get_sequence([RuleToken(None, None)], add_end_of=True)]
    )
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DataTableToken(None, None)], add_end_of=True)]   # <- not enough columns
    )
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DataTableToken(None, None), RuleToken(None, None)], add_end_of=True)]
    )

    remove_eof_from_chain(grammar.rule)


def test_and_grammar():
    pass

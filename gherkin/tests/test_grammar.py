from gherkin.compiler_base.exception import GrammarNotUsed, GrammarInvalid
from gherkin.compiler_base.wrapper import RuleToken, RuleAlias
from gherkin.grammar import DescriptionGrammar, TagsGrammar, DocStringGrammar, DataTableGrammar
from gherkin.token import EOF, Description, EndOfLine, Rule, Tag, DocString, DataTable
from gherkin.ast import Description as ASTDescription
from test_utils import assert_callable_raises


class TestRuleToken(RuleToken):
    def get_place_to_search(self) -> str:
        return ''


def append_eof_to_chain(chain):
    chain.child_rule.append(RuleAlias(EOF))


def remove_eof_from_chain(chain):
    if chain.child_rule[-1] == RuleAlias(EOF):
        chain.child_rule = chain.child_rule[:len(chain.child_rule) - 1]
    return chain


def get_sequence(sequence, add_end_of=False):
    output = []

    for entry in sequence:
        output.append(TestRuleToken(entry))

        if add_end_of:
            output.append(TestRuleToken(EndOfLine(None, None)))

    if add_end_of:
        output.append(TestRuleToken(EOF(None, None)))
    return output


def test_description_grammar_convert():
    """Check that the description grammar works as expected when converting."""
    grammar = DescriptionGrammar()
    append_eof_to_chain(grammar.rule)

    # check a valid sequence
    sequence = get_sequence([Description(text='teasd', line=None)], add_end_of=True)
    output = grammar.convert(sequence=sequence)
    assert isinstance(output, ASTDescription)
    assert output.text == 'teasd'

    # check invalid sequences
    sequence = get_sequence([Rule(text='asd', line=None)], add_end_of=True)
    assert_callable_raises(grammar.convert, GrammarNotUsed, args=[sequence])
    sequence = get_sequence([Description(text='asd', line=None), Rule(text='asd', line=None)])
    assert_callable_raises(grammar.convert, GrammarInvalid, args=[sequence])

    remove_eof_from_chain(grammar.rule)


def test_description_get_name_and_description():
    """Check that the DescriptionGrammar helps building the name and description of other grammars."""
    descriptions = [ASTDescription(text='val1'), ASTDescription(text='val2'), ASTDescription(text='val3')]

    name, description = DescriptionGrammar.get_name_and_description(descriptions)
    assert name == 'val1'
    assert description == 'val2 val3'


def test_tags_grammar():
    """Check that TagsGrammar converts just as expected."""
    grammar = TagsGrammar()
    append_eof_to_chain(grammar.rule)

    # valid 1
    sequence = get_sequence(
        [Tag(text='tag1', line=None), Tag(text='tag2', line=None), EndOfLine(None, None), EOF(None, None)])
    output = grammar.convert(sequence)
    assert len(output) == 2
    assert output[0].name == 'tag1'
    assert output[1].name == 'tag2'

    # valid 2
    sequence = get_sequence([Tag(text='tag1', line=None), EndOfLine(None, None), EOF(None, None)])
    output = grammar.convert(sequence)
    assert len(output) == 1
    assert output[0].name == 'tag1'

    # invalid sequences
    assert_callable_raises(
        grammar.convert, GrammarNotUsed, args=[get_sequence([EndOfLine(None, None), EOF(None, None)])])
    assert_callable_raises(
        grammar.convert, GrammarInvalid, args=[get_sequence([Tag('tag1', None), EOF(None, None)])])
    assert_callable_raises(
        grammar.convert, GrammarInvalid, args=[get_sequence([Tag('tag1', None), Rule(None, None), EOF(None, None)])])

    remove_eof_from_chain(grammar.rule)


def test_doc_string_grammar():
    """Check that DocStrings work as expecting when converting."""
    grammar = DocStringGrammar()
    append_eof_to_chain(grammar.rule)

    # check valid input
    sequence = get_sequence(
        [DocString(None, None), Description('a', None), Description('b', None), DocString(None, None)], add_end_of=True)
    output = grammar.convert(sequence)
    assert output.text == 'a b'

    sequence = get_sequence([DocString(None, None), DocString(None, None)], add_end_of=True)
    output = grammar.convert(sequence)
    assert output.text == ''

    assert_callable_raises(
        grammar.convert,
        GrammarNotUsed,
        args=[get_sequence([Description(None, None)], add_end_of=True)])
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DocString(None, None), Description(None, None)], add_end_of=True)])
    assert_callable_raises(
        grammar.convert,
        GrammarNotUsed,     # <- since description is at the beginning, DocString cant be identified.
        args=[get_sequence([Description(None, None), DocString(None, None)], add_end_of=True)])
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DocString(None, None), Rule(None, None)], add_end_of=True)])

    remove_eof_from_chain(grammar.rule)


def test_data_table():
    """Check that data tables are converted correctly."""
    grammar = DataTableGrammar()
    append_eof_to_chain(grammar.rule)

    # check a valid sequence
    sequence = get_sequence(
        [DataTable('| col1 | col2|    col3|', None), DataTable('| val1 | val2|val3', None)], add_end_of=True)
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
        args=[get_sequence([DataTable('|a|b|c|', None), DataTable('|a|b|', None)], add_end_of=True)]
    )
    assert_callable_raises(
        grammar.convert,
        GrammarNotUsed,
        args=[get_sequence([Rule(None, None)], add_end_of=True)]
    )
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DataTable(None, None)], add_end_of=True)]   # <- not enough columns
    )
    assert_callable_raises(
        grammar.convert,
        GrammarInvalid,
        args=[get_sequence([DataTable(None, None), Rule(None, None)], add_end_of=True)]
    )

    remove_eof_from_chain(grammar.rule)

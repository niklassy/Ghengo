from gherkin.compiler_base.exception import GrammarInvalid, GrammarNotUsed
from gherkin.compiler_base.rule import Optional, RuleAlias, RuleToken, Grammar, Chain, OneOf, Repeatable
from gherkin.token import Description, EndOfLine, EOF, Feature
from test_utils import assert_callable_raises


class RuleTestToken(RuleToken):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [RuleTestToken(t) for t in sequence]


def test_grammar_invalid_input():
    """Check if invalid input to grammar is handled."""
    class Grammar1(Grammar):
        rule = None

    class Grammar2(Grammar):
        rule = Repeatable(RuleAlias(EOF))

    class Grammar3(Grammar):
        rule = Optional(RuleAlias(EOF))

    class Grammar6(Grammar):
        rule = OneOf([RuleAlias(EOF)])

    class Grammar4(Grammar):
        criterion_rule_alias = EOF
        rule = Chain([RuleAlias(EOF)])

    class Grammar5(Grammar):
        criterion_rule_alias = Chain([RuleAlias(EOF)])
        rule = Chain([RuleAlias(EOF)])

    assert_callable_raises(Grammar1, ValueError)
    assert_callable_raises(Grammar2, ValueError)
    assert_callable_raises(Grammar3, ValueError)
    assert_callable_raises(Grammar4, ValueError)
    assert_callable_raises(Grammar5, ValueError)
    assert_callable_raises(Grammar6, ValueError)


def test_grammar_chain():
    """Check that the grammar handles a chain as a rule correctly."""
    class MyGrammar(Grammar):
        criterion_rule_alias = RuleAlias(EOF)
        rule = Chain([
            RuleAlias(EOF),
            RuleAlias(EndOfLine),
            RuleAlias(Feature),
        ])

    grammar = MyGrammar()
    # valid input
    grammar.validate_sequence(token_sequence([EOF(None), EndOfLine(None), Feature('', None)]))

    # some other grammar that does not fit this
    assert_callable_raises(
        grammar.validate_sequence,
        GrammarNotUsed,
        args=[token_sequence([Feature('', None), Description('', None)])]   # <- criterion_rule_alias missing
    )

    # the grammar is not valid
    assert_callable_raises(
        grammar.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOF(None), EndOfLine(None), EOF(None)])]      # <- grammar not complete
    )
    assert_callable_raises(
        grammar.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOF(None), EOF(None), EOF(None)])]  # <- grammar not complete
    )


def test_grammar_nested():
    """Check what happens if a grammars are nested."""
    class NestedGrammar(Grammar):
        criterion_rule_alias = RuleAlias(Description)
        rule = Chain([
            RuleAlias(Description),
            RuleAlias(EndOfLine),
        ])

    nested_grammar = NestedGrammar()

    class ParentGrammar(Grammar):
        criterion_rule_alias = RuleAlias(Feature)
        rule = Chain([
            RuleAlias(Feature),
            nested_grammar,
            RuleAlias(EOF),
        ])

    grammar = ParentGrammar()

    # valid input
    grammar.validate_sequence(token_sequence([Feature('', None), Description('', None), EndOfLine(None), EOF(None)]))

    # grammar of parent not used
    error = assert_callable_raises(
        grammar.validate_sequence,
        GrammarNotUsed,
        args=[token_sequence([EOF(None)])],
    )
    assert error.grammar == grammar

    # grammar of child not used, so the grammar of the parent is not valid
    error = assert_callable_raises(
        grammar.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([Feature('', None), EOF(None)])],
    )
    assert error.grammar == grammar

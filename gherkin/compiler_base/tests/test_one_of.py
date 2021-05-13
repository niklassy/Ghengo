from gherkin.compiler_base.exception import GrammarInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.rule import Optional, RuleAlias, RuleToken, Grammar, Chain, OneOf, Repeatable
from gherkin.token import Description, EndOfLine, EOF, Feature, Token
from test_utils import assert_callable_raises


class RuleTestToken(RuleToken):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    assert all([isinstance(t, Token) for t in sequence])
    return [RuleTestToken(t) for t in sequence]


def test_one_of_invalid_input():
    """Check if invalid input to optional is handled."""
    assert_callable_raises(OneOf, ValueError, args=(Description,))
    assert_callable_raises(OneOf, ValueError, args=([Optional(RuleAlias(EOF))],))
    assert_callable_raises(OneOf, ValueError, args=([Repeatable(RuleAlias(EOF), minimum=0)],))
    assert_callable_raises(OneOf, ValueError, args=(RuleAlias(Description),))


def test_one_of_rule_alias():
    """Check that a OneOf rule correctly checks RuleAlias."""
    optional = OneOf([RuleAlias(Description), RuleAlias(EOF), RuleAlias(EndOfLine)])
    optional.validate_sequence(token_sequence([Description('', None)]))
    optional.validate_sequence(token_sequence([EOF(None)]))
    optional.validate_sequence(token_sequence([EndOfLine(None)]))
    assert_callable_raises(optional.validate_sequence, RuleNotFulfilled, args=[[]])
    assert_callable_raises(optional.validate_sequence, RuleNotFulfilled, args=(token_sequence([Feature('', None)]),))


def test_one_of_grammar():
    """Checks that OneOf correctly handles a list of grammars."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(Description)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLine)])

    class Test2Grammar(Grammar):
        criterion_rule_alias = RuleAlias(Feature)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLine)])

    grammar_one_of = OneOf([TestGrammar(), Test2Grammar()])
    # grammar 1 is recognized and works
    grammar_one_of.validate_sequence(token_sequence([Description('', None), EndOfLine(None)]))
    # grammar 2 is recognized and works
    grammar_one_of.validate_sequence(token_sequence([Feature('', None), EndOfLine(None)]))
    # none of the grammars are recognized, so the rule is not fulfilled
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOF(None), EndOfLine(None)])],
    )
    # grammar 1 is recognized and does not work
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([Description('', None), Feature('', None)])],
    )
    # grammar 2 is recognized and does not work
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([Feature('', None), EOF(None)])],
    )


def test_one_of_grammar_and_rule_alias():
    """Checks that OneOf correctly handles a list of combination of grammars and rule aliases."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(Description)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLine)])

    one_of = OneOf([TestGrammar(), RuleAlias(EOF)])
    # rule alias is valid
    one_of.validate_sequence(token_sequence([EOF(None)]))
    # both are not valid
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[token_sequence([EndOfLine(None)])])
    # grammar is recognized and not valid
    assert_callable_raises(
        one_of.validate_sequence, GrammarInvalid, args=[token_sequence([Description('', None), EOF(None)])])


def test_one_of_grammar_and_rules():
    """Checks that OneOf correctly handles a list of combination of grammars and other rules."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(Description)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLine)])

    one_of = OneOf([TestGrammar(), OneOf([RuleAlias(EOF), RuleAlias(Feature)])])
    # rule is valid
    one_of.validate_sequence(token_sequence([EOF(None)]))
    one_of.validate_sequence(token_sequence([Feature('', None)]))
    # both are not valid
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[token_sequence([EndOfLine(None)])])
    # grammar is recognized and not valid
    assert_callable_raises(
        one_of.validate_sequence, GrammarInvalid, args=[token_sequence([Description('', None), EOF(None)])])


def test_one_of_chain():
    """Check that OneOf behaves as expected when combined with a Chain."""
    one_of = OneOf([
        Chain([RuleAlias(Description), RuleAlias(EndOfLine)]),
        Chain([RuleAlias(Feature), RuleAlias(EOF)]),
    ])
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[[]])
    one_of.validate_sequence(token_sequence([Description('', None), EndOfLine(None)]))
    one_of.validate_sequence(token_sequence([Feature('', None), EOF(None)]))
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOF(None), Feature('', None)])]
    )
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLine(None), Description('', None)])]
    )


def test_one_of_repeatable():
    """Check that OneOf behaves as wanted with Repeatable as a child."""
    one_of = OneOf([
        Repeatable(RuleAlias(Description)),
        Repeatable(RuleAlias(Feature)),
    ])

    # check both sequences
    one_of.validate_sequence(token_sequence([Description('', None), Description('', None), Description('', None)]))
    one_of.validate_sequence(token_sequence([Feature('', None), Feature('', None)]))

    # check for empty sequence
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[[]])
    # check if sequence suddenly stops
    assert_callable_raises(
        one_of.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([Feature('', None), Description('', None), Description('', None)])]
    )
    # check if none of values match
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOF(None), Description('', None), Description('', None)])]
    )

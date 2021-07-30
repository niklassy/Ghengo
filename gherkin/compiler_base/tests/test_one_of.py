from gherkin.compiler_base.exception import GrammarInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.rule import Optional, RuleAlias, TokenWrapper, Grammar, Chain, OneOf, Repeatable
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken, Token
from test_utils import assert_callable_raises


class CustomTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    assert all([isinstance(t, Token) for t in sequence])
    return [CustomTokenWrapper(t) for t in sequence]


def test_one_of_invalid_input():
    """Check if invalid input to optional is handled."""
    assert_callable_raises(OneOf, ValueError, args=(DescriptionToken,))
    assert_callable_raises(OneOf, ValueError, args=([Optional(RuleAlias(EOFToken))],))
    assert_callable_raises(OneOf, ValueError, args=([Repeatable(RuleAlias(EOFToken), minimum=0)],))
    assert_callable_raises(OneOf, ValueError, args=(RuleAlias(DescriptionToken),))


def test_one_of_rule_alias():
    """Check that a OneOf rule correctly checks RuleAlias."""
    optional = OneOf([RuleAlias(DescriptionToken), RuleAlias(EOFToken), RuleAlias(EndOfLineToken)])
    optional.validate_sequence(token_sequence([DescriptionToken('', None)]))
    optional.validate_sequence(token_sequence([EOFToken(None)]))
    optional.validate_sequence(token_sequence([EndOfLineToken(None)]))
    assert_callable_raises(optional.validate_sequence, RuleNotFulfilled, args=[[]])
    assert_callable_raises(optional.validate_sequence, RuleNotFulfilled, args=(token_sequence([FeatureToken('', None)]),))


def test_one_of_grammar():
    """Checks that OneOf correctly handles a list of grammars."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(DescriptionToken)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLineToken)])

    class Test2Grammar(Grammar):
        criterion_rule_alias = RuleAlias(FeatureToken)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLineToken)])

    grammar_one_of = OneOf([TestGrammar(), Test2Grammar()])
    # grammar 1 is recognized and works
    grammar_one_of.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None)]))
    # grammar 2 is recognized and works
    grammar_one_of.validate_sequence(token_sequence([FeatureToken('', None), EndOfLineToken(None)]))
    # none of the grammars are recognized, so the rule is not fulfilled
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None)])],
    )
    # grammar 1 is recognized and does not work
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([DescriptionToken('', None), FeatureToken('', None)])],
    )
    # grammar 2 is recognized and does not work
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([FeatureToken('', None), EOFToken(None)])],
    )


def test_one_of_grammar_and_rule_alias():
    """Checks that OneOf correctly handles a list of combination of grammars and rule aliases."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(DescriptionToken)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLineToken)])

    one_of = OneOf([TestGrammar(), RuleAlias(EOFToken)])
    # rule alias is valid
    one_of.validate_sequence(token_sequence([EOFToken(None)]))
    # both are not valid
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[token_sequence([EndOfLineToken(None)])])
    # grammar is recognized and not valid
    assert_callable_raises(
        one_of.validate_sequence, GrammarInvalid, args=[token_sequence([DescriptionToken('', None), EOFToken(None)])])


def test_one_of_grammar_and_rules():
    """Checks that OneOf correctly handles a list of combination of grammars and other rules."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(DescriptionToken)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLineToken)])

    one_of = OneOf([TestGrammar(), OneOf([RuleAlias(EOFToken), RuleAlias(FeatureToken)])])
    # rule is valid
    one_of.validate_sequence(token_sequence([EOFToken(None)]))
    one_of.validate_sequence(token_sequence([FeatureToken('', None)]))
    # both are not valid
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[token_sequence([EndOfLineToken(None)])])
    # grammar is recognized and not valid
    assert_callable_raises(
        one_of.validate_sequence, GrammarInvalid, args=[token_sequence([DescriptionToken('', None), EOFToken(None)])])


def test_one_of_chain():
    """Check that OneOf behaves as expected when combined with a Chain."""
    one_of = OneOf([
        Chain([RuleAlias(DescriptionToken), RuleAlias(EndOfLineToken)]),
        Chain([RuleAlias(FeatureToken), RuleAlias(EOFToken)]),
    ])
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[[]])
    one_of.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None)]))
    one_of.validate_sequence(token_sequence([FeatureToken('', None), EOFToken(None)]))
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), FeatureToken('', None)])]
    )
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None), DescriptionToken('', None)])]
    )


def test_one_of_repeatable():
    """Check that OneOf behaves as wanted with Repeatable as a child."""
    one_of = OneOf([
        Repeatable(RuleAlias(DescriptionToken)),
        Repeatable(RuleAlias(FeatureToken)),
    ])

    # check both sequences
    one_of.validate_sequence(token_sequence([DescriptionToken('', None), DescriptionToken('', None), DescriptionToken('', None)]))
    one_of.validate_sequence(token_sequence([FeatureToken('', None), FeatureToken('', None)]))

    # check for empty sequence
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[[]])
    # check if sequence suddenly stops
    assert_callable_raises(
        one_of.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([FeatureToken('', None), DescriptionToken('', None), DescriptionToken('', None)])]
    )
    # check if none of values match
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), DescriptionToken('', None), DescriptionToken('', None)])]
    )

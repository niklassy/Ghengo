from gherkin.compiler_base.exception import GrammarInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.rule import Optional, RuleAlias, TokenWrapper, Grammar, Chain, OneOf, Repeatable
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken
from test_utils import assert_callable_raises


class TestTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [TestTokenWrapper(t) for t in sequence]


def test_optional_invalid_input():
    """Check if invalid input to optional is handled."""
    assert_callable_raises(Optional, ValueError, args=(DescriptionToken,))
    assert_callable_raises(Optional, ValueError, args=([RuleAlias(DescriptionToken)],))
    assert_callable_raises(Optional, ValueError, args=(Repeatable(RuleAlias(EOFToken)),))


def test_optional_rule_alias():
    """Check that an optional rule makes everything related to a rule alias pass."""
    # ======= validate a rule alias
    optional = Optional(RuleAlias(DescriptionToken))
    optional.validate_sequence(token_sequence([DescriptionToken('', None)]))
    optional.validate_sequence([])


def test_optional_grammar():
    """Check that an optional makes grammars pass if they are not used."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(DescriptionToken)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLineToken)])

    optional = Optional(TestGrammar())
    # the grammar is used, so the grammar should raise an error and Optional should not catch it
    assert_callable_raises(
        optional.validate_sequence,
        GrammarInvalid,
        args=(token_sequence([DescriptionToken('', None), DescriptionToken('', None)]),),
    )
    assert_callable_raises(
        optional.validate_sequence,
        SequenceNotFinished,
        args=(token_sequence([EOFToken(None), EOFToken(None)]),),
    )

    optional.validate_sequence(token_sequence([]))


def test_optional_chain():
    """Check that optional behaves as expected when combined with a Chain."""
    optional = Optional(Chain([
        RuleAlias(DescriptionToken),
        RuleAlias(EndOfLineToken),
    ]))
    optional.validate_sequence(token_sequence([]))
    optional.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None)]))

    assert_callable_raises(
        optional.validate_sequence,
        SequenceNotFinished,
        args=(token_sequence([EOFToken(None)]),)
    )


def test_optional_one_of():
    """Check that one of is correctly handled by Optional."""
    optional = Chain([
        Optional(OneOf([
            RuleAlias(DescriptionToken),
            RuleAlias(EndOfLineToken),
        ])),
        RuleAlias(EOFToken),
    ])
    optional.validate_sequence(token_sequence([EOFToken(None)]))
    optional.validate_sequence(token_sequence([DescriptionToken('', None), EOFToken(None)]))
    optional.validate_sequence(token_sequence([EndOfLineToken(None), EOFToken(None)]))

    assert_callable_raises(
        optional.validate_sequence,
        RuleNotFulfilled,
        args=(token_sequence([FeatureToken('', None), EOFToken(None)]),),
    )


from gherkin.compiler_base.exception import GrammarInvalid, GrammarNotUsed
from gherkin.compiler_base.grammar import Grammar
from gherkin.compiler_base.rule import Optional, Chain, OneOf, Repeatable
from gherkin.compiler_base.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken
from test_utils import assert_callable_raises


class CustomTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [CustomTokenWrapper(t) for t in sequence]


def test_grammar_invalid_input():
    """Check if invalid input to grammar is handled."""
    class Grammar1(Grammar):
        rule = None

    class Grammar2(Grammar):
        rule = Repeatable(TerminalSymbol(EOFToken))

    class Grammar3(Grammar):
        rule = Optional(TerminalSymbol(EOFToken))

    class Grammar6(Grammar):
        rule = OneOf([TerminalSymbol(EOFToken)])

    class Grammar4(Grammar):
        criterion_terminal_symbol = EOFToken
        rule = Chain([TerminalSymbol(EOFToken)])

    class Grammar5(Grammar):
        criterion_terminal_symbol = Chain([TerminalSymbol(EOFToken)])
        rule = Chain([TerminalSymbol(EOFToken)])

    assert_callable_raises(Grammar1, ValueError)
    assert_callable_raises(Grammar2, ValueError)
    assert_callable_raises(Grammar3, ValueError)
    assert_callable_raises(Grammar4, ValueError)
    assert_callable_raises(Grammar5, ValueError)
    assert_callable_raises(Grammar6, ValueError)


def test_grammar_chain():
    """Check that the grammar handles a chain as a rule correctly."""
    class MyGrammar(Grammar):
        criterion_terminal_symbol = TerminalSymbol(EOFToken)
        rule = Chain([
            TerminalSymbol(EOFToken),
            TerminalSymbol(EndOfLineToken),
            TerminalSymbol(FeatureToken),
        ])

    grammar = MyGrammar()
    # valid input
    grammar.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), FeatureToken('', None)]))

    # some other grammar that does not fit this
    assert_callable_raises(
        grammar.validate_sequence,
        GrammarNotUsed,
        args=[token_sequence([FeatureToken('', None), DescriptionToken('', None)])]   # <- criterion_terminal_symbol missing
    )

    # the grammar is not valid
    assert_callable_raises(
        grammar.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None)])]      # <- grammar not complete
    )
    assert_callable_raises(
        grammar.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)])]  # <- grammar not complete
    )


def test_grammar_nested():
    """Check what happens if a grammars are nested."""
    class NestedGrammar(Grammar):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([
            TerminalSymbol(DescriptionToken),
            TerminalSymbol(EndOfLineToken),
        ])

    nested_grammar = NestedGrammar()

    class ParentGrammar(Grammar):
        criterion_terminal_symbol = TerminalSymbol(FeatureToken)
        rule = Chain([
            TerminalSymbol(FeatureToken),
            nested_grammar,
            TerminalSymbol(EOFToken),
        ])

    grammar = ParentGrammar()

    # valid input
    grammar.validate_sequence(token_sequence([FeatureToken('', None), DescriptionToken('', None), EndOfLineToken(None), EOFToken(None)]))

    # grammar of parent not used
    error = assert_callable_raises(
        grammar.validate_sequence,
        GrammarNotUsed,
        args=[token_sequence([EOFToken(None)])],
    )
    assert error.grammar == grammar

    # grammar of child not used, so the grammar of the parent is not valid
    error = assert_callable_raises(
        grammar.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([FeatureToken('', None), EOFToken(None)])],
    )
    assert error.grammar == grammar

from gherkin.compiler import GherkinParser
from gherkin.compiler_base.exception import NonTerminalInvalid, NonTerminalNotUsed
from gherkin.compiler_base.line import Line
from gherkin.exception import GherkinInvalid
from gherkin.non_terminal import ExamplesNonTerminal, GivenNonTerminal, WhenNonTerminal, ThenNonTerminal, ScenarioOutlineNonTerminal, \
    ScenarioNonTerminal, BackgroundNonTerminal, RuleNonTerminal, FeatureNonTerminal
from gherkin.token import EndOfLineToken, EOFToken
from settings import GHERKIN_INDENT_SPACES


def get_sequence_as_lines(sequence):
    sequence_by_line = []

    tokens_in_line = []
    for token in sequence:
        if isinstance(token, EndOfLineToken):
            sequence_by_line.append(tokens_in_line.copy())
            tokens_in_line = []
            continue

        if not isinstance(token, EOFToken):
            tokens_in_line.append(token)

    return sequence_by_line


def get_token_suggestion_after_line(sequence, line_index, return_full_sequence=False):
    sequence = [token.copy() for token in sequence]

    suggested_grammars = [
        GivenNonTerminal,
        WhenNonTerminal,
        ThenNonTerminal,
        ScenarioNonTerminal,
        ExamplesNonTerminal,
        ScenarioOutlineNonTerminal,
        # next two cases are needed to enable autocomplete of Background since it always needs scenarios
        [BackgroundNonTerminal, ScenarioNonTerminal],
        [GivenNonTerminal, ScenarioNonTerminal],
        RuleNonTerminal,
        FeatureNonTerminal,
    ]
    valid_suggestions = []

    tokens_before_line = []
    tokens_after_and_in_line = []

    for token in sequence:
        token_line_index = token.line.line_index

        # remove any token that already exists in that line
        if token_line_index == line_index and not isinstance(token, EOFToken):
            continue

        if token_line_index < line_index:
            tokens_before_line.append(token)

        if token_line_index >= line_index:
            tokens_after_and_in_line.append(token)

    new_line = Line('', line_index)

    for suggested_grammar in suggested_grammars:
        if not isinstance(suggested_grammar, list):
            token_sequence = [token_cls('', new_line) for token_cls in suggested_grammar.get_minimal_sequence()]
        else:
            token_sequence = []
            for grammar in suggested_grammar:
                token_sequence += [token_cls('', new_line) for token_cls in grammar.get_minimal_sequence()]
            suggested_grammar = suggested_grammar[0]
        new_sequence = tokens_before_line + token_sequence + tokens_after_and_in_line

        try:
            GherkinParser(None).parse(new_sequence)
        except (NonTerminalInvalid, NonTerminalNotUsed):
            continue
        else:
            criterion_token_cls = suggested_grammar.criterion_terminal_symbol.token_cls

            if not return_full_sequence:
                valid_suggestions.append(criterion_token_cls)
            else:
                valid_suggestions.append(token_sequence)

    return valid_suggestions


def get_indent_level_for_next_line(tokens, line_index, filter_token):
    token_sequence_suggestions = get_token_suggestion_after_line(
        sequence=tokens,
        line_index=line_index,
        return_full_sequence=True,
    )

    fitting_token = None
    for token_sequence in token_sequence_suggestions:
        first_token = token_sequence[0]

        if first_token.__class__ == filter_token.__class__:
            fitting_token = first_token
            break

        if first_token.line.line_index == line_index and fitting_token is None:
            fitting_token = first_token

    if fitting_token is not None:
        return fitting_token.grammar_meta.get('suggested_indent_level')

    return 0


def get_intend_level_for_line(compiler, text, line_index):
    try:
        compiler.compile_text(text)
        tokens = compiler.parser.tokens

        for token in tokens:
            if token.line.line_index != line_index:
                continue

            return token.grammar_meta.get('suggested_indent_level', 0)

        return 0
    except GherkinInvalid:
        return -1


def get_suggested_intend_after_line(sequence, line_index):
    sequences_lines = get_sequence_as_lines(sequence)

    line_tokens = sequences_lines[line_index]
    intend_level = int(line_tokens[0].line.indent / GHERKIN_INDENT_SPACES)

    children_more_indented = any([token.children_intended for token in line_tokens])
    if children_more_indented:
        intend_level += 1

    return ' ' * GHERKIN_INDENT_SPACES * intend_level


from gherkin.compiler import GherkinParser
from gherkin.compiler_base.exception import NonTerminalInvalid, NonTerminalNotUsed
from gherkin.compiler_base.line import Line
from gherkin.non_terminal import ExamplesNonTerminal, GivenNonTerminal, WhenNonTerminal, ThenNonTerminal, \
    ScenarioOutlineNonTerminal, ScenarioNonTerminal, BackgroundNonTerminal, RuleNonTerminal, FeatureNonTerminal
from gherkin.token import EndOfLineToken, EOFToken


def get_sequence_as_lines(sequence):
    """
    Returns a list of lists. Each entry in the list represents a line and will hold a list of tokens.

    :argument: sequence [Token] - a list of tokens in a document
    """
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
    """
    Returns a list of tokens that can come after a given line.

    :argument: sequence [Token] - a list of tokens that are already present in the document
    :argument: line_index int - the line after that index will be checked
    :argument: return_full_sequence bool - returns the whole sequence that makes something valid; if false only the
                                           first token of that sequence is returned
    """
    sequence = [token.copy() for token in sequence]

    suggested_non_terminals = [
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

    for suggested_non_terminal in suggested_non_terminals:
        if not isinstance(suggested_non_terminal, list):
            token_sequence = [token_cls('', new_line) for token_cls in suggested_non_terminal.get_minimal_sequence()]
        else:
            token_sequence = []
            for non_terminal in suggested_non_terminal:
                token_sequence += [token_cls('', new_line) for token_cls in non_terminal.get_minimal_sequence()]
            suggested_non_terminal = suggested_non_terminal[0]
        new_sequence = tokens_before_line + token_sequence + tokens_after_and_in_line

        try:
            GherkinParser(None).parse(new_sequence)
        except (NonTerminalInvalid, NonTerminalNotUsed):
            continue
        else:
            criterion_token_cls = suggested_non_terminal.criterion_terminal_symbol.token_cls

            if not return_full_sequence:
                valid_suggestions.append(criterion_token_cls)
            else:
                valid_suggestions.append(token_sequence)

    return valid_suggestions


def get_indent_level_for_next_line(tokens, line_index, filter_token):
    """
    Returns the indent level for the next line in Gherkin. This can be used to determine how indented the cursor
    should be after hitting Enter in a gherkin document.

    :argument: tokens [Token] - list of tokens that are already in the document
    :argument: line_index - the index of a line in the document, this will return the indent for the line after that
    :argument: filter_token Token - a token which this function will filter for as valid next tokens
    """
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
        return fitting_token.non_terminal_meta.get('suggested_indent_level')

    return 0


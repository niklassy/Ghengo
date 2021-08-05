from gherkin.token import EndOfLineToken, EOFToken
from settings import GHERKIN_INDENT_SPACES


def get_suggested_intend_after_line(sequence, line_index):
    sequence_by_line = []

    tokens_in_line = []
    for token in sequence:
        if isinstance(token, EndOfLineToken):
            sequence_by_line.append(tokens_in_line.copy())
            tokens_in_line = []
            continue

        if not isinstance(token, EOFToken):
            tokens_in_line.append(token)

    line_tokens = sequence_by_line[line_index]
    intend_level = int(line_tokens[0].line.intend / GHERKIN_INDENT_SPACES)

    children_more_indented = any([token.children_intended for token in line_tokens])
    if children_more_indented:
        intend_level += 1

    return ' ' * GHERKIN_INDENT_SPACES * intend_level


from gherkin.compiler import GherkinParser
from gherkin.compiler_base.exception import GrammarInvalid, GrammarNotUsed
from gherkin.compiler_base.line import Line
from gherkin.grammar import ExamplesGrammar, GivenGrammar, WhenGrammar, ThenGrammar, ScenarioOutlineGrammar, \
    ScenarioGrammar, BackgroundGrammar, RuleGrammar, FeatureGrammar
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


def get_token_suggestion_after_line(sequence, line_index):
    sequence = [token.copy() for token in sequence]

    suggested_grammars = [
        GivenGrammar,
        WhenGrammar,
        ThenGrammar,
        ScenarioGrammar,
        ExamplesGrammar,
        ScenarioOutlineGrammar,
        BackgroundGrammar,
        RuleGrammar,
        FeatureGrammar,
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
        token_sequence = [token_cls('', new_line) for token_cls in suggested_grammar.get_minimal_sequence()]
        new_sequence = tokens_before_line + token_sequence + tokens_after_and_in_line

        try:
            GherkinParser(None).parse(new_sequence)
        except (GrammarInvalid, GrammarNotUsed):
            continue
        else:
            criterion_token_cls = suggested_grammar.criterion_rule_alias.token_cls

            for keyword in criterion_token_cls.get_keywords():
                if '*' not in keyword:
                    valid_suggestions.append(keyword)

    return valid_suggestions


def get_suggested_intend_after_line(sequence, line_index):
    sequences_lines = get_sequence_as_lines(sequence)

    line_tokens = sequences_lines[line_index]
    intend_level = int(line_tokens[0].line.intend / GHERKIN_INDENT_SPACES)

    children_more_indented = any([token.children_intended for token in line_tokens])
    if children_more_indented:
        intend_level += 1

    return ' ' * GHERKIN_INDENT_SPACES * intend_level


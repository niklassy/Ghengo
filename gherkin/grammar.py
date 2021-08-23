from gherkin.compiler_base.grammar import Grammar
from gherkin.non_terminal import GherkinDocumentNonTerminal


class GherkinGrammar(Grammar):
    start_non_terminal = GherkinDocumentNonTerminal()


a = GherkinGrammar().to_ebnf()
b = 1

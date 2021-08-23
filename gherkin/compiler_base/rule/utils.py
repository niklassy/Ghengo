from gherkin.compiler_base.mixin import IndentMixin
from gherkin.compiler_base.recursive import RecursiveValidationContainer, RecursiveValidationBase
from gherkin.compiler_base.rule.operator import Chain


class IndentBlock(IndentMixin, RecursiveValidationContainer):
    """
    This class can be used to indicate that every child should be of a higher indent.
    """
    def __init__(self, child):
        if isinstance(child, list):
            child = Chain(child)

        super().__init__()
        self.child = child
        self.child.set_parent(self)

    def to_ebnf(self, ebnf_entries=None):
        return self.child.to_ebnf(ebnf_entries)

    def get_child_validator(self) -> RecursiveValidationBase:
        """Simply pass all validation to the child."""
        return self.child

    def get_suggested_indent_level(self):
        """
        Everything below this element has a higher level of ident.
        """
        level = super().get_suggested_indent_level()

        return level + 1

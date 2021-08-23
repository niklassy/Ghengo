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
        self.child_rule = child
        self.child_rule.set_parent(self)

    def get_child_validator(self) -> RecursiveValidationBase:
        """Simply pass all validation to the child."""
        return self.child_rule

    def get_suggested_indent_level(self):
        """
        Everything below this element has a higher level of ident.
        """
        level = super().get_suggested_indent_level()

        return level + 1

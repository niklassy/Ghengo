from abc import ABC

from gherkin.compiler_base.mixin import IndentMixin, SequenceToObjectMixin


class Symbol(IndentMixin, SequenceToObjectMixin, ABC):
    pass

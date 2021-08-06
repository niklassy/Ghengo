class SequenceToObjectMixin(object):
    """
    This mixin is used in Rules, Grammars and so on to define a function that turns a sequence of tokens into
    an object.
    """
    def sequence_to_object(self, sequence, index=0):
        """
        Defines how a sequence at a given index is transformed into an object.

        This function may return a RuleToken, None, [RuleToken] or a custom object.
        """
        raise NotImplementedError()


class IndentMixin(object):
    def __init__(self):
        super().__init__()

        self.parent = None

    def set_parent(self, parent):
        self.parent = parent

    def get_suggested_indent_level(self):
        if self.parent is None:
            return 0

        return self.parent.get_suggested_indent_level()

class IndentMixin(object):
    """
    This is a mixin that is used to keep track of parents and the definition on indentation.
    """
    def __init__(self):
        super().__init__()

        self.parent = None

    def set_parent(self, parent):
        self.parent = parent

    def get_suggested_indent_level(self):
        if self.parent is None:
            return 0

        return self.parent.get_suggested_indent_level()

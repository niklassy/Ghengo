class _WindowValues(object):
    def __init__(self):
        self.values = {}

    def set_values(self, values):
        self.values = values

    def get_values(self):
        return self.values


WindowValues = _WindowValues()

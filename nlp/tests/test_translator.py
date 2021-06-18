class CallCounter:
    def __init__(self, func):
        self.func = func
        self.call_counter = 0

    def __call__(self, *args, **kwargs):
        self.call_counter += 1
        return self.func(*args, **kwargs)


# TODO: write tests again

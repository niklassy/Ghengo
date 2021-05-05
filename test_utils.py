def assert_callable_raises(to_call, exception_cls, message=None, args=None, kwargs=None):
    """Checks that a given callable results in an error."""
    if args is None:
        args = ()

    if kwargs is None:
        kwargs = {}

    try:
        to_call(*args, **kwargs)
        assert False
    except exception_cls as e:
        if message is not None:
            assert message == str(e)
        return e

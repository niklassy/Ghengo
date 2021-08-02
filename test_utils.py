def assert_callable_raises(to_call, exception_cls, message=None, args=None, kwargs=None):
    """Checks that a given callable results in an error."""
    if args is None:
        args = ()

    if kwargs is None:
        kwargs = {}

    try:
        out = to_call(*args, **kwargs)
        assert False, 'The call did not raise the provided error. It returned: {}'.format(out)
    except exception_cls as e:
        if message is not None:
            assert message == str(e)
        return e

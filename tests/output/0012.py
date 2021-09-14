import pytest


@pytest.mark.django_db
def test_0(to_do_factory):
    to_do_factory(
        from_other_system=False,
        text='qwe',
        number=123123123123123123123123123123123123123123123123123123123123,
        owner='alice'
    )
    to_do_factory(
        from_other_system=False,
        text='qwe',
        number=123123123123123123123123123123123123123123123123123123123123,
        owner='alice'
    )


@pytest.mark.parametrize(
    'name',
    [
        ('asdasdasdasdasdasdasdasd123123123123123123123123123123',),
        ('asdasdasdasdasdasdasdqweqweqweqwe3123123123123123123123123123',)
    ]
)
@pytest.mark.django_db
def test_1(name, order_factory):
    order_factory(name=name)

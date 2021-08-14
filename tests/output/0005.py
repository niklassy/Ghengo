import pytest


@pytest.mark.django_db
def test_simple_create(order_factory):
    order_factory()
    order_factory(name='foo')


@pytest.mark.django_db
def test_non_existant(roof_factory):
    roof_factory(broad=3, length=7)


@pytest.mark.django_db
def test_referencing(to_do_factory, order_factory):
    to_do_1 = to_do_factory()
    order_1 = order_factory()
    order_1.to_dos.add(to_do_1)

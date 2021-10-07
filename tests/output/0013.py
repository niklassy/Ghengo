import pytest
from django_sample_project.apps.order.models import Order


@pytest.mark.django_db
def test_0(order_factory):
    order_factory(number=2)
    order_factory(number=3, name='test')
    qs_0 = Order.objects.filter(number__gte=2)
    assert qs_0.count() >= 2


@pytest.mark.django_db
def test_1(order_factory):
    order_factory(number=2)
    order_factory(number=3, name='test')
    qs_0 = Order.objects.filter(number__gte=2)
    assert qs_0.count() <= 3


@pytest.mark.django_db
def test_2(order_factory):
    order_factory(number=2)
    order_factory(number=3, name='test')
    qs_0 = Order.objects.filter(number__lte=4)
    assert qs_0.count() < 3

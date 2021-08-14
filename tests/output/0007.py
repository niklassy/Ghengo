import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django_sample_project.apps.order.models import Order


@pytest.mark.django_db
def test_previous_model(order_factory):
    order_1 = order_factory()
    client = APIClient()
    client.put(reverse('orders-detail', {'pk': order_1.pk}), {'name': 'foo'})
    qs_0 = Order.objects.filter(give=True, name='foo')
    assert qs_0.count() == 1


@pytest.mark.django_db
def test_1(order_factory):
    order_1 = order_factory()
    client = APIClient()
    client.put(reverse('orders-detail', {'pk': order_1.pk}), {'name': 'bar'})
    qs_0 = Order.objects.filter(name='bar')
    assert qs_0.exists()

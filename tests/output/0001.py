import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django_sample_project.apps.order.models import Order


@pytest.mark.django_db
def test_file(order_factory):
    order_1 = order_factory(name='foo')
    order_factory()
    client = APIClient()
    client.delete(reverse('orders-detail', {'pk': order_1.pk}))
    client.post(reverse('orders-detail'))
    qs_0 = Order.objects.all()
    assert qs_0.count() == 2
    qs_1 = Order.objects.all()
    assert qs_1.count() == 2

import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_previous_model(order_factory):
    order_1 = order_factory()
    client = APIClient()
    client.put(reverse('orders-detail', {'pk': order_1.pk}), {'name': 'foo'})
    order_1.refresh_from_db()
    assert order_1.name == 'foo'

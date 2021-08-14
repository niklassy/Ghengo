import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_0(order_factory, user_factory):
    order_1 = order_factory()
    alice = user_factory()
    client = APIClient()
    client.force_authenticate(alice)
    client.get(reverse('orders-detail', {'pk': order_1.pk}))


def test_1():
    client = APIClient()
    client.get(reverse('orders-list'))

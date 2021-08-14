import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_put(order_factory):
    order_factory()
    client = APIClient()
    client.put(reverse('orders-detail'), {'name': 'foo'})


def test_post_office():
    client = APIClient()
    client.post(reverse('orders-detail'), {'name': 'foo'})


@pytest.mark.django_db
def test_delete(order_factory):
    order_1 = order_factory()
    client = APIClient()
    client.delete(reverse('orders-detail', {'pk': order_1.pk}))


def test_custom_endpoint():
    client = APIClient()
    client.post(reverse('orders-book'))

import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_file_and_use_in_order(order_factory):
    order_factory(name='foo')
    client = APIClient()
    response = client.get(reverse('orders-list'))
    assert response.status_code == 200
    assert len(response.data) == 1
    entry_0 = response.data[0]
    assert entry_0.get('name') == 'foo'


@pytest.mark.django_db
def test_1(order_factory):
    order_factory(name='foo')
    order_factory(name='baz')
    client = APIClient()
    response = client.get(reverse('orders-list'))
    assert len(response.data) == 2
    entry_1 = response.data[1]
    assert entry_1.get('name') == 'baz'

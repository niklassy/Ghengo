import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_check_single_response_entry(order_factory):
    order_1 = order_factory(name='foo')
    client = APIClient()
    response = client.get(reverse('orders-detail', {'pk': order_1.pk}))
    resp_data = response.data
    assert resp_data.get('name') == 'foo'
    assert resp_data.get('id') == order_1.pk

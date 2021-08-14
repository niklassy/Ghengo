from django.core.files.uploadedfile import SimpleUploadedFile
import pytest
from rest_framework.test import APIClient
from django.urls import reverse


@pytest.mark.django_db
def test_newwwww(user_factory, order_factory):
    asd = SimpleUploadedFile(content='My content', name='asd.docx')
    alice = user_factory(last_name='alice', email='a@local.local')
    order_factory(name='Hallo')
    client = APIClient()
    client.force_authenticate(alice)
    client.post(reverse('orders-detail'), {'file': asd})

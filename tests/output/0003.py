from django.core.files.uploadedfile import SimpleUploadedFile
import pytest


@pytest.mark.django_db
def test_file_and_use_in_order(order_factory):
    bar = SimpleUploadedFile(content='foo', name='bar.psd')
    order_factory(proof=bar)

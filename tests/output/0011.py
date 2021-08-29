import pytest
from django.contrib.auth.models import Permission


@pytest.mark.django_db
def test_0(to_do_factory, order_factory):
    to_do_1 = to_do_factory()
    order_1 = order_factory()
    order_1.to_dos.add(to_do_1)


@pytest.mark.django_db
def test_1(order_factory):
    order_1 = order_factory()
    order_1.name = 'foo'
    order_1.save()


@pytest.mark.django_db
def test_2(user_factory):
    user_1 = user_factory()
    user_1.user_permissions.add(Permission.objects.filter(
        content_type__model='order',
        content_type__app_label='order',
        codename='view_order'
    ))

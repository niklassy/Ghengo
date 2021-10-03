from rest_framework.serializers import ModelSerializer

from django_sample_project.apps.order.models import Order


class OrderSerializer(ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'owner', 'number']

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from django_sample_project.apps.order.models import Order


class OrderSerializer(ModelSerializer):
    uses_coal = serializers.BooleanField()

    class Meta:
        model = Order
        fields = ['id', 'uses_coal']

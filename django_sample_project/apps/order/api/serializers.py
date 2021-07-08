from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from django_sample_project.apps.order.models import Order, ToDo


class OrderSerializer(ModelSerializer):
    uses_coal = serializers.BooleanField()
    name = serializers.ModelField(Order.name)
    collections = serializers.PrimaryKeyRelatedField(many=True, queryset=ToDo.objects.all())

    class Meta:
        model = Order
        fields = ['id', 'uses_coal', 'name', 'owner', 'collections']

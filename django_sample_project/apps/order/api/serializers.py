from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField

from django_sample_project.apps.order.models import Order, Product


class OrderSerializer(ModelSerializer):
    name = serializers.ModelField(Order.name)   # <-- needed for tests

    class Meta:
        model = Order
        fields = ['id', 'owner', 'number', 'name']


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']


class ProductAddSerializer(ModelSerializer):
    order = PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Product
        fields = ['order']

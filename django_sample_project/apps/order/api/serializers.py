from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField

from django_sample_project.apps.order.models import Order, Product, Item


class ItemSerializer(ModelSerializer):
    quantity = serializers.IntegerField()

    class Meta:
        model = Item
        fields = ['product_id', 'quantity']


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']


class OrderSerializer(ModelSerializer):
    name = serializers.ModelField(Order.name)   # <-- needed for tests
    items = ItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'owner', 'number', 'name', 'items']


class ProductAddSerializer(ModelSerializer):
    order = PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Product
        fields = ['order']

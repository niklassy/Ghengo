from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from django_sample_project.apps.order.api.serializers import OrderSerializer, ProductSerializer, ProductAddSerializer
from django_sample_project.apps.order.models import Order, Product


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @action(detail=False, methods=['post'])
    def book(self, *args, **kwargs):
        return super().create(*args, **kwargs)


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_serializer_class(self):
        if self.action == 'add':
            return ProductAddSerializer

        return self.serializer_class

    @action(detail=True, methods=['post'])
    def add(self, *args, **kwargs):
        return super().create(*args, **kwargs)

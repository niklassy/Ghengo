from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from django_sample_project.apps.order.api.serializers import OrderSerializer
from django_sample_project.apps.order.models import Order


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @action(detail=False, methods=['get'])
    def my_route(self, *args, **kwargs):
        return super().list(*args, **kwargs)

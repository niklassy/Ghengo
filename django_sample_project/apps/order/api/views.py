from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from django_sample_project.apps.order.api.serializers import OrderSerializer, ToDoSerializer
from django_sample_project.apps.order.models import Order, ToDo


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @action(detail=False, methods=['post'])
    def book(self, *args, **kwargs):
        return super().create(*args, **kwargs)


# Currently not used
class ToDoViewSet(ModelViewSet):
    queryset = ToDo.objects.all()
    serializer_class = ToDoSerializer

from rest_framework import viewsets

from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by("-paid_at")
    serializer_class = PaymentSerializer

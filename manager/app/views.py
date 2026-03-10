from rest_framework import viewsets

from .models import Manager
from .serializers import ManagerSerializer


class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all().order_by("-created_at")
    serializer_class = ManagerSerializer

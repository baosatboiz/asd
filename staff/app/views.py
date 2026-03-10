from rest_framework import viewsets

from .models import Staff
from .serializers import StaffSerializer


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by("-created_at")
    serializer_class = StaffSerializer

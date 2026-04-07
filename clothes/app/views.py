from rest_framework import viewsets

from .models import ClothingItem
from .serializers import ClothingItemSerializer


class ClothingItemViewSet(viewsets.ModelViewSet):
    queryset = ClothingItem.objects.all().order_by("name")
    serializer_class = ClothingItemSerializer

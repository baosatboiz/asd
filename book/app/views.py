from rest_framework import viewsets

from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all().order_by("title")
    serializer_class = BookSerializer

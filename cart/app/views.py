import os

import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Cart, CartItem, ClothingCartItem
from .serializers import CartItemSerializer, CartSerializer, ClothingCartItemSerializer


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all().order_by("-created_at")
    serializer_class = CartSerializer

    @action(detail=True, methods=["post"], url_path="add-item")
    def add_item(self, request, pk=None):
        cart = self.get_object()
        book_id = request.data.get("book_id")
        try:
            quantity = int(request.data.get("quantity", 1))
        except (TypeError, ValueError):
            return Response({"detail": "quantity must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if not book_id:
            return Response({"detail": "book_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        book_service_url = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        try:
            book_response = requests.get(f"{book_service_url}/books/{book_id}/", timeout=5)
            if book_response.status_code != 200:
                return Response(
                    {"detail": "Book does not exist in book-service."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except requests.RequestException:
            return Response(
                {"detail": "book-service is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            book_id=book_id,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity"])

        serializer = CartItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="add-clothing")
    def add_clothing(self, request, pk=None):
        cart = self.get_object()
        clothing_item_id = request.data.get("clothing_item_id")
        try:
            quantity = int(request.data.get("quantity", 1))
        except (TypeError, ValueError):
            return Response({"detail": "quantity must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if not clothing_item_id:
            return Response({"detail": "clothing_item_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        clothes_service_url = os.getenv("CLOTHES_SERVICE_URL", "http://clothes:8000")
        try:
            r = requests.get(f"{clothes_service_url}/clothes/{clothing_item_id}/", timeout=5)
            if r.status_code != 200:
                return Response({"detail": "Clothing item not found."}, status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException:
            return Response({"detail": "clothes-service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        item, created = ClothingCartItem.objects.get_or_create(
            cart=cart,
            clothing_item_id=clothing_item_id,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity"])

        serializer = ClothingCartItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="clear-items")
    def clear_items(self, request, pk=None):
        cart = self.get_object()
        book_deleted, _ = CartItem.objects.filter(cart=cart).delete()
        clothing_deleted, _ = ClothingCartItem.objects.filter(cart=cart).delete()
        total = book_deleted + clothing_deleted
        return Response(
            {"detail": f"Cleared {total} items from cart.", "cart_id": cart.id},
            status=status.HTTP_200_OK,
        )

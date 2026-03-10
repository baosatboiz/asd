import os

import requests
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import CommentRate
from .serializers import CommentRateSerializer


def _extract_order_book_ids(order_obj):
    # Primary source: explicit list if provided by order-service.
    raw_ids = order_obj.get("ordered_book_ids", [])
    if isinstance(raw_ids, list):
        out = []
        for value in raw_ids:
            try:
                out.append(int(value))
            except (TypeError, ValueError):
                continue
        if out:
            return out

    # Backward-compatible fallback: parse marker from shipping_address.
    marker = "|books:"
    shipping_address = order_obj.get("shipping_address", "")
    if marker in shipping_address:
        suffix = shipping_address.split(marker, 1)[1]
        values = []
        for token in suffix.split(","):
            token = token.strip()
            try:
                values.append(int(token))
            except (TypeError, ValueError):
                continue
        return values

    return []


class CommentRateViewSet(viewsets.ModelViewSet):
    queryset = CommentRate.objects.all().order_by("-created_at")
    serializer_class = CommentRateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_id = serializer.validated_data["customer_id"]
        book_id = serializer.validated_data["book_id"]

        order_service_url = os.getenv("ORDER_SERVICE_URL", "http://order-service:8000")
        try:
            orders_response = requests.get(f"{order_service_url}/orders/", timeout=5)
            if orders_response.status_code != 200:
                return Response(
                    {"detail": "Unable to validate purchase history at this time."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            orders = orders_response.json()
        except (requests.RequestException, ValueError):
            return Response(
                {"detail": "Unable to validate purchase history at this time."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        has_purchased = False
        for order in orders if isinstance(orders, list) else []:
            try:
                same_customer = int(order.get("customer_id")) == int(customer_id)
            except (TypeError, ValueError):
                same_customer = False
            if not same_customer:
                continue

            order_book_ids = _extract_order_book_ids(order)
            if int(book_id) in order_book_ids:
                has_purchased = True
                break

        if not has_purchased:
            return Response(
                {"detail": "You can only review books you have purchased"},
                status=status.HTTP_403_FORBIDDEN,
            )

        review = serializer.save()
        output = self.get_serializer(review)
        return Response(output.data, status=status.HTTP_201_CREATED)

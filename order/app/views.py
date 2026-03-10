import os

import requests
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        pay_service_url = os.getenv("PAY_SERVICE_URL", "http://pay:8000")
        ship_service_url = os.getenv("SHIP_SERVICE_URL", "http://ship:8000")

        payment_status = "pending"
        shipping_status = "pending"
        payment_error = None
        shipping_error = None

        try:
            pay_res = requests.post(
                f"{pay_service_url}/payments/",
                json={"order_id": int(order.id), "amount": str(order.total_price), "status": "paid"},
                timeout=5,
            )
            if pay_res.status_code in (200, 201):
                payment_status = "paid"
            else:
                payment_status = "failed"
                payment_error = f"pay-service returned status {pay_res.status_code}."
        except requests.RequestException:
            payment_status = "failed"
            payment_error = "pay-service is unavailable."

        try:
            ship_res = requests.post(
                f"{ship_service_url}/shipments/",
                json={
                    "order_id": int(order.id),
                    "customer_id": int(order.customer_id),
                    "address": order.shipping_address,
                    "status": "processing",
                },
                timeout=5,
            )
            if ship_res.status_code in (200, 201):
                shipping_status = "processing"
            else:
                shipping_status = "failed"
                shipping_error = f"ship-service returned status {ship_res.status_code}."
        except requests.RequestException:
            shipping_status = "failed"
            shipping_error = "ship-service is unavailable."

        if payment_status == "paid":
            order.status = "paid"
            order.save(update_fields=["status"])

        data = self.get_serializer(order).data
        data["payment_status"] = payment_status
        data["shipping_status"] = shipping_status
        if payment_error:
            data["payment_error"] = payment_error
        if shipping_error:
            data["shipping_error"] = shipping_error

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

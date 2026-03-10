import os

import requests
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by("-created_at")
    serializer_class = CustomerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()

        cart_service_url = os.getenv("CART_SERVICE_URL", "http://cart:8000")
        cart_payload = {"customer_id": customer.id}
        cart_warning = None

        try:
            response = requests.post(
                f"{cart_service_url}/carts/",
                json=cart_payload,
                timeout=5,
            )
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                except ValueError:
                    data = {}
                    cart_warning = "cart-service returned non-JSON response."
                cart_id = data.get("id")
                if cart_id:
                    customer.cart_id = cart_id
                    customer.save(update_fields=["cart_id"])
            else:
                cart_warning = (
                    f"cart-service returned status {response.status_code} while creating cart."
                )
        except requests.RequestException:
            # Customer registration still succeeds even when cart-service is unavailable.
            cart_warning = "cart-service is unavailable; cart was not auto-created."

        headers = self.get_success_headers(serializer.data)
        output = self.get_serializer(customer)
        data = output.data
        if cart_warning:
            data["cart_warning"] = cart_warning
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

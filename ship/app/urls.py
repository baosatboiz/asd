from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ShipmentViewSet

router = DefaultRouter()
router.register("shipments", ShipmentViewSet, basename="shipment")

urlpatterns = [
    path("", include(router.urls)),
]

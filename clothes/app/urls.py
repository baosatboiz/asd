from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClothingItemViewSet

router = DefaultRouter()
router.register("clothes", ClothingItemViewSet, basename="clothing")

urlpatterns = [
    path("", include(router.urls)),
]

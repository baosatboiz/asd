from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommentRateViewSet

router = DefaultRouter()
router.register("comments", CommentRateViewSet, basename="comment")
router.register("comments-rates", CommentRateViewSet, basename="comment-rate")

urlpatterns = [
    path("", include(router.urls)),
]

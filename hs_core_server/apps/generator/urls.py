from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.generator.views import StorySegmentViewSet

router = DefaultRouter()
router.register(r"generator", StorySegmentViewSet, basename="generator")

urlpatterns = [
    path("", include(router.urls)),
]

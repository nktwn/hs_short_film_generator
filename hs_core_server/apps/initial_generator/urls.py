from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.initial_generator.views import InitialVideoGenerationViewSet

router = DefaultRouter()
router.register(
    r"initial_generator", InitialVideoGenerationViewSet, basename="initial-generator"
)

urlpatterns = [
    path("", include(router.urls)),
]

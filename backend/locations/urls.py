from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LocationViewSet


app_name = "locations"

router = DefaultRouter()
router.register(
    prefix="locations",
    viewset=LocationViewSet,
    basename="location",
)

urlpatterns = [
    path("", include(router.urls)),
]
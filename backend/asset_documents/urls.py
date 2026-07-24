from rest_framework.routers import DefaultRouter

from .views import AssetDocumentViewSet


router = DefaultRouter()

router.register(
    "",
    AssetDocumentViewSet,
    basename="asset-document",
)

urlpatterns = router.urls
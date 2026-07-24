from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


admin.site.site_header = "سامانه مهندسی رادیس"
admin.site.site_title = "مدیریت سامانه رادیس"
admin.site.index_title = "پنل مدیریت"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/users/", include("accounts.urls")),
    path("api/projects/", include("projects.urls")),
    path("api/assets/", include("assets.urls")),
    path("api/asset-documents/", include("asset_documents.urls")),
    path("api/locations/", include("locations.urls")),
    path("api/work-orders/", include("work_orders.urls")),
    path(
        "api/preventive-maintenance/",
        include("preventive_maintenance.urls"),
    ),
    path("api/inventory/", include("inventory.urls")),
    path(
        "api/auth/login/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),
    path(
        "api/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ProjectNumberingSettingsView,
    ProjectStageViewSet,
    ProjectViewSet,
)

router = DefaultRouter()
router.register("", ProjectViewSet, basename="projects")

stage_router = DefaultRouter()
stage_router.register("", ProjectStageViewSet, basename="project-stages")

urlpatterns = [
    path("numbering/", ProjectNumberingSettingsView.as_view(), name="project-numbering"),
    path("", include(router.urls)),
    path(
        "<int:project_pk>/stages/",
        include(stage_router.urls),
    ),
]

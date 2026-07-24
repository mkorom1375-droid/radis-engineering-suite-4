from rest_framework.routers import DefaultRouter

from .views import (
    PreventiveMaintenanceGenerationViewSet,
    PreventiveMaintenancePlanViewSet,
    PreventiveMaintenanceTaskResultViewSet,
    PreventiveMaintenanceTaskViewSet,
)


app_name = "preventive_maintenance"


router = DefaultRouter()

router.register(
    "plans",
    PreventiveMaintenancePlanViewSet,
    basename="preventive-maintenance-plan",
)

router.register(
    "tasks",
    PreventiveMaintenanceTaskViewSet,
    basename="preventive-maintenance-task",
)

router.register(
    "generations",
    PreventiveMaintenanceGenerationViewSet,
    basename="preventive-maintenance-generation",
)

router.register(
    "task-results",
    PreventiveMaintenanceTaskResultViewSet,
    basename="preventive-maintenance-task-result",
)


urlpatterns = router.urls
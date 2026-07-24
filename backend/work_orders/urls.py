from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    WorkOrderAssignmentViewSet,
    WorkOrderDowntimeViewSet,
    WorkOrderFailureViewSet,
    WorkOrderLaborViewSet,
    WorkOrderViewSet,
    WorkRequestViewSet,
)

app_name = "work_orders"

router = DefaultRouter()

router.register(
    "requests",
    WorkRequestViewSet,
    basename="work-request",
)

router.register(
    "orders",
    WorkOrderViewSet,
    basename="work-order",
)

router.register(
    "assignments",
    WorkOrderAssignmentViewSet,
    basename="work-order-assignment",
)

router.register(
    "labor",
    WorkOrderLaborViewSet,
    basename="work-order-labor",
)

router.register(
    "downtime",
    WorkOrderDowntimeViewSet,
    basename="work-order-downtime",
)

router.register(
    "failures",
    WorkOrderFailureViewSet,
    basename="work-order-failure",
)

urlpatterns = [
    path("", include(router.urls)),
]
"""
URL configuration for the inventory application.
"""

from django.urls import include
from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import (
    InventoryItemViewSet,
    StockBalanceViewSet,
    StockTransactionViewSet,
    WarehouseViewSet,
    WorkOrderPartViewSet,
)

app_name = "inventory"

router = DefaultRouter()

router.register(
    r"warehouses",
    WarehouseViewSet,
    basename="warehouse",
)

router.register(
    r"items",
    InventoryItemViewSet,
    basename="inventory-item",
)

router.register(
    r"stock-balances",
    StockBalanceViewSet,
    basename="stock-balance",
)

router.register(
    r"work-order-parts",
    WorkOrderPartViewSet,
    basename="work-order-part",
)

router.register(
    r"stock-transactions",
    StockTransactionViewSet,
    basename="stock-transaction",
)

urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]
"""
Permissions for the inventory application.
"""

from rest_framework.permissions import BasePermission
from rest_framework.permissions import SAFE_METHODS


class InventoryPermission(BasePermission):
    """
    Base inventory permission.

    Current policy:
    - Any authenticated user can view inventory.
    - Write operations require Django model permissions.

    This class is designed to be extended later with:
        - Project permissions
        - Warehouse permissions
        - Organization permissions
        - Role Based Access Control (RBAC)
    """

    read_permission = ""
    write_permission = ""

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if request.method in SAFE_METHODS:
            if self.read_permission:
                return user.has_perm(self.read_permission)
            return True

        if self.write_permission:
            return user.has_perm(self.write_permission)

        return False


class WarehousePermission(InventoryPermission):
    read_permission = "inventory.view_warehouse"
    write_permission = "inventory.change_warehouse"


class InventoryItemPermission(InventoryPermission):
    read_permission = "inventory.view_inventoryitem"
    write_permission = "inventory.change_inventoryitem"


class StockBalancePermission(InventoryPermission):
    """
    Stock balances are read-only.

    Changes must be performed through service actions.
    """

    read_permission = "inventory.view_stockbalance"
    write_permission = "inventory.change_stockbalance"


class WorkOrderPartPermission(InventoryPermission):
    read_permission = "inventory.view_workorderpart"
    write_permission = "inventory.change_workorderpart"


class StockTransactionPermission(InventoryPermission):
    """
    Stock transactions are immutable.

    Nobody edits them directly except superusers if needed.
    """

    read_permission = "inventory.view_stocktransaction"
    write_permission = "inventory.change_stocktransaction"


class InventoryOperationPermission(BasePermission):
    """
    Permission for inventory operations such as:

        Receive
        Issue
        Reserve
        Release Reservation
        Consume
        Return
        Transfer
        Adjustment
    """

    required_permission = "inventory.change_stockbalance"

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.has_perm(self.required_permission)
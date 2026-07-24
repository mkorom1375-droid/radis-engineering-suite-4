"""
FilterSet classes for the inventory application.

All query-parameter filtering is defined in this module so API views remain
focused on queryset optimization, serialization and stock operations.
"""

from __future__ import annotations

from typing import Any

import django_filters
from django.db.models import F, QuerySet

from .models import (
    InventoryItem,
    StockBalance,
    StockTransaction,
    Warehouse,
    WorkOrderPart,
)


class NumberInFilter(
    django_filters.BaseInFilter,
    django_filters.NumberFilter,
):
    """Filter a numeric field using comma-separated values."""


class CharInFilter(
    django_filters.BaseInFilter,
    django_filters.CharFilter,
):
    """Filter a text field using comma-separated values."""


class StrictBooleanFilter(django_filters.BooleanFilter):
    """
    Boolean filter accepting standard API boolean representations.

    django-filter and Django REST Framework support values such as:

        true
        false
        1
        0

    Empty values are ignored.
    """


class ProjectFilterMixin:
    """
    Add ``project`` and ``project_id`` aliases to a FilterSet.

    Subclasses may override ``project_field_name`` when the project relation
    is reached through another model.
    """

    project_field_name = "project_id"

    project = django_filters.NumberFilter(
        method="filter_project",
        label="Project",
    )

    project_id = django_filters.NumberFilter(
        method="filter_project",
        label="Project ID",
    )

    def filter_project(
        self,
        queryset: QuerySet,
        name: str,
        value: Any,
    ) -> QuerySet:
        if value in (None, ""):
            return queryset

        return queryset.filter(
            **{
                self.project_field_name: value,
            }
        )


class WarehouseFilter(
    ProjectFilterMixin,
    django_filters.FilterSet,
):
    """Filters for warehouse list and retrieve endpoints."""

    warehouse_type = django_filters.CharFilter(
        field_name="warehouse_type",
        lookup_expr="exact",
    )

    manager = django_filters.NumberFilter(
        field_name="manager_id",
    )

    manager_id = django_filters.NumberFilter(
        field_name="manager_id",
    )

    is_active = StrictBooleanFilter(
        field_name="is_active",
    )

    class Meta:
        model = Warehouse
        fields = [
            "project",
            "project_id",
            "warehouse_type",
            "manager",
            "manager_id",
            "is_active",
        ]


class InventoryItemFilter(
    ProjectFilterMixin,
    django_filters.FilterSet,
):
    """Filters for inventory master items."""

    item_type = django_filters.CharFilter(
        field_name="item_type",
        lookup_expr="exact",
    )

    category = django_filters.CharFilter(
        method="filter_category",
    )

    manufacturer = django_filters.CharFilter(
        method="filter_manufacturer",
    )

    unit_of_measure = django_filters.CharFilter(
        field_name="unit_of_measure",
        lookup_expr="exact",
    )

    is_active = StrictBooleanFilter(
        field_name="is_active",
    )

    is_critical = StrictBooleanFilter(
        field_name="is_critical",
    )

    below_reorder = StrictBooleanFilter(
        method="filter_below_reorder",
    )

    has_stock = StrictBooleanFilter(
        method="filter_has_stock",
    )

    def filter_category(
        self,
        queryset: QuerySet,
        name: str,
        value: str,
    ) -> QuerySet:
        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            category__iexact=value,
        )

    def filter_manufacturer(
        self,
        queryset: QuerySet,
        name: str,
        value: str,
    ) -> QuerySet:
        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            manufacturer__icontains=value,
        )

    def filter_below_reorder(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                total_available_quantity__lte=F(
                    "reorder_point"
                )
            )

        return queryset.filter(
            total_available_quantity__gt=F(
                "reorder_point"
            )
        )

    def filter_has_stock(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                total_quantity_on_hand__gt=0
            )

        return queryset.filter(
            total_quantity_on_hand__lte=0
        )

    class Meta:
        model = InventoryItem
        fields = [
            "project",
            "project_id",
            "item_type",
            "category",
            "manufacturer",
            "unit_of_measure",
            "is_active",
            "is_critical",
            "below_reorder",
            "has_stock",
        ]


class StockBalanceFilter(
    ProjectFilterMixin,
    django_filters.FilterSet,
):
    """Filters for the read-only stock balance endpoint."""

    project_field_name = "warehouse__project_id"

    warehouse = django_filters.NumberFilter(
        field_name="warehouse_id",
    )

    warehouse_id = django_filters.NumberFilter(
        field_name="warehouse_id",
    )

    item = django_filters.NumberFilter(
        field_name="item_id",
    )

    item_id = django_filters.NumberFilter(
        field_name="item_id",
    )

    item_type = django_filters.CharFilter(
        field_name="item__item_type",
        lookup_expr="exact",
    )

    is_critical = StrictBooleanFilter(
        field_name="item__is_critical",
    )

    below_reorder = StrictBooleanFilter(
        method="filter_below_reorder",
    )

    positive_only = StrictBooleanFilter(
        method="filter_positive_only",
    )

    has_available_stock = StrictBooleanFilter(
        method="filter_has_available_stock",
    )

    def filter_below_reorder(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        threshold = (
            F("reserved_quantity")
            + F("item__reorder_point")
        )

        if value:
            return queryset.filter(
                quantity_on_hand__lte=threshold
            )

        return queryset.filter(
            quantity_on_hand__gt=threshold
        )

    def filter_positive_only(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                quantity_on_hand__gt=0
            )

        return queryset.filter(
            quantity_on_hand__lte=0
        )

    def filter_has_available_stock(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                quantity_on_hand__gt=F(
                    "reserved_quantity"
                )
            )

        return queryset.filter(
            quantity_on_hand__lte=F(
                "reserved_quantity"
            )
        )
    class Meta:
        model = StockBalance
        fields = [
        "warehouse",
        "warehouse_id",
        "item",
        "item_id",
        "item_type",
        "is_critical",
        "below_reorder",
        "positive_only",
        "has_available_stock",
    ]


class WorkOrderPartFilter(
    ProjectFilterMixin,
    django_filters.FilterSet,
):
    """Filters for work-order required parts."""

    project_field_name = "work_order__project_id"

    work_order = django_filters.NumberFilter(
        field_name="work_order_id",
    )

    work_order_id = django_filters.NumberFilter(
        field_name="work_order_id",
    )

    warehouse = django_filters.NumberFilter(
        field_name="warehouse_id",
    )

    warehouse_id = django_filters.NumberFilter(
        field_name="warehouse_id",
    )

    item = django_filters.NumberFilter(
        field_name="item_id",
    )

    item_id = django_filters.NumberFilter(
        field_name="item_id",
    )

    pending = StrictBooleanFilter(
        method="filter_pending",
    )

    has_reservation = StrictBooleanFilter(
        method="filter_has_reservation",
    )

    has_issued_quantity = StrictBooleanFilter(
        method="filter_has_issued_quantity",
    )

    def filter_pending(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        allocated_quantity = (
            F("reserved_quantity")
            + F("issued_quantity")
        )

        if value:
            return queryset.filter(
                requested_quantity__gt=allocated_quantity
            )

        return queryset.filter(
            requested_quantity__lte=allocated_quantity
        )

    def filter_has_reservation(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                reserved_quantity__gt=0
            )

        return queryset.filter(
            reserved_quantity__lte=0
        )

    def filter_has_issued_quantity(
        self,
        queryset: QuerySet,
        name: str,
        value: bool | None,
    ) -> QuerySet:
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                issued_quantity__gt=0
            )

        return queryset.filter(
            issued_quantity__lte=0
        )

    class Meta:
        model = WorkOrderPart
        fields = [
          
            "work_order",
            "work_order_id",
            "warehouse",
            "warehouse_id",
            "item",
            "item_id",
            "pending",
            "has_reservation",
            "has_issued_quantity",
        ]


class StockTransactionFilter(
    ProjectFilterMixin,
    django_filters.FilterSet,
):
    """Filters for the immutable stock transaction ledger."""

    warehouse = django_filters.NumberFilter(
        field_name="warehouse_id",
    )

    warehouse_id = django_filters.NumberFilter(
        field_name="warehouse_id",
    )

    item = django_filters.NumberFilter(
        field_name="item_id",
    )

    item_id = django_filters.NumberFilter(
        field_name="item_id",
    )

    work_order = django_filters.NumberFilter(
        field_name="work_order_id",
    )

    work_order_id = django_filters.NumberFilter(
        field_name="work_order_id",
    )

    work_order_part = django_filters.NumberFilter(
        field_name="work_order_part_id",
    )

    work_order_part_id = django_filters.NumberFilter(
        field_name="work_order_part_id",
    )

    counterpart_warehouse = django_filters.NumberFilter(
        field_name="counterpart_warehouse_id",
    )

    counterpart_warehouse_id = django_filters.NumberFilter(
        field_name="counterpart_warehouse_id",
    )

    transaction_type = CharInFilter(
        field_name="transaction_type",
        lookup_expr="in",
    )

    reference_number = django_filters.CharFilter(
        method="filter_reference_number",
    )

    performed_by = django_filters.NumberFilter(
        field_name="performed_by_id",
    )

    performed_by_id = django_filters.NumberFilter(
        field_name="performed_by_id",
    )

    is_void = StrictBooleanFilter(
        field_name="is_void",
    )

    occurred_from = django_filters.IsoDateTimeFilter(
        field_name="occurred_at",
        lookup_expr="gte",
    )

    occurred_to = django_filters.IsoDateTimeFilter(
        field_name="occurred_at",
        lookup_expr="lte",
    )

    def filter_reference_number(
        self,
        queryset: QuerySet,
        name: str,
        value: str,
    ) -> QuerySet:
        value = value.strip()

        if not value:
            return queryset

        return queryset.filter(
            reference_number__icontains=value
        )

    class Meta:
        model = StockTransaction
        fields = [
            "project",
            "project_id",
            "warehouse",
            "warehouse_id",
            "item",
            "item_id",
            "work_order",
            "work_order_id",
            "work_order_part",
            "work_order_part_id",
            "counterpart_warehouse",
            "counterpart_warehouse_id",
            "transaction_type",
            "reference_number",
            "performed_by",
            "performed_by_id",
            "is_void",
            "occurred_from",
            "occurred_to",
        ]
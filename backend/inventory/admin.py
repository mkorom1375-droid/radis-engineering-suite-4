"""
Django admin configuration for the inventory application.

Stock balances and stock transactions are protected against direct creation,
editing, and deletion because inventory quantities must only change through
the service layer.
"""

from __future__ import annotations

from django.contrib import admin
from django.db.models import DecimalField
from django.db.models import ExpressionWrapper
from django.db.models import F
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    InventoryItem,
    StockBalance,
    StockTransaction,
    Warehouse,
    WorkOrderPart,
)


QUANTITY_OUTPUT_FIELD = DecimalField(
    max_digits=18,
    decimal_places=3,
)

COST_OUTPUT_FIELD = DecimalField(
    max_digits=24,
    decimal_places=2,
)


class ReadOnlyInventoryRecordAdminMixin:
    """
    Prevent direct mutation of service-managed inventory records.

    StockBalance and StockTransaction records must only be changed through
    inventory services.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_view_permission(
        self,
        request,
        obj=None,
    ):
        return request.user.is_active and request.user.is_staff

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


class ActiveStatusListFilter(admin.SimpleListFilter):
    title = _("وضعیت فعالیت")
    parameter_name = "active_status"

    def lookups(self, request, model_admin):
        return (
            ("active", _("فعال")),
            ("inactive", _("غیرفعال")),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_active=True)

        if self.value() == "inactive":
            return queryset.filter(is_active=False)

        return queryset


class StockStatusListFilter(admin.SimpleListFilter):
    title = _("وضعیت موجودی")
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("available", _("دارای موجودی قابل‌مصرف")),
            ("reserved", _("دارای موجودی رزروشده")),
            ("empty", _("بدون موجودی")),
            ("below_reorder", _("زیر نقطه سفارش")),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == "available":
            return queryset.filter(
                quantity_on_hand__gt=F("reserved_quantity")
            )

        if value == "reserved":
            return queryset.filter(
                reserved_quantity__gt=0
            )

        if value == "empty":
            return queryset.filter(
                quantity_on_hand=0
            )

        if value == "below_reorder":
            return queryset.filter(
                quantity_on_hand__lte=(
                    F("reserved_quantity")
                    + F("item__reorder_point")
                )
            )

        return queryset


class WorkOrderPartStatusListFilter(admin.SimpleListFilter):
    title = _("وضعیت تأمین قطعه")
    parameter_name = "part_status"

    def lookups(self, request, model_admin):
        return (
            ("pending", _("در انتظار تأمین")),
            ("reserved", _("دارای رزرو")),
            ("issued", _("تحویل‌شده")),
            ("consumed", _("مصرف‌شده")),
            ("returned", _("دارای برگشتی")),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == "pending":
            return queryset.filter(
                requested_quantity__gt=(
                    F("reserved_quantity")
                    + F("issued_quantity")
                )
            )

        if value == "reserved":
            return queryset.filter(
                reserved_quantity__gt=0
            )

        if value == "issued":
            return queryset.filter(
                issued_quantity__gt=0
            )

        if value == "consumed":
            return queryset.filter(
                consumed_quantity__gt=0
            )

        if value == "returned":
            return queryset.filter(
                returned_quantity__gt=0
            )

        return queryset


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "project",
        "warehouse_type",
        "manager",
        "active_badge",
        "created_at",
    )

    list_filter = (
        ActiveStatusListFilter,
        "warehouse_type",
        "project",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
        "address",
        "description",
        "manager__email",
        "manager__first_name",
        "manager__last_name",
        "project__name",
    )

    ordering = (
        "project",
        "name",
        "id",
    )

    list_select_related = (
        "project",
        "manager",
    )

    raw_id_fields = (
        "project",
        "manager",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("اطلاعات اصلی"),
            {
                "fields": (
                    "project",
                    "code",
                    "name",
                    "warehouse_type",
                    "manager",
                    "is_active",
                )
            },
        ),
        (
            _("اطلاعات تکمیلی"),
            {
                "fields": (
                    "address",
                    "description",
                )
            },
        ),
        (
            _("اطلاعات سیستمی"),
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    list_per_page = 50
    save_on_top = True

    @admin.display(
        description=_("وضعیت"),
        ordering="is_active",
    )
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<strong style="color:#16803c;">{}</strong>',
                _("فعال"),
            )

        return format_html(
            '<strong style="color:#b42318;">{}</strong>',
            _("غیرفعال"),
        )


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "project",
        "item_type",
        "unit_of_measure",
        "is_critical",
        "active_badge",
        "total_on_hand_display",
        "total_available_display",
        "reorder_point",
    )

    list_filter = (
        ActiveStatusListFilter,
        "is_critical",
        "item_type",
        "unit_of_measure",
        "project",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
        "category",
        "manufacturer",
        "part_number",
        "manufacturer_part_number",
        "description",
        "project__name",
    )

    ordering = (
        "project",
        "name",
        "id",
    )

    list_select_related = (
        "project",
    )

    raw_id_fields = (
        "project",
    )

    readonly_fields = (
        "total_quantity_on_hand_display",
        "total_reserved_quantity_display",
        "total_available_quantity_display",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("شناسه کالا"),
            {
                "fields": (
                    "project",
                    "code",
                    "name",
                    "item_type",
                    "category",
                    "unit_of_measure",
                    "is_critical",
                    "is_active",
                )
            },
        ),
        (
            _("اطلاعات سازنده"),
            {
                "fields": (
                    "manufacturer",
                    "part_number",
                    "manufacturer_part_number",
                )
            },
        ),
        (
            _("کنترل موجودی"),
            {
                "fields": (
                    "minimum_stock",
                    "maximum_stock",
                    "reorder_point",
                    "standard_unit_cost",
                )
            },
        ),
        (
            _("خلاصه موجودی"),
            {
                "fields": (
                    "total_quantity_on_hand_display",
                    "total_reserved_quantity_display",
                    "total_available_quantity_display",
                )
            },
        ),
        (
            _("توضیحات"),
            {
                "fields": (
                    "description",
                )
            },
        ),
        (
            _("اطلاعات سیستمی"),
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    list_per_page = 50
    save_on_top = True

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.annotate(
            admin_total_on_hand=Coalesce(
                Sum(
                    "stock_balances__quantity_on_hand"
                ),
                0,
                output_field=QUANTITY_OUTPUT_FIELD,
            ),
            admin_total_reserved=Coalesce(
                Sum(
                    "stock_balances__reserved_quantity"
                ),
                0,
                output_field=QUANTITY_OUTPUT_FIELD,
            ),
        ).annotate(
            admin_total_available=ExpressionWrapper(
                F("admin_total_on_hand")
                - F("admin_total_reserved"),
                output_field=QUANTITY_OUTPUT_FIELD,
            )
        )

    @admin.display(
        description=_("وضعیت"),
        ordering="is_active",
    )
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<strong style="color:#16803c;">{}</strong>',
                _("فعال"),
            )

        return format_html(
            '<strong style="color:#b42318;">{}</strong>',
            _("غیرفعال"),
        )

    @admin.display(
        description=_("موجودی کل"),
        ordering="admin_total_on_hand",
    )
    def total_on_hand_display(self, obj):
        return getattr(
            obj,
            "admin_total_on_hand",
            0,
        )

    @admin.display(
        description=_("موجودی قابل‌مصرف"),
        ordering="admin_total_available",
    )
    def total_available_display(self, obj):
        quantity = getattr(
            obj,
            "admin_total_available",
            0,
        )

        if quantity <= obj.reorder_point:
            return format_html(
                '<strong style="color:#b42318;">{}</strong>',
                quantity,
            )

        return quantity

    @admin.display(
        description=_("موجودی فیزیکی کل"),
    )
    def total_quantity_on_hand_display(self, obj):
        return getattr(
            obj,
            "admin_total_on_hand",
            0,
        )

    @admin.display(
        description=_("موجودی رزروشده کل"),
    )
    def total_reserved_quantity_display(self, obj):
        return getattr(
            obj,
            "admin_total_reserved",
            0,
        )

    @admin.display(
        description=_("موجودی قابل‌مصرف کل"),
    )
    def total_available_quantity_display(self, obj):
        return getattr(
            obj,
            "admin_total_available",
            0,
        )


@admin.register(StockBalance)
class StockBalanceAdmin(
    ReadOnlyInventoryRecordAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "warehouse",
        "item",
        "quantity_on_hand",
        "reserved_quantity",
        "available_quantity_display",
        "average_unit_cost",
        "stock_value_display",
        "reorder_status",
        "last_transaction_at",
    )

    list_filter = (
        StockStatusListFilter,
        "warehouse__project",
        "warehouse",
        "item__item_type",
        "item__is_critical",
        "last_transaction_at",
    )

    search_fields = (
        "warehouse__code",
        "warehouse__name",
        "item__code",
        "item__name",
        "item__category",
        "item__manufacturer",
        "item__part_number",
        "item__manufacturer_part_number",
    )

    ordering = (
        "warehouse",
        "item",
        "id",
    )

    list_select_related = (
        "warehouse",
        "warehouse__project",
        "item",
        "item__project",
    )

    readonly_fields = (
        "warehouse",
        "item",
        "quantity_on_hand",
        "reserved_quantity",
        "available_quantity_display",
        "average_unit_cost",
        "stock_value_display",
        "reorder_status",
        "last_transaction_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("شناسه موجودی"),
            {
                "fields": (
                    "warehouse",
                    "item",
                )
            },
        ),
        (
            _("مقادیر موجودی"),
            {
                "fields": (
                    "quantity_on_hand",
                    "reserved_quantity",
                    "available_quantity_display",
                )
            },
        ),
        (
            _("ارزش موجودی"),
            {
                "fields": (
                    "average_unit_cost",
                    "stock_value_display",
                )
            },
        ),
        (
            _("وضعیت"),
            {
                "fields": (
                    "reorder_status",
                    "last_transaction_at",
                )
            },
        ),
        (
            _("اطلاعات سیستمی"),
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    list_per_page = 75

    @admin.display(
        description=_("موجودی قابل‌مصرف"),
    )
    def available_quantity_display(self, obj):
        return obj.available_quantity

    @admin.display(
        description=_("ارزش موجودی"),
    )
    def stock_value_display(self, obj):
        return obj.stock_value

    @admin.display(
        description=_("وضعیت سفارش"),
        boolean=True,
    )
    def reorder_status(self, obj):
        return obj.is_below_reorder_point


@admin.register(WorkOrderPart)
class WorkOrderPartAdmin(admin.ModelAdmin):
    list_display = (
        "work_order",
        "item",
        "warehouse",
        "requested_quantity",
        "reserved_quantity",
        "issued_quantity",
        "consumed_quantity",
        "returned_quantity",
        "remaining_quantity_display",
        "estimated_total_cost_display",
    )

    list_filter = (
        WorkOrderPartStatusListFilter,
        "work_order__project",
        "warehouse",
        "item__item_type",
        "item__is_critical",
        "created_at",
    )

    search_fields = (
        "item__code",
        "item__name",
        "item__category",
        "item__manufacturer",
        "item__part_number",
        "item__manufacturer_part_number",
        "warehouse__code",
        "warehouse__name",
        "notes",
    )

    ordering = (
        "work_order",
        "item",
        "id",
    )

    list_select_related = (
        "work_order",
        "work_order__project",
        "item",
        "item__project",
        "warehouse",
        "warehouse__project",
    )

    raw_id_fields = (
        "work_order",
        "item",
        "warehouse",
    )

    readonly_fields = (
        "reserved_quantity",
        "issued_quantity",
        "consumed_quantity",
        "returned_quantity",
        "remaining_quantity_display",
        "issued_available_quantity_display",
        "estimated_total_cost_display",
        "consumed_total_cost_display",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("اطلاعات درخواست قطعه"),
            {
                "fields": (
                    "work_order",
                    "item",
                    "warehouse",
                    "requested_quantity",
                    "estimated_unit_cost",
                )
            },
        ),
        (
            _("وضعیت گردش قطعه"),
            {
                "fields": (
                    "reserved_quantity",
                    "issued_quantity",
                    "consumed_quantity",
                    "returned_quantity",
                    "remaining_quantity_display",
                    "issued_available_quantity_display",
                )
            },
        ),
        (
            _("هزینه"),
            {
                "fields": (
                    "estimated_total_cost_display",
                    "consumed_total_cost_display",
                )
            },
        ),
        (
            _("توضیحات"),
            {
                "fields": (
                    "notes",
                )
            },
        ),
        (
            _("اطلاعات سیستمی"),
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    list_per_page = 75
    save_on_top = True

    @admin.display(
        description=_("مقدار باقی‌مانده"),
    )
    def remaining_quantity_display(self, obj):
        return obj.remaining_requested_quantity

    @admin.display(
        description=_("تحویل‌شده قابل‌مصرف"),
    )
    def issued_available_quantity_display(self, obj):
        return obj.issued_available_quantity

    @admin.display(
        description=_("هزینه برآوردی کل"),
    )
    def estimated_total_cost_display(self, obj):
        return obj.estimated_total_cost

    @admin.display(
        description=_("هزینه مصرف‌شده"),
    )
    def consumed_total_cost_display(self, obj):
        return obj.consumed_total_cost


@admin.register(StockTransaction)
class StockTransactionAdmin(
    ReadOnlyInventoryRecordAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "occurred_at",
        "transaction_type",
        "warehouse",
        "item",
        "quantity",
        "unit_cost",
        "total_value_display",
        "balance_after",
        "reserved_balance_after",
        "reference_number",
        "performed_by",
        "void_status",
    )

    list_filter = (
        "transaction_type",
        "is_void",
        "project",
        "warehouse",
        "item__item_type",
        "occurred_at",
        "created_at",
    )

    search_fields = (
        "reference_number",
        "notes",
        "warehouse__code",
        "warehouse__name",
        "item__code",
        "item__name",
        "item__category",
        "item__manufacturer",
        "item__part_number",
        "item__manufacturer_part_number",
        "counterpart_warehouse__code",
        "counterpart_warehouse__name",
        "performed_by__email",
        "performed_by__first_name",
        "performed_by__last_name",
        "void_reason",
    )

    ordering = (
        "-occurred_at",
        "-id",
    )

    list_select_related = (
        "project",
        "warehouse",
        "item",
        "work_order",
        "work_order_part",
        "counterpart_warehouse",
        "performed_by",
        "voided_by",
    )

    readonly_fields = (
        "project",
        "warehouse",
        "item",
        "transaction_type",
        "quantity",
        "unit_cost",
        "total_value_display",
        "balance_after",
        "reserved_balance_after",
        "work_order",
        "work_order_part",
        "counterpart_warehouse",
        "reference_number",
        "performed_by",
        "occurred_at",
        "notes",
        "is_void",
        "voided_by",
        "voided_at",
        "void_reason",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("اطلاعات تراکنش"),
            {
                "fields": (
                    "project",
                    "warehouse",
                    "item",
                    "transaction_type",
                    "occurred_at",
                    "performed_by",
                    "reference_number",
                )
            },
        ),
        (
            _("مقادیر"),
            {
                "fields": (
                    "quantity",
                    "unit_cost",
                    "total_value_display",
                    "balance_after",
                    "reserved_balance_after",
                )
            },
        ),
        (
            _("ارتباطات"),
            {
                "fields": (
                    "work_order",
                    "work_order_part",
                    "counterpart_warehouse",
                )
            },
        ),
        (
            _("ابطال تراکنش"),
            {
                "fields": (
                    "is_void",
                    "voided_by",
                    "voided_at",
                    "void_reason",
                )
            },
        ),
        (
            _("توضیحات"),
            {
                "fields": (
                    "notes",
                )
            },
        ),
        (
            _("اطلاعات سیستمی"),
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    date_hierarchy = "occurred_at"
    list_per_page = 100

    @admin.display(
        description=_("ارزش کل"),
    )
    def total_value_display(self, obj):
        return obj.quantity * obj.unit_cost

    @admin.display(
        description=_("باطل‌شده"),
        boolean=True,
        ordering="is_void",
    )
    def void_status(self, obj):
        return obj.is_void
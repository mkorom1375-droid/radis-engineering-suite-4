from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    InventoryItem,
    StockBalance,
    StockTransaction,
    Warehouse,
    WorkOrderPart,
)
from .services import (
    AdjustmentService,
    ConsumptionService,
    InventoryServiceError,
    ReservationService,
    StockIssueService,
    StockReceiptService,
    TransferService,
)


QUANTITY_FIELD = {
    "max_digits": 18,
    "decimal_places": 3,
    "min_value": Decimal("0.001"),
}
COST_FIELD = {
    "max_digits": 18,
    "decimal_places": 2,
    "min_value": Decimal("0"),
}


def _raise_drf_validation_error(exc: Exception) -> None:
    """Translate service/model validation failures into DRF validation errors."""
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise serializers.ValidationError(exc.message_dict) from exc
        raise serializers.ValidationError(exc.messages) from exc
    if isinstance(exc, InventoryServiceError):
        raise serializers.ValidationError({"detail": str(exc)}) from exc
    raise exc


class WarehouseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ("id", "code", "name", "warehouse_type", "is_active")
        read_only_fields = fields


class InventoryItemBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "code",
            "name",
            "item_type",
            "unit_of_measure",
            "is_critical",
            "is_active",
        )
        read_only_fields = fields


class WarehouseSerializer(serializers.ModelSerializer):
    manager_display = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        fields = (
            "id",
            "project",
            "code",
            "name",
            "warehouse_type",
            "manager",
            "manager_display",
            "address",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "manager_display", "created_at", "updated_at")

    def get_manager_display(self, obj):
        if obj.manager_id is None:
            return None
        manager = obj.manager
        full_name = manager.get_full_name().strip() if hasattr(manager, "get_full_name") else ""
        return full_name or getattr(manager, "email", None) or str(manager)

    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        manager = attrs.get("manager", getattr(self.instance, "manager", None))
        if project is not None and not project.is_active:
            raise serializers.ValidationError(
                {"project": "امکان ثبت یا ویرایش انبار برای پروژه غیرفعال وجود ندارد."}
            )
        if manager is not None and hasattr(manager, "is_active") and not manager.is_active:
            raise serializers.ValidationError({"manager": "کاربر انتخاب‌شده غیرفعال است."})
        return attrs


class InventoryItemSerializer(serializers.ModelSerializer):
    total_quantity_on_hand = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    total_reserved_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    total_available_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "project",
            "code",
            "name",
            "item_type",
            "category",
            "unit_of_measure",
            "manufacturer",
            "part_number",
            "manufacturer_part_number",
            "description",
            "minimum_stock",
            "maximum_stock",
            "reorder_point",
            "standard_unit_cost",
            "is_critical",
            "is_active",
            "total_quantity_on_hand",
            "total_reserved_quantity",
            "total_available_quantity",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "total_quantity_on_hand",
            "total_reserved_quantity",
            "total_available_quantity",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        minimum_stock = attrs.get(
            "minimum_stock", getattr(self.instance, "minimum_stock", 0)
        )
        maximum_stock = attrs.get(
            "maximum_stock", getattr(self.instance, "maximum_stock", 0)
        )
        reorder_point = attrs.get(
            "reorder_point", getattr(self.instance, "reorder_point", 0)
        )

        errors = {}
        if project is not None and not project.is_active:
            errors["project"] = "امکان ثبت یا ویرایش کالا برای پروژه غیرفعال وجود ندارد."
        if maximum_stock > 0 and minimum_stock > maximum_stock:
            errors["minimum_stock"] = "حداقل موجودی نمی‌تواند بیشتر از حداکثر موجودی باشد."
        if maximum_stock > 0 and reorder_point > maximum_stock:
            errors["reorder_point"] = "نقطه سفارش نمی‌تواند بیشتر از حداکثر موجودی باشد."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def validate_standard_unit_cost(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "standard_unit_cost cannot be negative."
            )
        return value


class StockBalanceSerializer(serializers.ModelSerializer):
    warehouse_detail = WarehouseBriefSerializer(source="warehouse", read_only=True)
    item_detail = InventoryItemBriefSerializer(source="item", read_only=True)
    available_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    stock_value = serializers.DecimalField(
        max_digits=24, decimal_places=2, read_only=True
    )
    is_below_reorder_point = serializers.BooleanField(read_only=True)

    class Meta:
        model = StockBalance
        fields = (
            "id",
            "warehouse",
            "warehouse_detail",
            "item",
            "item_detail",
            "quantity_on_hand",
            "reserved_quantity",
            "available_quantity",
            "average_unit_cost",
            "stock_value",
            "is_below_reorder_point",
            "last_transaction_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkOrderPartSerializer(serializers.ModelSerializer):
    item_detail = InventoryItemBriefSerializer(source="item", read_only=True)
    warehouse_detail = WarehouseBriefSerializer(source="warehouse", read_only=True)
    remaining_requested_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    remaining_required_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    issued_available_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    estimated_total_cost = serializers.DecimalField(
        max_digits=24, decimal_places=2, read_only=True
    )
    consumed_total_cost = serializers.DecimalField(
        max_digits=24, decimal_places=2, read_only=True
    )

    class Meta:
        model = WorkOrderPart
        fields = (
            "id",
            "work_order",
            "item",
            "item_detail",
            "warehouse",
            "warehouse_detail",
            "requested_quantity",
            "reserved_quantity",
            "issued_quantity",
            "consumed_quantity",
            "returned_quantity",
            "remaining_requested_quantity",
            "remaining_required_quantity",
            "issued_available_quantity",
            "estimated_unit_cost",
            "estimated_total_cost",
            "consumed_total_cost",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "reserved_quantity",
            "issued_quantity",
            "consumed_quantity",
            "returned_quantity",
            "remaining_requested_quantity",
            "remaining_required_quantity",
            "issued_available_quantity",
            "estimated_total_cost",
            "consumed_total_cost",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        instance = self.instance
        work_order = attrs.get("work_order", getattr(instance, "work_order", None))
        item = attrs.get("item", getattr(instance, "item", None))
        warehouse = attrs.get("warehouse", getattr(instance, "warehouse", None))

        errors = {}
        if work_order and item and work_order.project_id != item.project_id:
            errors["item"] = "کالا و دستورکار باید متعلق به یک پروژه باشند."
        if warehouse and item and warehouse.project_id != item.project_id:
            errors["warehouse"] = "انبار و کالا باید متعلق به یک پروژه باشند."
        if warehouse and work_order and warehouse.project_id != work_order.project_id:
            errors["warehouse"] = "انبار و دستورکار باید متعلق به یک پروژه باشند."
        if item and not item.is_active:
            errors["item"] = "کالای غیرفعال قابل انتخاب نیست."
        if warehouse and not warehouse.is_active:
            errors["warehouse"] = "انبار غیرفعال قابل انتخاب نیست."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class StockTransactionSerializer(serializers.ModelSerializer):
    warehouse_detail = WarehouseBriefSerializer(source="warehouse", read_only=True)
    item_detail = InventoryItemBriefSerializer(source="item", read_only=True)
    counterpart_warehouse_detail = WarehouseBriefSerializer(
        source="counterpart_warehouse", read_only=True
    )
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )
    performed_by_display = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = StockTransaction
        fields = (
            "id",
            "project",
            "warehouse",
            "warehouse_detail",
            "item",
            "item_detail",
            "transaction_type",
            "transaction_type_display",
            "quantity",
            "unit_cost",
            "total_value",
            "balance_after",
            "reserved_balance_after",
            "work_order",
            "work_order_part",
            "counterpart_warehouse",
            "counterpart_warehouse_detail",
            "reference_number",
            "performed_by",
            "performed_by_display",
            "occurred_at",
            "notes",
            "is_void",
            "voided_by",
            "voided_at",
            "void_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_performed_by_display(self, obj):
        user = obj.performed_by
        full_name = user.get_full_name().strip() if hasattr(user, "get_full_name") else ""
        return full_name or getattr(user, "email", None) or str(user)

    def get_total_value(self, obj):
        return obj.quantity * obj.unit_cost


class StockOperationResultSerializer(serializers.Serializer):
    balance = StockBalanceSerializer(read_only=True)
    stock_transaction = StockTransactionSerializer(read_only=True)
    work_order_part = WorkOrderPartSerializer(read_only=True, allow_null=True)


class TransferResultSerializer(serializers.Serializer):
    source_balance = StockBalanceSerializer(read_only=True)
    destination_balance = StockBalanceSerializer(read_only=True)
    transfer_out_transaction = StockTransactionSerializer(read_only=True)
    transfer_in_transaction = StockTransactionSerializer(read_only=True)


class BaseInventoryActionSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(**QUANTITY_FIELD)
    reference_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    occurred_at = serializers.DateTimeField(required=False, allow_null=True)

    def _actor(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise serializers.ValidationError(
                {"detail": "کاربر احراز هویت‌شده برای ثبت عملیات لازم است."}
            )
        return user

    def _common_kwargs(self, validated_data):
        return {
            "quantity": validated_data["quantity"],
            "performed_by": self._actor(),
            "reference_number": validated_data.get("reference_number", ""),
            "notes": validated_data.get("notes", ""),
            "occurred_at": validated_data.get("occurred_at"),
        }


class StockReceiptSerializer(BaseInventoryActionSerializer):
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    item = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all())
    unit_cost = serializers.DecimalField(
        **COST_FIELD, required=False, allow_null=True
    )

    def validate(self, attrs):
        if attrs["warehouse"].project_id != attrs["item"].project_id:
            raise serializers.ValidationError(
                {"item": "کالا و انبار باید متعلق به یک پروژه باشند."}
            )
        return attrs

    def create(self, validated_data):
        try:
            return StockReceiptService.receive_stock(
                warehouse=validated_data["warehouse"],
                item=validated_data["item"],
                unit_cost=validated_data.get("unit_cost"),
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class WorkOrderPartActionSerializer(BaseInventoryActionSerializer):
    work_order_part = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrderPart.objects.select_related(
            "work_order", "item", "warehouse"
        ).all()
    )

    def validate_work_order_part(self, value):
        if value.warehouse_id is None:
            raise serializers.ValidationError(
                "برای قطعه دستورکار باید انبار تأمین‌کننده تعیین شده باشد."
            )
        return value


class StockReservationSerializer(WorkOrderPartActionSerializer):
    def create(self, validated_data):
        try:
            return ReservationService.reserve_stock(
                work_order_part=validated_data["work_order_part"],
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class StockReservationReleaseSerializer(WorkOrderPartActionSerializer):
    def create(self, validated_data):
        try:
            return ReservationService.release_reservation(
                work_order_part=validated_data["work_order_part"],
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class StockIssueSerializer(WorkOrderPartActionSerializer):
    def create(self, validated_data):
        try:
            return StockIssueService.issue_stock(
                work_order_part=validated_data["work_order_part"],
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class StockConsumptionSerializer(WorkOrderPartActionSerializer):
    def create(self, validated_data):
        try:
            return ConsumptionService.consume_part(
                work_order_part=validated_data["work_order_part"],
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class StockReturnSerializer(WorkOrderPartActionSerializer):
    def create(self, validated_data):
        try:
            return ConsumptionService.return_unused_part(
                work_order_part=validated_data["work_order_part"],
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class StockTransferSerializer(BaseInventoryActionSerializer):
    source_warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all()
    )
    destination_warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all()
    )
    item = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all())

    def validate(self, attrs):
        source = attrs["source_warehouse"]
        destination = attrs["destination_warehouse"]
        item = attrs["item"]
        errors = {}
        if source.pk == destination.pk:
            errors["destination_warehouse"] = "انبار مقصد باید با انبار مبدأ متفاوت باشد."
        if source.project_id != destination.project_id:
            errors["destination_warehouse"] = "انتقال بین پروژه‌های متفاوت مجاز نیست."
        if source.project_id != item.project_id:
            errors["item"] = "کالا و انبار مبدأ باید متعلق به یک پروژه باشند."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        try:
            return TransferService.transfer_stock(
                source_warehouse=validated_data["source_warehouse"],
                destination_warehouse=validated_data["destination_warehouse"],
                item=validated_data["item"],
                **self._common_kwargs(validated_data),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


class StockAdjustmentSerializer(BaseInventoryActionSerializer):
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    item = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all())
    quantity = serializers.DecimalField(
        **QUANTITY_FIELD,
        required=False,
    )
    quantity_difference = serializers.DecimalField(
        max_digits=18,
        decimal_places=3,
        required=False,
        allow_null=True,
    )
    direction = serializers.ChoiceField(
        choices=("in", "out"),
        required=False,
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    unit_cost = serializers.DecimalField(
        **COST_FIELD, required=False, allow_null=True
    )

    def validate(self, attrs):
        quantity_difference = attrs.get("quantity_difference")
        quantity = attrs.get("quantity")
        direction = attrs.get("direction")

        if quantity_difference is not None:
            if quantity_difference == 0:
                raise serializers.ValidationError(
                    {"quantity_difference": "Adjustment cannot be zero."}
                )
            inferred_direction = "in" if quantity_difference > 0 else "out"
            inferred_quantity = abs(quantity_difference)
            if quantity is not None and quantity != inferred_quantity:
                raise serializers.ValidationError(
                    {"quantity": "quantity must match quantity_difference."}
                )
            if direction is not None and direction != inferred_direction:
                raise serializers.ValidationError(
                    {"direction": "direction must match quantity_difference."}
                )
            attrs["quantity"] = inferred_quantity
            attrs["direction"] = inferred_direction
        elif quantity is None or direction is None:
            raise serializers.ValidationError(
                {
                    "quantity": "quantity or quantity_difference is required.",
                    "direction": "direction is required when quantity is used.",
                }
            )

        if attrs["warehouse"].project_id != attrs["item"].project_id:
            raise serializers.ValidationError(
                {"item": "کالا و انبار باید متعلق به یک پروژه باشند."}
            )
        if attrs["direction"] == "out" and attrs.get("unit_cost") is not None:
            raise serializers.ValidationError(
                {"unit_cost": "برای اصلاح کاهشی، بهای واحد از موجودی فعلی محاسبه می‌شود."}
            )
        reason = attrs.get("reason", "")
        if reason and not attrs.get("notes"):
            attrs["notes"] = reason
        return attrs

    def create(self, validated_data):
        try:
            return AdjustmentService.adjust_stock(
                warehouse=validated_data["warehouse"],
                item=validated_data["item"],
                quantity=validated_data["quantity"],
                direction=validated_data["direction"],
                performed_by=self._actor(),
                unit_cost=validated_data.get("unit_cost"),
                reference_number=validated_data.get("reference_number", ""),
                notes=validated_data.get("notes", ""),
                occurred_at=validated_data.get("occurred_at"),
            )
        except (InventoryServiceError, DjangoValidationError) as exc:
            _raise_drf_validation_error(exc)


# Backward-compatible names for views/tests that may use shorter serializer names.
StockReleaseSerializer = StockReservationReleaseSerializer
ReservationSerializer = StockReservationSerializer
ReservationReleaseSerializer = StockReservationReleaseSerializer
ConsumptionSerializer = StockConsumptionSerializer
ReturnSerializer = StockReturnSerializer
TransferSerializer = StockTransferSerializer
AdjustmentSerializer = StockAdjustmentSerializer

"""
API views for the inventory application.

Stock-changing business rules are not implemented in this module.
All operational actions are validated by serializers and executed through
the inventory service layer.
"""

from __future__ import annotations

from django.db.models import (
    DecimalField,
    F,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    filters,
    mixins,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import (
    InventoryItemFilter,
    StockBalanceFilter,
    StockTransactionFilter,
    WarehouseFilter,
    WorkOrderPartFilter,
)
from .models import (
    InventoryItem,
    StockBalance,
    StockTransaction,
    Warehouse,
    WorkOrderPart,
)
from .serializers import (
    InventoryItemSerializer,
    StockAdjustmentSerializer,
    StockBalanceSerializer,
    StockConsumptionSerializer,
    StockIssueSerializer,
    StockOperationResultSerializer,
    StockReceiptSerializer,
    StockReservationReleaseSerializer,
    StockReservationSerializer,
    StockReturnSerializer,
    StockTransactionSerializer,
    StockTransferSerializer,
    TransferResultSerializer,
    WarehouseSerializer,
    WorkOrderPartSerializer,
)


QUANTITY_OUTPUT_FIELD = DecimalField(
    max_digits=18,
    decimal_places=3,
)

ZERO_QUANTITY = Value(
    0,
    output_field=QUANTITY_OUTPUT_FIELD,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    CRUD API for warehouses.

    Available filters:
        project
        project_id
        warehouse_type
        manager
        manager_id
        is_active

    Search fields:
        code
        name
        address
        description
    """

    serializer_class = WarehouseSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = WarehouseFilter

    search_fields = [
        "code",
        "name",
        "address",
        "description",
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
        "warehouse_type",
        "is_active",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "project_id",
        "name",
        "id",
    ]

    queryset = Warehouse.objects.none()

    def get_queryset(self):
        return (
            Warehouse.objects
            .select_related(
                "project",
                "manager",
            )
            .all()
        )


class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    CRUD API for inventory item master data.

    Available filters:
        project
        project_id
        item_type
        category
        manufacturer
        unit_of_measure
        is_active
        is_critical
        below_reorder
        has_stock

    Search fields:
        code
        name
        category
        manufacturer
        part_number
        manufacturer_part_number
        description
    """

    serializer_class = InventoryItemSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = InventoryItemFilter

    search_fields = [
        "code",
        "name",
        "category",
        "manufacturer",
        "part_number",
        "manufacturer_part_number",
        "description",
    ]

    ordering_fields = [
        "id",
        "code",
        "name",
        "item_type",
        "category",
        "unit_of_measure",
        "manufacturer",
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
    ]

    ordering = [
        "project_id",
        "name",
        "id",
    ]

    queryset = InventoryItem.objects.none()

    def get_queryset(self):
        return (
            InventoryItem.objects
            .select_related(
                "project",
            )
            .annotate(
                total_quantity_on_hand=Coalesce(
                    Sum(
                        "stock_balances__quantity_on_hand"
                    ),
                    ZERO_QUANTITY,
                    output_field=QUANTITY_OUTPUT_FIELD,
                ),
                total_reserved_quantity=Coalesce(
                    Sum(
                        "stock_balances__reserved_quantity"
                    ),
                    ZERO_QUANTITY,
                    output_field=QUANTITY_OUTPUT_FIELD,
                ),
            )
            .annotate(
                total_available_quantity=(
                    F("total_quantity_on_hand")
                    - F("total_reserved_quantity")
                )
            )
        )


class StockBalanceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only API for stock balances.

    Stock balance rows cannot be directly created, edited or deleted through
    the API. All stock changes must use one of the operational actions.

    Operational endpoints:
        POST /stock-balances/receive/
        POST /stock-balances/reserve/
        POST /stock-balances/release-reservation/
        POST /stock-balances/issue/
        POST /stock-balances/consume/
        POST /stock-balances/return/
        POST /stock-balances/transfer/
        POST /stock-balances/adjust/

    Available filters:
        project
        project_id
        warehouse
        warehouse_id
        item
        item_id
        item_type
        is_critical
        below_reorder
        positive_only
        has_available_stock
    """

    serializer_class = StockBalanceSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = StockBalanceFilter

    search_fields = [
        "warehouse__code",
        "warehouse__name",
        "item__code",
        "item__name",
        "item__category",
        "item__manufacturer",
        "item__part_number",
        "item__manufacturer_part_number",
    ]

    ordering_fields = [
        "id",
        "warehouse__code",
        "warehouse__name",
        "item__code",
        "item__name",
        "quantity_on_hand",
        "reserved_quantity",
        "average_unit_cost",
        "last_transaction_at",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "warehouse__code",
        "item__name",
        "id",
    ]

    queryset = StockBalance.objects.none()

    action_serializer_classes = {
        "receive": StockReceiptSerializer,
        "reserve": StockReservationSerializer,
        "release_reservation": (
            StockReservationReleaseSerializer
        ),
        "issue": StockIssueSerializer,
        "consume": StockConsumptionSerializer,
        "return_stock": StockReturnSerializer,
        "transfer": StockTransferSerializer,
        "adjust": StockAdjustmentSerializer,
    }

    def get_serializer_class(self):
        return self.action_serializer_classes.get(
            self.action,
            self.serializer_class,
        )

    def get_queryset(self):
        return (
            StockBalance.objects
            .select_related(
                "warehouse",
                "warehouse__project",
                "warehouse__manager",
                "item",
                "item__project",
            )
            .all()
        )

    def execute_stock_operation(
        self,
        request,
        *,
        result_serializer_class,
    ):
        input_serializer = self.get_serializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                "request": request,
            },
        )

        input_serializer.is_valid(
            raise_exception=True
        )

        operation_result = input_serializer.save()

        output_serializer = result_serializer_class(
            operation_result,
            context=self.get_serializer_context(),
        )

        return Response(
            output_serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="receive",
    )
    def receive(self, request):
        """
        Receive stock into a warehouse.

        Request example:
        {
            "warehouse": 1,
            "item": 10,
            "quantity": "5.000",
            "unit_cost": "250.00",
            "reference_number": "GRN-1001",
            "notes": "Initial receipt"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="reserve",
    )
    def reserve(self, request):
        """
        Reserve available stock for a work-order part.

        Request example:
        {
            "work_order_part": 4,
            "quantity": "2.000",
            "reference_number": "RES-1001"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="release-reservation",
    )
    def release_reservation(self, request):
        """
        Release previously reserved stock.

        Request example:
        {
            "work_order_part": 4,
            "quantity": "1.000",
            "reference_number": "REL-1001"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="issue",
    )
    def issue(self, request):
        """
        Issue stock to a work-order part.

        Request example:
        {
            "work_order_part": 4,
            "quantity": "1.000",
            "reference_number": "ISS-1001"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="consume",
    )
    def consume(self, request):
        """
        Record consumption of an issued work-order part.

        Request example:
        {
            "work_order_part": 4,
            "quantity": "1.000",
            "reference_number": "CON-1001"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="return",
    )
    def return_stock(self, request):
        """
        Return an unused issued part to stock.

        Request example:
        {
            "work_order_part": 4,
            "quantity": "1.000",
            "reference_number": "RET-1001"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="transfer",
    )
    def transfer(self, request):
        """
        Transfer stock between two warehouses.

        Request example:
        {
            "source_warehouse": 1,
            "destination_warehouse": 2,
            "item": 10,
            "quantity": "3.000",
            "reference_number": "TRF-1001"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                TransferResultSerializer
            ),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="adjust",
    )
    def adjust(self, request):
        """
        Apply an increasing or decreasing stock adjustment.

        Increasing adjustment:
        {
            "warehouse": 1,
            "item": 10,
            "direction": "in",
            "quantity": "2.000",
            "unit_cost": "150.00",
            "reference_number": "ADJ-1001"
        }

        Decreasing adjustment:
        {
            "warehouse": 1,
            "item": 10,
            "direction": "out",
            "quantity": "2.000",
            "reference_number": "ADJ-1002"
        }
        """

        return self.execute_stock_operation(
            request,
            result_serializer_class=(
                StockOperationResultSerializer
            ),
        )


class WorkOrderPartViewSet(viewsets.ModelViewSet):
    """
    CRUD API for parts required by work orders.

    Quantity fields changed by stock operations are read-only in the serializer.

    Available filters:
        project
        project_id
        work_order
        work_order_id
        warehouse
        warehouse_id
        item
        item_id
        pending
        has_reservation
        has_issued_quantity
    """

    serializer_class = WorkOrderPartSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = WorkOrderPartFilter

    search_fields = [
        "item__code",
        "item__name",
        "item__category",
        "item__manufacturer",
        "item__part_number",
        "item__manufacturer_part_number",
        "warehouse__code",
        "warehouse__name",
        "notes",
    ]

    ordering_fields = [
        "id",
        "work_order_id",
        "item__code",
        "item__name",
        "warehouse__code",
        "requested_quantity",
        "reserved_quantity",
        "issued_quantity",
        "consumed_quantity",
        "returned_quantity",
        "estimated_unit_cost",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "work_order_id",
        "item_id",
        "id",
    ]

    queryset = WorkOrderPart.objects.none()

    def get_queryset(self):
        return (
            WorkOrderPart.objects
            .select_related(
                "work_order",
                "work_order__project",
                "item",
                "item__project",
                "warehouse",
                "warehouse__project",
            )
            .all()
        )


class StockTransactionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Immutable read-only inventory transaction ledger.

    Stock transactions must never be created, edited or deleted directly.
    They are automatically registered by inventory services.

    Available filters:
        project
        project_id
        warehouse
        warehouse_id
        item
        item_id
        work_order
        work_order_id
        work_order_part
        work_order_part_id
        counterpart_warehouse
        counterpart_warehouse_id
        transaction_type
        reference_number
        performed_by
        performed_by_id
        is_void
        occurred_from
        occurred_to
    """

    serializer_class = StockTransactionSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = StockTransactionFilter

    search_fields = [
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
    ]

    ordering_fields = [
        "id",
        "transaction_type",
        "quantity",
        "unit_cost",
        "balance_after",
        "reserved_balance_after",
        "reference_number",
        "occurred_at",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-occurred_at",
        "-id",
    ]

    queryset = StockTransaction.objects.none()

    def get_queryset(self):
        return (
            StockTransaction.objects
            .select_related(
                "project",
                "warehouse",
                "warehouse__project",
                "item",
                "item__project",
                "work_order",
                "work_order_part",
                "counterpart_warehouse",
                "performed_by",
                "voided_by",
            )
            .all()
        )
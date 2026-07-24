from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    InventoryItem,
    StockBalance,
    StockTransaction,
    StockTransactionType,
    Warehouse,
    WorkOrderPart,
)


QUANTITY_STEP = Decimal("0.001")
COST_STEP = Decimal("0.01")
ZERO_QUANTITY = Decimal("0.000")
ZERO_COST = Decimal("0.00")


class InventoryServiceError(Exception):
    """Base exception for inventory business-rule failures."""


class InvalidInventoryOperationError(InventoryServiceError):
    """Raised when an operation or its arguments are not valid."""


class InactiveInventoryObjectError(InventoryServiceError):
    """Raised when an inactive warehouse or item is used."""


class InventoryProjectMismatchError(InventoryServiceError):
    """Raised when related inventory objects belong to different projects."""


class StockBalanceNotFoundError(InventoryServiceError):
    """Raised when a stock balance is required but does not exist."""


class InsufficientStockError(InventoryServiceError):
    """Raised when physical or available stock is insufficient."""


class InsufficientReservedStockError(InventoryServiceError):
    """Raised when reserved stock is insufficient."""


class WorkOrderPartError(InventoryServiceError):
    """Raised for invalid work-order part operations."""


@dataclass(frozen=True, slots=True)
class StockOperationResult:
    """Result returned by single-warehouse stock operations."""

    balance: StockBalance
    stock_transaction: StockTransaction
    work_order_part: WorkOrderPart | None = None


@dataclass(frozen=True, slots=True)
class TransferResult:
    """Result returned by an inter-warehouse transfer."""

    source_balance: StockBalance
    destination_balance: StockBalance
    transfer_out_transaction: StockTransaction
    transfer_in_transaction: StockTransaction


def _as_quantity(value: Any, *, field_name: str = "quantity") -> Decimal:
    try:
        quantity = Decimal(str(value)).quantize(
            QUANTITY_STEP,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidInventoryOperationError(
            f"{field_name} must be a valid decimal number."
        ) from exc

    if quantity <= ZERO_QUANTITY:
        raise InvalidInventoryOperationError(
            f"{field_name} must be greater than zero."
        )

    return quantity


def _as_cost(value: Any, *, field_name: str = "unit_cost") -> Decimal:
    try:
        cost = Decimal(str(value)).quantize(
            COST_STEP,
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidInventoryOperationError(
            f"{field_name} must be a valid decimal number."
        ) from exc

    if cost < ZERO_COST:
        raise InvalidInventoryOperationError(
            f"{field_name} cannot be negative."
        )

    return cost


def _clean_text(value: Any, *, upper: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    return text.upper() if upper else text


def _validate_actor(performed_by: Any) -> None:
    if performed_by is None or getattr(performed_by, "pk", None) is None:
        raise InvalidInventoryOperationError(
            "performed_by must be a saved user instance."
        )


def _validate_active_objects(
    *,
    warehouse: Warehouse,
    item: InventoryItem,
) -> None:
    if not warehouse.is_active:
        raise InactiveInventoryObjectError("The warehouse is inactive.")
    if not item.is_active:
        raise InactiveInventoryObjectError("The inventory item is inactive.")
    if warehouse.project_id != item.project_id:
        raise InventoryProjectMismatchError(
            "The warehouse and item must belong to the same project."
        )


def _lock_warehouse_and_item(
    *,
    warehouse_id: int,
    item_id: int,
) -> tuple[Warehouse, InventoryItem]:
    warehouse = (
        Warehouse.objects.select_for_update()
        .select_related("project")
        .get(pk=warehouse_id)
    )
    item = (
        InventoryItem.objects.select_for_update()
        .select_related("project")
        .get(pk=item_id)
    )
    _validate_active_objects(warehouse=warehouse, item=item)
    return warehouse, item


def _get_or_create_locked_balance(
    *,
    warehouse: Warehouse,
    item: InventoryItem,
) -> StockBalance:
    try:
        return StockBalance.objects.select_for_update().get(
            warehouse=warehouse,
            item=item,
        )
    except StockBalance.DoesNotExist:
        try:
            return StockBalance.objects.create(
                warehouse=warehouse,
                item=item,
                quantity_on_hand=ZERO_QUANTITY,
                reserved_quantity=ZERO_QUANTITY,
                average_unit_cost=ZERO_COST,
            )
        except IntegrityError:
            # A concurrent transaction may have created the row after our read.
            return StockBalance.objects.select_for_update().get(
                warehouse=warehouse,
                item=item,
            )


def _get_locked_balance(
    *,
    warehouse: Warehouse,
    item: InventoryItem,
) -> StockBalance:
    try:
        return StockBalance.objects.select_for_update().get(
            warehouse=warehouse,
            item=item,
        )
    except StockBalance.DoesNotExist as exc:
        raise StockBalanceNotFoundError(
            f"No stock balance exists for warehouse={warehouse.pk}, "
            f"item={item.pk}."
        ) from exc


def _lock_work_order_part(work_order_part_id: int) -> WorkOrderPart:
    try:
        return (
            WorkOrderPart.objects.select_for_update()
            .select_related("work_order", "item", "warehouse")
            .get(pk=work_order_part_id)
        )
    except WorkOrderPart.DoesNotExist as exc:
        raise WorkOrderPartError("The work-order part does not exist.") from exc


def _validate_work_order_part(part: WorkOrderPart) -> None:
    if part.warehouse_id is None:
        raise WorkOrderPartError(
            "A supplying warehouse must be assigned to the work-order part."
        )
    if not part.warehouse.is_active:
        raise InactiveInventoryObjectError(
            "The work-order part warehouse is inactive."
        )
    if not part.item.is_active:
        raise InactiveInventoryObjectError(
            "The work-order part item is inactive."
        )
    if part.work_order.project_id != part.item.project_id:
        raise InventoryProjectMismatchError(
            "The work order and item belong to different projects."
        )
    if part.warehouse.project_id != part.work_order.project_id:
        raise InventoryProjectMismatchError(
            "The work order and warehouse belong to different projects."
        )


def _create_stock_transaction(
    *,
    warehouse: Warehouse,
    item: InventoryItem,
    transaction_type: str,
    quantity: Decimal,
    unit_cost: Decimal,
    balance: StockBalance,
    performed_by: Any,
    occurred_at: Any = None,
    work_order_part: WorkOrderPart | None = None,
    counterpart_warehouse: Warehouse | None = None,
    reference_number: str = "",
    notes: str = "",
) -> StockTransaction:
    work_order = work_order_part.work_order if work_order_part else None

    return StockTransaction.objects.create(
        project=warehouse.project,
        warehouse=warehouse,
        item=item,
        transaction_type=transaction_type,
        quantity=quantity,
        unit_cost=unit_cost,
        balance_after=balance.quantity_on_hand,
        reserved_balance_after=balance.reserved_quantity,
        work_order=work_order,
        work_order_part=work_order_part,
        counterpart_warehouse=counterpart_warehouse,
        reference_number=_clean_text(reference_number, upper=True),
        performed_by=performed_by,
        occurred_at=occurred_at or timezone.now(),
        notes=_clean_text(notes),
    )


class InventoryService:
    """Read-oriented helpers and shared stock-balance operations."""

    @staticmethod
    def get_stock_balance(
        *,
        warehouse: Warehouse,
        item: InventoryItem,
    ) -> StockBalance | None:
        _validate_active_objects(warehouse=warehouse, item=item)
        return StockBalance.objects.filter(
            warehouse=warehouse,
            item=item,
        ).first()

    @staticmethod
    def get_available_quantity(
        *,
        warehouse: Warehouse,
        item: InventoryItem,
    ) -> Decimal:
        balance = InventoryService.get_stock_balance(
            warehouse=warehouse,
            item=item,
        )
        return balance.available_quantity if balance else ZERO_QUANTITY

    @staticmethod
    @transaction.atomic
    def get_or_create_balance(
        *,
        warehouse: Warehouse,
        item: InventoryItem,
    ) -> StockBalance:
        locked_warehouse, locked_item = _lock_warehouse_and_item(
            warehouse_id=warehouse.pk,
            item_id=item.pk,
        )
        return _get_or_create_locked_balance(
            warehouse=locked_warehouse,
            item=locked_item,
        )


class StockReceiptService:
    """Receive stock and maintain weighted-average inventory cost."""

    @staticmethod
    @transaction.atomic
    def receive_stock(
        *,
        warehouse: Warehouse,
        item: InventoryItem,
        quantity: Any,
        performed_by: Any,
        unit_cost: Any | None = None,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        cost_value = _as_cost(
            item.standard_unit_cost if unit_cost is None else unit_cost
        )

        locked_warehouse, locked_item = _lock_warehouse_and_item(
            warehouse_id=warehouse.pk,
            item_id=item.pk,
        )
        balance = _get_or_create_locked_balance(
            warehouse=locked_warehouse,
            item=locked_item,
        )

        old_quantity = balance.quantity_on_hand
        old_value = old_quantity * balance.average_unit_cost
        received_value = quantity_value * cost_value
        new_quantity = old_quantity + quantity_value
        new_average_cost = (
            (old_value + received_value) / new_quantity
        ).quantize(COST_STEP, rounding=ROUND_HALF_UP)

        balance.quantity_on_hand = new_quantity
        balance.average_unit_cost = new_average_cost
        balance.last_transaction_at = occurred_at or timezone.now()
        balance.save(
            update_fields=[
                "quantity_on_hand",
                "average_unit_cost",
                "last_transaction_at",
                "updated_at",
            ]
        )

        stock_transaction = _create_stock_transaction(
            warehouse=locked_warehouse,
            item=locked_item,
            transaction_type=StockTransactionType.RECEIPT,
            quantity=quantity_value,
            unit_cost=cost_value,
            balance=balance,
            performed_by=performed_by,
            occurred_at=balance.last_transaction_at,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction)


class ReservationService:
    """Reserve and release available stock for a work order."""

    @staticmethod
    @transaction.atomic
    def reserve_stock(
        *,
        work_order_part: WorkOrderPart,
        quantity: Any,
        performed_by: Any,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        part = _lock_work_order_part(work_order_part.pk)
        _validate_work_order_part(part)

        warehouse, item = _lock_warehouse_and_item(
            warehouse_id=part.warehouse_id,
            item_id=part.item_id,
        )
        balance = _get_locked_balance(warehouse=warehouse, item=item)

        if quantity_value > part.remaining_requested_quantity:
            raise WorkOrderPartError(
                "The requested reservation exceeds the unissued quantity."
            )
        if quantity_value > balance.available_quantity:
            raise InsufficientStockError(
                "Available stock is insufficient for this reservation."
            )

        operation_time = occurred_at or timezone.now()
        balance.reserved_quantity += quantity_value
        balance.last_transaction_at = operation_time
        balance.save(
            update_fields=[
                "reserved_quantity",
                "last_transaction_at",
                "updated_at",
            ]
        )

        part.reserved_quantity += quantity_value
        part.save(update_fields=["reserved_quantity", "updated_at"])

        stock_transaction = _create_stock_transaction(
            warehouse=warehouse,
            item=item,
            transaction_type=StockTransactionType.RESERVATION,
            quantity=quantity_value,
            unit_cost=balance.average_unit_cost,
            balance=balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            work_order_part=part,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction, part)

    @staticmethod
    @transaction.atomic
    def release_reservation(
        *,
        work_order_part: WorkOrderPart,
        quantity: Any,
        performed_by: Any,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        part = _lock_work_order_part(work_order_part.pk)
        _validate_work_order_part(part)

        warehouse, item = _lock_warehouse_and_item(
            warehouse_id=part.warehouse_id,
            item_id=part.item_id,
        )
        balance = _get_locked_balance(warehouse=warehouse, item=item)

        if quantity_value > part.reserved_quantity:
            raise InsufficientReservedStockError(
                "The work-order part does not have enough reserved quantity."
            )
        if quantity_value > balance.reserved_quantity:
            raise InsufficientReservedStockError(
                "The stock balance does not have enough reserved quantity."
            )

        operation_time = occurred_at or timezone.now()
        balance.reserved_quantity -= quantity_value
        balance.last_transaction_at = operation_time
        balance.save(
            update_fields=[
                "reserved_quantity",
                "last_transaction_at",
                "updated_at",
            ]
        )

        part.reserved_quantity -= quantity_value
        part.save(update_fields=["reserved_quantity", "updated_at"])

        stock_transaction = _create_stock_transaction(
            warehouse=warehouse,
            item=item,
            transaction_type=StockTransactionType.RESERVATION_RELEASE,
            quantity=quantity_value,
            unit_cost=balance.average_unit_cost,
            balance=balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            work_order_part=part,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction, part)


class StockIssueService:
    """Issue previously reserved stock to a work order."""

    @staticmethod
    @transaction.atomic
    def issue_stock(
        *,
        work_order_part: WorkOrderPart,
        quantity: Any,
        performed_by: Any,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        part = _lock_work_order_part(work_order_part.pk)
        _validate_work_order_part(part)

        warehouse, item = _lock_warehouse_and_item(
            warehouse_id=part.warehouse_id,
            item_id=part.item_id,
        )
        balance = _get_locked_balance(warehouse=warehouse, item=item)

        if quantity_value > part.reserved_quantity:
            raise InsufficientReservedStockError(
                "Issue quantity exceeds the part's reserved quantity."
            )
        if quantity_value > balance.reserved_quantity:
            raise InsufficientReservedStockError(
                "Issue quantity exceeds the warehouse's reserved quantity."
            )
        if quantity_value > balance.quantity_on_hand:
            raise InsufficientStockError(
                "Physical stock is insufficient for this issue."
            )
        if part.issued_quantity + quantity_value > part.requested_quantity:
            raise WorkOrderPartError(
                "Issue quantity would exceed the requested quantity."
            )

        operation_time = occurred_at or timezone.now()
        issue_cost = balance.average_unit_cost
        balance.quantity_on_hand -= quantity_value
        balance.reserved_quantity -= quantity_value
        balance.last_transaction_at = operation_time
        balance.save(
            update_fields=[
                "quantity_on_hand",
                "reserved_quantity",
                "last_transaction_at",
                "updated_at",
            ]
        )

        part.reserved_quantity -= quantity_value
        part.issued_quantity += quantity_value
        if part.estimated_unit_cost == ZERO_COST:
            part.estimated_unit_cost = issue_cost
        part.save(
            update_fields=[
                "reserved_quantity",
                "issued_quantity",
                "estimated_unit_cost",
                "updated_at",
            ]
        )

        stock_transaction = _create_stock_transaction(
            warehouse=warehouse,
            item=item,
            transaction_type=StockTransactionType.ISSUE,
            quantity=quantity_value,
            unit_cost=issue_cost,
            balance=balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            work_order_part=part,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction, part)


class ConsumptionService:
    """Record consumption or return of stock already issued to a work order."""

    @staticmethod
    @transaction.atomic
    def consume_part(
        *,
        work_order_part: WorkOrderPart,
        quantity: Any,
        performed_by: Any,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        part = _lock_work_order_part(work_order_part.pk)
        _validate_work_order_part(part)

        warehouse, item = _lock_warehouse_and_item(
            warehouse_id=part.warehouse_id,
            item_id=part.item_id,
        )
        balance = _get_locked_balance(warehouse=warehouse, item=item)

        if quantity_value > part.issued_available_quantity:
            raise WorkOrderPartError(
                "Consumption exceeds the issued quantity still available."
            )

        operation_time = occurred_at or timezone.now()
        part.consumed_quantity += quantity_value
        part.save(update_fields=["consumed_quantity", "updated_at"])

        # Stock was reduced at issue time; consumption only changes WO usage.
        balance.last_transaction_at = operation_time
        balance.save(update_fields=["last_transaction_at", "updated_at"])

        stock_transaction = _create_stock_transaction(
            warehouse=warehouse,
            item=item,
            transaction_type=StockTransactionType.CONSUMPTION,
            quantity=quantity_value,
            unit_cost=part.estimated_unit_cost,
            balance=balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            work_order_part=part,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction, part)

    @staticmethod
    @transaction.atomic
    def return_unused_part(
        *,
        work_order_part: WorkOrderPart,
        quantity: Any,
        performed_by: Any,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        part = _lock_work_order_part(work_order_part.pk)
        _validate_work_order_part(part)

        warehouse, item = _lock_warehouse_and_item(
            warehouse_id=part.warehouse_id,
            item_id=part.item_id,
        )
        balance = _get_or_create_locked_balance(
            warehouse=warehouse,
            item=item,
        )

        if quantity_value > part.issued_available_quantity:
            raise WorkOrderPartError(
                "Return quantity exceeds the issued quantity still available."
            )

        operation_time = occurred_at or timezone.now()
        old_quantity = balance.quantity_on_hand
        return_cost = part.estimated_unit_cost
        new_quantity = old_quantity + quantity_value

        if return_cost > ZERO_COST:
            old_value = old_quantity * balance.average_unit_cost
            return_value = quantity_value * return_cost
            balance.average_unit_cost = (
                (old_value + return_value) / new_quantity
            ).quantize(COST_STEP, rounding=ROUND_HALF_UP)

        balance.quantity_on_hand = new_quantity
        balance.last_transaction_at = operation_time
        balance.save(
            update_fields=[
                "quantity_on_hand",
                "average_unit_cost",
                "last_transaction_at",
                "updated_at",
            ]
        )

        part.returned_quantity += quantity_value
        part.save(update_fields=["returned_quantity", "updated_at"])

        stock_transaction = _create_stock_transaction(
            warehouse=warehouse,
            item=item,
            transaction_type=StockTransactionType.RETURN,
            quantity=quantity_value,
            unit_cost=return_cost,
            balance=balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            work_order_part=part,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction, part)


class TransferService:
    """Transfer available stock between active warehouses in one project."""

    @staticmethod
    @transaction.atomic
    def transfer_stock(
        *,
        source_warehouse: Warehouse,
        destination_warehouse: Warehouse,
        item: InventoryItem,
        quantity: Any,
        performed_by: Any,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> TransferResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)

        if source_warehouse.pk == destination_warehouse.pk:
            raise InvalidInventoryOperationError(
                "Source and destination warehouses must be different."
            )

        warehouse_ids = sorted(
            [source_warehouse.pk, destination_warehouse.pk]
        )
        locked_warehouses = {
            warehouse.pk: warehouse
            for warehouse in Warehouse.objects.select_for_update()
            .select_related("project")
            .filter(pk__in=warehouse_ids)
            .order_by("pk")
        }
        if len(locked_warehouses) != 2:
            raise InvalidInventoryOperationError(
                "One or both warehouses do not exist."
            )

        source = locked_warehouses[source_warehouse.pk]
        destination = locked_warehouses[destination_warehouse.pk]
        locked_item = (
            InventoryItem.objects.select_for_update()
            .select_related("project")
            .get(pk=item.pk)
        )

        _validate_active_objects(warehouse=source, item=locked_item)
        _validate_active_objects(warehouse=destination, item=locked_item)
        if source.project_id != destination.project_id:
            raise InventoryProjectMismatchError(
                "Transfers between different projects are not allowed."
            )

        source_balance = _get_locked_balance(
            warehouse=source,
            item=locked_item,
        )
        destination_balance = _get_or_create_locked_balance(
            warehouse=destination,
            item=locked_item,
        )

        if quantity_value > source_balance.available_quantity:
            raise InsufficientStockError(
                "Available stock is insufficient for this transfer."
            )

        operation_time = occurred_at or timezone.now()
        transfer_cost = source_balance.average_unit_cost
        source_balance.quantity_on_hand -= quantity_value
        source_balance.last_transaction_at = operation_time
        source_balance.save(
            update_fields=[
                "quantity_on_hand",
                "last_transaction_at",
                "updated_at",
            ]
        )

        destination_old_quantity = destination_balance.quantity_on_hand
        destination_new_quantity = destination_old_quantity + quantity_value
        destination_old_value = (
            destination_old_quantity * destination_balance.average_unit_cost
        )
        transfer_value = quantity_value * transfer_cost
        destination_balance.quantity_on_hand = destination_new_quantity
        destination_balance.average_unit_cost = (
            (destination_old_value + transfer_value)
            / destination_new_quantity
        ).quantize(COST_STEP, rounding=ROUND_HALF_UP)
        destination_balance.last_transaction_at = operation_time
        destination_balance.save(
            update_fields=[
                "quantity_on_hand",
                "average_unit_cost",
                "last_transaction_at",
                "updated_at",
            ]
        )

        transfer_out = _create_stock_transaction(
            warehouse=source,
            item=locked_item,
            transaction_type=StockTransactionType.TRANSFER_OUT,
            quantity=quantity_value,
            unit_cost=transfer_cost,
            balance=source_balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            counterpart_warehouse=destination,
            reference_number=reference_number,
            notes=notes,
        )
        transfer_in = _create_stock_transaction(
            warehouse=destination,
            item=locked_item,
            transaction_type=StockTransactionType.TRANSFER_IN,
            quantity=quantity_value,
            unit_cost=transfer_cost,
            balance=destination_balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            counterpart_warehouse=source,
            reference_number=reference_number,
            notes=notes,
        )

        return TransferResult(
            source_balance=source_balance,
            destination_balance=destination_balance,
            transfer_out_transaction=transfer_out,
            transfer_in_transaction=transfer_in,
        )


class AdjustmentService:
    """Apply approved physical stock adjustments."""

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        *,
        warehouse: Warehouse,
        item: InventoryItem,
        quantity: Any,
        direction: str,
        performed_by: Any,
        unit_cost: Any | None = None,
        reference_number: str = "",
        notes: str = "",
        occurred_at: Any = None,
    ) -> StockOperationResult:
        _validate_actor(performed_by)
        quantity_value = _as_quantity(quantity)
        normalized_direction = _clean_text(direction).lower()
        if normalized_direction not in {"in", "out"}:
            raise InvalidInventoryOperationError(
                "direction must be either 'in' or 'out'."
            )

        locked_warehouse, locked_item = _lock_warehouse_and_item(
            warehouse_id=warehouse.pk,
            item_id=item.pk,
        )
        balance = _get_or_create_locked_balance(
            warehouse=locked_warehouse,
            item=locked_item,
        )
        operation_time = occurred_at or timezone.now()

        if normalized_direction == "in":
            adjustment_cost = _as_cost(
                balance.average_unit_cost
                if unit_cost is None
                else unit_cost
            )
            old_quantity = balance.quantity_on_hand
            new_quantity = old_quantity + quantity_value
            old_value = old_quantity * balance.average_unit_cost
            new_value = quantity_value * adjustment_cost
            balance.quantity_on_hand = new_quantity
            balance.average_unit_cost = (
                (old_value + new_value) / new_quantity
            ).quantize(COST_STEP, rounding=ROUND_HALF_UP)
            transaction_type = StockTransactionType.ADJUSTMENT_IN
        else:
            if quantity_value > balance.available_quantity:
                raise InsufficientStockError(
                    "Available stock is insufficient for this adjustment."
                )
            adjustment_cost = balance.average_unit_cost
            balance.quantity_on_hand -= quantity_value
            transaction_type = StockTransactionType.ADJUSTMENT_OUT

        balance.last_transaction_at = operation_time
        balance.save(
            update_fields=[
                "quantity_on_hand",
                "average_unit_cost",
                "last_transaction_at",
                "updated_at",
            ]
        )

        stock_transaction = _create_stock_transaction(
            warehouse=locked_warehouse,
            item=locked_item,
            transaction_type=transaction_type,
            quantity=quantity_value,
            unit_cost=adjustment_cost,
            balance=balance,
            performed_by=performed_by,
            occurred_at=operation_time,
            reference_number=reference_number,
            notes=notes,
        )
        return StockOperationResult(balance, stock_transaction)


# Backward-friendly aliases for concise imports in serializers and tests.
StockService = InventoryService
ReturnService = ConsumptionService
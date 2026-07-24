"""
Comprehensive tests for the inventory application.
"""

from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

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
    StockTransactionType,
    Warehouse,
    WorkOrderPart,
    UnitOfMeasure,
)

from .serializers import (
    InventoryItemSerializer,
    StockAdjustmentSerializer,
    StockReceiptSerializer,
    StockTransferSerializer,
    WarehouseSerializer,
    WorkOrderPartSerializer,
)

from .services import (
    AdjustmentService,
    ConsumptionService,
    InactiveInventoryObjectError,
    InsufficientReservedStockError,
    InsufficientStockError,
    InvalidInventoryOperationError,
    InventoryProjectMismatchError,
    ReservationService,
    StockIssueService,
    StockReceiptService,
    TransferService,
    WorkOrderPartError,
    InventoryService,
    StockBalanceNotFoundError,
)

from .views import (
    InventoryItemViewSet,
    StockBalanceViewSet,
    StockTransactionViewSet,
    WarehouseViewSet,
    WorkOrderPartViewSet,
)

D0 = Decimal("0.000")
D1 = Decimal("1.000")
D2 = Decimal("2.000")
D3 = Decimal("3.000")
D5 = Decimal("5.000")
D10 = Decimal("10.000")
D20 = Decimal("20.000")
D4 = Decimal("4.000")
D6 = Decimal("6.000")
D12 = Decimal("12.000")
class InventoryFixtureMixin:

    @classmethod
    def setUpTestData(cls):

        User = get_user_model()

        username_field = User.USERNAME_FIELD

        kwargs = {
            username_field:
                "inventory@example.com"
                if username_field == "email"
                else "inventory"
        }

        for field in getattr(User, "REQUIRED_FIELDS", []):

            if field not in kwargs:

                model_field = User._meta.get_field(field)

                if model_field.get_internal_type() == "EmailField":
                    kwargs[field] = f"{field}@example.com"
                else:
                    kwargs[field] = field

        cls.user = User.objects.create_user(
            password="Password123!",
            **kwargs,
        )

        Organization = apps.get_model(
            "organizations",
            "Organization",
        )

        cls.organization = Organization.objects.create(
            code="ORG1",
            name="Organization",
        )

        Project = apps.get_model(
            "projects",
            "Project",
        )

        cls.project = Project.objects.create(
            organization=cls.organization,
            code="P1",
            name="Project One",
            is_active=True,
        )

        cls.project2 = Project.objects.create(
            organization=cls.organization,
            code="P2",
            name="Project Two",
            is_active=True,
        )

        cls.warehouse = Warehouse.objects.create(
            project=cls.project,
            code=" wh-main ",
            name=" Main Warehouse ",
            manager=cls.user,
            is_active=True,
        )

        cls.destination = Warehouse.objects.create(
            project=cls.project,
            code="WH-DEST",
            name="Destination",
            manager=cls.user,
            is_active=True,
        )

        cls.other_warehouse = Warehouse.objects.create(
            project=cls.project2,
            code="WH-OTHER",
            name="Other",
            manager=cls.user,
            is_active=True,
        )

        cls.item = InventoryItem.objects.create(
            project=cls.project,
            code=" itm-100 ",
            name=" Main Bearing ",
            category=" Mechanical ",
            manufacturer=" SKF ",
            part_number=" br-100 ",
            manufacturer_part_number=" skf-100 ",
            unit_of_measure=UnitOfMeasure.EACH,
            minimum_stock=Decimal("2.000"),
            maximum_stock=Decimal("100.000"),
            reorder_point=Decimal("5.000"),
            standard_unit_cost=Decimal("10.00"),
            is_active=True,
            is_critical=True,
        )

        cls.item2 = InventoryItem.objects.create(
            project=cls.project,
            code="ITM-200",
            name="Seal",
            unit_of_measure=UnitOfMeasure.EACH,
            standard_unit_cost=Decimal("5.00"),
            is_active=True,
        )

        cls.other_item = InventoryItem.objects.create(
            project=cls.project2,
            code="ITM-OTHER",
            name="Other Item",
            unit_of_measure=UnitOfMeasure.EACH,
            standard_unit_cost=Decimal("7.00"),
            is_active=True,
        )

        WorkOrder = apps.get_model(
            "work_orders",
            "WorkOrder",
        )

        cls.work_order = WorkOrder.objects.create(
    project=cls.project,
    work_order_number="WO-1",
    title="Inventory Test",
    description="Inventory test work order",
    created_by=cls.user,
)

        
    def create_balance(
        self,
        warehouse=None,
        item=None,
        quantity=D10,
        reserved=D0,
        cost=Decimal("10.00"),
    ):

        return StockBalance.objects.create(
            warehouse=warehouse or self.warehouse,
            item=item or self.item,
            quantity_on_hand=quantity,
            reserved_quantity=reserved,
            average_unit_cost=cost,
        )

    def create_part(
        self,
        requested=D10,
        reserved=D0,
        issued=D0,
        consumed=D0,
        returned=D0,
    ):

        return WorkOrderPart.objects.create(
            work_order=self.work_order,
            warehouse=self.warehouse,
            item=self.item,
            requested_quantity=requested,
            reserved_quantity=reserved,
            issued_quantity=issued,
            consumed_quantity=consumed,
            returned_quantity=returned,
        )
class WarehouseModelTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_warehouse_fields_are_normalized(self):

        self.assertEqual(
            self.warehouse.code,
            "WH-MAIN",
        )

        self.assertEqual(
            self.warehouse.name,
            "Main Warehouse",
        )

    def test_warehouse_string_representation(self):

        self.assertEqual(
            str(self.warehouse),
            "WH-MAIN - Main Warehouse",
        )

    def test_duplicate_warehouse_code_in_same_project_is_invalid(self):

        with self.assertRaises(
            (
                ValidationError,
                IntegrityError,
            )
        ):

            with transaction.atomic():

                Warehouse.objects.create(
                    project=self.project,
                    code="WH-MAIN",
                    name="Duplicate Warehouse",
                )

    def test_same_warehouse_code_in_different_projects_is_allowed(self):

        warehouse = Warehouse.objects.create(
            project=self.project2,
            code="WH-MAIN",
            name="Warehouse in Project Two",
        )

        self.assertIsNotNone(
            warehouse.pk,
        )

    def test_inactive_project_cannot_have_new_warehouse(self):

        self.project.is_active = False

        self.project.save(
            update_fields=[
                "is_active",
            ]
        )

        with self.assertRaises(
            ValidationError,
        ):

            Warehouse.objects.create(
                project=self.project,
                code="WH-INACTIVE",
                name="Invalid Warehouse",
            )


class InventoryItemModelTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_item_text_fields_are_normalized(self):

        self.assertEqual(
            self.item.code,
            "ITM-100",
        )

        self.assertEqual(
            self.item.name,
            "Main Bearing",
        )

        self.assertEqual(
            self.item.category,
            "Mechanical",
        )

        self.assertEqual(
            self.item.manufacturer,
            "SKF",
        )

        self.assertEqual(
            self.item.part_number,
            "BR-100",
        )

        self.assertEqual(
            self.item.manufacturer_part_number,
            "SKF-100",
        )

    def test_item_string_representation(self):

        self.assertEqual(
            str(self.item),
            "ITM-100 - Main Bearing",
        )

    def test_duplicate_item_code_in_same_project_is_invalid(self):

        with self.assertRaises(
            (
                ValidationError,
                IntegrityError,
            )
        ):

            with transaction.atomic():

                InventoryItem.objects.create(
                    project=self.project,
                    code="ITM-100",
                    name="Duplicate Item",
                    unit_of_measure=UnitOfMeasure.EACH,
                )

    def test_same_item_code_in_different_project_is_allowed(self):

        item = InventoryItem.objects.create(
            project=self.project2,
            code="ITM-100",
            name="Other Project Item",
            unit_of_measure=UnitOfMeasure.EACH,
        )

        self.assertIsNotNone(
            item.pk,
        )

    def test_minimum_stock_cannot_exceed_maximum_stock(self):

        with self.assertRaises(
            ValidationError,
        ):

            InventoryItem.objects.create(
                project=self.project,
                code="ITM-BAD-1",
                name="Invalid Minimum",
                unit_of_measure=UnitOfMeasure.EACH,
                minimum_stock=Decimal("20.000"),
                maximum_stock=Decimal("10.000"),
            )

    def test_reorder_point_cannot_exceed_maximum_stock(self):

        with self.assertRaises(
            ValidationError,
        ):

            InventoryItem.objects.create(
                project=self.project,
                code="ITM-BAD-2",
                name="Invalid Reorder Point",
                unit_of_measure=UnitOfMeasure.EACH,
                maximum_stock=Decimal("10.000"),
                reorder_point=Decimal("15.000"),
            )

    def test_negative_standard_unit_cost_is_invalid(self):

        with self.assertRaises(
            ValidationError,
        ):

            InventoryItem.objects.create(
                project=self.project,
                code="ITM-BAD-3",
                name="Negative Cost",
                unit_of_measure=UnitOfMeasure.EACH,
                standard_unit_cost=Decimal("-1.00"),
            )


class StockBalanceModelTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_available_quantity(self):

        balance = self.create_balance(
            quantity=D10,
            reserved=D3,
        )

        self.assertEqual(
            balance.available_quantity,
            Decimal("7.000"),
        )

    def test_stock_value(self):

        balance = self.create_balance(
            quantity=D10,
            cost=Decimal("12.50"),
        )

        self.assertEqual(
            balance.stock_value,
            Decimal("125.00000"),
        )

    def test_below_reorder_point_uses_available_quantity(self):

        balance = self.create_balance(
            quantity=D10,
            reserved=D5,
        )

        self.assertTrue(
            balance.is_below_reorder_point,
        )

    def test_balance_string_representation(self):

        balance = self.create_balance(
            quantity=D10,
        )

        self.assertEqual(
            str(balance),
            "WH-MAIN - ITM-100 - 10.000",
        )

    def test_reserved_quantity_cannot_exceed_stock(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_balance(
                quantity=D2,
                reserved=D3,
            )

    def test_negative_quantity_on_hand_is_invalid(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_balance(
                quantity=Decimal("-1.000"),
            )

    def test_negative_reserved_quantity_is_invalid(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_balance(
                reserved=Decimal("-1.000"),
            )

    def test_negative_average_cost_is_invalid(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_balance(
                cost=Decimal("-1.00"),
            )

    def test_cross_project_stock_balance_is_invalid(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_balance(
                warehouse=self.warehouse,
                item=self.other_item,
            )

    def test_balance_must_be_unique_for_warehouse_and_item(self):

        self.create_balance()

        with self.assertRaises(
            (
                ValidationError,
                IntegrityError,
            )
        ):

            with transaction.atomic():

                self.create_balance()


class WorkOrderPartModelTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_remaining_required_quantity(self):

        part = self.create_part(
            requested=D10,
            issued=D3,
        )

        self.assertEqual(
            part.remaining_required_quantity,
            Decimal("7.000"),
        )

    def test_issued_available_quantity(self):

        part = self.create_part(
            requested=D10,
            issued=D5,
            consumed=D2,
            returned=D1,
        )

        self.assertEqual(
            part.issued_available_quantity,
            Decimal("2.000"),
        )

    def test_requested_quantity_must_be_positive(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_part(
                requested=D0,
            )

    def test_reserved_quantity_cannot_be_negative(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_part(
                reserved=Decimal("-1.000"),
            )

    def test_issued_quantity_cannot_be_negative(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_part(
                issued=Decimal("-1.000"),
            )

    def test_consumed_quantity_cannot_exceed_issued_quantity(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_part(
                issued=D2,
                consumed=D3,
            )

    def test_returned_quantity_cannot_exceed_issued_quantity(self):

        with self.assertRaises(
            ValidationError,
        ):

            self.create_part(
                issued=D2,
                returned=D3,
            )


class StockReceiptServiceTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_first_receipt_creates_stock_balance(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D10,
            unit_cost=Decimal("12.50"),
            performed_by=self.user,
        )

        self.assertIsInstance(
            result.balance,
            StockBalance,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            D10,
        )

        self.assertEqual(
            result.balance.reserved_quantity,
            D0,
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("12.50"),
        )

    def test_first_receipt_creates_stock_transaction(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
            reference_number=" grn-001 ",
            notes=" first receipt ",
        )

        stock_transaction = result.stock_transaction

        self.assertEqual(
            stock_transaction.transaction_type,
            StockTransactionType.RECEIPT,
        )

        self.assertEqual(
            stock_transaction.quantity,
            D5,
        )

        self.assertEqual(
            stock_transaction.unit_cost,
            Decimal("10.00"),
        )

        self.assertEqual(
            stock_transaction.balance_after,
            D5,
        )

        self.assertEqual(
            stock_transaction.reserved_balance_after,
            D0,
        )

        self.assertEqual(
            stock_transaction.reference_number,
            "GRN-001",
        )

        self.assertEqual(
            stock_transaction.notes,
            "first receipt",
        )

        self.assertEqual(
            stock_transaction.performed_by,
            self.user,
        )

    def test_receipt_uses_standard_cost_when_unit_cost_is_missing(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            self.item.standard_unit_cost,
        )

        self.assertEqual(
            result.stock_transaction.unit_cost,
            self.item.standard_unit_cost,
        )

    def test_receipt_calculates_weighted_average_cost(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D10,
            unit_cost=Decimal("20.00"),
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            D20,
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("15.00"),
        )

    def test_receipt_quantity_is_rounded_to_three_decimal_places(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity="1.2345",
            unit_cost="10.00",
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            Decimal("1.235"),
        )

    def test_receipt_cost_is_rounded_to_two_decimal_places(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            unit_cost="10.555",
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("10.56"),
        )

    def test_zero_receipt_quantity_is_rejected(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D0,
                unit_cost=Decimal("10.00"),
                performed_by=self.user,
            )

    def test_negative_receipt_quantity_is_rejected(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=Decimal("-1.000"),
                unit_cost=Decimal("10.00"),
                performed_by=self.user,
            )

    def test_invalid_receipt_quantity_is_rejected(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity="invalid",
                unit_cost=Decimal("10.00"),
                performed_by=self.user,
            )

    def test_negative_receipt_cost_is_rejected(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                unit_cost=Decimal("-10.00"),
                performed_by=self.user,
            )

    def test_unsaved_user_is_rejected(self):

        unsaved_user = get_user_model()()

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                unit_cost=Decimal("10.00"),
                performed_by=unsaved_user,
            )

    def test_missing_user_is_rejected(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                unit_cost=Decimal("10.00"),
                performed_by=None,
            )

    def test_inactive_warehouse_is_rejected(self):

        self.warehouse.is_active = False

        self.warehouse.save(
            update_fields=[
                "is_active",
            ]
        )

        with self.assertRaises(
            InactiveInventoryObjectError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                performed_by=self.user,
            )

    def test_inactive_item_is_rejected(self):

        self.item.is_active = False

        self.item.save(
            update_fields=[
                "is_active",
            ]
        )

        with self.assertRaises(
            InactiveInventoryObjectError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                performed_by=self.user,
            )

    def test_cross_project_receipt_is_rejected(self):

        with self.assertRaises(
            InventoryProjectMismatchError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.other_item,
                quantity=D1,
                performed_by=self.user,
            )

    def test_failed_receipt_does_not_create_balance_or_transaction(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D0,
                performed_by=self.user,
            )

        self.assertFalse(
            StockBalance.objects.exists(),
        )

        self.assertFalse(
            StockTransaction.objects.exists(),
        )

class ReservationServiceTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.balance = self.create_balance(
            quantity=D10,
            reserved=D0,
            cost=Decimal("10.00"),
        )

        self.part = self.create_part(
            requested=D10,
        )

    def test_reserve_stock_successfully(self):

        result = ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            D10,
        )

        self.assertEqual(
            self.balance.reserved_quantity,
            D5,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D5,
        )

        self.assertEqual(
            result.stock_transaction.transaction_type,
            StockTransactionType.RESERVATION,
        )

    def test_reservation_cannot_exceed_available_quantity(self):

        with self.assertRaises(
            InsufficientStockError,
        ):

            ReservationService.reserve_stock(
                work_order_part=self.part,
                quantity=Decimal("11.000"),
                performed_by=self.user,
            )

        self.balance.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            D10,
        )

        self.assertEqual(
            self.balance.reserved_quantity,
            D0,
        )

        self.assertFalse(
            StockTransaction.objects.exists(),
        )

    def test_multiple_reservations(self):

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D3,
            performed_by=self.user,
        )

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D2,
            performed_by=self.user,
        )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.reserved_quantity,
            D5,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D5,
        )

    def test_release_reserved_stock(self):

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        ReservationService.release_reservation(
            work_order_part=self.part,
            quantity=D2,
            performed_by=self.user,
        )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.reserved_quantity,
            D3,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D3,
        )

    def test_release_all_reserved_stock(self):

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        ReservationService.release_reservation(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.reserved_quantity,
            D0,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D0,
        )

    def test_release_more_than_reserved_quantity(self):

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D2,
            performed_by=self.user,
        )

        with self.assertRaises(
            InsufficientReservedStockError,
        ):

            ReservationService.release_reservation(
                work_order_part=self.part,
                quantity=D3,
                performed_by=self.user,
            )

    def test_release_zero_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            ReservationService.release_reservation(
                work_order_part=self.part,
                quantity=D0,
                performed_by=self.user,
            )

    def test_release_negative_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            ReservationService.release_reservation(
                work_order_part=self.part,
                quantity=Decimal("-1.000"),
                performed_by=self.user,
            )

    def test_failed_reservation_is_atomic(self):

        with self.assertRaises(
            InsufficientStockError,
        ):

            ReservationService.reserve_stock(
                work_order_part=self.part,
                quantity=Decimal("20.000"),
                performed_by=self.user,
            )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.reserved_quantity,
            D0,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D0,
        )

        self.assertEqual(
            StockTransaction.objects.count(),
            0,
        )


class StockIssueServiceTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.balance = self.create_balance(
            quantity=D10,
            reserved=D0,
            cost=Decimal("12.00"),
        )

        self.part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

    def test_issue_reserved_stock(self):

        result = StockIssueService.issue_stock(
            work_order_part=self.part,
            quantity=D3,
            performed_by=self.user,
        )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            Decimal("7.000"),
        )

        self.assertEqual(
            self.balance.reserved_quantity,
            D2,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D2,
        )

        self.assertEqual(
            self.part.issued_quantity,
            D3,
        )

        self.assertEqual(
            self.part.estimated_unit_cost,
            Decimal("12.00"),
        )

        self.assertEqual(
            result.stock_transaction.transaction_type,
            StockTransactionType.ISSUE,
        )

    def test_issue_all_reserved_stock(self):

        StockIssueService.issue_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            D5,
        )

        self.assertEqual(
            self.balance.reserved_quantity,
            D0,
        )

        self.assertEqual(
            self.part.reserved_quantity,
            D0,
        )

        self.assertEqual(
            self.part.issued_quantity,
            D5,
        )

    def test_issue_more_than_reserved_stock(self):

        with self.assertRaises(
            InsufficientReservedStockError,
        ):

            StockIssueService.issue_stock(
                work_order_part=self.part,
                quantity=D10,
                performed_by=self.user,
            )

    def test_issue_zero_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockIssueService.issue_stock(
                work_order_part=self.part,
                quantity=D0,
                performed_by=self.user,
            )

    def test_issue_negative_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockIssueService.issue_stock(
                work_order_part=self.part,
                quantity=Decimal("-1.000"),
                performed_by=self.user,
            )

    def test_issue_updates_stock_transaction(self):

        result = StockIssueService.issue_stock(
            work_order_part=self.part,
            quantity=D2,
            performed_by=self.user,
        )

        trx = result.stock_transaction

        self.assertEqual(
            trx.transaction_type,
            StockTransactionType.ISSUE,
        )

        self.assertEqual(
            trx.quantity,
            D2,
        )

        self.assertEqual(
            trx.balance_after,
            Decimal("8.000"),
        )

        self.assertEqual(
            trx.reserved_balance_after,
            Decimal("3.000"),
        )

        self.assertEqual(
            trx.performed_by,
            self.user,
        )

    def test_issue_is_atomic(self):

        with self.assertRaises(
            InsufficientReservedStockError,
        ):

            StockIssueService.issue_stock(
                work_order_part=self.part,
                quantity=Decimal("6.000"),
                performed_by=self.user,
            )

        self.balance.refresh_from_db()
        self.part.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            D10,
        )

        self.assertEqual(
            self.balance.reserved_quantity,
            D5,
        )

        self.assertEqual(
            self.part.issued_quantity,
            D0,
        )

class ConsumptionServiceTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.balance = self.create_balance(
            quantity=D10,
            reserved=D0,
            cost=Decimal("15.00"),
        )

        self.part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        StockIssueService.issue_stock(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

    def test_consume_partial_quantity(self):

        result = ConsumptionService.consume_part(
            work_order_part=self.part,
            quantity=D3,
            performed_by=self.user,
        )

        self.part.refresh_from_db()

        self.assertEqual(
            self.part.consumed_quantity,
            D3,
        )

        self.assertEqual(
            self.part.issued_quantity,
            D5,
        )

        self.assertEqual(
            self.part.issued_available_quantity,
            D2,
        )

        self.assertEqual(
            result.stock_transaction.transaction_type,
            StockTransactionType.CONSUMPTION,
        )

    def test_consume_all_issued_quantity(self):

        ConsumptionService.consume_part(
            work_order_part=self.part,
            quantity=D5,
            performed_by=self.user,
        )

        self.part.refresh_from_db()

        self.assertEqual(
            self.part.consumed_quantity,
            D5,
        )

        self.assertEqual(
            self.part.issued_available_quantity,
            D0,
        )

    def test_consume_more_than_issued_quantity(self):

        with self.assertRaises(
            WorkOrderPartError,
        ):

            ConsumptionService.consume_part(
                work_order_part=self.part,
                quantity=D6,
                performed_by=self.user,
            )

    def test_consume_zero_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            ConsumptionService.consume_part(
                work_order_part=self.part,
                quantity=D0,
                performed_by=self.user,
            )

    def test_consume_negative_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            ConsumptionService.consume_part(
                work_order_part=self.part,
                quantity=Decimal("-1.000"),
                performed_by=self.user,
            )

    def test_consumption_is_atomic(self):

        with self.assertRaises(
            WorkOrderPartError,
        ):

            ConsumptionService.consume_part(
                work_order_part=self.part,
                quantity=D20,
                performed_by=self.user,
            )

        self.part.refresh_from_db()

        self.assertEqual(
            self.part.consumed_quantity,
            D0,
        )

        self.assertEqual(
            StockTransaction.objects.filter(
                transaction_type=StockTransactionType.CONSUMPTION,
            ).count(),
            0,
        )


class TransferServiceTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.source = self.create_balance(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D10,
            cost=Decimal("25.00"),
        )

    def test_transfer_stock(self):

        TransferService.transfer_stock(
            source_warehouse=self.warehouse,
            destination_warehouse=self.destination,
            item=self.item,
            quantity=D3,
            performed_by=self.user,
        )

        self.source.refresh_from_db()

        destination = StockBalance.objects.get(
            warehouse=self.destination,
            item=self.item,
        )

        self.assertEqual(
            self.source.quantity_on_hand,
            Decimal("7.000"),
        )

        self.assertEqual(
            destination.quantity_on_hand,
            Decimal("3.000"),
        )

        self.assertEqual(
            destination.average_unit_cost,
            Decimal("25.00"),
        )

    def test_transfer_creates_two_transactions(self):

        before = StockTransaction.objects.count()

        TransferService.transfer_stock(
            source_warehouse=self.warehouse,
            destination_warehouse=self.destination,
            item=self.item,
            quantity=D2,
            performed_by=self.user,
        )

        after = StockTransaction.objects.count()

        self.assertEqual(
            after - before,
            2,
        )

    def test_transfer_to_same_warehouse_is_invalid(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            TransferService.transfer_stock(
                source_warehouse=self.warehouse,
                destination_warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                performed_by=self.user,
            )

    def test_transfer_more_than_available_quantity(self):

        with self.assertRaises(
            InsufficientStockError,
        ):

            TransferService.transfer_stock(
                source_warehouse=self.warehouse,
                destination_warehouse=self.destination,
                item=self.item,
                quantity=D20,
                performed_by=self.user,
            )

    def test_transfer_between_projects_is_invalid(self):

        with self.assertRaises(
            InventoryProjectMismatchError,
        ):

            TransferService.transfer_stock(
                source_warehouse=self.warehouse,
                destination_warehouse=self.other_warehouse,
                item=self.item,
                quantity=D1,
                performed_by=self.user,
            )

    def test_transfer_preserves_total_stock(self):

        TransferService.transfer_stock(
            source_warehouse=self.warehouse,
            destination_warehouse=self.destination,
            item=self.item,
            quantity=D4,
            performed_by=self.user,
        )

        total = sum(
            StockBalance.objects.filter(
                item=self.item,
            ).values_list(
                "quantity_on_hand",
                flat=True,
            )
        )

        self.assertEqual(
            total,
            D10,
        )


class AdjustmentServiceTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.balance = self.create_balance(
            quantity=D10,
            cost=Decimal("8.00"),
        )

    def test_positive_adjustment(self):

        AdjustmentService.adjust_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D2,
            direction="in",
            unit_cost=Decimal("8.00"),
            notes="Cycle Count",
            performed_by=self.user,
        )

        self.balance.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            D12,
        )

    def test_negative_adjustment(self):

        AdjustmentService.adjust_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D3,
            direction="out",
            notes="Damage",
            performed_by=self.user,
        )

        self.balance.refresh_from_db()

        self.assertEqual(
            self.balance.quantity_on_hand,
            Decimal("7.000"),
        )

    def test_adjustment_cannot_make_negative_stock(self):

        with self.assertRaises(
            InsufficientStockError,
        ):

            AdjustmentService.adjust_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D20,
                direction="out",
                notes="Inventory Count",
                performed_by=self.user,
            )

    def test_adjustment_in_creates_transaction(self):

        before = StockTransaction.objects.count()

        AdjustmentService.adjust_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            direction="in",
            unit_cost=Decimal("8.00"),
            notes="Correction",
            performed_by=self.user,
        )

        self.assertEqual(
            StockTransaction.objects.count(),
            before + 1,
        )

        trx = StockTransaction.objects.latest(
            "id",
        )

        self.assertEqual(
            trx.transaction_type,
            StockTransactionType.ADJUSTMENT_IN,
        )

    def test_adjustment_out_creates_transaction(self):

        AdjustmentService.adjust_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            direction="out",
            performed_by=self.user,
        )

        trx = StockTransaction.objects.latest(
            "id",
        )

        self.assertEqual(
            trx.transaction_type,
            StockTransactionType.ADJUSTMENT_OUT,
        )

    def test_adjustment_zero_quantity_is_invalid(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            AdjustmentService.adjust_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D0,
                direction="in",
                performed_by=self.user,
            )

    def test_invalid_adjustment_direction_is_rejected(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            AdjustmentService.adjust_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                direction="invalid",
                performed_by=self.user,
            )
class WarehouseSerializerTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_warehouse_serializer_output(self):

        serializer = WarehouseSerializer(
            instance=self.warehouse,
        )

        data = serializer.data

        self.assertEqual(
            data["code"],
            "WH-MAIN",
        )

        self.assertEqual(
            data["name"],
            "Main Warehouse",
        )

        self.assertTrue(
            data["is_active"],
        )

    def test_create_warehouse_serializer(self):

        serializer = WarehouseSerializer(
            data={
                "project": self.project.pk,
                "code": "WH-NEW",
                "name": "New Warehouse",
                "manager": self.user.pk,
                "is_active": True,
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_duplicate_code_validation(self):

        serializer = WarehouseSerializer(
            data={
                "project": self.project.pk,
                "code": "WH-MAIN",
                "name": "Duplicate",
                "manager": self.user.pk,
            }
        )

        self.assertFalse(
            serializer.is_valid(),
        )


class InventoryItemSerializerTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_serializer_output(self):

        serializer = InventoryItemSerializer(
            instance=self.item,
        )

        data = serializer.data

        self.assertEqual(
            data["code"],
            "ITM-100",
        )

        self.assertEqual(
            data["name"],
            "Main Bearing",
        )

    def test_create_serializer(self):

        serializer = InventoryItemSerializer(
            data={
                "project": self.project.pk,
                "code": "ITM-500",
                "name": "New Item",
                "unit_of_measure": "each",
                "standard_unit_cost": "12.50",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_invalid_cost(self):

        serializer = InventoryItemSerializer(
            data={
                "project": self.project.pk,
                "code": "ITM-600",
                "name": "Bad",
                "unit_of_measure": "each",
                "standard_unit_cost": "-1",
            }
        )

        self.assertFalse(
            serializer.is_valid(),
        )


class StockReceiptSerializerTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_valid_serializer(self):

        serializer = StockReceiptSerializer(
            data={
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity": "5",
                "unit_cost": "10.00",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_invalid_quantity(self):

        serializer = StockReceiptSerializer(
            data={
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity": "-5",
                "unit_cost": "10",
            }
        )

        self.assertFalse(
            serializer.is_valid(),
        )


class StockTransferSerializerTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_valid_transfer_serializer(self):

        serializer = StockTransferSerializer(
            data={
                "source_warehouse": self.warehouse.pk,
                "destination_warehouse": self.destination.pk,
                "item": self.item.pk,
                "quantity": "3",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_same_warehouse_validation(self):

        serializer = StockTransferSerializer(
            data={
                "source_warehouse": self.warehouse.pk,
                "destination_warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity": "2",
            }
        )

        self.assertFalse(
            serializer.is_valid(),
        )


class StockAdjustmentSerializerTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_valid_adjustment(self):

        serializer = StockAdjustmentSerializer(
            data={
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity_difference": "5",
                "reason": "Cycle Count",
            }
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_zero_adjustment(self):

        serializer = StockAdjustmentSerializer(
            data={
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity_difference": "0",
                "reason": "Nothing",
            }
        )

        self.assertFalse(
            serializer.is_valid(),
        )


class WarehouseFilterTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_filter_by_code(self):

        qs = WarehouseFilter(
            {
                "code": "MAIN",
            },
            queryset=Warehouse.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )

    def test_filter_by_active(self):

        self.destination.is_active = False
        self.destination.save()

        qs = WarehouseFilter(
            {
                "is_active": True,
            },
            queryset=Warehouse.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            2,
        )


class InventoryItemFilterTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_filter_by_name(self):

        qs = InventoryItemFilter(
            {
                "name": "Bearing",
            },
            queryset=InventoryItem.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )

    def test_filter_by_category(self):

        qs = InventoryItemFilter(
            {
                "category": "Mechanical",
            },
            queryset=InventoryItem.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )


class StockBalanceFilterTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.create_balance(
            quantity=D10,
        )

    def test_filter_by_item(self):

        qs = StockBalanceFilter(
            {
                "item": self.item.pk,
            },
            queryset=StockBalance.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )

    def test_filter_by_warehouse(self):

        qs = StockBalanceFilter(
            {
                "warehouse": self.warehouse.pk,
            },
            queryset=StockBalance.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )


class StockTransactionFilterTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("10"),
            performed_by=self.user,
        )

    def test_filter_by_transaction_type(self):

        qs = StockTransactionFilter(
            {
                "transaction_type": StockTransactionType.RECEIPT,
            },
            queryset=StockTransaction.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )

    def test_filter_by_item(self):

        qs = StockTransactionFilter(
            {
                "item": self.item.pk,
            },
            queryset=StockTransaction.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )


class WorkOrderPartFilterTests(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.create_part()

    def test_filter_by_work_order(self):

        qs = WorkOrderPartFilter(
            {
                "work_order": self.work_order.pk,
            },
            queryset=WorkOrderPart.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )

    def test_filter_by_item(self):

        qs = WorkOrderPartFilter(
            {
                "item": self.item.pk,
            },
            queryset=WorkOrderPart.objects.all(),
        ).qs

        self.assertEqual(
            qs.count(),
            1,
        )


class ViewSetTestMixin(
    InventoryFixtureMixin,
    TestCase,
):

    def setUp(self):

        self.factory = APIRequestFactory()

    def authenticate(
        self,
        request,
    ):

        force_authenticate(
            request,
            user=self.user,
        )
        return request

class WarehouseViewSetTests(
    ViewSetTestMixin,
):

    def test_list_warehouses_requires_authentication(self):

        view = WarehouseViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/warehouses/",
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_list_warehouses(self):

        view = WarehouseViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/warehouses/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_retrieve_warehouse(self):

        view = WarehouseViewSet.as_view(
            {
                "get": "retrieve",
            }
        )

        request = self.factory.get(
            f"/api/inventory/warehouses/{self.warehouse.pk}/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.warehouse.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["code"],
            "WH-MAIN",
        )

    def test_create_warehouse(self):

        view = WarehouseViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self.factory.post(
            "/api/inventory/warehouses/",
            {
                "project": self.project.pk,
                "code": "WH-API",
                "name": "API Warehouse",
                "manager": self.user.pk,
                "is_active": True,
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Warehouse.objects.filter(
                project=self.project,
                code="WH-API",
            ).exists(),
        )

    def test_update_warehouse(self):

        view = WarehouseViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )

        request = self.factory.patch(
            f"/api/inventory/warehouses/{self.warehouse.pk}/",
            {
                "name": "Updated Warehouse",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.warehouse.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.warehouse.refresh_from_db()

        self.assertEqual(
            self.warehouse.name,
            "Updated Warehouse",
        )

    def test_delete_warehouse(self):

        warehouse = Warehouse.objects.create(
            project=self.project,
            code="WH-DELETE",
            name="Delete Warehouse",
            manager=self.user,
        )

        view = WarehouseViewSet.as_view(
            {
                "delete": "destroy",
            }
        )

        request = self.factory.delete(
            f"/api/inventory/warehouses/{warehouse.pk}/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=warehouse.pk,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_204_NO_CONTENT,
                status.HTTP_200_OK,
            ),
        )


class InventoryItemViewSetTests(
    ViewSetTestMixin,
):

    def test_list_items(self):

        view = InventoryItemViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/items/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_retrieve_item(self):

        view = InventoryItemViewSet.as_view(
            {
                "get": "retrieve",
            }
        )

        request = self.factory.get(
            f"/api/inventory/items/{self.item.pk}/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.item.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["code"],
            "ITM-100",
        )

    def test_create_item(self):

        view = InventoryItemViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self.factory.post(
            "/api/inventory/items/",
            {
                "project": self.project.pk,
                "code": "ITM-API",
                "name": "API Item",
                "unit_of_measure": "each",
                "minimum_stock": "1.000",
                "maximum_stock": "50.000",
                "reorder_point": "5.000",
                "standard_unit_cost": "18.50",
                "is_active": True,
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            InventoryItem.objects.filter(
                project=self.project,
                code="ITM-API",
            ).exists(),
        )

    def test_partial_update_item(self):

        view = InventoryItemViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )

        request = self.factory.patch(
            f"/api/inventory/items/{self.item.pk}/",
            {
                "name": "Updated Bearing",
                "is_critical": False,
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.item.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.name,
            "Updated Bearing",
        )

        self.assertFalse(
            self.item.is_critical,
        )

    def test_search_items_by_code(self):

        view = InventoryItemViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/items/",
            {
                "search": "ITM-100",
            },
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


class StockBalanceViewSetTests(
    ViewSetTestMixin,
):

    def setUp(self):

        super().setUp()

        self.balance = self.create_balance(
            quantity=D10,
            reserved=D2,
            cost=Decimal("12.00"),
        )

    def test_list_stock_balances(self):

        view = StockBalanceViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/stock-balances/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_retrieve_stock_balance(self):

        view = StockBalanceViewSet.as_view(
            {
                "get": "retrieve",
            }
        )

        request = self.factory.get(
            f"/api/inventory/stock-balances/{self.balance.pk}/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.balance.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_balance_response_contains_available_quantity(self):

        view = StockBalanceViewSet.as_view(
            {
                "get": "retrieve",
            }
        )

        request = self.factory.get(
            f"/api/inventory/stock-balances/{self.balance.pk}/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.balance.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        if "available_quantity" in response.data:

            self.assertEqual(
                Decimal(
                    str(
                        response.data["available_quantity"]
                    )
                ),
                Decimal("8.000"),
            )

    def test_filter_balances_by_warehouse(self):

        view = StockBalanceViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/stock-balances/",
            {
                "warehouse": self.warehouse.pk,
            },
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


class StockTransactionViewSetTests(
    ViewSetTestMixin,
):

    def setUp(self):

        super().setUp()

        self.receipt_result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
            reference_number="GRN-API",
        )

    def test_list_stock_transactions(self):

        view = StockTransactionViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/stock-transactions/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_retrieve_stock_transaction(self):

        transaction_object = (
            self.receipt_result.stock_transaction
        )

        view = StockTransactionViewSet.as_view(
            {
                "get": "retrieve",
            }
        )

        request = self.factory.get(
            (
                "/api/inventory/stock-transactions/"
                f"{transaction_object.pk}/"
            ),
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=transaction_object.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_filter_transactions_by_type(self):

        view = StockTransactionViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/stock-transactions/",
            {
                "transaction_type":
                    StockTransactionType.RECEIPT,
            },
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )


class WorkOrderPartViewSetTests(
    ViewSetTestMixin,
):

    def setUp(self):

        super().setUp()

        self.part = self.create_part(
            requested=D10,
        )

        self.balance = self.create_balance(
            quantity=D20,
            reserved=D0,
            cost=Decimal("10.00"),
        )

    def test_list_work_order_parts(self):

        view = WorkOrderPartViewSet.as_view(
            {
                "get": "list",
            }
        )

        request = self.factory.get(
            "/api/inventory/work-order-parts/",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_retrieve_work_order_part(self):

        view = WorkOrderPartViewSet.as_view(
            {
                "get": "retrieve",
            }
        )

        request = self.factory.get(
            (
                "/api/inventory/work-order-parts/"
                f"{self.part.pk}/"
            ),
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=self.part.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_create_work_order_part(self):

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self.factory.post(
            "/api/inventory/work-order-parts/",
            {
                "work_order": self.work_order.pk,
                "warehouse": self.warehouse.pk,
                "item": self.item2.pk,
                "requested_quantity": "4.000",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


class InventoryActionViewSetTests(
    ViewSetTestMixin,
):

    def test_receipt_action(self):

        view = StockBalanceViewSet.as_view(
            {
                "post": "receive",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/receive/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity": "10.000",
                "unit_cost": "14.00",
                "reference_number": "GRN-100",
                "notes": "API receipt",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ),
        )

        balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            balance.quantity_on_hand,
            D10,
        )

    def test_transfer_action(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        view = StockBalanceViewSet.as_view(
            {
                "post": "transfer",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/transfer/",
            {
                "source_warehouse": self.warehouse.pk,
                "destination_warehouse":
                    self.destination.pk,
                "item": self.item.pk,
                "quantity": "3.000",
                "reference_number": "TRF-100",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ),
        )

        source_balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )

        destination_balance = StockBalance.objects.get(
            warehouse=self.destination,
            item=self.item,
        )

        self.assertEqual(
            source_balance.quantity_on_hand,
            Decimal("7.000"),
        )

        self.assertEqual(
            destination_balance.quantity_on_hand,
            D3,
        )

    def test_adjustment_action(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        view = StockBalanceViewSet.as_view(
            {
                "post": "adjust",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/adjust/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity_difference": "-2.000",
                "reason": "Cycle count correction",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ),
        )

        balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            balance.quantity_on_hand,
            Decimal("8.000"),
        )

    def test_reserve_action(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "reserve",
            }
        )

        request = self.factory.post(
            (
                "/api/inventory/work-order-parts/"
                f"{part.pk}/reserve/"
            ),
            {
                "quantity": "4.000",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=part.pk,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ),
        )

        part.refresh_from_db()

        self.assertEqual(
            part.reserved_quantity,
            Decimal("4.000"),
        )

    def test_issue_action(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D5,
            performed_by=self.user,
        )

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "issue",
            }
        )

        request = self.factory.post(
            (
                "/api/inventory/work-order-parts/"
                f"{part.pk}/issue/"
            ),
            {
                "quantity": "3.000",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=part.pk,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ),
        )

        part.refresh_from_db()

        self.assertEqual(
            part.issued_quantity,
            D3,
        )

    def test_consume_action(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D5,
            performed_by=self.user,
        )

        StockIssueService.issue_stock(
            work_order_part=part,
            quantity=D5,
            performed_by=self.user,
        )

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "consume",
            }
        )

        request = self.factory.post(
            (
                "/api/inventory/work-order-parts/"
                f"{part.pk}/consume/"
            ),
            {
                "quantity": "2.000",
            },
            format="json",
        )

        self.authenticate(
            request,
        )

        response = view(
            request,
            pk=part.pk,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
            ),
        )

        part.refresh_from_db()

        self.assertEqual(
            part.consumed_quantity,
            D2,
        )

class InventoryAPIValidationTests(
    ViewSetTestMixin,
):

    def test_receipt_action_rejects_zero_quantity(self):

        view = StockBalanceViewSet.as_view(
            {
                "post": "receive",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/receive/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity": "0.000",
                "unit_cost": "10.00",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            StockBalance.objects.filter(
                warehouse=self.warehouse,
                item=self.item,
            ).exists(),
        )

    def test_receipt_action_rejects_cross_project_item(self):

        view = StockBalanceViewSet.as_view(
            {
                "post": "receive",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/receive/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.other_item.pk,
                "quantity": "5.000",
                "unit_cost": "10.00",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_transfer_action_rejects_insufficient_stock(self):

        self.create_balance(
            quantity=D2,
            cost=Decimal("10.00"),
        )

        view = StockBalanceViewSet.as_view(
            {
                "post": "transfer",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/transfer/",
            {
                "source_warehouse": self.warehouse.pk,
                "destination_warehouse": self.destination.pk,
                "item": self.item.pk,
                "quantity": "5.000",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        source_balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            source_balance.quantity_on_hand,
            D2,
        )

        self.assertFalse(
            StockBalance.objects.filter(
                warehouse=self.destination,
                item=self.item,
            ).exists(),
        )

    def test_adjustment_action_rejects_negative_final_balance(self):

        self.create_balance(
            quantity=D3,
            cost=Decimal("10.00"),
        )

        view = StockBalanceViewSet.as_view(
            {
                "post": "adjust",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-balances/adjust/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity_difference": "-5.000",
                "reason": "Invalid correction",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            balance.quantity_on_hand,
            D3,
        )

    def test_reserve_action_rejects_quantity_above_available_stock(self):

        self.create_balance(
            quantity=D3,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "reserve",
            }
        )

        request = self.factory.post(
            (
                "/api/inventory/work-order-parts/"
                f"{part.pk}/reserve/"
            ),
            {
                "quantity": "5.000",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(
            request,
            pk=part.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        part.refresh_from_db()

        self.assertEqual(
            part.reserved_quantity,
            D0,
        )

    def test_issue_action_rejects_quantity_above_reservation(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D2,
            performed_by=self.user,
        )

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "issue",
            }
        )

        request = self.factory.post(
            (
                "/api/inventory/work-order-parts/"
                f"{part.pk}/issue/"
            ),
            {
                "quantity": "3.000",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(
            request,
            pk=part.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        part.refresh_from_db()

        self.assertEqual(
            part.issued_quantity,
            D0,
        )

        self.assertEqual(
            part.reserved_quantity,
            D2,
        )

    def test_consume_action_rejects_quantity_above_issued_available(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D2,
            performed_by=self.user,
        )

        StockIssueService.issue_stock(
            work_order_part=part,
            quantity=D2,
            performed_by=self.user,
        )

        view = WorkOrderPartViewSet.as_view(
            {
                "post": "consume",
            }
        )

        request = self.factory.post(
            (
                "/api/inventory/work-order-parts/"
                f"{part.pk}/consume/"
            ),
            {
                "quantity": "3.000",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(
            request,
            pk=part.pk,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        part.refresh_from_db()

        self.assertEqual(
            part.consumed_quantity,
            D0,
        )


class InventoryTransactionAtomicityTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_failed_transfer_rolls_back_all_changes(self):

        source_balance = self.create_balance(
            quantity=D5,
            reserved=D3,
            cost=Decimal("18.00"),
        )

        transaction_count = StockTransaction.objects.count()

        with self.assertRaises(
            InsufficientStockError,
        ):

            TransferService.transfer_stock(
                source_warehouse=self.warehouse,
                destination_warehouse=self.destination,
                item=self.item,
                quantity=D3,
                performed_by=self.user,
            )

        source_balance.refresh_from_db()

        self.assertEqual(
            source_balance.quantity_on_hand,
            D5,
        )

        self.assertEqual(
            source_balance.reserved_quantity,
            D3,
        )

        self.assertFalse(
            StockBalance.objects.filter(
                warehouse=self.destination,
                item=self.item,
            ).exists(),
        )

        self.assertEqual(
            StockTransaction.objects.count(),
            transaction_count,
        )

    def test_failed_adjustment_rolls_back_balance(self):

        balance = self.create_balance(
            quantity=D5,
            reserved=D3,
            cost=Decimal("10.00"),
        )

        transaction_count = StockTransaction.objects.count()

        with self.assertRaises(
            InsufficientStockError,
        ):

            AdjustmentService.adjust_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity_difference=Decimal("-4.000"),
                reason="Invalid adjustment",
                performed_by=self.user,
            )

        balance.refresh_from_db()

        self.assertEqual(
            balance.quantity_on_hand,
            D5,
        )

        self.assertEqual(
            balance.reserved_quantity,
            D3,
        )

        self.assertEqual(
            StockTransaction.objects.count(),
            transaction_count,
        )

    def test_failed_issue_keeps_reservation_unchanged(self):

        balance = self.create_balance(
            quantity=D10,
            reserved=D0,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D3,
            performed_by=self.user,
        )

        transaction_count = StockTransaction.objects.count()

        with self.assertRaises(
            InsufficientReservedStockError,
        ):

            StockIssueService.issue_stock(
                work_order_part=part,
                quantity=D5,
                performed_by=self.user,
            )

        balance.refresh_from_db()
        part.refresh_from_db()

        self.assertEqual(
            balance.quantity_on_hand,
            D10,
        )

        self.assertEqual(
            balance.reserved_quantity,
            D3,
        )

        self.assertEqual(
            part.reserved_quantity,
            D3,
        )

        self.assertEqual(
            part.issued_quantity,
            D0,
        )

        self.assertEqual(
            StockTransaction.objects.count(),
            transaction_count,
        )

    def test_failed_consumption_keeps_part_quantities_unchanged(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D3,
            performed_by=self.user,
        )

        StockIssueService.issue_stock(
            work_order_part=part,
            quantity=D3,
            performed_by=self.user,
        )

        transaction_count = StockTransaction.objects.count()

        with self.assertRaises(
            WorkOrderPartError,
        ):

            ConsumptionService.consume_part(
                work_order_part=part,
                quantity=D5,
                performed_by=self.user,
            )

        part.refresh_from_db()

        self.assertEqual(
            part.issued_quantity,
            D3,
        )

        self.assertEqual(
            part.consumed_quantity,
            D0,
        )

        self.assertEqual(
            part.returned_quantity,
            D0,
        )

        self.assertEqual(
            StockTransaction.objects.count(),
            transaction_count,
        )


class StockTransactionLedgerTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_receipt_ledger_matches_balance(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D10,
            unit_cost=Decimal("11.00"),
            performed_by=self.user,
        )

        result.balance.refresh_from_db()
        result.stock_transaction.refresh_from_db()

        self.assertEqual(
            result.stock_transaction.balance_after,
            result.balance.quantity_on_hand,
        )

        self.assertEqual(
            result.stock_transaction.reserved_balance_after,
            result.balance.reserved_quantity,
        )

    def test_reservation_ledger_matches_balance(self):

        balance = self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        result = ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D3,
            performed_by=self.user,
        )

        balance.refresh_from_db()
        result.stock_transaction.refresh_from_db()

        self.assertEqual(
            result.stock_transaction.balance_after,
            D10,
        )

        self.assertEqual(
            result.stock_transaction.reserved_balance_after,
            D3,
        )

    def test_issue_ledger_matches_balance(self):

        balance = self.create_balance(
            quantity=D10,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D5,
            performed_by=self.user,
        )

        result = StockIssueService.issue_stock(
            work_order_part=part,
            quantity=D2,
            performed_by=self.user,
        )

        balance.refresh_from_db()
        result.stock_transaction.refresh_from_db()

        self.assertEqual(
            result.stock_transaction.balance_after,
            Decimal("8.000"),
        )

        self.assertEqual(
            result.stock_transaction.reserved_balance_after,
            D3,
        )

        self.assertEqual(
            result.stock_transaction.balance_after,
            balance.quantity_on_hand,
        )

        self.assertEqual(
            result.stock_transaction.reserved_balance_after,
            balance.reserved_quantity,
        )

    def test_transfer_ledger_contains_source_and_destination_entries(self):

        self.create_balance(
            quantity=D10,
            cost=Decimal("20.00"),
        )

        TransferService.transfer_stock(
            source_warehouse=self.warehouse,
            destination_warehouse=self.destination,
            item=self.item,
            quantity=D3,
            performed_by=self.user,
            reference_number="TRF-LEDGER",
        )

        transactions = StockTransaction.objects.filter(
            reference_number="TRF-LEDGER",
        )

        self.assertEqual(
            transactions.count(),
            2,
        )

        warehouse_ids = set(
            transactions.values_list(
                "warehouse_id",
                flat=True,
            )
        )

        self.assertEqual(
            warehouse_ids,
            {
                self.warehouse.pk,
                self.destination.pk,
            },
        )

    def test_transactions_are_linked_to_correct_item(self):

        StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            performed_by=self.user,
        )

        transaction_object = StockTransaction.objects.get()

        self.assertEqual(
            transaction_object.item,
            self.item,
        )

        self.assertEqual(
            transaction_object.warehouse,
            self.warehouse,
        )


class InventoryEndToEndWorkflowTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_complete_receipt_reserve_issue_consume_workflow(self):

        receipt_result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D20,
            unit_cost=Decimal("15.00"),
            performed_by=self.user,
            reference_number="GRN-E2E",
        )

        part = self.create_part(
            requested=D10,
        )

        ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D10,
            performed_by=self.user,
            reference_number="RES-E2E",
        )

        StockIssueService.issue_stock(
            work_order_part=part,
            quantity=D5,
            performed_by=self.user,
            reference_number="ISS-E2E",
        )

        ConsumptionService.consume_part(
            work_order_part=part,
            quantity=D3,
            performed_by=self.user,
            reference_number="CON-E2E",
        )

        receipt_result.balance.refresh_from_db()
        part.refresh_from_db()

        self.assertEqual(
            receipt_result.balance.quantity_on_hand,
            Decimal("15.000"),
        )

        self.assertEqual(
            receipt_result.balance.reserved_quantity,
            D5,
        )

        self.assertEqual(
            receipt_result.balance.available_quantity,
            D10,
        )

        self.assertEqual(
            part.requested_quantity,
            D10,
        )

        self.assertEqual(
            part.reserved_quantity,
            D5,
        )

        self.assertEqual(
            part.issued_quantity,
            D5,
        )

        self.assertEqual(
            part.consumed_quantity,
            D3,
        )

        self.assertEqual(
            part.issued_available_quantity,
            D2,
        )

        transaction_types = list(
            StockTransaction.objects.order_by(
                "pk",
            ).values_list(
                "transaction_type",
                flat=True,
            )
        )

        self.assertEqual(
            transaction_types,
            [
                StockTransactionType.RECEIPT,
                StockTransactionType.RESERVATION,
                StockTransactionType.ISSUE,
                StockTransactionType.CONSUMPTION,
            ],
        )

    def test_receipt_transfer_and_adjustment_workflow(self):

        StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D20,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
        )

        TransferService.transfer_stock(
            source_warehouse=self.warehouse,
            destination_warehouse=self.destination,
            item=self.item,
            quantity=D5,
            performed_by=self.user,
        )

        AdjustmentService.adjust_stock(
            warehouse=self.destination,
            item=self.item,
            quantity_difference=Decimal("-2.000"),
            reason="Damaged during inspection",
            performed_by=self.user,
        )

        source_balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )

        destination_balance = StockBalance.objects.get(
            warehouse=self.destination,
            item=self.item,
        )

        self.assertEqual(
            source_balance.quantity_on_hand,
            Decimal("15.000"),
        )

        self.assertEqual(
            destination_balance.quantity_on_hand,
            D3,
        )

        total_quantity = (
            source_balance.quantity_on_hand
            + destination_balance.quantity_on_hand
        )

        self.assertEqual(
            total_quantity,
            Decimal("18.000"),
        )


class InventoryReadOnlyLedgerTests(
    ViewSetTestMixin,
):

    def setUp(self):

        super().setUp()

        self.result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
        )

    def test_stock_transaction_create_is_not_allowed(self):

        view = StockTransactionViewSet.as_view(
            {
                "post": "create",
            }
        )

        request = self.factory.post(
            "/api/inventory/stock-transactions/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "transaction_type": StockTransactionType.RECEIPT,
                "quantity": "100.000",
                "unit_cost": "1.00",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(request)

        self.assertIn(
            response.status_code,
            (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

    def test_stock_transaction_update_is_not_allowed(self):

        transaction_object = self.result.stock_transaction

        view = StockTransactionViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )

        request = self.factory.patch(
            (
                "/api/inventory/stock-transactions/"
                f"{transaction_object.pk}/"
            ),
            {
                "quantity": "100.000",
            },
            format="json",
        )

        self.authenticate(request)

        response = view(
            request,
            pk=transaction_object.pk,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

        transaction_object.refresh_from_db()

        self.assertEqual(
            transaction_object.quantity,
            D5,
        )

    def test_stock_transaction_delete_is_not_allowed(self):

        transaction_object = self.result.stock_transaction

        view = StockTransactionViewSet.as_view(
            {
                "delete": "destroy",
            }
        )

        request = self.factory.delete(
            (
                "/api/inventory/stock-transactions/"
                f"{transaction_object.pk}/"
            ),
        )

        self.authenticate(request)

        response = view(
            request,
            pk=transaction_object.pk,
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

        self.assertTrue(
            StockTransaction.objects.filter(
                pk=transaction_object.pk,
            ).exists(),
        )
class InventoryPermissionTests(TestCase):
    """
    دسترسی کاربران مختلف
    - Anonymous
    - Authenticated
    - ReadOnly
    - Manager
    """

class InventorySearchOrderingTests(TestCase):
    """
    search
    ordering
    pagination
    """

class InventoryConcurrencyTests(TransactionTestCase):
    """
    select_for_update
    race condition
    concurrent reservation
    concurrent receipt
    """

class StockBalancePropertyTests(TestCase):
    """
    available_quantity
    stock_value
    reorder
    """

class StockTransactionAuditTests(TestCase):
    """
    immutable ledger
    chronological ordering
    reference_number uniqueness
    """

class LargeVolumeTests(TestCase):
    """
    1000 receipts
    1000 transfers
    performance
    """

class RegressionTests(TestCase):
    """
    تست باگ‌هایی که قبلاً پیدا شده‌اند
    """
class InventoryServiceHelperTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_get_stock_balance_returns_existing_balance(self):

        balance = self.create_balance(
            quantity=D10,
            reserved=D2,
            cost=Decimal("10.00"),
        )

        result = InventoryService.get_stock_balance(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            result,
            balance,
        )

    def test_get_stock_balance_returns_none_when_balance_does_not_exist(self):

        result = InventoryService.get_stock_balance(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertIsNone(
            result,
        )

    def test_get_available_quantity_returns_available_stock(self):

        self.create_balance(
            quantity=D10,
            reserved=D3,
            cost=Decimal("10.00"),
        )

        result = InventoryService.get_available_quantity(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            result,
            Decimal("7.000"),
        )

    def test_get_available_quantity_returns_zero_without_balance(self):

        result = InventoryService.get_available_quantity(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            result,
            D0,
        )

    def test_get_or_create_balance_creates_empty_balance(self):

        balance = InventoryService.get_or_create_balance(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertIsNotNone(
            balance.pk,
        )

        self.assertEqual(
            balance.warehouse,
            self.warehouse,
        )

        self.assertEqual(
            balance.item,
            self.item,
        )

        self.assertEqual(
            balance.quantity_on_hand,
            D0,
        )

        self.assertEqual(
            balance.reserved_quantity,
            D0,
        )

        self.assertEqual(
            balance.average_unit_cost,
            Decimal("0.00"),
        )

    def test_get_or_create_balance_returns_existing_balance(self):

        existing_balance = self.create_balance(
            quantity=D5,
            reserved=D1,
            cost=Decimal("14.00"),
        )

        returned_balance = InventoryService.get_or_create_balance(
            warehouse=self.warehouse,
            item=self.item,
        )

        self.assertEqual(
            returned_balance.pk,
            existing_balance.pk,
        )

        self.assertEqual(
            StockBalance.objects.filter(
                warehouse=self.warehouse,
                item=self.item,
            ).count(),
            1,
        )

    def test_get_stock_balance_rejects_inactive_warehouse(self):

        self.warehouse.is_active = False

        self.warehouse.save(
            update_fields=[
                "is_active",
            ]
        )

        with self.assertRaises(
            InactiveInventoryObjectError,
        ):

            InventoryService.get_stock_balance(
                warehouse=self.warehouse,
                item=self.item,
            )

    def test_get_stock_balance_rejects_inactive_item(self):

        self.item.is_active = False

        self.item.save(
            update_fields=[
                "is_active",
            ]
        )

        with self.assertRaises(
            InactiveInventoryObjectError,
        ):

            InventoryService.get_stock_balance(
                warehouse=self.warehouse,
                item=self.item,
            )

    def test_get_stock_balance_rejects_project_mismatch(self):

        with self.assertRaises(
            InventoryProjectMismatchError,
        ):

            InventoryService.get_stock_balance(
                warehouse=self.warehouse,
                item=self.other_item,
            )

    def test_get_or_create_balance_rejects_project_mismatch(self):

        with self.assertRaises(
            InventoryProjectMismatchError,
        ):

            InventoryService.get_or_create_balance(
                warehouse=self.warehouse,
                item=self.other_item,
            )

        self.assertFalse(
            StockBalance.objects.filter(
                warehouse=self.warehouse,
                item=self.other_item,
            ).exists(),
        )


class InventoryDecimalNormalizationTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_receipt_quantity_rounds_half_up(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity="1.2345",
            unit_cost="10.00",
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            Decimal("1.235"),
        )

        self.assertEqual(
            result.stock_transaction.quantity,
            Decimal("1.235"),
        )

    def test_receipt_quantity_rounds_down_when_fourth_decimal_is_below_five(
        self,
    ):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity="1.2344",
            unit_cost="10.00",
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            Decimal("1.234"),
        )

    def test_receipt_cost_rounds_half_up(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            unit_cost="10.555",
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("10.56"),
        )

        self.assertEqual(
            result.stock_transaction.unit_cost,
            Decimal("10.56"),
        )

    def test_receipt_accepts_integer_quantity(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=5,
            unit_cost=10,
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            D5,
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("10.00"),
        )

    def test_receipt_accepts_decimal_quantity(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=Decimal("2.500"),
            unit_cost=Decimal("8.25"),
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            Decimal("2.500"),
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("8.25"),
        )

    def test_receipt_rejects_none_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=None,
                unit_cost=Decimal("10.00"),
                performed_by=self.user,
            )

    def test_receipt_rejects_empty_quantity(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity="",
                unit_cost=Decimal("10.00"),
                performed_by=self.user,
            )

    def test_receipt_rejects_none_cost(self):

        self.item.standard_unit_cost = None

        with self.assertRaises(
            (
                InvalidInventoryOperationError,
                TypeError,
                ValidationError,
            )
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                unit_cost=None,
                performed_by=self.user,
            )

    def test_receipt_rejects_invalid_cost_text(self):

        with self.assertRaises(
            InvalidInventoryOperationError,
        ):

            StockReceiptService.receive_stock(
                warehouse=self.warehouse,
                item=self.item,
                quantity=D1,
                unit_cost="invalid-cost",
                performed_by=self.user,
            )


class InventoryTextNormalizationTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_receipt_normalizes_reference_number(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
            reference_number="  grn-test-001  ",
        )

        self.assertEqual(
            result.stock_transaction.reference_number,
            "GRN-TEST-001",
        )

    def test_receipt_trims_notes(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
            notes="  Received after inspection.  ",
        )

        self.assertEqual(
            result.stock_transaction.notes,
            "Received after inspection.",
        )

    def test_none_reference_number_becomes_empty_string(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
            reference_number=None,
        )

        self.assertEqual(
            result.stock_transaction.reference_number,
            "",
        )

    def test_none_notes_becomes_empty_string(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D1,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
            notes=None,
        )

        self.assertEqual(
            result.stock_transaction.notes,
            "",
        )


class StockReceiptWeightedAverageTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_weighted_average_with_different_quantities(self):

        self.create_balance(
            quantity=Decimal("10.000"),
            reserved=D0,
            cost=Decimal("10.00"),
        )

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=Decimal("5.000"),
            unit_cost=Decimal("20.00"),
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            Decimal("15.000"),
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("13.33"),
        )

    def test_weighted_average_with_fractional_quantities(self):

        self.create_balance(
            quantity=Decimal("2.500"),
            reserved=D0,
            cost=Decimal("10.00"),
        )

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=Decimal("1.500"),
            unit_cost=Decimal("14.00"),
            performed_by=self.user,
        )

        self.assertEqual(
            result.balance.quantity_on_hand,
            Decimal("4.000"),
        )

        self.assertEqual(
            result.balance.average_unit_cost,
            Decimal("11.50"),
        )

    def test_receipt_does_not_change_reserved_quantity(self):

        balance = self.create_balance(
            quantity=D10,
            reserved=D3,
            cost=Decimal("10.00"),
        )

        StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("12.00"),
            performed_by=self.user,
        )

        balance.refresh_from_db()

        self.assertEqual(
            balance.quantity_on_hand,
            Decimal("15.000"),
        )

        self.assertEqual(
            balance.reserved_quantity,
            D3,
        )

    def test_receipt_transaction_records_final_reserved_balance(self):

        self.create_balance(
            quantity=D10,
            reserved=D3,
            cost=Decimal("10.00"),
        )

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("12.00"),
            performed_by=self.user,
        )

        self.assertEqual(
            result.stock_transaction.balance_after,
            Decimal("15.000"),
        )

        self.assertEqual(
            result.stock_transaction.reserved_balance_after,
            D3,
        )


class StockOperationResultTests(
    InventoryFixtureMixin,
    TestCase,
):

    def test_receipt_result_contains_balance_and_transaction(self):

        result = StockReceiptService.receive_stock(
            warehouse=self.warehouse,
            item=self.item,
            quantity=D5,
            unit_cost=Decimal("10.00"),
            performed_by=self.user,
        )

        self.assertIsInstance(
            result.balance,
            StockBalance,
        )

        self.assertIsInstance(
            result.stock_transaction,
            StockTransaction,
        )

        self.assertIsNone(
            result.work_order_part,
        )

    def test_reservation_result_contains_work_order_part(self):

        self.create_balance(
            quantity=D10,
            reserved=D0,
            cost=Decimal("10.00"),
        )

        part = self.create_part(
            requested=D10,
        )

        result = ReservationService.reserve_stock(
            work_order_part=part,
            quantity=D3,
            performed_by=self.user,
        )

        self.assertEqual(
            result.work_order_part.pk,
            part.pk,
        )

        self.assertEqual(
            result.balance.warehouse,
            self.warehouse,
        )

        self.assertEqual(
            result.balance.item,
            self.item,
        )

        self.assertEqual(
            result.stock_transaction.work_order_part_id,
            part.pk,
        )

        self.assertEqual(
            result.stock_transaction.work_order_id,
            self.work_order.pk,
        )
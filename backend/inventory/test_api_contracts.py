"""Route-level regression tests for the public inventory API contract."""

from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from organizations.models import Organization
from projects.models import Project
from work_orders.models import WorkOrder

from inventory.models import (
    InventoryItem,
    StockBalance,
    StockTransaction,
    UnitOfMeasure,
    Warehouse,
    WorkOrderPart,
)
from inventory.services import ReservationService, StockIssueService


class InventoryAPIContractTests(TestCase):
    """Exercise the router, authentication boundary, and action contracts."""

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="inventory-api-user",
            email="inventory-api-user@example.com",
            password="Password123!",
        )
        self.organization = Organization.objects.create(
            code="API-ORG",
            name="Inventory API Organization",
        )
        self.project = Project.objects.create(
            organization=self.organization,
            code="API-PROJECT",
            name="Inventory API Project",
            is_active=True,
        )
        self.warehouse = Warehouse.objects.create(
            project=self.project,
            code="API-WH",
            name="API Warehouse",
            manager=self.user,
            is_active=True,
        )
        self.destination = Warehouse.objects.create(
            project=self.project,
            code="API-WH-2",
            name="API Destination",
            manager=self.user,
            is_active=True,
        )
        self.item = InventoryItem.objects.create(
            project=self.project,
            code="API-ITEM",
            name="API Item",
            unit_of_measure=UnitOfMeasure.EACH,
            standard_unit_cost=Decimal("10.00"),
            is_active=True,
        )
        self.work_order = WorkOrder.objects.create(
            project=self.project,
            work_order_number="API-WO-1",
            title="Inventory API work order",
            description="Route contract regression fixture",
            created_by=self.user,
        )
        self.part = WorkOrderPart.objects.create(
            work_order=self.work_order,
            warehouse=self.warehouse,
            item=self.item,
            requested_quantity=Decimal("10.000"),
        )
        self.client.force_authenticate(user=self.user)

    def balance(self, quantity="10.000"):
        return StockBalance.objects.create(
            warehouse=self.warehouse,
            item=self.item,
            quantity_on_hand=Decimal(quantity),
            average_unit_cost=Decimal("10.00"),
        )

    def action_url(self, action):
        return (
            "/api/inventory/work-order-parts/"
            f"{self.part.pk}/{action}/"
        )

    def test_release_reservation_route_releases_reserved_quantity(self):
        self.balance()
        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=Decimal("4.000"),
            performed_by=self.user,
            reference_number="RES-API",
        )

        response = self.client.post(
            self.action_url("release-reservation"),
            {
                "quantity": "1.000",
                "reference_number": "REL-API",
                "notes": "release one",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.part.refresh_from_db()
        self.assertEqual(self.part.reserved_quantity, Decimal("3.000"))
        self.assertEqual(response.data["work_order_part"]["id"], self.part.pk)
        self.assertEqual(
            response.data["stock_transaction"]["reference_number"],
            "REL-API",
        )

    def test_return_route_returns_unused_issued_quantity(self):
        self.balance()
        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=Decimal("4.000"),
            performed_by=self.user,
        )
        StockIssueService.issue_stock(
            work_order_part=self.part,
            quantity=Decimal("3.000"),
            performed_by=self.user,
        )

        response = self.client.post(
            self.action_url("return"),
            {
                "quantity": "1.000",
                "reference_number": "RET-API",
                "notes": "unused part",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.part.refresh_from_db()
        balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )
        self.assertEqual(self.part.returned_quantity, Decimal("1.000"))
        self.assertEqual(self.part.issued_available_quantity, Decimal("2.000"))
        self.assertEqual(balance.quantity_on_hand, Decimal("8.000"))
        self.assertEqual(
            response.data["stock_transaction"]["transaction_type"],
            "return",
        )

    def test_action_audit_fields_are_normalized_and_returned(self):
        occurred_at = datetime(2025, 1, 15, 10, 30, 0)
        response = self.client.post(
            "/api/inventory/stock-balances/receive/",
            {
                "warehouse": self.warehouse.pk,
                "item": self.item.pk,
                "quantity": "2.000",
                "unit_cost": "12.50",
                "reference_number": "  grn-api-1  ",
                "notes": "  received at dock  ",
                "occurred_at": occurred_at.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transaction = StockTransaction.objects.get()
        expected_time = timezone.make_aware(
            occurred_at,
            timezone.get_current_timezone(),
        )
        self.assertEqual(transaction.reference_number, "GRN-API-1")
        self.assertEqual(transaction.notes, "received at dock")
        self.assertEqual(transaction.performed_by_id, self.user.pk)
        self.assertEqual(transaction.occurred_at, expected_time)
        response_time = datetime.fromisoformat(
            response.data["stock_transaction"]["occurred_at"].replace(
                "Z",
                "+00:00",
            )
        )
        self.assertEqual(response_time, transaction.occurred_at)
        balance = StockBalance.objects.get(
            warehouse=self.warehouse,
            item=self.item,
        )
        self.assertEqual(balance.last_transaction_at, expected_time)

    def test_anonymous_inventory_route_returns_bearer_401(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/inventory/stock-transactions/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(
            response.headers.get("WWW-Authenticate", "").startswith(
                "Bearer"
            )
        )

    def test_release_without_reservation_returns_structured_400(self):
        self.balance()

        response = self.client.post(
            self.action_url("release-reservation"),
            {"quantity": "1.000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.part.refresh_from_db()
        self.assertEqual(self.part.reserved_quantity, Decimal("0.000"))
        self.assertEqual(StockTransaction.objects.count(), 0)

    def test_return_above_issued_available_returns_structured_400(self):
        self.balance()
        ReservationService.reserve_stock(
            work_order_part=self.part,
            quantity=Decimal("2.000"),
            performed_by=self.user,
        )
        StockIssueService.issue_stock(
            work_order_part=self.part,
            quantity=Decimal("2.000"),
            performed_by=self.user,
        )

        response = self.client.post(
            self.action_url("return"),
            {"quantity": "3.000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.part.refresh_from_db()
        self.assertEqual(self.part.returned_quantity, Decimal("0.000"))
        self.assertEqual(StockTransaction.objects.count(), 2)

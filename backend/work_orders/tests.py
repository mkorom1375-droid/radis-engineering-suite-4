from django.test import SimpleTestCase
from django.urls import resolve, reverse
from rest_framework.routers import DefaultRouter

from .models import (
    AssignmentRole,
    FailureType,
    MaintenanceType,
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderDowntime,
    WorkOrderFailure,
    WorkOrderLabor,
    WorkOrderSource,
    WorkOrderStatus,
    WorkOrderStatusHistory,
    WorkPriority,
    WorkRequest,
    WorkRequestStatus,
)
from .urls import router
from .views import (
    WorkOrderAssignmentViewSet,
    WorkOrderDowntimeViewSet,
    WorkOrderFailureViewSet,
    WorkOrderLaborViewSet,
    WorkOrderViewSet,
    WorkRequestViewSet,
)


class WorkOrderChoiceTests(SimpleTestCase):
    def test_work_priority_values(self):
        self.assertEqual(WorkPriority.LOW, "low")
        self.assertEqual(WorkPriority.NORMAL, "normal")
        self.assertEqual(WorkPriority.HIGH, "high")
        self.assertEqual(WorkPriority.URGENT, "urgent")
        self.assertEqual(WorkPriority.EMERGENCY, "emergency")

    def test_maintenance_type_values(self):
        expected_values = {
            "corrective",
            "preventive",
            "predictive",
            "inspection",
            "lubrication",
            "calibration",
            "installation",
            "modification",
            "safety",
            "general",
        }

        actual_values = {
            choice.value
            for choice in MaintenanceType
        }

        self.assertEqual(actual_values, expected_values)

    def test_work_request_status_values(self):
        expected_values = {
            "draft",
            "submitted",
            "under_review",
            "approved",
            "rejected",
            "converted",
            "cancelled",
        }

        actual_values = {
            choice.value
            for choice in WorkRequestStatus
        }

        self.assertEqual(actual_values, expected_values)

    def test_work_order_status_values(self):
        expected_values = {
            "draft",
            "open",
            "assigned",
            "in_progress",
            "on_hold",
            "completed",
            "closed",
            "cancelled",
        }

        actual_values = {
            choice.value
            for choice in WorkOrderStatus
        }

        self.assertEqual(actual_values, expected_values)

    def test_work_order_source_values(self):
        expected_values = {
            "manual",
            "work_request",
            "preventive_maintenance",
            "inspection",
            "condition_monitoring",
            "breakdown",
            "other",
        }

        actual_values = {
            choice.value
            for choice in WorkOrderSource
        }

        self.assertEqual(actual_values, expected_values)

    def test_failure_type_values(self):
        expected_values = {
            "mechanical",
            "electrical",
            "instrumentation",
            "hydraulic",
            "pneumatic",
            "process",
            "structural",
            "software",
            "operational",
            "unknown",
            "other",
        }

        actual_values = {
            choice.value
            for choice in FailureType
        }

        self.assertEqual(actual_values, expected_values)

    def test_assignment_role_values(self):
        expected_values = {
            "supervisor",
            "technician",
            "engineer",
            "inspector",
            "contractor",
            "helper",
            "other",
        }

        actual_values = {
            choice.value
            for choice in AssignmentRole
        }

        self.assertEqual(actual_values, expected_values)


class WorkOrderModelMetadataTests(SimpleTestCase):
    def test_work_request_verbose_names(self):
        self.assertEqual(
            str(WorkRequest._meta.verbose_name),
            "درخواست تعمیرات",
        )

        self.assertEqual(
            str(WorkRequest._meta.verbose_name_plural),
            "درخواست‌های تعمیرات",
        )

    def test_work_order_verbose_names(self):
        self.assertEqual(
            str(WorkOrder._meta.verbose_name),
            "دستورکار",
        )

        self.assertEqual(
            str(WorkOrder._meta.verbose_name_plural),
            "دستورکارها",
        )

    def test_assignment_verbose_names(self):
        self.assertEqual(
            str(WorkOrderAssignment._meta.verbose_name),
            "تخصیص دستورکار",
        )

        self.assertEqual(
            str(WorkOrderAssignment._meta.verbose_name_plural),
            "تخصیص‌های دستورکار",
        )

    def test_labor_verbose_names(self):
        self.assertEqual(
            str(WorkOrderLabor._meta.verbose_name),
            "کارکرد نیروی انسانی",
        )

        self.assertEqual(
            str(WorkOrderLabor._meta.verbose_name_plural),
            "کارکردهای نیروی انسانی",
        )

    def test_downtime_verbose_names(self):
        self.assertEqual(
            str(WorkOrderDowntime._meta.verbose_name),
            "توقف تجهیز",
        )

        self.assertEqual(
            str(WorkOrderDowntime._meta.verbose_name_plural),
            "توقف‌های تجهیز",
        )

    def test_failure_verbose_names(self):
        self.assertEqual(
            str(WorkOrderFailure._meta.verbose_name),
            "تحلیل خرابی",
        )

        self.assertEqual(
            str(WorkOrderFailure._meta.verbose_name_plural),
            "تحلیل‌های خرابی",
        )

    def test_status_history_verbose_names(self):
        self.assertEqual(
            str(WorkOrderStatusHistory._meta.verbose_name),
            "تاریخچه وضعیت دستورکار",
        )

        self.assertEqual(
            str(WorkOrderStatusHistory._meta.verbose_name_plural),
            "تاریخچه وضعیت دستورکارها",
        )

    def test_work_request_ordering(self):
        self.assertEqual(
            WorkRequest._meta.ordering,
            ["-requested_at", "-id"],
        )

    def test_work_order_ordering(self):
        self.assertEqual(
            WorkOrder._meta.ordering,
            ["-created_at", "-id"],
        )

    def test_assignment_ordering(self):
        self.assertEqual(
            WorkOrderAssignment._meta.ordering,
            ["-assigned_at", "-id"],
        )

    def test_labor_ordering(self):
        self.assertEqual(
            WorkOrderLabor._meta.ordering,
            ["-work_date", "-id"],
        )

    def test_downtime_ordering(self):
        self.assertEqual(
            WorkOrderDowntime._meta.ordering,
            ["-started_at", "-id"],
        )

    def test_status_history_ordering(self):
        self.assertEqual(
            WorkOrderStatusHistory._meta.ordering,
            ["-changed_at", "-id"],
        )


class WorkOrderModelDefaultTests(SimpleTestCase):
    def test_work_request_defaults(self):
        work_request = WorkRequest(
            request_number="WR-001",
            title="Test request",
            description="Test description",
        )

        self.assertEqual(
            work_request.maintenance_type,
            MaintenanceType.CORRECTIVE,
        )

        self.assertEqual(
            work_request.priority,
            WorkPriority.NORMAL,
        )

        self.assertEqual(
            work_request.status,
            WorkRequestStatus.DRAFT,
        )

        self.assertFalse(work_request.production_stopped)
        self.assertFalse(work_request.safety_risk)
        self.assertFalse(work_request.environmental_risk)
        self.assertTrue(work_request.is_active)

    def test_work_order_defaults(self):
        work_order = WorkOrder(
            work_order_number="WO-001",
            title="Test order",
            description="Test description",
        )

        self.assertEqual(
            work_order.maintenance_type,
            MaintenanceType.CORRECTIVE,
        )

        self.assertEqual(
            work_order.priority,
            WorkPriority.NORMAL,
        )

        self.assertEqual(
            work_order.status,
            WorkOrderStatus.DRAFT,
        )

        self.assertEqual(
            work_order.source,
            WorkOrderSource.MANUAL,
        )

        self.assertFalse(work_order.production_stopped)
        self.assertFalse(work_order.permit_required)
        self.assertFalse(work_order.lockout_tagout_required)
        self.assertTrue(work_order.is_active)

    def test_assignment_defaults(self):
        assignment = WorkOrderAssignment()

        self.assertEqual(
            assignment.role,
            AssignmentRole.TECHNICIAN,
        )

        self.assertTrue(assignment.is_active)

    def test_failure_defaults(self):
        failure = WorkOrderFailure()

        self.assertEqual(
            failure.failure_type,
            FailureType.UNKNOWN,
        )

        self.assertFalse(failure.requires_follow_up)


class WorkOrderPropertyTests(SimpleTestCase):
    def test_work_order_without_planned_finish_is_not_overdue(self):
        work_order = WorkOrder(
            status=WorkOrderStatus.OPEN,
            planned_finish=None,
        )

        self.assertFalse(work_order.is_overdue)

    def test_completed_work_order_is_not_overdue(self):
        from django.utils import timezone

        work_order = WorkOrder(
            status=WorkOrderStatus.COMPLETED,
            planned_finish=timezone.now()
            - timezone.timedelta(days=1),
        )

        self.assertFalse(work_order.is_overdue)

    def test_closed_work_order_is_not_overdue(self):
        from django.utils import timezone

        work_order = WorkOrder(
            status=WorkOrderStatus.CLOSED,
            planned_finish=timezone.now()
            - timezone.timedelta(days=1),
        )

        self.assertFalse(work_order.is_overdue)

    def test_cancelled_work_order_is_not_overdue(self):
        from django.utils import timezone

        work_order = WorkOrder(
            status=WorkOrderStatus.CANCELLED,
            planned_finish=timezone.now()
            - timezone.timedelta(days=1),
        )

        self.assertFalse(work_order.is_overdue)

    def test_open_overdue_work_order(self):
        from django.utils import timezone

        work_order = WorkOrder(
            status=WorkOrderStatus.OPEN,
            planned_finish=timezone.now()
            - timezone.timedelta(hours=1),
        )

        self.assertTrue(work_order.is_overdue)

    def test_planned_duration_hours(self):
        from django.utils import timezone

        start_time = timezone.now()
        finish_time = start_time + timezone.timedelta(
            hours=4,
            minutes=30,
        )

        work_order = WorkOrder(
            planned_start=start_time,
            planned_finish=finish_time,
        )

        self.assertEqual(
            work_order.planned_duration_hours,
            4.5,
        )

    def test_planned_duration_without_dates_returns_none(self):
        work_order = WorkOrder()

        self.assertIsNone(
            work_order.planned_duration_hours
        )

    def test_actual_duration_hours(self):
        from django.utils import timezone

        start_time = timezone.now()
        finish_time = start_time + timezone.timedelta(
            hours=2,
            minutes=15,
        )

        work_order = WorkOrder(
            actual_start=start_time,
            actual_finish=finish_time,
        )

        self.assertEqual(
            work_order.actual_duration_hours,
            2.25,
        )

    def test_actual_duration_without_dates_returns_none(self):
        work_order = WorkOrder()

        self.assertIsNone(
            work_order.actual_duration_hours
        )

    def test_labor_cost(self):
        from decimal import Decimal

        labor = WorkOrderLabor(
            hours=Decimal("8.00"),
            hourly_rate=Decimal("125.50"),
        )

        self.assertEqual(
            labor.labor_cost,
            Decimal("1004.0000"),
        )


class WorkOrderRouterTests(SimpleTestCase):
    def test_router_type(self):
        self.assertIsInstance(router, DefaultRouter)

    def test_router_registry_count(self):
        self.assertEqual(
            len(router.registry),
            6,
        )

    def test_work_request_router_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "requests"
        )

        self.assertIs(
            registration[1],
            WorkRequestViewSet,
        )

        self.assertEqual(
            registration[2],
            "work-request",
        )

    def test_work_order_router_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "orders"
        )

        self.assertIs(
            registration[1],
            WorkOrderViewSet,
        )

        self.assertEqual(
            registration[2],
            "work-order",
        )

    def test_assignment_router_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "assignments"
        )

        self.assertIs(
            registration[1],
            WorkOrderAssignmentViewSet,
        )

        self.assertEqual(
            registration[2],
            "work-order-assignment",
        )

    def test_labor_router_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "labor"
        )

        self.assertIs(
            registration[1],
            WorkOrderLaborViewSet,
        )

        self.assertEqual(
            registration[2],
            "work-order-labor",
        )

    def test_downtime_router_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "downtime"
        )

        self.assertIs(
            registration[1],
            WorkOrderDowntimeViewSet,
        )

        self.assertEqual(
            registration[2],
            "work-order-downtime",
        )

    def test_failure_router_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "failures"
        )

        self.assertIs(
            registration[1],
            WorkOrderFailureViewSet,
        )

        self.assertEqual(
            registration[2],
            "work-order-failure",
        )


class WorkOrderURLTests(SimpleTestCase):
    def test_work_request_list_url(self):
        url = reverse("work_orders:work-request-list")
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-request-list",
        )

        self.assertEqual(
            match.func.cls,
            WorkRequestViewSet,
        )

    def test_work_order_list_url(self):
        url = reverse("work_orders:work-order-list")
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-list",
        )

        self.assertEqual(
            match.func.cls,
            WorkOrderViewSet,
        )

    def test_assignment_list_url(self):
        url = reverse(
            "work_orders:work-order-assignment-list"
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-assignment-list",
        )

        self.assertEqual(
            match.func.cls,
            WorkOrderAssignmentViewSet,
        )

    def test_labor_list_url(self):
        url = reverse(
            "work_orders:work-order-labor-list"
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-labor-list",
        )

        self.assertEqual(
            match.func.cls,
            WorkOrderLaborViewSet,
        )

    def test_downtime_list_url(self):
        url = reverse(
            "work_orders:work-order-downtime-list"
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-downtime-list",
        )

        self.assertEqual(
            match.func.cls,
            WorkOrderDowntimeViewSet,
        )

    def test_failure_list_url(self):
        url = reverse(
            "work_orders:work-order-failure-list"
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-failure-list",
        )

        self.assertEqual(
            match.func.cls,
            WorkOrderFailureViewSet,
        )

    def test_work_request_submit_url(self):
        url = reverse(
            "work_orders:work-request-submit",
            kwargs={"pk": 1},
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-request-submit",
        )

    def test_work_request_convert_url(self):
        url = reverse(
            "work_orders:work-request-convert",
            kwargs={"pk": 1},
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-request-convert",
        )

    def test_work_order_start_url(self):
        url = reverse(
            "work_orders:work-order-start",
            kwargs={"pk": 1},
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-start",
        )

    def test_work_order_complete_url(self):
        url = reverse(
            "work_orders:work-order-complete",
            kwargs={"pk": 1},
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-complete",
        )

    def test_work_order_close_url(self):
        url = reverse(
            "work_orders:work-order-close",
            kwargs={"pk": 1},
        )
        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "work-order-close",
        )
from datetime import date, timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from assets.models import Asset
from locations.models import Location
from projects.models import Project
from work_orders.models import (
    MaintenanceType,
    WorkOrder,
    WorkOrderSource,
    WorkOrderStatus,
    WorkPriority,
)

from .models import (
    GenerationStatus,
    PreventiveMaintenanceGeneration,
    PreventiveMaintenancePlan,
    PreventiveMaintenanceStatus,
    PreventiveMaintenanceTask,
    PreventiveMaintenanceTaskResult,
    ScheduleFrequency,
    TaskType,
)


User = get_user_model()
Organization = apps.get_model(
    "organizations",
    "Organization",
)


class PreventiveMaintenanceTestDataMixin:
    password = "Strong-Test-Password-123!"

    @classmethod
    def setUpTestData(cls):
        cls.organization = cls.create_organization(
            code="ORG-001",
            name="Test Organization",
        )

        cls.other_organization = cls.create_organization(
            code="ORG-002",
            name="Other Organization",
        )

        cls.user = User.objects.create_user(
            username="pm-user",
            email="pm-user@example.com",
            password=cls.password,
            organization=cls.organization,
        )

        cls.supervisor = User.objects.create_user(
            username="pm-supervisor",
            email="pm-supervisor@example.com",
            password=cls.password,
            organization=cls.organization,
        )

        cls.other_user = User.objects.create_user(
            username="other-user",
            email="other-user@example.com",
            password=cls.password,
            organization=cls.other_organization,
        )

        cls.superuser = User.objects.create_superuser(
            username="pm-admin",
            email="pm-admin@example.com",
            password=cls.password,
        )

        cls.project = Project.objects.create(
            organization=cls.organization,
            code="PRJ-001",
            name="Main Project",
            description="Main test project",
            is_active=True,
        )

        cls.other_project = Project.objects.create(
            organization=cls.other_organization,
            code="PRJ-002",
            name="Other Project",
            description="Other test project",
            is_active=True,
        )

        cls.location = Location.objects.create(
            project=cls.project,
            code="LOC-001",
            name="Main Plant",
            location_type=Location.LocationType.PLANT,
            description="Main plant location",
            is_active=True,
        )

        cls.other_location = Location.objects.create(
            project=cls.other_project,
            code="LOC-002",
            name="Other Plant",
            location_type=Location.LocationType.PLANT,
            description="Other plant location",
            is_active=True,
        )

        cls.asset = Asset.objects.create(
            project=cls.project,
            location=cls.location,
            code="AST-001",
            name="Primary Pump",
            asset_type=Asset.AssetType.EQUIPMENT,
            manufacturer="Test Manufacturer",
            model="P-100",
            serial_number="SN-001",
            description="Primary test asset",
            is_active=True,
        )

        cls.other_asset = Asset.objects.create(
            project=cls.other_project,
            location=cls.other_location,
            code="AST-002",
            name="Other Pump",
            asset_type=Asset.AssetType.EQUIPMENT,
            manufacturer="Other Manufacturer",
            model="P-200",
            serial_number="SN-002",
            description="Other test asset",
            is_active=True,
        )

    @classmethod
    def create_organization(
        cls,
        code,
        name,
    ):
        field_names = {
            field.name
            for field in Organization._meta.fields
        }

        values = {}

        if "code" in field_names:
            values["code"] = code

        if "name" in field_names:
            values["name"] = name

        if "title" in field_names:
            values["title"] = name

        if "slug" in field_names:
            values["slug"] = code.lower()

        if "is_active" in field_names:
            values["is_active"] = True

        return Organization.objects.create(
            **values
        )

    def create_plan(
        self,
        *,
        project=None,
        asset=None,
        location=None,
        created_by=None,
        supervisor=None,
        plan_number=None,
        title="Monthly Pump Maintenance",
        description="Preventive maintenance plan",
        status=PreventiveMaintenanceStatus.DRAFT,
        maintenance_type=MaintenanceType.PREVENTIVE,
        priority=WorkPriority.NORMAL,
        frequency=ScheduleFrequency.MONTHLY,
        custom_interval_days=None,
        start_date=None,
        end_date=None,
        last_due_date=None,
        next_due_date=None,
        generation_lead_days=7,
        auto_generate_work_order=True,
        allow_duplicate_open_orders=False,
        estimated_duration_hours=Decimal("2.00"),
        estimated_labor_hours=Decimal("3.00"),
        estimated_cost=Decimal("1500.00"),
        safety_instructions="Use PPE",
        required_tools="Standard tools",
        required_materials="Lubricant",
        permit_required=False,
        lockout_tagout_required=False,
        production_stop_required=False,
        is_active=True,
    ):
        project = project or self.project
        asset = asset or self.asset
        location = (
            self.location
            if location is None
            else location
        )
        created_by = created_by or self.user
        supervisor = (
            self.supervisor
            if supervisor is None
            else supervisor
        )
        start_date = (
            start_date
            or timezone.localdate()
        )

        if plan_number is None:
            count = (
                PreventiveMaintenancePlan.objects
                .filter(project=project)
                .count()
                + 1
            )
            plan_number = f"PM-{count:04d}"

        plan = PreventiveMaintenancePlan(
            project=project,
            plan_number=plan_number,
            title=title,
            description=description,
            asset=asset,
            location=location,
            status=status,
            maintenance_type=maintenance_type,
            priority=priority,
            frequency=frequency,
            custom_interval_days=custom_interval_days,
            start_date=start_date,
            end_date=end_date,
            last_due_date=last_due_date,
            next_due_date=next_due_date,
            generation_lead_days=generation_lead_days,
            auto_generate_work_order=(
                auto_generate_work_order
            ),
            allow_duplicate_open_orders=(
                allow_duplicate_open_orders
            ),
            estimated_duration_hours=(
                estimated_duration_hours
            ),
            estimated_labor_hours=(
                estimated_labor_hours
            ),
            estimated_cost=estimated_cost,
            supervisor=supervisor,
            safety_instructions=safety_instructions,
            required_tools=required_tools,
            required_materials=required_materials,
            permit_required=permit_required,
            lockout_tagout_required=(
                lockout_tagout_required
            ),
            production_stop_required=(
                production_stop_required
            ),
            created_by=created_by,
            is_active=is_active,
        )

        plan.full_clean()
        plan.save()

        return plan

    def create_task(
        self,
        *,
        plan=None,
        sequence=None,
        task_type=TaskType.GENERAL,
        title="Inspect equipment",
        description="Inspect the equipment",
        acceptance_criteria="No visible defects",
        estimated_duration_minutes=30,
        requires_shutdown=False,
        requires_photo=False,
        requires_measurement=False,
        measurement_unit="",
        minimum_acceptable_value=None,
        maximum_acceptable_value=None,
        is_mandatory=True,
        is_active=True,
    ):
        plan = plan or self.create_plan()

        if sequence is None:
            sequence = plan.tasks.count() + 1

        task = PreventiveMaintenanceTask(
            plan=plan,
            sequence=sequence,
            task_type=task_type,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            estimated_duration_minutes=(
                estimated_duration_minutes
            ),
            requires_shutdown=requires_shutdown,
            requires_photo=requires_photo,
            requires_measurement=(
                requires_measurement
            ),
            measurement_unit=measurement_unit,
            minimum_acceptable_value=(
                minimum_acceptable_value
            ),
            maximum_acceptable_value=(
                maximum_acceptable_value
            ),
            is_mandatory=is_mandatory,
            is_active=is_active,
        )

        task.full_clean()
        task.save()

        return task

    def create_work_order(
        self,
        *,
        project=None,
        asset=None,
        location=None,
        created_by=None,
        work_order_number=None,
        title="Generated PM Work Order",
        description="Generated from PM plan",
        maintenance_type=MaintenanceType.PREVENTIVE,
        priority=WorkPriority.NORMAL,
        status=WorkOrderStatus.OPEN,
        source=WorkOrderSource.PREVENTIVE_MAINTENANCE,
        supervisor=None,
        planned_start=None,
        planned_finish=None,
    ):
        project = project or self.project
        asset = asset or self.asset
        location = (
            self.location
            if location is None
            else location
        )
        created_by = created_by or self.user
        supervisor = (
            self.supervisor
            if supervisor is None
            else supervisor
        )

        if work_order_number is None:
            count = (
                WorkOrder.objects
                .filter(project=project)
                .count()
                + 1
            )
            work_order_number = f"WO-PM-{count:04d}"

        return WorkOrder.objects.create(
            project=project,
            asset=asset,
            location=location,
            work_order_number=work_order_number,
            title=title,
            description=description,
            maintenance_type=maintenance_type,
            priority=priority,
            status=status,
            source=source,
            created_by=created_by,
            supervisor=supervisor,
            planned_start=planned_start,
            planned_finish=planned_finish,
        )

    def create_generation(
        self,
        *,
        plan=None,
        due_date=None,
        scheduled_generation_date=None,
        status=GenerationStatus.PENDING,
        work_order=None,
        generated_by=None,
        generated_at=None,
        error_message="",
        notes="",
    ):
        plan = plan or self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        due_date = (
            due_date
            or plan.next_due_date
            or plan.start_date
        )

        scheduled_generation_date = (
            scheduled_generation_date
            or (
                due_date
                - timedelta(
                    days=plan.generation_lead_days,
                )
            )
        )

        return PreventiveMaintenanceGeneration.objects.create(
            plan=plan,
            due_date=due_date,
            scheduled_generation_date=(
                scheduled_generation_date
            ),
            status=status,
            work_order=work_order,
            generated_by=generated_by,
            generated_at=generated_at,
            error_message=error_message,
            notes=notes,
        )

    def create_task_result(
        self,
        *,
        generation=None,
        task=None,
        is_completed=False,
        completed_at=None,
        completed_by=None,
        measured_value=None,
        result_is_acceptable=None,
        result_notes="",
    ):
        generation = (
            generation
            or self.create_generation()
        )

        task = (
            task
            or self.create_task(
                plan=generation.plan,
            )
        )

        result = PreventiveMaintenanceTaskResult(
            generation=generation,
            task=task,
            is_completed=is_completed,
            completed_at=completed_at,
            completed_by=completed_by,
            measured_value=measured_value,
            result_is_acceptable=(
                result_is_acceptable
            ),
            result_notes=result_notes,
        )

        result.full_clean()
        result.save()

        return result


class PreventiveMaintenanceChoiceTests(
    SimpleTestCase
):
    def test_status_values(self):
        expected_values = {
            "draft",
            "active",
            "suspended",
            "completed",
            "cancelled",
        }

        actual_values = {
            choice.value
            for choice in PreventiveMaintenanceStatus
        }

        self.assertEqual(
            actual_values,
            expected_values,
        )

    def test_schedule_frequency_values(self):
        expected_values = {
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "semiannual",
            "annual",
            "custom_days",
        }

        actual_values = {
            choice.value
            for choice in ScheduleFrequency
        }

        self.assertEqual(
            actual_values,
            expected_values,
        )

    def test_generation_status_values(self):
        expected_values = {
            "pending",
            "generated",
            "skipped",
            "failed",
        }

        actual_values = {
            choice.value
            for choice in GenerationStatus
        }

        self.assertEqual(
            actual_values,
            expected_values,
        )

    def test_task_type_values(self):
        expected_values = {
            "inspection",
            "lubrication",
            "cleaning",
            "adjustment",
            "replacement",
            "calibration",
            "testing",
            "measurement",
            "tightening",
            "general",
        }

        actual_values = {
            choice.value
            for choice in TaskType
        }

        self.assertEqual(
            actual_values,
            expected_values,
        )


class PreventiveMaintenanceMetadataTests(
    SimpleTestCase
):
    def test_plan_metadata(self):
        self.assertEqual(
            str(
                PreventiveMaintenancePlan
                ._meta
                .verbose_name
            ),
            "برنامه نگهداری پیشگیرانه",
        )

        self.assertEqual(
            str(
                PreventiveMaintenancePlan
                ._meta
                .verbose_name_plural
            ),
            "برنامه‌های نگهداری پیشگیرانه",
        )

        self.assertEqual(
            PreventiveMaintenancePlan._meta.ordering,
            [
                "next_due_date",
                "plan_number",
            ],
        )

    def test_task_metadata(self):
        self.assertEqual(
            str(
                PreventiveMaintenanceTask
                ._meta
                .verbose_name
            ),
            "فعالیت نگهداری پیشگیرانه",
        )

        self.assertEqual(
            str(
                PreventiveMaintenanceTask
                ._meta
                .verbose_name_plural
            ),
            "فعالیت‌های نگهداری پیشگیرانه",
        )

        self.assertEqual(
            PreventiveMaintenanceTask._meta.ordering,
            [
                "sequence",
                "id",
            ],
        )

    def test_generation_metadata(self):
        self.assertEqual(
            str(
                PreventiveMaintenanceGeneration
                ._meta
                .verbose_name
            ),
            "سابقه تولید دستورکار پیشگیرانه",
        )

        self.assertEqual(
            PreventiveMaintenanceGeneration
            ._meta
            .ordering,
            [
                "-due_date",
                "-id",
            ],
        )

    def test_task_result_metadata(self):
        self.assertEqual(
            str(
                PreventiveMaintenanceTaskResult
                ._meta
                .verbose_name
            ),
            "نتیجه فعالیت نگهداری",
        )

        self.assertEqual(
            PreventiveMaintenanceTaskResult
            ._meta
            .ordering,
            [
                "task__sequence",
                "id",
            ],
        )


class PreventiveMaintenanceDefaultTests(
    SimpleTestCase
):
    def test_plan_defaults(self):
        plan = PreventiveMaintenancePlan(
            project_id=1,
            asset_id=1,
            plan_number="PM-001",
            title="Test Plan",
            created_by_id=1,
        )

        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.DRAFT,
        )
        self.assertEqual(
            plan.maintenance_type,
            MaintenanceType.PREVENTIVE,
        )
        self.assertEqual(
            plan.priority,
            WorkPriority.NORMAL,
        )
        self.assertEqual(
            plan.frequency,
            ScheduleFrequency.MONTHLY,
        )
        self.assertEqual(
            plan.generation_lead_days,
            7,
        )
        self.assertTrue(
            plan.auto_generate_work_order
        )
        self.assertFalse(
            plan.allow_duplicate_open_orders
        )
        self.assertEqual(
            plan.estimated_duration_hours,
            Decimal("0.00"),
        )
        self.assertEqual(
            plan.estimated_labor_hours,
            Decimal("0.00"),
        )
        self.assertEqual(
            plan.estimated_cost,
            Decimal("0.00"),
        )
        self.assertFalse(
            plan.permit_required
        )
        self.assertFalse(
            plan.lockout_tagout_required
        )
        self.assertFalse(
            plan.production_stop_required
        )
        self.assertTrue(
            plan.is_active
        )

    def test_task_defaults(self):
        task = PreventiveMaintenanceTask(
            plan_id=1,
            title="Test Task",
        )

        self.assertEqual(
            task.sequence,
            1,
        )
        self.assertEqual(
            task.task_type,
            TaskType.GENERAL,
        )
        self.assertEqual(
            task.estimated_duration_minutes,
            0,
        )
        self.assertFalse(
            task.requires_shutdown
        )
        self.assertFalse(
            task.requires_photo
        )
        self.assertFalse(
            task.requires_measurement
        )
        self.assertTrue(
            task.is_mandatory
        )
        self.assertTrue(
            task.is_active
        )

    def test_generation_defaults(self):
        generation = PreventiveMaintenanceGeneration(
            plan_id=1,
            due_date=date(2026, 1, 1),
            scheduled_generation_date=(
                date(2025, 12, 25)
            ),
        )

        self.assertEqual(
            generation.status,
            GenerationStatus.PENDING,
        )
        self.assertEqual(
            generation.error_message,
            "",
        )
        self.assertEqual(
            generation.notes,
            "",
        )

    def test_task_result_defaults(self):
        result = PreventiveMaintenanceTaskResult(
            generation_id=1,
            task_id=1,
        )

        self.assertFalse(
            result.is_completed
        )
        self.assertIsNone(
            result.completed_at
        )
        self.assertIsNone(
            result.completed_by_id
        )
        self.assertIsNone(
            result.measured_value
        )
        self.assertIsNone(
            result.result_is_acceptable
        )
        self.assertEqual(
            result.result_notes,
            "",
        )


class PreventiveMaintenancePlanModelTests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def test_string_representation(self):
        plan = self.create_plan(
            plan_number="PM-100",
            title="Pump Service",
        )

        self.assertEqual(
            str(plan),
            "PM-100 - Pump Service",
        )

    def test_custom_frequency_requires_interval(self):
        plan = PreventiveMaintenancePlan(
            project=self.project,
            plan_number="PM-CUSTOM-001",
            title="Custom Plan",
            asset=self.asset,
            location=self.location,
            frequency=ScheduleFrequency.CUSTOM_DAYS,
            custom_interval_days=None,
            start_date=timezone.localdate(),
            created_by=self.user,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            plan.full_clean()

        self.assertIn(
            "custom_interval_days",
            context.exception.message_dict,
        )

    def test_non_custom_frequency_rejects_interval(self):
        plan = PreventiveMaintenancePlan(
            project=self.project,
            plan_number="PM-MONTHLY-001",
            title="Monthly Plan",
            asset=self.asset,
            location=self.location,
            frequency=ScheduleFrequency.MONTHLY,
            custom_interval_days=10,
            start_date=timezone.localdate(),
            created_by=self.user,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            plan.full_clean()

        self.assertIn(
            "custom_interval_days",
            context.exception.message_dict,
        )

    def test_end_date_cannot_precede_start_date(self):
        plan = PreventiveMaintenancePlan(
            project=self.project,
            plan_number="PM-DATE-001",
            title="Invalid Dates",
            asset=self.asset,
            location=self.location,
            start_date=date(2026, 2, 10),
            end_date=date(2026, 2, 9),
            created_by=self.user,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            plan.full_clean()

        self.assertIn(
            "end_date",
            context.exception.message_dict,
        )

    def test_asset_must_belong_to_plan_project(self):
        plan = PreventiveMaintenancePlan(
            project=self.project,
            plan_number="PM-ASSET-001",
            title="Invalid Asset",
            asset=self.other_asset,
            location=self.location,
            start_date=timezone.localdate(),
            created_by=self.user,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            plan.full_clean()

        self.assertIn(
            "asset",
            context.exception.message_dict,
        )

    def test_location_must_belong_to_plan_project(self):
        plan = PreventiveMaintenancePlan(
            project=self.project,
            plan_number="PM-LOCATION-001",
            title="Invalid Location",
            asset=self.asset,
            location=self.other_location,
            start_date=timezone.localdate(),
            created_by=self.user,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            plan.full_clean()

        self.assertIn(
            "location",
            context.exception.message_dict,
        )

    def test_plan_number_is_unique_per_project(self):
        self.create_plan(
            plan_number="PM-UNIQUE-001",
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                PreventiveMaintenancePlan.objects.create(
                    project=self.project,
                    plan_number="PM-UNIQUE-001",
                    title="Duplicate Plan",
                    asset=self.asset,
                    location=self.location,
                    start_date=timezone.localdate(),
                    created_by=self.user,
                )

    def test_same_plan_number_allowed_in_other_project(self):
        self.create_plan(
            plan_number="PM-SHARED-001",
        )

        other_plan = self.create_plan(
            project=self.other_project,
            asset=self.other_asset,
            location=self.other_location,
            created_by=self.other_user,
            supervisor=None,
            plan_number="PM-SHARED-001",
        )

        self.assertEqual(
            other_plan.plan_number,
            "PM-SHARED-001",
        )

    def test_is_due_false_without_next_due_date(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
        )
        plan.next_due_date = None

        self.assertFalse(
            plan.is_due
        )

    def test_is_due_false_for_non_active_plan(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.SUSPENDED,
            next_due_date=timezone.localdate(),
        )

        self.assertFalse(
            plan.is_due
        )

    def test_is_due_true_on_due_date(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        self.assertTrue(
            plan.is_due
        )

    def test_is_due_true_after_due_date(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                - timedelta(days=1)
            ),
        )

        self.assertTrue(
            plan.is_due
        )

    def test_is_due_false_before_due_date(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=1)
            ),
        )

        self.assertFalse(
            plan.is_due
        )

    def test_generation_date_without_due_date(self):
        plan = self.create_plan()
        plan.next_due_date = None

        self.assertIsNone(
            plan.generation_date
        )

    def test_generation_date_uses_lead_days(self):
        plan = self.create_plan(
            next_due_date=date(2026, 5, 20),
            generation_lead_days=7,
        )

        self.assertEqual(
            plan.generation_date,
            date(2026, 5, 13),
        )

    def test_ready_for_generation_true(self):
        today = timezone.localdate()

        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=today + timedelta(days=5),
            generation_lead_days=7,
            auto_generate_work_order=True,
            is_active=True,
        )

        self.assertTrue(
            plan.is_ready_for_generation
        )

    def test_ready_for_generation_false_when_auto_generation_disabled(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
            auto_generate_work_order=False,
        )

        self.assertFalse(
            plan.is_ready_for_generation
        )

    def test_ready_for_generation_false_when_plan_inactive(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
            is_active=False,
        )

        self.assertFalse(
            plan.is_ready_for_generation
        )

    def test_ready_for_generation_false_for_draft_plan(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.DRAFT,
            next_due_date=timezone.localdate(),
        )

        self.assertFalse(
            plan.is_ready_for_generation
        )

    def test_ready_for_generation_false_without_due_date(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
        )
        plan.next_due_date = None

        self.assertFalse(
            plan.is_ready_for_generation
        )

    def test_ready_for_generation_false_after_end_date(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            start_date=date(2026, 5, 1),
            next_due_date=date(2026, 5, 20),
            end_date=date(2026, 5, 19),
        )

        self.assertFalse(
            plan.is_ready_for_generation
        )

    def test_initialize_next_due_date(self):
        plan = self.create_plan(
            start_date=date(2026, 1, 15),
            next_due_date=None,
        )

        result = plan.initialize_next_due_date()

        self.assertEqual(
            result,
            date(2026, 1, 15),
        )
        self.assertEqual(
            plan.next_due_date,
            date(2026, 1, 15),
        )

    def test_initialize_does_not_replace_existing_due_date(
        self,
    ):
        plan = self.create_plan(
            start_date=date(2026, 1, 15),
            next_due_date=date(2026, 2, 15),
        )

        result = plan.initialize_next_due_date()

        self.assertEqual(
            result,
            date(2026, 2, 15),
        )

    def test_calculate_daily_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.DAILY,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 10),
        )

        self.assertEqual(
            result,
            date(2026, 1, 11),
        )

    def test_calculate_weekly_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.WEEKLY,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 10),
        )

        self.assertEqual(
            result,
            date(2026, 1, 17),
        )

    def test_calculate_monthly_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.MONTHLY,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 15),
        )

        self.assertEqual(
            result,
            date(2026, 2, 15),
        )

    def test_monthly_schedule_handles_month_end(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.MONTHLY,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 31),
        )

        self.assertEqual(
            result,
            date(2026, 2, 28),
        )

    def test_monthly_schedule_handles_leap_year(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.MONTHLY,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2028, 1, 31),
        )

        self.assertEqual(
            result,
            date(2028, 2, 29),
        )

    def test_calculate_quarterly_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.QUARTERLY,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 15),
        )

        self.assertEqual(
            result,
            date(2026, 4, 15),
        )

    def test_calculate_semiannual_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.SEMIANNUAL,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 15),
        )

        self.assertEqual(
            result,
            date(2026, 7, 15),
        )

    def test_calculate_annual_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.ANNUAL,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 15),
        )

        self.assertEqual(
            result,
            date(2027, 1, 15),
        )

    def test_annual_schedule_handles_leap_day(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.ANNUAL,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2028, 2, 29),
        )

        self.assertEqual(
            result,
            date(2029, 2, 28),
        )

    def test_calculate_custom_days_due_date(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.CUSTOM_DAYS,
            custom_interval_days=45,
        )

        result = plan.calculate_next_due_date(
            reference_date=date(2026, 1, 1),
        )

        self.assertEqual(
            result,
            date(2026, 2, 15),
        )

    def test_calculation_uses_last_due_date_first(self):
        plan = self.create_plan(
            frequency=ScheduleFrequency.DAILY,
            start_date=date(2026, 1, 1),
            last_due_date=date(2026, 1, 10),
            next_due_date=date(2026, 1, 20),
        )

        result = plan.calculate_next_due_date()

        self.assertEqual(
            result,
            date(2026, 1, 11),
        )

    def test_advance_schedule_updates_dates(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            frequency=ScheduleFrequency.MONTHLY,
            next_due_date=date(2026, 1, 15),
        )

        plan.advance_schedule()
        plan.refresh_from_db()

        self.assertEqual(
            plan.last_due_date,
            date(2026, 1, 15),
        )
        self.assertEqual(
            plan.next_due_date,
            date(2026, 2, 15),
        )
        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.ACTIVE,
        )

    def test_advance_schedule_completes_plan_after_end_date(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            frequency=ScheduleFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            next_due_date=date(2026, 1, 15),
            end_date=date(2026, 1, 31),
        )

        plan.advance_schedule()
        plan.refresh_from_db()

        self.assertEqual(
            plan.last_due_date,
            date(2026, 1, 15),
        )
        self.assertEqual(
            plan.next_due_date,
            date(2026, 2, 15),
        )
        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.COMPLETED,
        )


class PreventiveMaintenanceTaskModelTests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def test_string_representation(self):
        plan = self.create_plan(
            plan_number="PM-TASK-001",
        )

        task = self.create_task(
            plan=plan,
            sequence=2,
            title="Check Oil Level",
        )

        self.assertEqual(
            str(task),
            (
                "PM-TASK-001 - "
                "2. Check Oil Level"
            ),
        )

    def test_task_sequence_unique_per_plan(self):
        plan = self.create_plan()

        self.create_task(
            plan=plan,
            sequence=1,
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                PreventiveMaintenanceTask.objects.create(
                    plan=plan,
                    sequence=1,
                    title="Duplicate Sequence",
                )

    def test_same_sequence_allowed_for_different_plans(
        self,
    ):
        first_plan = self.create_plan(
            plan_number="PM-TASK-A",
        )
        second_plan = self.create_plan(
            plan_number="PM-TASK-B",
        )

        first_task = self.create_task(
            plan=first_plan,
            sequence=1,
        )
        second_task = self.create_task(
            plan=second_plan,
            sequence=1,
        )

        self.assertEqual(
            first_task.sequence,
            second_task.sequence,
        )

    def test_maximum_value_cannot_be_less_than_minimum(
        self,
    ):
        task = PreventiveMaintenanceTask(
            plan=self.create_plan(),
            sequence=1,
            title="Measure Pressure",
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("5.00"),
            maximum_acceptable_value=Decimal("4.00"),
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            task.full_clean()

        self.assertIn(
            "maximum_acceptable_value",
            context.exception.message_dict,
        )

    def test_acceptance_limits_require_measurement(
        self,
    ):
        task = PreventiveMaintenanceTask(
            plan=self.create_plan(),
            sequence=1,
            title="Invalid Measurement Task",
            requires_measurement=False,
            minimum_acceptable_value=Decimal("5.00"),
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            task.full_clean()

        self.assertIn(
            "requires_measurement",
            context.exception.message_dict,
        )

    def test_measurement_requires_unit(self):
        task = PreventiveMaintenanceTask(
            plan=self.create_plan(),
            sequence=1,
            title="Measure Pressure",
            requires_measurement=True,
            measurement_unit="",
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            task.full_clean()

        self.assertIn(
            "measurement_unit",
            context.exception.message_dict,
        )

    def test_valid_measurement_task(self):
        task = self.create_task(
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )

        self.assertTrue(
            task.requires_measurement
        )
        self.assertEqual(
            task.measurement_unit,
            "bar",
        )


class PreventiveMaintenanceGenerationModelTests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def test_string_representation(self):
        plan = self.create_plan(
            plan_number="PM-GEN-001",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=date(2026, 3, 10),
        )

        generation = self.create_generation(
            plan=plan,
            due_date=date(2026, 3, 10),
        )

        self.assertEqual(
            str(generation),
            "PM-GEN-001 - 2026-03-10",
        )

    def test_generation_unique_per_plan_and_due_date(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=date(2026, 3, 10),
        )

        self.create_generation(
            plan=plan,
            due_date=date(2026, 3, 10),
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                PreventiveMaintenanceGeneration.objects.create(
                    plan=plan,
                    due_date=date(2026, 3, 10),
                    scheduled_generation_date=(
                        date(2026, 3, 3)
                    ),
                )

    def test_mark_generated(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        generation = self.create_generation(
            plan=plan,
        )
        work_order = self.create_work_order()

        generation.mark_generated(
            work_order=work_order,
            generated_by=self.user,
        )
        generation.refresh_from_db()

        self.assertEqual(
            generation.status,
            GenerationStatus.GENERATED,
        )
        self.assertEqual(
            generation.work_order,
            work_order,
        )
        self.assertEqual(
            generation.generated_by,
            self.user,
        )
        self.assertIsNotNone(
            generation.generated_at
        )
        self.assertEqual(
            generation.error_message,
            "",
        )

    def test_mark_generated_clears_error_message(self):
        generation = self.create_generation(
            status=GenerationStatus.FAILED,
            error_message="Previous failure",
        )
        work_order = self.create_work_order()

        generation.mark_generated(
            work_order=work_order,
            generated_by=self.user,
        )
        generation.refresh_from_db()

        self.assertEqual(
            generation.error_message,
            "",
        )

    def test_mark_failed(self):
        generation = self.create_generation()

        generation.mark_failed(
            "  Work order creation failed  "
        )
        generation.refresh_from_db()

        self.assertEqual(
            generation.status,
            GenerationStatus.FAILED,
        )
        self.assertEqual(
            generation.error_message,
            "Work order creation failed",
        )

    def test_mark_skipped(self):
        generation = self.create_generation()

        generation.mark_skipped(
            "  Existing open work order  "
        )
        generation.refresh_from_db()

        self.assertEqual(
            generation.status,
            GenerationStatus.SKIPPED,
        )
        self.assertEqual(
            generation.notes,
            "Existing open work order",
        )


class PreventiveMaintenanceTaskResultModelTests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def test_string_representation(self):
        plan = self.create_plan(
            plan_number="PM-RESULT-001",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=date(2026, 4, 1),
        )
        task = self.create_task(
            plan=plan,
            title="Measure Temperature",
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        self.assertEqual(
            str(result),
            (
                "PM-RESULT-001 - 2026-04-01 - "
                "Measure Temperature"
            ),
        )

    def test_result_unique_per_generation_and_task(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
        )
        generation = self.create_generation(
            plan=plan,
        )

        self.create_task_result(
            generation=generation,
            task=task,
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                PreventiveMaintenanceTaskResult.objects.create(
                    generation=generation,
                    task=task,
                )

    def test_completed_measurement_requires_value(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
        )
        generation = self.create_generation(
            plan=plan,
        )

        result = PreventiveMaintenanceTaskResult(
            generation=generation,
            task=task,
            is_completed=True,
            completed_by=self.user,
            measured_value=None,
        )

        with self.assertRaises(
            ValidationError
        ) as context:
            result.full_clean()

        self.assertIn(
            "measured_value",
            context.exception.message_dict,
        )

    def test_clean_sets_completion_time(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
        )
        generation = self.create_generation(
            plan=plan,
        )

        result = PreventiveMaintenanceTaskResult(
            generation=generation,
            task=task,
            is_completed=True,
            completed_by=self.user,
        )

        result.full_clean()

        self.assertIsNotNone(
            result.completed_at
        )

    def test_evaluate_result_without_value(self):
        result = self.create_task_result()

        evaluation = result.evaluate_result()

        self.assertIsNone(
            evaluation
        )
        self.assertIsNone(
            result.result_is_acceptable
        )

    def test_evaluate_result_inside_limits(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
            measured_value=Decimal("5.00"),
        )

        evaluation = result.evaluate_result()

        self.assertTrue(
            evaluation
        )
        self.assertTrue(
            result.result_is_acceptable
        )

    def test_evaluate_result_equal_to_minimum(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
            measured_value=Decimal("4.00"),
        )

        self.assertTrue(
            result.evaluate_result()
        )

    def test_evaluate_result_equal_to_maximum(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
            measured_value=Decimal("6.00"),
        )

        self.assertTrue(
            result.evaluate_result()
        )

    def test_evaluate_result_below_minimum(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
            measured_value=Decimal("3.99"),
        )

        self.assertFalse(
            result.evaluate_result()
        )
        self.assertFalse(
            result.result_is_acceptable
        )

    def test_evaluate_result_above_maximum(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
            measured_value=Decimal("6.01"),
        )

        self.assertFalse(
            result.evaluate_result()
        )
        self.assertFalse(
            result.result_is_acceptable
        )

    def test_mark_completed_without_measurement(self):
        result = self.create_task_result()

        result.mark_completed(
            user=self.user,
            notes="  Completed successfully  ",
        )
        result.refresh_from_db()

        self.assertTrue(
            result.is_completed
        )
        self.assertEqual(
            result.completed_by,
            self.user,
        )
        self.assertIsNotNone(
            result.completed_at
        )
        self.assertEqual(
            result.result_notes,
            "Completed successfully",
        )
        self.assertIsNone(
            result.result_is_acceptable
        )

    def test_mark_completed_with_acceptable_measurement(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        result.mark_completed(
            user=self.user,
            measured_value=Decimal("5.00"),
            notes="Pressure is normal",
        )
        result.refresh_from_db()

        self.assertTrue(
            result.is_completed
        )
        self.assertEqual(
            result.measured_value,
            Decimal("5.0000"),
        )
        self.assertTrue(
            result.result_is_acceptable
        )

    def test_mark_completed_with_unacceptable_measurement(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        result.mark_completed(
            user=self.user,
            measured_value=Decimal("7.00"),
            notes="Pressure is too high",
        )
        result.refresh_from_db()

        self.assertTrue(
            result.is_completed
        )
        self.assertFalse(
            result.result_is_acceptable
        )

from unittest.mock import patch

from django.urls import resolve, reverse

from rest_framework import status, viewsets
from rest_framework.routers import DefaultRouter
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from .serializers import (
    PreventiveMaintenanceGenerationSerializer,
    PreventiveMaintenancePlanDetailSerializer,
    PreventiveMaintenancePlanListSerializer,
    PreventiveMaintenanceTaskResultSerializer,
    PreventiveMaintenanceTaskSerializer,
)
from .services import (
    PreventiveMaintenanceGenerationError,
    PreventiveMaintenanceService,
)
from .urls import router
from .views import (
    PreventiveMaintenanceGenerationViewSet,
    PreventiveMaintenancePlanViewSet,
    PreventiveMaintenanceTaskResultViewSet,
    PreventiveMaintenanceTaskViewSet,
)


class PreventiveMaintenanceSerializerTests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def test_plan_list_serializer(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        serializer = (
            PreventiveMaintenancePlanListSerializer(
                plan
            )
        )

        self.assertEqual(
            serializer.data["id"],
            plan.id,
        )
        self.assertEqual(
            serializer.data["plan_number"],
            plan.plan_number,
        )
        self.assertEqual(
            serializer.data["title"],
            plan.title,
        )

    def test_plan_detail_serializer(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        self.create_task(
            plan=plan,
            sequence=1,
            title="Inspect Pump",
        )

        serializer = (
            PreventiveMaintenancePlanDetailSerializer(
                plan
            )
        )

        self.assertEqual(
            serializer.data["id"],
            plan.id,
        )
        self.assertEqual(
            serializer.data["project"],
            plan.project_id,
        )
        self.assertEqual(
            serializer.data["asset"],
            plan.asset_id,
        )

    def test_task_serializer(self):
        plan = self.create_plan()
        task = self.create_task(
            plan=plan,
            sequence=1,
            title="Check Bearings",
        )

        serializer = (
            PreventiveMaintenanceTaskSerializer(
                task
            )
        )

        self.assertEqual(
            serializer.data["id"],
            task.id,
        )
        self.assertEqual(
            serializer.data["plan"],
            plan.id,
        )
        self.assertEqual(
            serializer.data["title"],
            "Check Bearings",
        )

    def test_generation_serializer(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        generation = self.create_generation(
            plan=plan,
        )

        serializer = (
            PreventiveMaintenanceGenerationSerializer(
                generation
            )
        )

        self.assertEqual(
            serializer.data["id"],
            generation.id,
        )
        self.assertEqual(
            serializer.data["plan"],
            plan.id,
        )
        self.assertEqual(
            serializer.data["status"],
            GenerationStatus.PENDING,
        )

    def test_task_result_serializer(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        serializer = (
            PreventiveMaintenanceTaskResultSerializer(
                result
            )
        )

        self.assertEqual(
            serializer.data["id"],
            result.id,
        )
        self.assertEqual(
            serializer.data["generation"],
            generation.id,
        )
        self.assertEqual(
            serializer.data["task"],
            task.id,
        )

    def test_task_serializer_rejects_invalid_limits(
        self,
    ):
        plan = self.create_plan()

        serializer = (
            PreventiveMaintenanceTaskSerializer(
                data={
                    "plan": plan.id,
                    "sequence": 1,
                    "task_type": TaskType.MEASUREMENT,
                    "title": "Measure Pressure",
                    "description": "",
                    "acceptance_criteria": "",
                    "estimated_duration_minutes": 10,
                    "requires_shutdown": False,
                    "requires_photo": False,
                    "requires_measurement": True,
                    "measurement_unit": "bar",
                    "minimum_acceptable_value": "10.00",
                    "maximum_acceptable_value": "5.00",
                    "is_mandatory": True,
                    "is_active": True,
                }
            )
        )

        self.assertFalse(
            serializer.is_valid()
        )

    def test_task_serializer_requires_measurement_unit(
        self,
    ):
        plan = self.create_plan()

        serializer = (
            PreventiveMaintenanceTaskSerializer(
                data={
                    "plan": plan.id,
                    "sequence": 1,
                    "task_type": TaskType.MEASUREMENT,
                    "title": "Measure Pressure",
                    "description": "",
                    "acceptance_criteria": "",
                    "estimated_duration_minutes": 10,
                    "requires_shutdown": False,
                    "requires_photo": False,
                    "requires_measurement": True,
                    "measurement_unit": "",
                    "is_mandatory": True,
                    "is_active": True,
                }
            )
        )

        self.assertFalse(
            serializer.is_valid()
        )


class PreventiveMaintenanceServiceTests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def test_service_class_exists(self):
        self.assertTrue(
            hasattr(
                PreventiveMaintenanceService,
                "generate_plan_work_order",
            )
        )

    def test_generate_returns_none_when_not_ready(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=30)
            ),
            generation_lead_days=7,
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
                force=False,
            )
        )

        self.assertIsNone(
            generation
        )
        self.assertFalse(
            PreventiveMaintenanceGeneration.objects
            .filter(plan=plan)
            .exists()
        )

    def test_force_generates_before_generation_date(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=30)
            ),
            generation_lead_days=7,
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
                force=True,
            )
        )

        self.assertIsNotNone(
            generation
        )
        self.assertEqual(
            generation.plan,
            plan,
        )

    def test_generation_creates_work_order(self):
        today = timezone.localdate()

        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=today,
            generation_lead_days=7,
        )

        self.create_task(
            plan=plan,
            sequence=1,
            title="Inspect Pump",
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
            )
        )

        self.assertIsNotNone(
            generation
        )

        generation.refresh_from_db()

        self.assertEqual(
            generation.status,
            GenerationStatus.GENERATED,
        )
        self.assertIsNotNone(
            generation.work_order
        )
        self.assertEqual(
            generation.generated_by,
            self.user,
        )
        self.assertEqual(
            generation.work_order.project,
            plan.project,
        )
        self.assertEqual(
            generation.work_order.asset,
            plan.asset,
        )
        self.assertEqual(
            generation.work_order.location,
            plan.location,
        )
        self.assertEqual(
            generation.work_order.source,
            WorkOrderSource.PREVENTIVE_MAINTENANCE,
        )
        self.assertEqual(
            generation.work_order.maintenance_type,
            plan.maintenance_type,
        )
        self.assertEqual(
            generation.work_order.priority,
            plan.priority,
        )

    def test_generation_creates_task_results(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        active_task = self.create_task(
            plan=plan,
            sequence=1,
            title="Active Task",
            is_active=True,
        )

        self.create_task(
            plan=plan,
            sequence=2,
            title="Inactive Task",
            is_active=False,
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
            )
        )

        self.assertEqual(
            generation.task_results.count(),
            1,
        )
        self.assertTrue(
            generation.task_results.filter(
                task=active_task,
            ).exists()
        )

    def test_generation_advances_plan_schedule(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            frequency=ScheduleFrequency.MONTHLY,
            next_due_date=date(2026, 1, 15),
            generation_lead_days=365,
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
                force=True,
            )
        )

        plan.refresh_from_db()

        self.assertIsNotNone(
            generation
        )
        self.assertEqual(
            plan.last_due_date,
            date(2026, 1, 15),
        )
        self.assertEqual(
            plan.next_due_date,
            date(2026, 2, 15),
        )

    def test_generation_record_is_unique_for_due_date(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        first_generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
            )
        )

        self.assertIsNotNone(
            first_generation
        )

        self.assertEqual(
            PreventiveMaintenanceGeneration.objects
            .filter(
                plan=plan,
                due_date=first_generation.due_date,
            )
            .count(),
            1,
        )

    def test_invalid_plan_id_raises_generation_error(
        self,
    ):
        with self.assertRaises(
            PreventiveMaintenanceGenerationError
        ):
            (
                PreventiveMaintenanceService
                .generate_plan_work_order(
                    plan_id=999999,
                    generated_by=self.user,
                )
            )

    def test_inactive_plan_cannot_generate(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
            is_active=False,
        )

        with self.assertRaises(
            PreventiveMaintenanceGenerationError
        ):
            (
                PreventiveMaintenanceService
                .generate_plan_work_order(
                    plan_id=plan.id,
                    generated_by=self.user,
                    force=True,
                )
            )

    def test_suspended_plan_cannot_generate(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.SUSPENDED,
            next_due_date=timezone.localdate(),
        )

        with self.assertRaises(
            PreventiveMaintenanceGenerationError
        ):
            (
                PreventiveMaintenanceService
                .generate_plan_work_order(
                    plan_id=plan.id,
                    generated_by=self.user,
                    force=True,
                )
            )

    def test_duplicate_open_order_is_skipped(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
            allow_duplicate_open_orders=False,
        )

        self.create_work_order(
            project=plan.project,
            asset=plan.asset,
            location=plan.location,
            status=WorkOrderStatus.OPEN,
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
                force=True,
            )
        )

        self.assertIsNotNone(
            generation
        )
        self.assertEqual(
            generation.status,
            GenerationStatus.SKIPPED,
        )
        self.assertIsNone(
            generation.work_order
        )

    def test_duplicate_open_order_allowed(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
            allow_duplicate_open_orders=True,
        )

        existing_order = self.create_work_order(
            project=plan.project,
            asset=plan.asset,
            location=plan.location,
            status=WorkOrderStatus.OPEN,
        )

        generation = (
            PreventiveMaintenanceService
            .generate_plan_work_order(
                plan_id=plan.id,
                generated_by=self.user,
                force=True,
            )
        )

        self.assertEqual(
            generation.status,
            GenerationStatus.GENERATED,
        )
        self.assertNotEqual(
            generation.work_order_id,
            existing_order.id,
        )


class PreventiveMaintenanceRouterTests(
    SimpleTestCase
):
    def test_router_type(self):
        self.assertIsInstance(
            router,
            DefaultRouter,
        )

    def test_plan_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "plans"
        )

        self.assertIs(
            registration[1],
            PreventiveMaintenancePlanViewSet,
        )
        self.assertEqual(
            registration[2],
            "preventive-maintenance-plan",
        )

    def test_task_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "tasks"
        )

        self.assertIs(
            registration[1],
            PreventiveMaintenanceTaskViewSet,
        )
        self.assertEqual(
            registration[2],
            "preventive-maintenance-task",
        )

    def test_generation_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "generations"
        )

        self.assertIs(
            registration[1],
            PreventiveMaintenanceGenerationViewSet,
        )
        self.assertEqual(
            registration[2],
            "preventive-maintenance-generation",
        )

    def test_task_result_registration(self):
        registration = next(
            item
            for item in router.registry
            if item[0] == "task-results"
        )

        self.assertIs(
            registration[1],
            PreventiveMaintenanceTaskResultViewSet,
        )
        self.assertEqual(
            registration[2],
            "preventive-maintenance-task-result",
        )


class PreventiveMaintenanceURLTests(
    SimpleTestCase
):
    def test_plan_list_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-list"
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "preventive-maintenance-plan-list",
        )
        self.assertIs(
            match.func.cls,
            PreventiveMaintenancePlanViewSet,
        )

    def test_plan_activate_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-activate",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "preventive-maintenance-plan-activate",
        )

    def test_plan_suspend_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-suspend",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "preventive-maintenance-plan-suspend",
        )

    def test_plan_complete_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-complete",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "preventive-maintenance-plan-complete",
        )

    def test_plan_cancel_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-cancel",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "preventive-maintenance-plan-cancel",
        )

    def test_generate_work_order_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-"
            "generate-work-order",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            (
                "preventive-maintenance-plan-"
                "generate-work-order"
            ),
        )

    def test_plan_generations_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-plan-generations",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            "preventive-maintenance-plan-generations",
        )

    def test_generation_task_results_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-generation-"
            "task-results",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            (
                "preventive-maintenance-generation-"
                "task-results"
            ),
        )

    def test_task_result_complete_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-task-result-"
            "complete",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            (
                "preventive-maintenance-task-result-"
                "complete"
            ),
        )

    def test_task_result_reopen_url(self):
        url = reverse(
            "preventive_maintenance:"
            "preventive-maintenance-task-result-"
            "reopen",
            kwargs={
                "pk": 1,
            },
        )

        match = resolve(url)

        self.assertEqual(
            match.url_name,
            (
                "preventive-maintenance-task-result-"
                "reopen"
            ),
        )


class PreventiveMaintenancePlanAPITests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def setUp(self):
        self.factory = APIRequestFactory()

    def execute_view(
        self,
        *,
        method,
        action_map,
        user=None,
        pk=None,
        data=None,
        query_string="",
    ):
        path = "/api/preventive-maintenance/plans/"

        if pk is not None:
            path += f"{pk}/"

        if query_string:
            path += f"?{query_string}"

        request_method = getattr(
            self.factory,
            method.lower(),
        )

        request = request_method(
            path,
            data=data or {},
            format="json",
        )

        if user is not None:
            force_authenticate(
                request,
                user=user,
            )

        view = (
            PreventiveMaintenancePlanViewSet
            .as_view(action_map)
        )

        kwargs = {}

        if pk is not None:
            kwargs["pk"] = pk

        return view(
            request,
            **kwargs,
        )

    def test_list_requires_authentication(self):
        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_authenticated_user_can_list(self):
        plan = self.create_plan()

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertIn(
            plan.id,
            response_ids,
        )

    def test_list_uses_list_serializer(self):
        view = PreventiveMaintenancePlanViewSet()
        view.action = "list"

        self.assertIs(
            view.get_serializer_class(),
            PreventiveMaintenancePlanListSerializer,
        )

    def test_retrieve_uses_detail_serializer(self):
        view = PreventiveMaintenancePlanViewSet()
        view.action = "retrieve"

        self.assertIs(
            view.get_serializer_class(),
            PreventiveMaintenancePlanDetailSerializer,
        )

    def test_filter_by_project(self):
        expected_plan = self.create_plan(
            plan_number="PM-FILTER-001",
        )

        self.create_plan(
            project=self.other_project,
            asset=self.other_asset,
            location=self.other_location,
            created_by=self.other_user,
            supervisor=None,
            plan_number="PM-FILTER-002",
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                f"project={self.project.id}"
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                expected_plan.id,
            },
        )

    def test_filter_by_asset(self):
        expected_plan = self.create_plan(
            plan_number="PM-ASSET-FILTER",
        )

        self.create_plan(
            project=self.other_project,
            asset=self.other_asset,
            location=self.other_location,
            created_by=self.other_user,
            supervisor=None,
            plan_number="PM-OTHER-ASSET",
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                f"asset={self.asset.id}"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                expected_plan.id,
            },
        )

    def test_filter_by_status(self):
        active_plan = self.create_plan(
            plan_number="PM-ACTIVE-FILTER",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        self.create_plan(
            plan_number="PM-DRAFT-FILTER",
            status=PreventiveMaintenanceStatus.DRAFT,
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                "status=active"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                active_plan.id,
            },
        )

    def test_filter_by_frequency(self):
        weekly_plan = self.create_plan(
            plan_number="PM-WEEKLY-FILTER",
            frequency=ScheduleFrequency.WEEKLY,
        )

        self.create_plan(
            plan_number="PM-MONTHLY-FILTER",
            frequency=ScheduleFrequency.MONTHLY,
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                "frequency=weekly"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                weekly_plan.id,
            },
        )

    def test_filter_by_active_boolean(self):
        active_plan = self.create_plan(
            plan_number="PM-IS-ACTIVE",
            is_active=True,
        )

        self.create_plan(
            plan_number="PM-IS-INACTIVE",
            is_active=False,
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                "is_active=true"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertIn(
            active_plan.id,
            response_ids,
        )

    def test_invalid_boolean_filter(self):
        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                "is_active=invalid"
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_search_by_plan_number(self):
        expected_plan = self.create_plan(
            plan_number="PM-SEARCH-999",
        )

        self.create_plan(
            plan_number="PM-NORMAL-001",
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "list",
            },
            user=self.superuser,
            query_string=(
                "search=SEARCH-999"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                expected_plan.id,
            },
        )

    def test_activate_plan(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.DRAFT,
            next_due_date=None,
        )

        response = self.execute_view(
            method="post",
            action_map={
                "post": "activate",
            },
            user=self.superuser,
            pk=plan.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.ACTIVE,
        )
        self.assertEqual(
            plan.next_due_date,
            plan.start_date,
        )

    def test_cannot_activate_system_inactive_plan(
        self,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.DRAFT,
            is_active=False,
        )

        response = self.execute_view(
            method="post",
            action_map={
                "post": "activate",
            },
            user=self.superuser,
            pk=plan.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_suspend_plan(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        response = self.execute_view(
            method="post",
            action_map={
                "post": "suspend",
            },
            user=self.superuser,
            pk=plan.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.SUSPENDED,
        )

    def test_complete_plan(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        response = self.execute_view(
            method="post",
            action_map={
                "post": "complete",
            },
            user=self.superuser,
            pk=plan.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.COMPLETED,
        )

    def test_cancel_plan(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        response = self.execute_view(
            method="post",
            action_map={
                "post": "cancel",
            },
            user=self.superuser,
            pk=plan.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        plan.refresh_from_db()

        self.assertEqual(
            plan.status,
            PreventiveMaintenanceStatus.CANCELLED,
        )

    @patch.object(
        PreventiveMaintenanceService,
        "generate_plan_work_order",
    )
    def test_generate_work_order_action(
        self,
        generate_mock,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        generation = self.create_generation(
            plan=plan,
        )

        generate_mock.return_value = generation

        response = self.execute_view(
            method="post",
            action_map={
                "post": "generate_work_order",
            },
            user=self.superuser,
            pk=plan.id,
            data={
                "force": True,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        generate_mock.assert_called_once_with(
            plan_id=plan.id,
            generated_by=self.superuser,
            force=True,
        )

    @patch.object(
        PreventiveMaintenanceService,
        "generate_plan_work_order",
    )
    def test_generate_action_returns_conflict_when_not_due(
        self,
        generate_mock,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=30)
            ),
        )

        generate_mock.return_value = None

        response = self.execute_view(
            method="post",
            action_map={
                "post": "generate_work_order",
            },
            user=self.superuser,
            pk=plan.id,
            data={
                "force": False,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    @patch.object(
        PreventiveMaintenanceService,
        "generate_plan_work_order",
    )
    def test_generate_action_handles_service_error(
        self,
        generate_mock,
    ):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )

        generate_mock.side_effect = (
            PreventiveMaintenanceGenerationError(
                "Generation failed"
            )
        )

        response = self.execute_view(
            method="post",
            action_map={
                "post": "generate_work_order",
            },
            user=self.superuser,
            pk=plan.id,
            data={
                "force": True,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_plan_generations_action(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        generation = self.create_generation(
            plan=plan,
        )

        response = self.execute_view(
            method="get",
            action_map={
                "get": "generations",
            },
            user=self.superuser,
            pk=plan.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertIn(
            generation.id,
            response_ids,
        )


class PreventiveMaintenanceTaskAPITests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def setUp(self):
        self.factory = APIRequestFactory()

    def execute_list(
        self,
        *,
        user=None,
        query_string="",
    ):
        path = "/api/preventive-maintenance/tasks/"

        if query_string:
            path += f"?{query_string}"

        request = self.factory.get(path)

        if user is not None:
            force_authenticate(
                request,
                user=user,
            )

        view = (
            PreventiveMaintenanceTaskViewSet
            .as_view(
                {
                    "get": "list",
                }
            )
        )

        return view(request)

    def test_task_list_requires_authentication(self):
        response = self.execute_list()

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_filter_tasks_by_plan(self):
        first_plan = self.create_plan(
            plan_number="PM-TASK-FILTER-1",
        )
        second_plan = self.create_plan(
            plan_number="PM-TASK-FILTER-2",
        )

        expected_task = self.create_task(
            plan=first_plan,
            sequence=1,
        )

        self.create_task(
            plan=second_plan,
            sequence=1,
        )

        response = self.execute_list(
            user=self.superuser,
            query_string=(
                f"plan={first_plan.id}"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                expected_task.id,
            },
        )

    def test_filter_tasks_by_measurement_requirement(
        self,
    ):
        plan = self.create_plan()

        measurement_task = self.create_task(
            plan=plan,
            sequence=1,
            requires_measurement=True,
            measurement_unit="bar",
        )

        self.create_task(
            plan=plan,
            sequence=2,
            requires_measurement=False,
        )

        response = self.execute_list(
            user=self.superuser,
            query_string=(
                "requires_measurement=true"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                measurement_task.id,
            },
        )


class PreventiveMaintenanceGenerationAPITests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def setUp(self):
        self.factory = APIRequestFactory()

    def execute_view(
        self,
        *,
        action,
        user=None,
        pk=None,
        query_string="",
    ):
        path = (
            "/api/preventive-maintenance/generations/"
        )

        if pk is not None:
            path += f"{pk}/"

        if query_string:
            path += f"?{query_string}"

        request = self.factory.get(path)

        if user is not None:
            force_authenticate(
                request,
                user=user,
            )

        view = (
            PreventiveMaintenanceGenerationViewSet
            .as_view(
                {
                    "get": action,
                }
            )
        )

        kwargs = {}

        if pk is not None:
            kwargs["pk"] = pk

        return view(
            request,
            **kwargs,
        )

    def test_generation_viewset_is_read_only(self):
        self.assertTrue(
            issubclass(
                PreventiveMaintenanceGenerationViewSet,
                viewsets.ReadOnlyModelViewSet,
            )
        )

    def test_filter_generations_by_plan(self):
        first_plan = self.create_plan(
            plan_number="PM-GEN-FILTER-1",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        second_plan = self.create_plan(
            plan_number="PM-GEN-FILTER-2",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=1)
            ),
        )

        expected_generation = self.create_generation(
            plan=first_plan,
        )

        self.create_generation(
            plan=second_plan,
        )

        response = self.execute_view(
            action="list",
            user=self.superuser,
            query_string=(
                f"plan={first_plan.id}"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                expected_generation.id,
            },
        )

    def test_filter_generations_by_status(self):
        first_plan = self.create_plan(
            plan_number="PM-GEN-STATUS-1",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        second_plan = self.create_plan(
            plan_number="PM-GEN-STATUS-2",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=1)
            ),
        )

        failed_generation = self.create_generation(
            plan=first_plan,
            status=GenerationStatus.FAILED,
            error_message="Failure",
        )

        self.create_generation(
            plan=second_plan,
            status=GenerationStatus.PENDING,
        )

        response = self.execute_view(
            action="list",
            user=self.superuser,
            query_string=(
                "status=failed"
            ),
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                failed_generation.id,
            },
        )

    def test_task_results_action(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        response = self.execute_view(
            action="task_results",
            user=self.superuser,
            pk=generation.id,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                result.id,
            },
        )


class PreventiveMaintenanceTaskResultAPITests(
    PreventiveMaintenanceTestDataMixin,
    TestCase,
):
    def setUp(self):
        self.factory = APIRequestFactory()

    def execute_action(
        self,
        *,
        action,
        task_result,
        user=None,
        data=None,
    ):
        request = self.factory.post(
            (
                "/api/preventive-maintenance/"
                f"task-results/{task_result.id}/"
                f"{action}/"
            ),
            data=data or {},
            format="json",
        )

        if user is not None:
            force_authenticate(
                request,
                user=user,
            )

        view = (
            PreventiveMaintenanceTaskResultViewSet
            .as_view(
                {
                    "post": action,
                }
            )
        )

        return view(
            request,
            pk=task_result.id,
        )

    def test_http_methods_include_post(self):
        self.assertIn(
            "post",
            PreventiveMaintenanceTaskResultViewSet
            .http_method_names,
        )

    def test_complete_result_without_measurement(self):
        result = self.create_task_result()

        response = self.execute_action(
            action="complete",
            task_result=result,
            user=self.superuser,
            data={
                "result_notes": "Completed",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        result.refresh_from_db()

        self.assertTrue(
            result.is_completed
        )
        self.assertEqual(
            result.completed_by,
            self.superuser,
        )
        self.assertEqual(
            result.result_notes,
            "Completed",
        )

    def test_measurement_result_requires_value(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        response = self.execute_action(
            action="complete",
            task_result=result,
            user=self.superuser,
            data={
                "result_notes": "Missing value",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        result.refresh_from_db()

        self.assertFalse(
            result.is_completed
        )

    def test_complete_measurement_result(self):
        plan = self.create_plan(
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        task = self.create_task(
            plan=plan,
            requires_measurement=True,
            measurement_unit="bar",
            minimum_acceptable_value=Decimal("4.00"),
            maximum_acceptable_value=Decimal("6.00"),
        )
        generation = self.create_generation(
            plan=plan,
        )
        result = self.create_task_result(
            generation=generation,
            task=task,
        )

        response = self.execute_action(
            action="complete",
            task_result=result,
            user=self.superuser,
            data={
                "measured_value": "5.00",
                "result_notes": "Normal pressure",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        result.refresh_from_db()

        self.assertTrue(
            result.is_completed
        )
        self.assertEqual(
            result.measured_value,
            Decimal("5.0000"),
        )
        self.assertTrue(
            result.result_is_acceptable
        )

    def test_reopen_result(self):
        result = self.create_task_result()

        result.mark_completed(
            user=self.superuser,
            notes="Completed",
        )

        response = self.execute_action(
            action="reopen",
            task_result=result,
            user=self.superuser,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        result.refresh_from_db()

        self.assertFalse(
            result.is_completed
        )
        self.assertIsNone(
            result.completed_at
        )
        self.assertIsNone(
            result.completed_by
        )
        self.assertIsNone(
            result.result_is_acceptable
        )

    def test_complete_requires_authentication(self):
        result = self.create_task_result()

        response = self.execute_action(
            action="complete",
            task_result=result,
            data={
                "result_notes": "Completed",
            },
        )

        self.assertIn(
            response.status_code,
            {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            },
        )

    def test_filter_results_by_generation(self):
        first_plan = self.create_plan(
            plan_number="PM-RESULT-FILTER-1",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=timezone.localdate(),
        )
        second_plan = self.create_plan(
            plan_number="PM-RESULT-FILTER-2",
            status=PreventiveMaintenanceStatus.ACTIVE,
            next_due_date=(
                timezone.localdate()
                + timedelta(days=1)
            ),
        )

        first_task = self.create_task(
            plan=first_plan,
        )
        second_task = self.create_task(
            plan=second_plan,
        )

        first_generation = self.create_generation(
            plan=first_plan,
        )
        second_generation = self.create_generation(
            plan=second_plan,
        )

        expected_result = self.create_task_result(
            generation=first_generation,
            task=first_task,
        )

        self.create_task_result(
            generation=second_generation,
            task=second_task,
        )

        request = self.factory.get(
            (
                "/api/preventive-maintenance/"
                "task-results/"
                f"?generation={first_generation.id}"
            )
        )

        force_authenticate(
            request,
            user=self.superuser,
        )

        view = (
            PreventiveMaintenanceTaskResultViewSet
            .as_view(
                {
                    "get": "list",
                }
            )
        )

        response = view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        response_ids = {
            item["id"]
            for item in response.data
        }

        self.assertEqual(
            response_ids,
            {
                expected_result.id,
            },
        )
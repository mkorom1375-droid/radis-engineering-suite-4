
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from work_orders.models import (
    WorkOrder,
    WorkOrderSource,
    WorkOrderStatus,
)

from .models import (
    GenerationStatus,
    PreventiveMaintenanceGeneration,
    PreventiveMaintenancePlan,
    PreventiveMaintenanceStatus,
    PreventiveMaintenanceTaskResult,
)


class PreventiveMaintenanceGenerationError(Exception):
    """Raised when a PM work order cannot be generated."""


class PreventiveMaintenanceService:
    """
    Service responsible for generating work orders from preventive
    maintenance plans.
    """

    OPEN_WORK_ORDER_STATUSES = {
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.OPEN,
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.ON_HOLD,
    }

    @classmethod
    def generate_due_work_orders(
        cls,
        generated_by=None,
        generation_date=None,
    ):
        generation_date = (
            generation_date
            or timezone.localdate()
        )

        plan_ids = list(
            PreventiveMaintenancePlan.objects.filter(
                status=PreventiveMaintenanceStatus.ACTIVE,
                is_active=True,
                auto_generate_work_order=True,
                next_due_date__isnull=False,
            )
            .order_by(
                "next_due_date",
                "id",
            )
            .values_list(
                "id",
                flat=True,
            )
        )

        results = {
            "generated": [],
            "skipped": [],
            "failed": [],
            "not_due": [],
        }

        for plan_id in plan_ids:
            try:
                generation = cls.generate_plan_work_order(
                    plan_id=plan_id,
                    generated_by=generated_by,
                    generation_date=generation_date,
                )

                if generation is None:
                    results["not_due"].append(plan_id)
                    continue

                if generation.status == GenerationStatus.GENERATED:
                    results["generated"].append(generation)

                elif generation.status == GenerationStatus.SKIPPED:
                    results["skipped"].append(generation)

                elif generation.status == GenerationStatus.FAILED:
                    results["failed"].append(generation)

            except Exception as exc:
                results["failed"].append(
                    {
                        "plan_id": plan_id,
                        "error": str(exc),
                    }
                )

        return results

    @classmethod
    @transaction.atomic
    def generate_plan_work_order(
        cls,
        plan_id,
        generated_by=None,
        generation_date=None,
        force=False,
    ):
        generation_date = (
            generation_date
            or timezone.localdate()
        )

        try:
            plan = (
                PreventiveMaintenancePlan.objects
                .select_for_update()
                .select_related(
                    "project",
                    "asset",
                    "location",
                    "supervisor",
                    "created_by",
                )
                .get(pk=plan_id)
            )
        except PreventiveMaintenancePlan.DoesNotExist as exc:
            raise PreventiveMaintenanceGenerationError(
                "برنامه نگهداری پیشگیرانه یافت نشد."
            ) from exc

        scheduled_generation_date = (
            plan.next_due_date
            - timedelta(
                days=plan.generation_lead_days,
            )
            if plan.next_due_date
            else None
        )

        if (
            not force
            and scheduled_generation_date
            and scheduled_generation_date > generation_date
        ):
            return None

        cls._validate_plan_for_generation(
            plan=plan,
            generation_date=generation_date,
            force=force,
        )

        due_date = plan.next_due_date

        generation, _ = (
            PreventiveMaintenanceGeneration.objects
            .select_for_update()
            .get_or_create(
                plan=plan,
                due_date=due_date,
                defaults={
                    "scheduled_generation_date": (
                        scheduled_generation_date
                    ),
                    "status": GenerationStatus.PENDING,
                },
            )
        )

        if generation.status == GenerationStatus.GENERATED:
            return generation

        if generation.work_order_id:
            generation.status = GenerationStatus.GENERATED
            generation.generated_at = (
                generation.generated_at
                or timezone.now()
            )
            generation.error_message = ""

            generation.save(
                update_fields=[
                    "status",
                    "generated_at",
                    "error_message",
                    "updated_at",
                ]
            )

            return generation

        creator = (
            generated_by
            or plan.created_by
        )

        if creator is None:
            generation.mark_failed(
                "کاربر ایجادکننده دستورکار مشخص نیست."
            )
            return generation

        existing_open_work_order = (
            cls._find_existing_open_work_order(
                plan=plan,
            )
        )

        if (
            existing_open_work_order
            and not plan.allow_duplicate_open_orders
        ):
            generation.mark_skipped(
                notes=(
                    "به دلیل وجود دستورکار باز برای این برنامه، "
                    "دستورکار جدید تولید نشد. شماره دستورکار موجود: "
                    f"{existing_open_work_order.work_order_number}"
                )
            )

            plan.advance_schedule()

            return generation

        try:
            work_order = cls._create_work_order(
                plan=plan,
                generation=generation,
                creator=creator,
            )

            generation.mark_generated(
                work_order=work_order,
                generated_by=generated_by,
            )

            cls._create_task_results(
                plan=plan,
                generation=generation,
            )

            plan.advance_schedule()

            return generation

        except Exception as exc:
            generation.mark_failed(exc)
            raise

    @classmethod
    def _validate_plan_for_generation(
        cls,
        plan,
        generation_date,
        force=False,
    ):
        if not plan.is_active:
            raise PreventiveMaintenanceGenerationError(
                "برنامه نگهداری غیرفعال است."
            )

        if plan.status != PreventiveMaintenanceStatus.ACTIVE:
            raise PreventiveMaintenanceGenerationError(
                "وضعیت برنامه نگهداری فعال نیست."
            )

        if (
            not force
            and not plan.auto_generate_work_order
        ):
            raise PreventiveMaintenanceGenerationError(
                "تولید خودکار دستورکار غیرفعال است."
            )

        if not plan.next_due_date:
            raise PreventiveMaintenanceGenerationError(
                "تاریخ سررسید بعدی مشخص نشده است."
            )

        if (
            plan.end_date
            and plan.next_due_date > plan.end_date
        ):
            plan.status = PreventiveMaintenanceStatus.COMPLETED

            plan.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            raise PreventiveMaintenanceGenerationError(
                "تاریخ سررسید از تاریخ پایان برنامه عبور کرده است."
            )

        scheduled_generation_date = (
            plan.next_due_date
            - timedelta(
                days=plan.generation_lead_days,
            )
        )

        if (
            not force
            and scheduled_generation_date > generation_date
        ):
            raise PreventiveMaintenanceGenerationError(
                "هنوز زمان تولید دستورکار فرا نرسیده است."
            )

    @classmethod
    def _find_existing_open_work_order(
        cls,
        plan,
    ):
        queryset = WorkOrder.objects.filter(
            project=plan.project,
            asset=plan.asset,
            source=WorkOrderSource.PREVENTIVE_MAINTENANCE,
            status__in=cls.OPEN_WORK_ORDER_STATUSES,
            is_active=True,
        )

        if plan.location_id:
            queryset = queryset.filter(
                location_id=plan.location_id,
            )

        return (
            queryset
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

    @classmethod
    def _create_work_order(
        cls,
        plan,
        generation,
        creator,
    ):
        planned_start = cls._combine_date_and_time(
            generation.due_date,
            time.min,
        )

        duration_hours = (
            plan.estimated_duration_hours
            or Decimal("0.00")
        )

        planned_finish = (
            planned_start
            + timedelta(
                seconds=(
                    float(duration_hours)
                    * 3600
                ),
            )
        )

        work_order_number = (
            cls._generate_work_order_number(
                plan=plan,
                generation=generation,
            )
        )

        work_order = WorkOrder(
            project=plan.project,
            asset=plan.asset,
            location=plan.location,
            work_order_number=work_order_number,
            title=plan.title.strip(),
            description=cls._build_work_order_description(
                plan=plan,
            ),
            maintenance_type=plan.maintenance_type,
            priority=plan.priority,
            status=WorkOrderStatus.OPEN,
            source=WorkOrderSource.PREVENTIVE_MAINTENANCE,
            created_by=creator,
            supervisor=plan.supervisor,
            planned_start=planned_start,
            planned_finish=planned_finish,
            estimated_labor_hours=(
                plan.estimated_labor_hours
            ),
            estimated_cost=plan.estimated_cost,
            production_stopped=(
                plan.production_stop_required
            ),
            permit_required=plan.permit_required,
            lockout_tagout_required=(
                plan.lockout_tagout_required
            ),
            safety_notes=(
                plan.safety_instructions.strip()
            ),
            is_active=True,
        )

        try:
            work_order.save()
        except IntegrityError as exc:
            raise PreventiveMaintenanceGenerationError(
                "شماره دستورکار تکراری است یا ایجاد دستورکار "
                "با محدودیت پایگاه داده مواجه شد."
            ) from exc

        return work_order

    @classmethod
    def _generate_work_order_number(
        cls,
        plan,
        generation,
    ):
        """
        Example:
            WO-PM-2026-000001

        Generation primary key makes the number deterministic.
        In case an imported work order already has the same number,
        an incremental suffix is added.
        """

        year = generation.due_date.year

        base_number = (
            f"WO-PM-{year}-"
            f"{generation.pk:06d}"
        )

        if not WorkOrder.objects.filter(
            project=plan.project,
            work_order_number=base_number,
        ).exists():
            return base_number

        suffix = 2

        while True:
            candidate = (
                f"{base_number}-{suffix:02d}"
            )

            if not WorkOrder.objects.filter(
                project=plan.project,
                work_order_number=candidate,
            ).exists():
                return candidate

            suffix += 1

    @staticmethod
    def _create_task_results(
        plan,
        generation,
    ):
        active_tasks = list(
            plan.tasks.filter(
                is_active=True,
            ).order_by(
                "sequence",
                "id",
            )
        )

        existing_task_ids = set(
            generation.task_results.values_list(
                "task_id",
                flat=True,
            )
        )

        task_results = [
            PreventiveMaintenanceTaskResult(
                generation=generation,
                task=task,
            )
            for task in active_tasks
            if task.id not in existing_task_ids
        ]

        if task_results:
            PreventiveMaintenanceTaskResult.objects.bulk_create(
                task_results,
                ignore_conflicts=True,
            )

    @staticmethod
    def _combine_date_and_time(
        target_date,
        target_time,
    ):
        value = datetime.combine(
            target_date,
            target_time,
        )

        if timezone.is_aware(value):
            return value

        return timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    @staticmethod
    def _build_work_order_description(plan):
        sections = []

        description = plan.description.strip()

        if description:
            sections.append(description)

        active_tasks = plan.tasks.filter(
            is_active=True,
        ).order_by(
            "sequence",
            "id",
        )

        task_lines = []

        for task in active_tasks:
            task_lines.append(
                f"{task.sequence}. {task.title.strip()}"
            )

            task_description = task.description.strip()

            if task_description:
                task_lines.append(
                    f"   شرح: {task_description}"
                )

            acceptance_criteria = (
                task.acceptance_criteria.strip()
            )

            if acceptance_criteria:
                task_lines.append(
                    "   معیار پذیرش: "
                    f"{acceptance_criteria}"
                )

            if task.estimated_duration_minutes:
                task_lines.append(
                    "   مدت تخمینی: "
                    f"{task.estimated_duration_minutes} دقیقه"
                )

        if task_lines:
            sections.append(
                "فعالیت‌های برنامه‌ریزی‌شده:\n"
                + "\n".join(task_lines)
            )

        required_tools = plan.required_tools.strip()

        if required_tools:
            sections.append(
                "ابزارهای موردنیاز:\n"
                f"{required_tools}"
            )

        required_materials = (
            plan.required_materials.strip()
        )

        if required_materials:
            sections.append(
                "مواد و قطعات موردنیاز:\n"
                f"{required_materials}"
            )

        safety_instructions = (
            plan.safety_instructions.strip()
        )

        if safety_instructions:
            sections.append(
                "دستورالعمل‌های ایمنی:\n"
                f"{safety_instructions}"
            )

        if not sections:
            sections.append(
                "این دستورکار به‌صورت خودکار از برنامه "
                "نگهداری پیشگیرانه تولید شده است."
            )

        return "\n\n".join(sections)

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from work_orders.models import (
    WorkOrder,
    WorkOrderSource,
    WorkOrderStatus,
)

from .models import (
    GenerationStatus,
    PreventiveMaintenanceGeneration,
    PreventiveMaintenancePlan,
    PreventiveMaintenanceStatus,
    PreventiveMaintenanceTaskResult,
)


class PreventiveMaintenanceGenerationError(Exception):
    """Raised when a PM work order cannot be generated."""


class PreventiveMaintenanceService:
    """
    Service responsible for generating work orders from preventive
    maintenance plans.
    """

    OPEN_WORK_ORDER_STATUSES = {
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.OPEN,
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.ON_HOLD,
    }

    @classmethod
    def generate_due_work_orders(
        cls,
        generated_by=None,
        generation_date=None,
    ):
        generation_date = (
            generation_date
            or timezone.localdate()
        )

        plan_ids = list(
            PreventiveMaintenancePlan.objects.filter(
                status=PreventiveMaintenanceStatus.ACTIVE,
                is_active=True,
                auto_generate_work_order=True,
                next_due_date__isnull=False,
            )
            .order_by(
                "next_due_date",
                "id",
            )
            .values_list(
                "id",
                flat=True,
            )
        )

        results = {
            "generated": [],
            "skipped": [],
            "failed": [],
            "not_due": [],
        }

        for plan_id in plan_ids:
            try:
                generation = cls.generate_plan_work_order(
                    plan_id=plan_id,
                    generated_by=generated_by,
                    generation_date=generation_date,
                )

                if generation is None:
                    results["not_due"].append(plan_id)
                    continue

                if generation.status == GenerationStatus.GENERATED:
                    results["generated"].append(generation)

                elif generation.status == GenerationStatus.SKIPPED:
                    results["skipped"].append(generation)

                elif generation.status == GenerationStatus.FAILED:
                    results["failed"].append(generation)

            except Exception as exc:
                results["failed"].append(
                    {
                        "plan_id": plan_id,
                        "error": str(exc),
                    }
                )

        return results

    @classmethod
    @transaction.atomic
    def generate_plan_work_order(
        cls,
        plan_id,
        generated_by=None,
        generation_date=None,
        force=False,
    ):
        generation_date = (
            generation_date
            or timezone.localdate()
        )

        try:
            plan = (
                PreventiveMaintenancePlan.objects
                .select_for_update()
                .select_related(
                    "project",
                    "asset",
                    "location",
                    "supervisor",
                    "created_by",
                )
                .get(pk=plan_id)
            )
        except PreventiveMaintenancePlan.DoesNotExist as exc:
            raise PreventiveMaintenanceGenerationError(
                "برنامه نگهداری پیشگیرانه یافت نشد."
            ) from exc

        scheduled_generation_date = (
            plan.next_due_date
            - timedelta(
                days=plan.generation_lead_days,
            )
            if plan.next_due_date
            else None
        )

        if (
            not force
            and scheduled_generation_date
            and scheduled_generation_date > generation_date
        ):
            return None

        cls._validate_plan_for_generation(
            plan=plan,
            generation_date=generation_date,
            force=force,
        )

        due_date = plan.next_due_date

        generation, _ = (
            PreventiveMaintenanceGeneration.objects
            .select_for_update()
            .get_or_create(
                plan=plan,
                due_date=due_date,
                defaults={
                    "scheduled_generation_date": (
                        scheduled_generation_date
                    ),
                    "status": GenerationStatus.PENDING,
                },
            )
        )

        if generation.status == GenerationStatus.GENERATED:
            return generation

        if generation.work_order_id:
            generation.status = GenerationStatus.GENERATED
            generation.generated_at = (
                generation.generated_at
                or timezone.now()
            )
            generation.error_message = ""

            generation.save(
                update_fields=[
                    "status",
                    "generated_at",
                    "error_message",
                    "updated_at",
                ]
            )

            return generation

        creator = (
            generated_by
            or plan.created_by
        )

        if creator is None:
            generation.mark_failed(
                "کاربر ایجادکننده دستورکار مشخص نیست."
            )
            return generation

        existing_open_work_order = (
            cls._find_existing_open_work_order(
                plan=plan,
            )
        )

        if (
            existing_open_work_order
            and not plan.allow_duplicate_open_orders
        ):
            generation.mark_skipped(
                notes=(
                    "به دلیل وجود دستورکار باز برای این برنامه، "
                    "دستورکار جدید تولید نشد. شماره دستورکار موجود: "
                    f"{existing_open_work_order.work_order_number}"
                )
            )

            plan.advance_schedule()

            return generation

        try:
            work_order = cls._create_work_order(
                plan=plan,
                generation=generation,
                creator=creator,
            )

            generation.mark_generated(
                work_order=work_order,
                generated_by=generated_by,
            )

            cls._create_task_results(
                plan=plan,
                generation=generation,
            )

            plan.advance_schedule()

            return generation

        except Exception as exc:
            generation.mark_failed(exc)
            raise

    @classmethod
    def _validate_plan_for_generation(
        cls,
        plan,
        generation_date,
        force=False,
    ):
        if not plan.is_active:
            raise PreventiveMaintenanceGenerationError(
                "برنامه نگهداری غیرفعال است."
            )

        if plan.status != PreventiveMaintenanceStatus.ACTIVE:
            raise PreventiveMaintenanceGenerationError(
                "وضعیت برنامه نگهداری فعال نیست."
            )

        if (
            not force
            and not plan.auto_generate_work_order
        ):
            raise PreventiveMaintenanceGenerationError(
                "تولید خودکار دستورکار غیرفعال است."
            )

        if not plan.next_due_date:
            raise PreventiveMaintenanceGenerationError(
                "تاریخ سررسید بعدی مشخص نشده است."
            )

        if (
            plan.end_date
            and plan.next_due_date > plan.end_date
        ):
            plan.status = PreventiveMaintenanceStatus.COMPLETED

            plan.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            raise PreventiveMaintenanceGenerationError(
                "تاریخ سررسید از تاریخ پایان برنامه عبور کرده است."
            )

        scheduled_generation_date = (
            plan.next_due_date
            - timedelta(
                days=plan.generation_lead_days,
            )
        )

        if (
            not force
            and scheduled_generation_date > generation_date
        ):
            raise PreventiveMaintenanceGenerationError(
                "هنوز زمان تولید دستورکار فرا نرسیده است."
            )

    @classmethod
    def _find_existing_open_work_order(
        cls,
        plan,
    ):
        queryset = WorkOrder.objects.filter(
            project=plan.project,
            asset=plan.asset,
            source=WorkOrderSource.PREVENTIVE_MAINTENANCE,
            status__in=cls.OPEN_WORK_ORDER_STATUSES,
            is_active=True,
        )

        if plan.location_id:
            queryset = queryset.filter(
                location_id=plan.location_id,
            )

        return (
            queryset
            .order_by(
                "-created_at",
                "-id",
            )
            .first()
        )

    @classmethod
    def _create_work_order(
        cls,
        plan,
        generation,
        creator,
    ):
        planned_start = cls._combine_date_and_time(
            generation.due_date,
            time.min,
        )

        duration_hours = (
            plan.estimated_duration_hours
            or Decimal("0.00")
        )

        planned_finish = (
            planned_start
            + timedelta(
                seconds=(
                    float(duration_hours)
                    * 3600
                ),
            )
        )

        work_order_number = (
            cls._generate_work_order_number(
                plan=plan,
                generation=generation,
            )
        )

        work_order = WorkOrder(
            project=plan.project,
            asset=plan.asset,
            location=plan.location,
            work_order_number=work_order_number,
            title=plan.title.strip(),
            description=cls._build_work_order_description(
                plan=plan,
            ),
            maintenance_type=plan.maintenance_type,
            priority=plan.priority,
            status=WorkOrderStatus.OPEN,
            source=WorkOrderSource.PREVENTIVE_MAINTENANCE,
            created_by=creator,
            supervisor=plan.supervisor,
            planned_start=planned_start,
            planned_finish=planned_finish,
            estimated_labor_hours=(
                plan.estimated_labor_hours
            ),
            estimated_cost=plan.estimated_cost,
            production_stopped=(
                plan.production_stop_required
            ),
            permit_required=plan.permit_required,
            lockout_tagout_required=(
                plan.lockout_tagout_required
            ),
            safety_notes=(
                plan.safety_instructions.strip()
            ),
            is_active=True,
        )

        try:
            work_order.save()
        except IntegrityError as exc:
            raise PreventiveMaintenanceGenerationError(
                "شماره دستورکار تکراری است یا ایجاد دستورکار "
                "با محدودیت پایگاه داده مواجه شد."
            ) from exc

        return work_order

    @classmethod
    def _generate_work_order_number(
        cls,
        plan,
        generation,
    ):
        """
        Example:
            WO-PM-2026-000001

        Generation primary key makes the number deterministic.
        In case an imported work order already has the same number,
        an incremental suffix is added.
        """

        year = generation.due_date.year

        base_number = (
            f"WO-PM-{year}-"
            f"{generation.pk:06d}"
        )

        if not WorkOrder.objects.filter(
            project=plan.project,
            work_order_number=base_number,
        ).exists():
            return base_number

        suffix = 2

        while True:
            candidate = (
                f"{base_number}-{suffix:02d}"
            )

            if not WorkOrder.objects.filter(
                project=plan.project,
                work_order_number=candidate,
            ).exists():
                return candidate

            suffix += 1

    @staticmethod
    def _create_task_results(
        plan,
        generation,
    ):
        active_tasks = list(
            plan.tasks.filter(
                is_active=True,
            ).order_by(
                "sequence",
                "id",
            )
        )

        existing_task_ids = set(
            generation.task_results.values_list(
                "task_id",
                flat=True,
            )
        )

        task_results = [
            PreventiveMaintenanceTaskResult(
                generation=generation,
                task=task,
            )
            for task in active_tasks
            if task.id not in existing_task_ids
        ]

        if task_results:
            PreventiveMaintenanceTaskResult.objects.bulk_create(
                task_results,
                ignore_conflicts=True,
            )

    @staticmethod
    def _combine_date_and_time(
        target_date,
        target_time,
    ):
        value = datetime.combine(
            target_date,
            target_time,
        )

        if timezone.is_aware(value):
            return value

        return timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    @staticmethod
    def _build_work_order_description(plan):
        sections = []

        description = plan.description.strip()

        if description:
            sections.append(description)

        active_tasks = plan.tasks.filter(
            is_active=True,
        ).order_by(
            "sequence",
            "id",
        )

        task_lines = []

        for task in active_tasks:
            task_lines.append(
                f"{task.sequence}. {task.title.strip()}"
            )

            task_description = task.description.strip()

            if task_description:
                task_lines.append(
                    f"   شرح: {task_description}"
                )

            acceptance_criteria = (
                task.acceptance_criteria.strip()
            )

            if acceptance_criteria:
                task_lines.append(
                    "   معیار پذیرش: "
                    f"{acceptance_criteria}"
                )

            if task.estimated_duration_minutes:
                task_lines.append(
                    "   مدت تخمینی: "
                    f"{task.estimated_duration_minutes} دقیقه"
                )

        if task_lines:
            sections.append(
                "فعالیت‌های برنامه‌ریزی‌شده:\n"
                + "\n".join(task_lines)
            )

        required_tools = plan.required_tools.strip()

        if required_tools:
            sections.append(
                "ابزارهای موردنیاز:\n"
                f"{required_tools}"
            )

        required_materials = (
            plan.required_materials.strip()
        )

        if required_materials:
            sections.append(
                "مواد و قطعات موردنیاز:\n"
                f"{required_materials}"
            )

        safety_instructions = (
            plan.safety_instructions.strip()
        )

        if safety_instructions:
            sections.append(
                "دستورالعمل‌های ایمنی:\n"
                f"{safety_instructions}"
            )

        if not sections:
            sections.append(
                "این دستورکار به‌صورت خودکار از برنامه "
                "نگهداری پیشگیرانه تولید شده است."
            )

        return "\n\n".join(sections)
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from assets.models import Asset
from locations.models import Location
from projects.models import Project
from work_orders.models import (
    MaintenanceType,
    WorkOrder,
    WorkOrderSource,
    WorkPriority,
)


class PreventiveMaintenanceStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    ACTIVE = "active", "فعال"
    SUSPENDED = "suspended", "معلق"
    COMPLETED = "completed", "تکمیل‌شده"
    CANCELLED = "cancelled", "لغوشده"


class ScheduleFrequency(models.TextChoices):
    DAILY = "daily", "روزانه"
    WEEKLY = "weekly", "هفتگی"
    MONTHLY = "monthly", "ماهانه"
    QUARTERLY = "quarterly", "سه‌ماهه"
    SEMIANNUAL = "semiannual", "شش‌ماهه"
    ANNUAL = "annual", "سالانه"
    CUSTOM_DAYS = "custom_days", "تعداد روز سفارشی"


class GenerationStatus(models.TextChoices):
    PENDING = "pending", "در انتظار"
    GENERATED = "generated", "تولیدشده"
    SKIPPED = "skipped", "ردشده"
    FAILED = "failed", "ناموفق"


class TaskType(models.TextChoices):
    INSPECTION = "inspection", "بازرسی"
    LUBRICATION = "lubrication", "روان‌کاری"
    CLEANING = "cleaning", "تمیزکاری"
    ADJUSTMENT = "adjustment", "تنظیم"
    REPLACEMENT = "replacement", "تعویض"
    CALIBRATION = "calibration", "کالیبراسیون"
    TESTING = "testing", "آزمایش"
    MEASUREMENT = "measurement", "اندازه‌گیری"
    TIGHTENING = "tightening", "سفت‌کاری"
    GENERAL = "general", "عمومی"


class PreventiveMaintenancePlan(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="preventive_maintenance_plans",
        verbose_name="پروژه",
    )

    plan_number = models.CharField(
        max_length=50,
        verbose_name="شماره برنامه",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان برنامه",
    )

    description = models.TextField(
        blank=True,
        verbose_name="شرح برنامه",
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="preventive_maintenance_plans",
        verbose_name="تجهیز",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="preventive_maintenance_plans",
        null=True,
        blank=True,
        verbose_name="موقعیت",
    )

    status = models.CharField(
        max_length=20,
        choices=PreventiveMaintenanceStatus.choices,
        default=PreventiveMaintenanceStatus.DRAFT,
        db_index=True,
        verbose_name="وضعیت",
    )

    maintenance_type = models.CharField(
        max_length=30,
        choices=MaintenanceType.choices,
        default=MaintenanceType.PREVENTIVE,
        verbose_name="نوع نگهداری",
    )

    priority = models.CharField(
        max_length=20,
        choices=WorkPriority.choices,
        default=WorkPriority.NORMAL,
        db_index=True,
        verbose_name="اولویت",
    )

    frequency = models.CharField(
        max_length=20,
        choices=ScheduleFrequency.choices,
        default=ScheduleFrequency.MONTHLY,
        verbose_name="تناوب",
    )

    custom_interval_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
        ],
        verbose_name="فاصله سفارشی برحسب روز",
    )

    start_date = models.DateField(
        default=timezone.localdate,
        verbose_name="تاریخ شروع",
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پایان",
    )

    last_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="آخرین سررسید",
    )

    next_due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="سررسید بعدی",
    )

    generation_lead_days = models.PositiveIntegerField(
        default=7,
        verbose_name="تعداد روز تولید قبل از سررسید",
    )

    auto_generate_work_order = models.BooleanField(
        default=True,
        verbose_name="تولید خودکار دستورکار",
    )

    allow_duplicate_open_orders = models.BooleanField(
        default=False,
        verbose_name="اجازه ایجاد دستورکار باز تکراری",
    )

    estimated_duration_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="مدت تخمینی برحسب ساعت",
    )

    estimated_labor_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="ساعت کار تخمینی",
    )

    estimated_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="هزینه تخمینی",
    )

    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="supervised_preventive_maintenance_plans",
        null=True,
        blank=True,
        verbose_name="سرپرست",
    )

    safety_instructions = models.TextField(
        blank=True,
        verbose_name="دستورالعمل‌های ایمنی",
    )

    required_tools = models.TextField(
        blank=True,
        verbose_name="ابزارهای موردنیاز",
    )

    required_materials = models.TextField(
        blank=True,
        verbose_name="مواد و قطعات موردنیاز",
    )

    permit_required = models.BooleanField(
        default=False,
        verbose_name="نیازمند مجوز کار",
    )

    lockout_tagout_required = models.BooleanField(
        default=False,
        verbose_name="نیازمند قفل و برچسب‌گذاری",
    )

    production_stop_required = models.BooleanField(
        default=False,
        verbose_name="نیازمند توقف تولید",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_preventive_maintenance_plans",
        verbose_name="ایجادکننده",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="زمان ویرایش",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="فعال",
    )

    class Meta:
        verbose_name = "برنامه نگهداری پیشگیرانه"
        verbose_name_plural = "برنامه‌های نگهداری پیشگیرانه"
        ordering = [
            "next_due_date",
            "plan_number",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project",
                    "plan_number",
                ],
                name="unique_pm_plan_number_per_project",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(end_date__isnull=True)
                    | models.Q(end_date__gte=models.F("start_date"))
                ),
                name="pm_end_date_after_start_date",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    generation_lead_days__gte=0
                ),
                name="pm_generation_lead_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estimated_duration_hours__gte=0
                ),
                name="pm_duration_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estimated_labor_hours__gte=0
                ),
                name="pm_labor_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estimated_cost__gte=0
                ),
                name="pm_cost_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "project",
                    "status",
                ],
                name="pm_project_status_idx",
            ),
            models.Index(
                fields=[
                    "project",
                    "plan_number",
                ],
                name="pm_project_number_idx",
            ),
            models.Index(
                fields=[
                    "asset",
                    "status",
                ],
                name="pm_asset_status_idx",
            ),
            models.Index(
                fields=[
                    "next_due_date",
                    "status",
                ],
                name="pm_due_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.plan_number} - {self.title}"

    def clean(self):
        errors = {}

        if (
            self.frequency == ScheduleFrequency.CUSTOM_DAYS
            and not self.custom_interval_days
        ):
            errors["custom_interval_days"] = (
                "برای تناوب سفارشی، تعداد روز باید مشخص شود."
            )

        if (
            self.frequency != ScheduleFrequency.CUSTOM_DAYS
            and self.custom_interval_days
        ):
            errors["custom_interval_days"] = (
                "تعداد روز سفارشی فقط برای تناوب سفارشی مجاز است."
            )

        if self.end_date and self.end_date < self.start_date:
            errors["end_date"] = (
                "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."
            )

        if self.asset_id and self.project_id:
            asset_project_id = getattr(
                self.asset,
                "project_id",
                None,
            )

            if (
                asset_project_id is not None
                and asset_project_id != self.project_id
            ):
                errors["asset"] = (
                    "تجهیز انتخاب‌شده متعلق به این پروژه نیست."
                )

        if self.location_id and self.project_id:
            location_project_id = getattr(
                self.location,
                "project_id",
                None,
            )

            if (
                location_project_id is not None
                and location_project_id != self.project_id
            ):
                errors["location"] = (
                    "موقعیت انتخاب‌شده متعلق به این پروژه نیست."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def is_due(self):
        if not self.next_due_date:
            return False

        if self.status != PreventiveMaintenanceStatus.ACTIVE:
            return False

        return self.next_due_date <= timezone.localdate()

    @property
    def generation_date(self):
        if not self.next_due_date:
            return None

        return self.next_due_date - timedelta(
            days=self.generation_lead_days
        )

    @property
    def is_ready_for_generation(self):
        if not self.auto_generate_work_order:
            return False

        if not self.is_active:
            return False

        if self.status != PreventiveMaintenanceStatus.ACTIVE:
            return False

        if not self.next_due_date:
            return False

        if self.end_date and self.next_due_date > self.end_date:
            return False

        generation_date = self.generation_date

        return (
            generation_date is not None
            and generation_date <= timezone.localdate()
        )

    def calculate_next_due_date(
        self,
        reference_date=None,
    ):
        reference_date = (
            reference_date
            or self.last_due_date
            or self.next_due_date
            or self.start_date
        )

        if self.frequency == ScheduleFrequency.DAILY:
            return reference_date + timedelta(days=1)

        if self.frequency == ScheduleFrequency.WEEKLY:
            return reference_date + timedelta(weeks=1)

        if self.frequency == ScheduleFrequency.MONTHLY:
            return self._add_months(reference_date, 1)

        if self.frequency == ScheduleFrequency.QUARTERLY:
            return self._add_months(reference_date, 3)

        if self.frequency == ScheduleFrequency.SEMIANNUAL:
            return self._add_months(reference_date, 6)

        if self.frequency == ScheduleFrequency.ANNUAL:
            return self._add_months(reference_date, 12)

        if self.frequency == ScheduleFrequency.CUSTOM_DAYS:
            interval_days = self.custom_interval_days or 1
            return reference_date + timedelta(
                days=interval_days
            )

        return reference_date

    def initialize_next_due_date(self):
        if not self.next_due_date:
            self.next_due_date = self.start_date

        return self.next_due_date

    def advance_schedule(self):
        current_due_date = (
            self.next_due_date
            or self.start_date
        )

        self.last_due_date = current_due_date
        self.next_due_date = self.calculate_next_due_date(
            reference_date=current_due_date
        )

        if (
            self.end_date
            and self.next_due_date > self.end_date
        ):
            self.status = (
                PreventiveMaintenanceStatus.COMPLETED
            )

        self.save(
            update_fields=[
                "last_due_date",
                "next_due_date",
                "status",
                "updated_at",
            ]
        )

    @staticmethod
    def _add_months(
        source_date,
        months,
    ):
        month_index = (
            source_date.month - 1 + months
        )

        year = (
            source_date.year
            + month_index // 12
        )

        month = (
            month_index % 12
            + 1
        )

        month_days = [
            31,
            29 if PreventiveMaintenancePlan._is_leap_year(
                year
            ) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ]

        day = min(
            source_date.day,
            month_days[month - 1],
        )

        return date(
            year,
            month,
            day,
        )

    @staticmethod
    def _is_leap_year(year):
        return (
            year % 4 == 0
            and (
                year % 100 != 0
                or year % 400 == 0
            )
        )


class PreventiveMaintenanceTask(models.Model):
    plan = models.ForeignKey(
        PreventiveMaintenancePlan,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="برنامه نگهداری",
    )

    sequence = models.PositiveIntegerField(
        default=1,
        verbose_name="ترتیب",
    )

    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.GENERAL,
        verbose_name="نوع فعالیت",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان فعالیت",
    )

    description = models.TextField(
        blank=True,
        verbose_name="شرح فعالیت",
    )

    acceptance_criteria = models.TextField(
        blank=True,
        verbose_name="معیار پذیرش",
    )

    estimated_duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="مدت تخمینی برحسب دقیقه",
    )

    requires_shutdown = models.BooleanField(
        default=False,
        verbose_name="نیازمند توقف تجهیز",
    )

    requires_photo = models.BooleanField(
        default=False,
        verbose_name="نیازمند ثبت تصویر",
    )

    requires_measurement = models.BooleanField(
        default=False,
        verbose_name="نیازمند ثبت اندازه‌گیری",
    )

    measurement_unit = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="واحد اندازه‌گیری",
    )

    minimum_acceptable_value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="حداقل مقدار قابل‌قبول",
    )

    maximum_acceptable_value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="حداکثر مقدار قابل‌قبول",
    )

    is_mandatory = models.BooleanField(
        default=True,
        verbose_name="الزامی",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="فعال",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="زمان ویرایش",
    )

    class Meta:
        verbose_name = "فعالیت نگهداری پیشگیرانه"
        verbose_name_plural = "فعالیت‌های نگهداری پیشگیرانه"
        ordering = [
            "sequence",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "plan",
                    "sequence",
                ],
                name="unique_pm_task_sequence_per_plan",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    estimated_duration_minutes__gte=0
                ),
                name="pm_task_duration_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        minimum_acceptable_value__isnull=True
                    )
                    | models.Q(
                        maximum_acceptable_value__isnull=True
                    )
                    | models.Q(
                        maximum_acceptable_value__gte=models.F(
                            "minimum_acceptable_value"
                        )
                    )
                ),
                name="pm_task_max_value_gte_min_value",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "plan",
                    "sequence",
                ],
                name="pm_task_plan_seq_idx",
            ),
            models.Index(
                fields=[
                    "plan",
                    "is_active",
                ],
                name="pm_task_plan_active_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.plan.plan_number} - "
            f"{self.sequence}. {self.title}"
        )

    def clean(self):
        errors = {}

        if (
            self.minimum_acceptable_value is not None
            and self.maximum_acceptable_value is not None
            and self.maximum_acceptable_value
            < self.minimum_acceptable_value
        ):
            errors["maximum_acceptable_value"] = (
                "حداکثر مقدار نمی‌تواند کمتر از حداقل مقدار باشد."
            )

        if (
            (
                self.minimum_acceptable_value is not None
                or self.maximum_acceptable_value is not None
            )
            and not self.requires_measurement
        ):
            errors["requires_measurement"] = (
                "برای ثبت حدود پذیرش، اندازه‌گیری باید فعال باشد."
            )

        if (
            self.requires_measurement
            and not self.measurement_unit.strip()
        ):
            errors["measurement_unit"] = (
                "برای فعالیت اندازه‌گیری، ثبت واحد الزامی است."
            )

        if errors:
            raise ValidationError(errors)


class PreventiveMaintenanceGeneration(models.Model):
    plan = models.ForeignKey(
        PreventiveMaintenancePlan,
        on_delete=models.CASCADE,
        related_name="generations",
        verbose_name="برنامه نگهداری",
    )

    due_date = models.DateField(
        db_index=True,
        verbose_name="تاریخ سررسید",
    )

    scheduled_generation_date = models.DateField(
        verbose_name="تاریخ برنامه‌ریزی‌شده تولید",
    )

    status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
        db_index=True,
        verbose_name="وضعیت تولید",
    )

    work_order = models.OneToOneField(
        WorkOrder,
        on_delete=models.SET_NULL,
        related_name="preventive_maintenance_generation",
        null=True,
        blank=True,
        verbose_name="دستورکار تولیدشده",
    )

    generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان تولید",
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_preventive_maintenance_orders",
        null=True,
        blank=True,
        verbose_name="تولیدکننده",
    )

    error_message = models.TextField(
        blank=True,
        verbose_name="پیام خطا",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="یادداشت",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="زمان ویرایش",
    )

    class Meta:
        verbose_name = "سابقه تولید دستورکار پیشگیرانه"
        verbose_name_plural = (
            "سوابق تولید دستورکارهای پیشگیرانه"
        )
        ordering = [
            "-due_date",
            "-id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "plan",
                    "due_date",
                ],
                name="unique_pm_generation_per_due_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "status",
                    "scheduled_generation_date",
                ],
                name="pm_gen_status_date_idx",
            ),
            models.Index(
                fields=[
                    "plan",
                    "due_date",
                ],
                name="pm_gen_plan_due_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.plan.plan_number} - "
            f"{self.due_date}"
        )

    def mark_generated(
        self,
        work_order,
        generated_by=None,
    ):
        self.work_order = work_order
        self.status = GenerationStatus.GENERATED
        self.generated_at = timezone.now()
        self.generated_by = generated_by
        self.error_message = ""

        self.save(
            update_fields=[
                "work_order",
                "status",
                "generated_at",
                "generated_by",
                "error_message",
                "updated_at",
            ]
        )

    def mark_failed(
        self,
        error_message,
    ):
        self.status = GenerationStatus.FAILED
        self.error_message = str(
            error_message
        ).strip()

        self.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

    def mark_skipped(
        self,
        notes="",
    ):
        self.status = GenerationStatus.SKIPPED
        self.notes = str(notes).strip()

        self.save(
            update_fields=[
                "status",
                "notes",
                "updated_at",
            ]
        )


class PreventiveMaintenanceTaskResult(models.Model):
    generation = models.ForeignKey(
        PreventiveMaintenanceGeneration,
        on_delete=models.CASCADE,
        related_name="task_results",
        verbose_name="سابقه تولید",
    )

    task = models.ForeignKey(
        PreventiveMaintenanceTask,
        on_delete=models.PROTECT,
        related_name="results",
        verbose_name="فعالیت",
    )

    is_completed = models.BooleanField(
        default=False,
        verbose_name="انجام‌شده",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان انجام",
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="completed_preventive_maintenance_tasks",
        null=True,
        blank=True,
        verbose_name="انجام‌دهنده",
    )

    measured_value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="مقدار اندازه‌گیری‌شده",
    )

    result_is_acceptable = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="نتیجه قابل‌قبول",
    )

    result_notes = models.TextField(
        blank=True,
        verbose_name="یادداشت نتیجه",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="زمان ویرایش",
    )

    class Meta:
        verbose_name = "نتیجه فعالیت نگهداری"
        verbose_name_plural = "نتایج فعالیت‌های نگهداری"
        ordering = [
            "task__sequence",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "generation",
                    "task",
                ],
                name="unique_pm_task_result_per_generation",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "generation",
                    "is_completed",
                ],
                name="pm_result_gen_done_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.generation} - "
            f"{self.task.title}"
        )

    def clean(self):
        errors = {}

        if (
            self.task_id
            and self.task.requires_measurement
            and self.is_completed
            and self.measured_value is None
        ):
            errors["measured_value"] = (
                "ثبت مقدار اندازه‌گیری‌شده الزامی است."
            )

        if (
            self.is_completed
            and not self.completed_at
        ):
            self.completed_at = timezone.now()

        if errors:
            raise ValidationError(errors)

    def evaluate_result(self):
        if self.measured_value is None:
            self.result_is_acceptable = None
            return None

        minimum_value = (
            self.task.minimum_acceptable_value
        )

        maximum_value = (
            self.task.maximum_acceptable_value
        )

        acceptable = True

        if (
            minimum_value is not None
            and self.measured_value < minimum_value
        ):
            acceptable = False

        if (
            maximum_value is not None
            and self.measured_value > maximum_value
        ):
            acceptable = False

        self.result_is_acceptable = acceptable
        return acceptable

    def mark_completed(
        self,
        user=None,
        measured_value=None,
        notes="",
    ):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.completed_by = user
        self.measured_value = measured_value
        self.result_notes = str(notes).strip()

        self.evaluate_result()

        self.full_clean()

        self.save(
            update_fields=[
                "is_completed",
                "completed_at",
                "completed_by",
                "measured_value",
                "result_is_acceptable",
                "result_notes",
                "updated_at",
            ]
        )
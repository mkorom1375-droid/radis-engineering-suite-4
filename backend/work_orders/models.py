from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WorkPriority(models.TextChoices):
    LOW = "low", _("کم")
    NORMAL = "normal", _("عادی")
    HIGH = "high", _("زیاد")
    URGENT = "urgent", _("فوری")
    EMERGENCY = "emergency", _("اضطراری")


class MaintenanceType(models.TextChoices):
    CORRECTIVE = "corrective", _("تعمیرات اصلاحی")
    PREVENTIVE = "preventive", _("نگهداری پیشگیرانه")
    PREDICTIVE = "predictive", _("نگهداری پیش‌بینانه")
    INSPECTION = "inspection", _("بازرسی")
    LUBRICATION = "lubrication", _("روانکاری")
    CALIBRATION = "calibration", _("کالیبراسیون")
    INSTALLATION = "installation", _("نصب و راه‌اندازی")
    MODIFICATION = "modification", _("اصلاح و بهبود")
    SAFETY = "safety", _("ایمنی")
    GENERAL = "general", _("عمومی")


class WorkRequestStatus(models.TextChoices):
    DRAFT = "draft", _("پیش‌نویس")
    SUBMITTED = "submitted", _("ثبت‌شده")
    UNDER_REVIEW = "under_review", _("در حال بررسی")
    APPROVED = "approved", _("تأییدشده")
    REJECTED = "rejected", _("ردشده")
    CONVERTED = "converted", _("تبدیل‌شده به دستورکار")
    CANCELLED = "cancelled", _("لغوشده")


class WorkOrderStatus(models.TextChoices):
    DRAFT = "draft", _("پیش‌نویس")
    OPEN = "open", _("باز")
    ASSIGNED = "assigned", _("تخصیص‌یافته")
    IN_PROGRESS = "in_progress", _("در حال انجام")
    ON_HOLD = "on_hold", _("متوقف")
    COMPLETED = "completed", _("تکمیل‌شده")
    CLOSED = "closed", _("بسته‌شده")
    CANCELLED = "cancelled", _("لغوشده")


class WorkOrderSource(models.TextChoices):
    MANUAL = "manual", _("ثبت دستی")
    WORK_REQUEST = "work_request", _("درخواست تعمیرات")
    PREVENTIVE_MAINTENANCE = "preventive_maintenance", _("برنامه PM")
    INSPECTION = "inspection", _("بازرسی")
    CONDITION_MONITORING = "condition_monitoring", _("پایش وضعیت")
    BREAKDOWN = "breakdown", _("خرابی اضطراری")
    OTHER = "other", _("سایر")


class FailureType(models.TextChoices):
    MECHANICAL = "mechanical", _("مکانیکی")
    ELECTRICAL = "electrical", _("برقی")
    INSTRUMENTATION = "instrumentation", _("ابزار دقیق")
    HYDRAULIC = "hydraulic", _("هیدرولیک")
    PNEUMATIC = "pneumatic", _("پنوماتیک")
    PROCESS = "process", _("فرایندی")
    STRUCTURAL = "structural", _("سازه‌ای")
    SOFTWARE = "software", _("نرم‌افزاری")
    OPERATIONAL = "operational", _("بهره‌برداری")
    UNKNOWN = "unknown", _("نامشخص")
    OTHER = "other", _("سایر")


class AssignmentRole(models.TextChoices):
    SUPERVISOR = "supervisor", _("سرپرست")
    TECHNICIAN = "technician", _("تکنسین")
    ENGINEER = "engineer", _("مهندس")
    INSPECTOR = "inspector", _("بازرس")
    CONTRACTOR = "contractor", _("پیمانکار")
    HELPER = "helper", _("کمک‌کار")
    OTHER = "other", _("سایر")


class WorkRequest(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="work_requests",
        verbose_name=_("پروژه"),
    )

    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.PROTECT,
        related_name="work_requests",
        null=True,
        blank=True,
        verbose_name=_("تجهیز"),
    )

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.PROTECT,
        related_name="work_requests",
        null=True,
        blank=True,
        verbose_name=_("موقعیت"),
    )

    request_number = models.CharField(
        max_length=50,
        verbose_name=_("شماره درخواست"),
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("عنوان درخواست"),
    )

    description = models.TextField(
        verbose_name=_("شرح درخواست"),
    )

    maintenance_type = models.CharField(
        max_length=30,
        choices=MaintenanceType.choices,
        default=MaintenanceType.CORRECTIVE,
        verbose_name=_("نوع تعمیرات"),
    )

    priority = models.CharField(
        max_length=20,
        choices=WorkPriority.choices,
        default=WorkPriority.NORMAL,
        verbose_name=_("اولویت"),
    )

    status = models.CharField(
        max_length=20,
        choices=WorkRequestStatus.choices,
        default=WorkRequestStatus.DRAFT,
        verbose_name=_("وضعیت"),
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_work_requests",
        verbose_name=_("درخواست‌کننده"),
    )

    requested_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("زمان درخواست"),
    )

    required_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ موردنیاز"),
    )

    failure_observed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان مشاهده خرابی"),
    )

    production_stopped = models.BooleanField(
        default=False,
        verbose_name=_("توقف تولید"),
    )

    safety_risk = models.BooleanField(
        default=False,
        verbose_name=_("دارای ریسک ایمنی"),
    )

    environmental_risk = models.BooleanField(
        default=False,
        verbose_name=_("دارای ریسک زیست‌محیطی"),
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_work_requests",
        null=True,
        blank=True,
        verbose_name=_("بررسی‌کننده"),
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان بررسی"),
    )

    review_notes = models.TextField(
        blank=True,
        verbose_name=_("یادداشت بررسی"),
    )

    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("دلیل رد"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("درخواست تعمیرات")
        verbose_name_plural = _("درخواست‌های تعمیرات")
        ordering = ["-requested_at", "-id"]
        indexes = [
            models.Index(
                fields=["project", "request_number"],
                name="wr_project_number_idx",
            ),
            models.Index(
                fields=["project", "status"],
                name="wr_project_status_idx",
            ),
            models.Index(
                fields=["project", "priority"],
                name="wr_project_priority_idx",
            ),
            models.Index(
                fields=["asset", "status"],
                name="wr_asset_status_idx",
            ),
            models.Index(
                fields=["requested_by", "status"],
                name="wr_requester_status_idx",
            ),
            models.Index(
                fields=["requested_at"],
                name="wr_requested_at_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "request_number"],
                name="unique_work_request_number_per_project",
            ),
        ]

    def __str__(self):
        return f"{self.request_number} - {self.title}"

    def clean(self):
        errors = {}

        if self.project_id and not self.project.is_active:
            errors["project"] = _(
                "امکان ثبت درخواست تعمیرات در پروژه غیرفعال وجود ندارد."
            )

        if self.asset_id:
            if self.asset.project_id != self.project_id:
                errors["asset"] = _(
                    "تجهیز انتخاب‌شده باید متعلق به پروژه درخواست باشد."
                )

            if not self.asset.is_active:
                errors["asset"] = _("تجهیز انتخاب‌شده غیرفعال است.")

        if self.location_id:
            if self.location.project_id != self.project_id:
                errors["location"] = _(
                    "موقعیت انتخاب‌شده باید متعلق به پروژه درخواست باشد."
                )

            if not self.location.is_active:
                errors["location"] = _("موقعیت انتخاب‌شده غیرفعال است.")

        if self.asset_id and self.location_id:
            if (
                self.asset.location_id
                and self.asset.location_id != self.location_id
            ):
                errors["location"] = _(
                    "موقعیت درخواست با موقعیت ثبت‌شده برای تجهیز مطابقت ندارد."
                )

        if (
            self.required_date
            and self.requested_at
            and self.required_date < self.requested_at
        ):
            errors["required_date"] = _(
                "تاریخ موردنیاز نمی‌تواند قبل از زمان درخواست باشد."
            )

        if (
            self.failure_observed_at
            and self.requested_at
            and self.failure_observed_at > self.requested_at
        ):
            errors["failure_observed_at"] = _(
                "زمان مشاهده خرابی نمی‌تواند بعد از زمان درخواست باشد."
            )

        if self.status == WorkRequestStatus.REJECTED:
            if not self.rejection_reason.strip():
                errors["rejection_reason"] = _(
                    "برای درخواست ردشده، ثبت دلیل رد الزامی است."
                )

        if self.status in {
            WorkRequestStatus.APPROVED,
            WorkRequestStatus.REJECTED,
            WorkRequestStatus.CONVERTED,
        }:
            if not self.reviewed_by_id:
                errors["reviewed_by"] = _(
                    "برای این وضعیت، تعیین بررسی‌کننده الزامی است."
                )

            if not self.reviewed_at:
                errors["reviewed_at"] = _(
                    "برای این وضعیت، ثبت زمان بررسی الزامی است."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.request_number = self.request_number.strip().upper()
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.review_notes = self.review_notes.strip()
        self.rejection_reason = self.rejection_reason.strip()

        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrder(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="work_orders",
        verbose_name=_("پروژه"),
    )

    work_request = models.OneToOneField(
        WorkRequest,
        on_delete=models.PROTECT,
        related_name="work_order",
        null=True,
        blank=True,
        verbose_name=_("درخواست تعمیرات"),
    )

    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.PROTECT,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name=_("تجهیز"),
    )

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.PROTECT,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name=_("موقعیت"),
    )

    work_order_number = models.CharField(
        max_length=50,
        verbose_name=_("شماره دستورکار"),
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("عنوان دستورکار"),
    )

    description = models.TextField(
        verbose_name=_("شرح کار"),
    )

    maintenance_type = models.CharField(
        max_length=30,
        choices=MaintenanceType.choices,
        default=MaintenanceType.CORRECTIVE,
        verbose_name=_("نوع تعمیرات"),
    )

    priority = models.CharField(
        max_length=20,
        choices=WorkPriority.choices,
        default=WorkPriority.NORMAL,
        verbose_name=_("اولویت"),
    )

    status = models.CharField(
        max_length=20,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.DRAFT,
        verbose_name=_("وضعیت"),
    )

    source = models.CharField(
        max_length=30,
        choices=WorkOrderSource.choices,
        default=WorkOrderSource.MANUAL,
        verbose_name=_("منبع ایجاد"),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_work_orders",
        verbose_name=_("ایجادکننده"),
    )

    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supervised_work_orders",
        null=True,
        blank=True,
        verbose_name=_("سرپرست"),
    )

    planned_start = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("شروع برنامه‌ریزی‌شده"),
    )

    planned_finish = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("پایان برنامه‌ریزی‌شده"),
    )

    actual_start = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("شروع واقعی"),
    )

    actual_finish = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("پایان واقعی"),
    )

    estimated_labor_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("ساعت کار برآوردی"),
    )

    actual_labor_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("ساعت کار واقعی"),
    )

    estimated_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("هزینه برآوردی"),
    )

    actual_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("هزینه واقعی"),
    )

    production_stopped = models.BooleanField(
        default=False,
        verbose_name=_("توقف تولید"),
    )

    permit_required = models.BooleanField(
        default=False,
        verbose_name=_("نیازمند مجوز کار"),
    )

    lockout_tagout_required = models.BooleanField(
        default=False,
        verbose_name=_("نیازمند قفل و برچسب‌گذاری"),
    )

    safety_notes = models.TextField(
        blank=True,
        verbose_name=_("نکات ایمنی"),
    )

    work_performed = models.TextField(
        blank=True,
        verbose_name=_("شرح کار انجام‌شده"),
    )

    completion_notes = models.TextField(
        blank=True,
        verbose_name=_("یادداشت تکمیل"),
    )

    cancellation_reason = models.TextField(
        blank=True,
        verbose_name=_("دلیل لغو"),
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="completed_work_orders",
        null=True,
        blank=True,
        verbose_name=_("تکمیل‌کننده"),
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="closed_work_orders",
        null=True,
        blank=True,
        verbose_name=_("بسته‌شده توسط"),
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان بسته‌شدن"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("دستورکار")
        verbose_name_plural = _("دستورکارها")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["project", "work_order_number"],
                name="wo_project_number_idx",
            ),
            models.Index(
                fields=["project", "status"],
                name="wo_project_status_idx",
            ),
            models.Index(
                fields=["project", "priority"],
                name="wo_project_priority_idx",
            ),
            models.Index(
                fields=["asset", "status"],
                name="wo_asset_status_idx",
            ),
            models.Index(
                fields=["supervisor", "status"],
                name="wo_supervisor_status_idx",
            ),
            models.Index(
                fields=["planned_start"],
                name="wo_planned_start_idx",
            ),
            models.Index(
                fields=["actual_start"],
                name="wo_actual_start_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "work_order_number"],
                name="unique_work_order_number_per_project",
            ),
            models.CheckConstraint(
                condition=Q(estimated_labor_hours__gte=0),
                name="wo_estimated_labor_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(actual_labor_hours__gte=0),
                name="wo_actual_labor_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(estimated_cost__gte=0),
                name="wo_estimated_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(actual_cost__gte=0),
                name="wo_actual_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.work_order_number} - {self.title}"

    @property
    def is_overdue(self):
        if not self.planned_finish:
            return False

        if self.status in {
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.CANCELLED,
        }:
            return False

        return timezone.now() > self.planned_finish

    @property
    def planned_duration_hours(self):
        if not self.planned_start or not self.planned_finish:
            return None

        duration = self.planned_finish - self.planned_start
        return round(duration.total_seconds() / 3600, 2)

    @property
    def actual_duration_hours(self):
        if not self.actual_start or not self.actual_finish:
            return None

        duration = self.actual_finish - self.actual_start
        return round(duration.total_seconds() / 3600, 2)

    def clean(self):
        errors = {}

        if self.project_id and not self.project.is_active:
            errors["project"] = _(
                "امکان ثبت دستورکار در پروژه غیرفعال وجود ندارد."
            )

        if self.work_request_id:
            if self.work_request.project_id != self.project_id:
                errors["work_request"] = _(
                    "درخواست تعمیرات باید متعلق به همان پروژه باشد."
                )

            if self.source != WorkOrderSource.WORK_REQUEST:
                errors["source"] = _(
                    "منبع دستورکار مرتبط با درخواست باید «درخواست تعمیرات» باشد."
                )

        if self.source == WorkOrderSource.WORK_REQUEST:
            if not self.work_request_id:
                errors["work_request"] = _(
                    "برای این منبع، انتخاب درخواست تعمیرات الزامی است."
                )

        if self.asset_id:
            if self.asset.project_id != self.project_id:
                errors["asset"] = _(
                    "تجهیز انتخاب‌شده باید متعلق به پروژه دستورکار باشد."
                )

            if not self.asset.is_active:
                errors["asset"] = _("تجهیز انتخاب‌شده غیرفعال است.")

        if self.location_id:
            if self.location.project_id != self.project_id:
                errors["location"] = _(
                    "موقعیت انتخاب‌شده باید متعلق به پروژه دستورکار باشد."
                )

            if not self.location.is_active:
                errors["location"] = _("موقعیت انتخاب‌شده غیرفعال است.")

        if self.asset_id and self.location_id:
            if (
                self.asset.location_id
                and self.asset.location_id != self.location_id
            ):
                errors["location"] = _(
                    "موقعیت دستورکار با موقعیت ثبت‌شده برای تجهیز مطابقت ندارد."
                )

        if (
            self.planned_start
            and self.planned_finish
            and self.planned_finish < self.planned_start
        ):
            errors["planned_finish"] = _(
                "پایان برنامه‌ریزی‌شده نمی‌تواند قبل از شروع باشد."
            )

        if (
            self.actual_start
            and self.actual_finish
            and self.actual_finish < self.actual_start
        ):
            errors["actual_finish"] = _(
                "پایان واقعی نمی‌تواند قبل از شروع واقعی باشد."
            )

        if self.status == WorkOrderStatus.IN_PROGRESS:
            if not self.actual_start:
                errors["actual_start"] = _(
                    "برای دستورکار در حال انجام، ثبت زمان شروع واقعی الزامی است."
                )

        if self.status in {
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CLOSED,
        }:
            if not self.actual_start:
                errors["actual_start"] = _(
                    "برای تکمیل دستورکار، ثبت زمان شروع واقعی الزامی است."
                )

            if not self.actual_finish:
                errors["actual_finish"] = _(
                    "برای تکمیل دستورکار، ثبت زمان پایان واقعی الزامی است."
                )

            if not self.completed_by_id:
                errors["completed_by"] = _(
                    "برای تکمیل دستورکار، تعیین تکمیل‌کننده الزامی است."
                )

            if not self.work_performed.strip():
                errors["work_performed"] = _(
                    "برای تکمیل دستورکار، شرح کار انجام‌شده الزامی است."
                )

        if self.status == WorkOrderStatus.CLOSED:
            if not self.closed_by_id:
                errors["closed_by"] = _(
                    "برای بستن دستورکار، تعیین کاربر تأییدکننده الزامی است."
                )

            if not self.closed_at:
                errors["closed_at"] = _(
                    "برای بستن دستورکار، ثبت زمان بسته‌شدن الزامی است."
                )

        if self.status == WorkOrderStatus.CANCELLED:
            if not self.cancellation_reason.strip():
                errors["cancellation_reason"] = _(
                    "برای دستورکار لغوشده، ثبت دلیل لغو الزامی است."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.work_order_number = self.work_order_number.strip().upper()
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.safety_notes = self.safety_notes.strip()
        self.work_performed = self.work_performed.strip()
        self.completion_notes = self.completion_notes.strip()
        self.cancellation_reason = self.cancellation_reason.strip()

        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrderAssignment(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name=_("دستورکار"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_order_assignments",
        verbose_name=_("کاربر"),
    )

    role = models.CharField(
        max_length=20,
        choices=AssignmentRole.choices,
        default=AssignmentRole.TECHNICIAN,
        verbose_name=_("نقش"),
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_work_order_assignments",
        verbose_name=_("تخصیص‌دهنده"),
    )

    assigned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("زمان تخصیص"),
    )

    removed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان حذف تخصیص"),
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("یادداشت"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("تخصیص دستورکار")
        verbose_name_plural = _("تخصیص‌های دستورکار")
        ordering = ["-assigned_at", "-id"]
        indexes = [
            models.Index(
                fields=["work_order", "is_active"],
                name="woa_order_active_idx",
            ),
            models.Index(
                fields=["user", "is_active"],
                name="woa_user_active_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["work_order", "user", "role"],
                condition=Q(is_active=True),
                name="unique_active_work_order_assignment",
            ),
        ]

    def __str__(self):
        return (
            f"{self.work_order.work_order_number} - "
            f"{self.user} - {self.get_role_display()}"
        )

    def clean(self):
        errors = {}

        if self.removed_at and self.removed_at < self.assigned_at:
            errors["removed_at"] = _(
                "زمان حذف تخصیص نمی‌تواند قبل از زمان تخصیص باشد."
            )

        if not self.is_active and not self.removed_at:
            errors["removed_at"] = _(
                "برای تخصیص غیرفعال، ثبت زمان حذف الزامی است."
            )

        if self.is_active and self.removed_at:
            errors["removed_at"] = _(
                "تخصیص فعال نمی‌تواند زمان حذف داشته باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.notes = self.notes.strip()
        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrderLabor(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="labor_entries",
        verbose_name=_("دستورکار"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_order_labor_entries",
        verbose_name=_("کاربر"),
    )

    work_date = models.DateField(
        default=timezone.localdate,
        verbose_name=_("تاریخ کار"),
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان شروع"),
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("زمان پایان"),
    )

    hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("ساعات کار"),
    )

    hourly_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("نرخ ساعتی"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("شرح فعالیت"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("کارکرد نیروی انسانی")
        verbose_name_plural = _("کارکردهای نیروی انسانی")
        ordering = ["-work_date", "-id"]
        indexes = [
            models.Index(
                fields=["work_order", "work_date"],
                name="wol_order_date_idx",
            ),
            models.Index(
                fields=["user", "work_date"],
                name="wol_user_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(hours__gte=0),
                name="wol_hours_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(hourly_rate__gte=0),
                name="wol_hourly_rate_nonnegative",
            ),
        ]

    def __str__(self):
        return (
            f"{self.work_order.work_order_number} - "
            f"{self.user} - {self.hours}"
        )

    @property
    def labor_cost(self):
        return self.hours * self.hourly_rate

    def clean(self):
        errors = {}

        if self.started_at and self.finished_at:
            if self.finished_at < self.started_at:
                errors["finished_at"] = _(
                    "زمان پایان نمی‌تواند قبل از زمان شروع باشد."
                )

        if self.started_at and self.started_at.date() != self.work_date:
            errors["work_date"] = _(
                "تاریخ کار باید با زمان شروع ثبت‌شده مطابقت داشته باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.description = self.description.strip()

        if self.started_at and self.finished_at:
            duration = self.finished_at - self.started_at
            self.hours = Decimal(
                str(round(duration.total_seconds() / 3600, 2))
            )

        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrderDowntime(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="downtime_entries",
        verbose_name=_("دستورکار"),
    )

    started_at = models.DateTimeField(
        verbose_name=_("شروع توقف"),
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("پایان توقف"),
    )

    production_loss = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("میزان افت تولید"),
    )

    reason = models.TextField(
        blank=True,
        verbose_name=_("علت توقف"),
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("یادداشت"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("توقف تجهیز")
        verbose_name_plural = _("توقف‌های تجهیز")
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(
                fields=["work_order", "started_at"],
                name="wod_order_start_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(production_loss__gte=0),
                name="wod_production_loss_nonnegative",
            ),
        ]

    def __str__(self):
        return (
            f"{self.work_order.work_order_number} - "
            f"{self.started_at}"
        )

    @property
    def duration_hours(self):
        end_time = self.finished_at or timezone.now()
        duration = end_time - self.started_at
        return round(duration.total_seconds() / 3600, 2)

    def clean(self):
        errors = {}

        if self.finished_at and self.finished_at < self.started_at:
            errors["finished_at"] = _(
                "پایان توقف نمی‌تواند قبل از شروع توقف باشد."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.reason = self.reason.strip()
        self.notes = self.notes.strip()
        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrderFailure(models.Model):
    work_order = models.OneToOneField(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="failure",
        verbose_name=_("دستورکار"),
    )

    failure_type = models.CharField(
        max_length=30,
        choices=FailureType.choices,
        default=FailureType.UNKNOWN,
        verbose_name=_("نوع خرابی"),
    )

    failure_mode = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("مد خرابی"),
    )

    symptom = models.TextField(
        blank=True,
        verbose_name=_("نشانه خرابی"),
    )

    immediate_cause = models.TextField(
        blank=True,
        verbose_name=_("علت مستقیم"),
    )

    root_cause = models.TextField(
        blank=True,
        verbose_name=_("علت ریشه‌ای"),
    )

    corrective_action = models.TextField(
        blank=True,
        verbose_name=_("اقدام اصلاحی"),
    )

    preventive_action = models.TextField(
        blank=True,
        verbose_name=_("اقدام پیشگیرانه"),
    )

    requires_follow_up = models.BooleanField(
        default=False,
        verbose_name=_("نیازمند پیگیری"),
    )

    follow_up_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("مهلت پیگیری"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ ایجاد"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین ویرایش"),
    )

    class Meta:
        verbose_name = _("تحلیل خرابی")
        verbose_name_plural = _("تحلیل‌های خرابی")

    def __str__(self):
        return (
            f"{self.work_order.work_order_number} - "
            f"{self.get_failure_type_display()}"
        )

    def clean(self):
        errors = {}

        if self.requires_follow_up and not self.follow_up_due_date:
            errors["follow_up_due_date"] = _(
                "برای خرابی نیازمند پیگیری، ثبت مهلت پیگیری الزامی است."
            )

        if not self.requires_follow_up and self.follow_up_due_date:
            errors["follow_up_due_date"] = _(
                "برای ثبت مهلت پیگیری، گزینه نیازمند پیگیری را فعال کنید."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.failure_mode = self.failure_mode.strip()
        self.symptom = self.symptom.strip()
        self.immediate_cause = self.immediate_cause.strip()
        self.root_cause = self.root_cause.strip()
        self.corrective_action = self.corrective_action.strip()
        self.preventive_action = self.preventive_action.strip()

        self.full_clean()
        super().save(*args, **kwargs)


class WorkOrderStatusHistory(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("دستورکار"),
    )

    previous_status = models.CharField(
        max_length=20,
        choices=WorkOrderStatus.choices,
        blank=True,
        verbose_name=_("وضعیت قبلی"),
    )

    new_status = models.CharField(
        max_length=20,
        choices=WorkOrderStatus.choices,
        verbose_name=_("وضعیت جدید"),
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="work_order_status_changes",
        verbose_name=_("تغییردهنده"),
    )

    changed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("زمان تغییر"),
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("یادداشت"),
    )

    class Meta:
        verbose_name = _("تاریخچه وضعیت دستورکار")
        verbose_name_plural = _("تاریخچه وضعیت دستورکارها")
        ordering = ["-changed_at", "-id"]
        indexes = [
            models.Index(
                fields=["work_order", "changed_at"],
                name="wosh_order_changed_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.work_order.work_order_number}: "
            f"{self.previous_status} -> {self.new_status}"
        )

    def save(self, *args, **kwargs):
        self.notes = self.notes.strip()
        self.full_clean()
        super().save(*args, **kwargs)
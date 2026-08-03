from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class ProjectNumberingSettings(models.Model):
    """Organization-scoped, transactional project-code configuration."""

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="project_numbering_settings",
    )
    prefix = models.CharField(max_length=20, blank=True)
    separator = models.CharField(max_length=3, default="-")
    next_number = models.PositiveBigIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id"]

    def clean(self):
        errors = {}
        self.prefix = self.prefix.strip().upper()
        self.separator = self.separator.strip()
        if len(self.separator) > 3:
            errors["separator"] = _("جداکننده نمی‌تواند بیشتر از سه نویسه باشد.")
        if self.next_number < 1:
            errors["next_number"] = _("شماره بعدی باید حداقل یک باشد.")
        if not 1 <= self.padding <= 10:
            errors["padding"] = _("تعداد رقم‌های شماره باید بین ۱ و ۱۰ باشد.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Project(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="projects",
    )

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["organization", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_project_code_per_org",
            )
        ]

    def clean(self):
        errors = {}
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = _("تاریخ پایان پروژه قبل از تاریخ شروع است.")
        if self.organization_id and not self.organization.is_active:
            errors["organization"] = _("پروژه باید به سازمان فعال تعلق داشته باشد.")
        if errors:
            raise ValidationError(errors)

    @property
    def progress_percent(self):
        stages = list(self.stages.filter(is_active=True))
        if not stages:
            return Decimal("0.00")
        total_weight = sum((stage.weight for stage in stages), Decimal("0.000"))
        if not total_weight:
            return Decimal("0.00")
        completed_weight = sum(
            (
                stage.weight
                for stage in stages
                if stage.status == ProjectStageStatus.COMPLETED
            ),
            Decimal("0.000"),
        )
        return (completed_weight * Decimal("100") / total_weight).quantize(
            Decimal("0.01")
        )

    @property
    def completed_stage_count(self):
        return self.stages.filter(
            is_active=True,
            status=ProjectStageStatus.COMPLETED,
        ).count()

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProjectStageStatus(models.TextChoices):
    PLANNED = "planned", _("برنامه‌ریزی‌شده")
    IN_PROGRESS = "in_progress", _("در حال اجرا")
    BLOCKED = "blocked", _("مسدود")
    COMPLETED = "completed", _("تکمیل‌شده")
    CANCELLED = "cancelled", _("لغوشده")


class ProjectStage(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=ProjectStageStatus.choices,
        default=ProjectStageStatus.PLANNED,
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal("1.000"),
    )
    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project_id", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"],
                name="unique_project_stage_code",
            ),
            models.UniqueConstraint(
                fields=["project", "order"],
                condition=Q(is_active=True),
                name="unique_active_project_stage_order",
            ),
            models.CheckConstraint(
                condition=Q(weight__gt=0),
                name="project_stage_weight_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project", "status"],
                name="project_stage_status_idx",
            ),
        ]

    def clean(self):
        errors = {}
        if not self.project.is_active and self.is_active:
            errors["project"] = _("برای پروژه غیرفعال مرحله فعال ثبت نمی‌شود.")
        if self.weight <= 0:
            errors["weight"] = _("وزن مرحله باید بزرگ‌تر از صفر باشد.")
        if (
            self.planned_start
            and self.planned_end
            and self.planned_end < self.planned_start
        ):
            errors["planned_end"] = _("پایان برنامه‌ریزی‌شده قبل از شروع است.")
        if (
            self.actual_start
            and self.actual_end
            and self.actual_end < self.actual_start
        ):
            errors["actual_end"] = _("پایان واقعی قبل از شروع است.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        self.description = self.description.strip()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.code} / {self.code} - {self.name}"

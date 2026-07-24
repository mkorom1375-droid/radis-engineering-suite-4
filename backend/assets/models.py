from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Asset(models.Model):
    class AssetType(models.TextChoices):
        EQUIPMENT = "equipment", _("تجهیز")
        MACHINE = "machine", _("ماشین‌آلات")
        ELECTRICAL = "electrical", _("تجهیز برقی")
        INSTRUMENT = "instrument", _("ابزار دقیق")
        VEHICLE = "vehicle", _("وسیله نقلیه")
        BUILDING = "building", _("ساختمان")
        FACILITY = "facility", _("تأسیسات")
        TOOL = "tool", _("ابزار")
        OTHER = "other", _("سایر")

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="assets",
        verbose_name=_("پروژه"),
    )

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.PROTECT,
        related_name="assets",
        null=True,
        blank=True,
        verbose_name=_("موقعیت"),
    )

    code = models.CharField(
        max_length=50,
        verbose_name=_("کد تجهیز"),
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("نام تجهیز"),
    )

    asset_type = models.CharField(
        max_length=30,
        choices=AssetType.choices,
        default=AssetType.EQUIPMENT,
        verbose_name=_("نوع تجهیز"),
    )

    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("سازنده"),
    )

    model = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("مدل"),
    )

    serial_number = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("شماره سریال"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("توضیحات"),
    )

    commission_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("تاریخ راه‌اندازی"),
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
        verbose_name = _("تجهیز")
        verbose_name_plural = _("تجهیزات")
        ordering = [
            "project_id",
            "code",
        ]
        indexes = [
            models.Index(
                fields=["project", "code"],
                name="asset_project_code_idx",
            ),
            models.Index(
                fields=["project", "name"],
                name="asset_project_name_idx",
            ),
            models.Index(
                fields=["project", "asset_type"],
                name="asset_project_type_idx",
            ),
            models.Index(
                fields=["project", "is_active"],
                name="asset_project_active_idx",
            ),
            models.Index(
                fields=["location"],
                name="asset_location_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"],
                name="unique_asset_code_per_project",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        errors = {}

        if self.project_id and not self.project.is_active:
            errors["project"] = _(
                "امکان ثبت تجهیز در پروژه غیرفعال وجود ندارد."
            )

        if self.location_id:
            if self.project_id and self.location.project_id != self.project_id:
                errors["location"] = _(
                    "موقعیت انتخاب‌شده باید متعلق به همان پروژه تجهیز باشد."
                )

            if not self.location.is_active:
                errors["location"] = _(
                    "امکان انتخاب موقعیت غیرفعال وجود ندارد."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        self.manufacturer = self.manufacturer.strip()
        self.model = self.model.strip()
        self.serial_number = self.serial_number.strip()
        self.description = self.description.strip()

        self.full_clean()
        super().save(*args, **kwargs)
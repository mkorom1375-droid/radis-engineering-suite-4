import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def asset_document_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{extension}"

    organization_id = instance.asset.project.organization_id
    project_id = instance.asset.project_id
    asset_id = instance.asset_id

    return (
        f"organizations/{organization_id}/"
        f"projects/{project_id}/"
        f"assets/{asset_id}/"
        f"documents/{unique_filename}"
    )


class AssetDocument(models.Model):
    class DocumentType(models.TextChoices):
        MANUAL = "manual", "راهنمای فنی"
        DATASHEET = "datasheet", "دیتاشیت"
        DRAWING = "drawing", "نقشه"
        CERTIFICATE = "certificate", "گواهی‌نامه"
        TEST_REPORT = "test_report", "گزارش آزمون"
        INSPECTION_REPORT = "inspection_report", "گزارش بازرسی"
        PHOTO = "photo", "تصویر"
        WARRANTY = "warranty", "ضمانت‌نامه"
        PURCHASE_DOCUMENT = "purchase_document", "سند خرید"
        COMMISSIONING = "commissioning", "سند راه‌اندازی"
        MAINTENANCE = "maintenance", "سند نگهداری و تعمیرات"
        OTHER = "other", "سایر"

    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="تجهیز",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان سند",
    )

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        verbose_name="نوع سند",
    )

    document_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="شماره سند",
    )

    revision = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ویرایش",
    )

    document_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ سند",
    )

    file = models.FileField(
        upload_to=asset_document_upload_path,
        verbose_name="فایل",
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_asset_documents",
        verbose_name="بارگذاری‌کننده",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ آخرین ویرایش",
    )

    class Meta:
        verbose_name = "سند تجهیز"
        verbose_name_plural = "اسناد تجهیزات"

        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "asset",
                    "document_number",
                    "revision",
                ],
                condition=~models.Q(document_number=""),
                name="unique_asset_document_number_revision",
            )
        ]

    def __str__(self):
        if self.document_number:
            return f"{self.document_number} - {self.title}"

        return self.title

    def clean(self):
        super().clean()

        if self.asset_id and not self.asset.is_active:
            raise ValidationError(
                {
                    "asset": (
                        "امکان ثبت سند برای تجهیز غیرفعال وجود ندارد."
                    )
                }
            )

        if (
            self.asset_id
            and self.asset.project_id
            and not self.asset.project.is_active
        ):
            raise ValidationError(
                {
                    "asset": (
                        "پروژه مرتبط با این تجهیز غیرفعال است."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.title:
            self.title = self.title.strip()

        if self.document_number:
            self.document_number = self.document_number.strip()

        if self.revision:
            self.revision = self.revision.strip()

        self.full_clean()
        super().save(*args, **kwargs)
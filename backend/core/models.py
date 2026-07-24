from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ آخرین ویرایش",
    )

    class Meta:
        abstract = True


class ActiveModel(models.Model):
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="فعال",
    )

    class Meta:
        abstract = True

    def activate(self):
        if self.is_active:
            return

        self.is_active = True
        self.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

    def deactivate(self):
        if not self.is_active:
            return

        self.is_active = False
        self.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )


class BaseModel(
    TimeStampedModel,
    ActiveModel,
):
    class Meta:
        abstract = True
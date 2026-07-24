from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "asset_type",
        "project",
        "manufacturer",
        "model",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "asset_type",
        "is_active",
        "project",
        "manufacturer",
    ]

    search_fields = [
        "code",
        "name",
        "manufacturer",
        "model",
        "serial_number",
        "project__code",
        "project__name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "project",
    ]

    ordering = [
        "project",
        "code",
    ]

    fieldsets = [
        (
            "اطلاعات اصلی تجهیز",
            {
                "fields": [
                    "project",
                    "code",
                    "name",
                    "asset_type",
                ]
            },
        ),
        (
            "اطلاعات فنی",
            {
                "fields": [
                    "manufacturer",
                    "model",
                    "serial_number",
                    "commission_date",
                ]
            },
        ),
        (
            "توضیحات و وضعیت",
            {
                "fields": [
                    "description",
                    "is_active",
                ]
            },
        ),
        (
            "اطلاعات سیستمی",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]
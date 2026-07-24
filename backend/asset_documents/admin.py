from django.contrib import admin

from .models import AssetDocument


@admin.register(AssetDocument)
class AssetDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "document_type",
        "document_number",
        "revision",
        "asset",
        "document_date",
        "uploaded_by",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "document_type",
        "is_active",
        "document_date",
        "created_at",
        "asset__project",
    ]

    search_fields = [
        "title",
        "document_number",
        "revision",
        "description",
        "asset__code",
        "asset__name",
        "asset__project__code",
        "asset__project__name",
    ]

    readonly_fields = [
        "uploaded_by",
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "asset",
        "asset__project",
        "uploaded_by",
    ]

    ordering = [
        "-created_at",
    ]

    fieldsets = [
        (
            "اطلاعات اصلی سند",
            {
                "fields": [
                    "asset",
                    "title",
                    "document_type",
                    "document_number",
                    "revision",
                    "document_date",
                ]
            },
        ),
        (
            "فایل و توضیحات",
            {
                "fields": [
                    "file",
                    "description",
                ]
            },
        ),
        (
            "وضعیت",
            {
                "fields": [
                    "is_active",
                ]
            },
        ),
        (
            "اطلاعات سیستمی",
            {
                "fields": [
                    "uploaded_by",
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if obj.uploaded_by_id is None:
            obj.uploaded_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )
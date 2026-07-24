from django.contrib import admin

from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "location_type",
        "project",
        "parent",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "location_type",
        "is_active",
        "project",
        "created_at",
    ]

    search_fields = [
        "code",
        "name",
        "description",
        "project__code",
        "project__name",
        "parent__code",
        "parent__name",
    ]

    ordering = [
        "project__code",
        "code",
    ]

    autocomplete_fields = [
        "project",
        "parent",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "full_name",
        "full_code",
    ]

    fieldsets = [
        (
            "اطلاعات اصلی",
            {
                "fields": [
                    "project",
                    "parent",
                    "code",
                    "name",
                    "location_type",
                ]
            },
        ),
        (
            "اطلاعات تکمیلی",
            {
                "fields": [
                    "description",
                    "full_name",
                    "full_code",
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
                "classes": [
                    "collapse",
                ],
                "fields": [
                    "created_at",
                    "updated_at",
                ],
            },
        ),
    ]

    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "project",
            "parent",
        )
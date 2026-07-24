from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "phone",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
        "phone",
        "website",
    )

    ordering = ("name",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )
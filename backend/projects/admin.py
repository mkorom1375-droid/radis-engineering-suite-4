from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "organization",
        "start_date",
        "end_date",
        "is_active",
    )

    list_filter = (
        "organization",
        "is_active",
        "start_date",
    )

    search_fields = (
        "code",
        "name",
        "organization__name",
    )

    ordering = (
        "organization",
        "name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
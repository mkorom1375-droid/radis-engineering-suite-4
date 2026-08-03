from django.contrib import admin

from .models import (
    Project,
    ProjectNumberingSettings,
    ProjectStage,
)


@admin.register(ProjectNumberingSettings)
class ProjectNumberingSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "prefix",
        "separator",
        "next_number",
        "padding",
        "updated_at",
    )
    search_fields = (
        "organization__name",
        "organization__code",
        "prefix",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


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


@admin.register(ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "order",
        "code",
        "name",
        "status",
        "weight",
        "is_active",
    )
    list_filter = (
        "status",
        "is_active",
        "project__organization",
    )
    search_fields = (
        "code",
        "name",
        "project__code",
        "project__name",
    )
    ordering = (
        "project",
        "order",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )

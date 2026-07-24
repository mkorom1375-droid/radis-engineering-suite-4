from django.contrib import admin

from .models import Permission, Role, UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "organization",
        "is_system_role",
        "is_active",
    )

    list_filter = (
        "organization",
        "is_system_role",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "organization__name",
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "module",
        "name",
        "code",
        "is_system_permission",
    )

    list_filter = (
        "module",
        "is_system_permission",
    )

    search_fields = (
        "name",
        "code",
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "is_active",
        "assigned_at",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "user__username",
        "role__name",
    )
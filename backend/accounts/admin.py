from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "RADIS Profile",
            {
                "fields": (
                    "employee_code",
                    "job_title",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "RADIS Profile",
            {
                "fields": (
                    "email",
                    "employee_code",
                    "job_title",
                )
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "employee_code",
        "job_title",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "employee_code",
        "first_name",
        "last_name",
    )
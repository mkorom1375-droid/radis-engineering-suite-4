from django.contrib import admin

from .models import (
    PreventiveMaintenanceGeneration,
    PreventiveMaintenancePlan,
    PreventiveMaintenanceStatus,
    PreventiveMaintenanceTask,
    PreventiveMaintenanceTaskResult,
)


class PreventiveMaintenanceTaskInline(admin.TabularInline):
    model = PreventiveMaintenanceTask
    extra = 0
    fields = (
        "sequence",
        "task_type",
        "title",
        "estimated_duration_minutes",
        "requires_shutdown",
        "requires_photo",
        "requires_measurement",
        "is_mandatory",
        "is_active",
    )
    ordering = (
        "sequence",
        "id",
    )
    show_change_link = True


class PreventiveMaintenanceGenerationInline(admin.TabularInline):
    model = PreventiveMaintenanceGeneration
    extra = 0
    fields = (
        "due_date",
        "scheduled_generation_date",
        "status",
        "work_order",
        "generated_at",
    )
    readonly_fields = (
        "due_date",
        "scheduled_generation_date",
        "status",
        "work_order",
        "generated_at",
    )
    ordering = (
        "-due_date",
        "-id",
    )
    show_change_link = True
    can_delete = False


class PreventiveMaintenanceTaskResultInline(admin.TabularInline):
    model = PreventiveMaintenanceTaskResult
    extra = 0
    fields = (
        "task",
        "is_completed",
        "completed_by",
        "completed_at",
        "measured_value",
        "result_is_acceptable",
    )
    readonly_fields = (
        "task",
        "completed_by",
        "completed_at",
        "result_is_acceptable",
    )
    ordering = (
        "task__sequence",
        "id",
    )
    show_change_link = True


@admin.register(PreventiveMaintenancePlan)
class PreventiveMaintenancePlanAdmin(admin.ModelAdmin):
    list_display = (
        "plan_number",
        "title",
        "project",
        "asset",
        "status",
        "priority",
        "frequency",
        "next_due_date",
        "auto_generate_work_order",
        "is_active",
    )

    list_filter = (
        "status",
        "priority",
        "frequency",
        "maintenance_type",
        "auto_generate_work_order",
        "allow_duplicate_open_orders",
        "permit_required",
        "lockout_tagout_required",
        "production_stop_required",
        "is_active",
        "project",
    )

    search_fields = (
        "plan_number",
        "title",
        "description",
        "project__code",
        "project__name",
        "asset__code",
        "asset__name",
        "location__code",
        "location__name",
        "supervisor__username",
        "supervisor__first_name",
        "supervisor__last_name",
        "created_by__username",
    )

    ordering = (
        "next_due_date",
        "plan_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_due_date",
        "generation_date_display",
        "is_due_display",
        "is_ready_for_generation_display",
    )

    autocomplete_fields = (
        "project",
        "asset",
        "location",
        "supervisor",
        "created_by",
    )

    date_hierarchy = "next_due_date"

    inlines = (
        PreventiveMaintenanceTaskInline,
        PreventiveMaintenanceGenerationInline,
    )

    fieldsets = (
        (
            "اطلاعات اصلی",
            {
                "fields": (
                    "project",
                    "plan_number",
                    "title",
                    "description",
                    "asset",
                    "location",
                    "status",
                    "maintenance_type",
                    "priority",
                    "is_active",
                ),
            },
        ),
        (
            "برنامه‌ریزی",
            {
                "fields": (
                    "frequency",
                    "custom_interval_days",
                    "start_date",
                    "end_date",
                    "last_due_date",
                    "next_due_date",
                    "generation_lead_days",
                    "generation_date_display",
                    "is_due_display",
                    "is_ready_for_generation_display",
                ),
            },
        ),
        (
            "تولید دستورکار",
            {
                "fields": (
                    "auto_generate_work_order",
                    "allow_duplicate_open_orders",
                    "estimated_duration_hours",
                    "estimated_labor_hours",
                    "estimated_cost",
                    "supervisor",
                ),
            },
        ),
        (
            "الزامات اجرایی",
            {
                "fields": (
                    "safety_instructions",
                    "required_tools",
                    "required_materials",
                    "permit_required",
                    "lockout_tagout_required",
                    "production_stop_required",
                ),
            },
        ),
        (
            "اطلاعات سیستمی",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    actions = (
        "activate_selected_plans",
        "suspend_selected_plans",
        "cancel_selected_plans",
        "initialize_next_due_dates",
    )

    @admin.display(
        description="تاریخ تولید",
    )
    def generation_date_display(self, obj):
        return obj.generation_date

    @admin.display(
        boolean=True,
        description="سررسیدشده",
    )
    def is_due_display(self, obj):
        return obj.is_due

    @admin.display(
        boolean=True,
        description="آماده تولید",
    )
    def is_ready_for_generation_display(self, obj):
        return obj.is_ready_for_generation

    @admin.action(
        description="فعال‌کردن برنامه‌های انتخاب‌شده",
    )
    def activate_selected_plans(self, request, queryset):
        updated = queryset.update(
            status=PreventiveMaintenanceStatus.ACTIVE,
            is_active=True,
        )

        self.message_user(
            request,
            f"{updated} برنامه فعال شد.",
        )

    @admin.action(
        description="معلق‌کردن برنامه‌های انتخاب‌شده",
    )
    def suspend_selected_plans(self, request, queryset):
        updated = queryset.update(
            status=PreventiveMaintenanceStatus.SUSPENDED,
        )

        self.message_user(
            request,
            f"{updated} برنامه معلق شد.",
        )

    @admin.action(
        description="لغو برنامه‌های انتخاب‌شده",
    )
    def cancel_selected_plans(self, request, queryset):
        updated = queryset.update(
            status=PreventiveMaintenanceStatus.CANCELLED,
            is_active=False,
        )

        self.message_user(
            request,
            f"{updated} برنامه لغو شد.",
        )

    @admin.action(
        description="مقداردهی سررسید بعدی",
    )
    def initialize_next_due_dates(self, request, queryset):
        updated_count = 0

        for plan in queryset:
            if plan.next_due_date:
                continue

            plan.initialize_next_due_date()
            plan.save(
                update_fields=(
                    "next_due_date",
                    "updated_at",
                )
            )
            updated_count += 1

        self.message_user(
            request,
            f"سررسید بعدی برای {updated_count} برنامه مقداردهی شد.",
        )


@admin.register(PreventiveMaintenanceTask)
class PreventiveMaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "sequence",
        "task_type",
        "title",
        "estimated_duration_minutes",
        "requires_shutdown",
        "requires_measurement",
        "is_mandatory",
        "is_active",
    )

    list_filter = (
        "task_type",
        "requires_shutdown",
        "requires_photo",
        "requires_measurement",
        "is_mandatory",
        "is_active",
        "plan__project",
    )

    search_fields = (
        "plan__plan_number",
        "plan__title",
        "title",
        "description",
        "acceptance_criteria",
        "measurement_unit",
    )

    ordering = (
        "plan",
        "sequence",
        "id",
    )

    autocomplete_fields = (
        "plan",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "اطلاعات فعالیت",
            {
                "fields": (
                    "plan",
                    "sequence",
                    "task_type",
                    "title",
                    "description",
                    "acceptance_criteria",
                    "estimated_duration_minutes",
                    "is_mandatory",
                    "is_active",
                ),
            },
        ),
        (
            "الزامات فعالیت",
            {
                "fields": (
                    "requires_shutdown",
                    "requires_photo",
                    "requires_measurement",
                    "measurement_unit",
                    "minimum_acceptable_value",
                    "maximum_acceptable_value",
                ),
            },
        ),
        (
            "اطلاعات سیستمی",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(PreventiveMaintenanceGeneration)
class PreventiveMaintenanceGenerationAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "due_date",
        "scheduled_generation_date",
        "status",
        "work_order",
        "generated_at",
        "generated_by",
    )

    list_filter = (
        "status",
        "scheduled_generation_date",
        "due_date",
        "plan__project",
    )

    search_fields = (
        "plan__plan_number",
        "plan__title",
        "work_order__work_order_number",
        "work_order__title",
        "error_message",
        "notes",
    )

    ordering = (
        "-due_date",
        "-id",
    )

    date_hierarchy = "due_date"

    autocomplete_fields = (
        "plan",
        "work_order",
        "generated_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "generated_at",
    )

    inlines = (
        PreventiveMaintenanceTaskResultInline,
    )

    fieldsets = (
        (
            "اطلاعات برنامه",
            {
                "fields": (
                    "plan",
                    "due_date",
                    "scheduled_generation_date",
                    "status",
                ),
            },
        ),
        (
            "دستورکار",
            {
                "fields": (
                    "work_order",
                    "generated_at",
                    "generated_by",
                ),
            },
        ),
        (
            "نتیجه اجرا",
            {
                "fields": (
                    "error_message",
                    "notes",
                ),
            },
        ),
        (
            "اطلاعات سیستمی",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(PreventiveMaintenanceTaskResult)
class PreventiveMaintenanceTaskResultAdmin(admin.ModelAdmin):
    list_display = (
        "generation",
        "task",
        "is_completed",
        "completed_by",
        "completed_at",
        "measured_value",
        "result_is_acceptable",
    )

    list_filter = (
        "is_completed",
        "result_is_acceptable",
        "task__task_type",
        "generation__plan__project",
    )

    search_fields = (
        "generation__plan__plan_number",
        "generation__plan__title",
        "task__title",
        "result_notes",
        "completed_by__username",
        "completed_by__first_name",
        "completed_by__last_name",
    )

    ordering = (
        "generation",
        "task__sequence",
        "id",
    )

    autocomplete_fields = (
        "generation",
        "task",
        "completed_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "result_is_acceptable",
    )

    fieldsets = (
        (
            "اطلاعات فعالیت",
            {
                "fields": (
                    "generation",
                    "task",
                    "is_completed",
                    "completed_at",
                    "completed_by",
                ),
            },
        ),
        (
            "نتیجه",
            {
                "fields": (
                    "measured_value",
                    "result_is_acceptable",
                    "result_notes",
                ),
            },
        ),
        (
            "اطلاعات سیستمی",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
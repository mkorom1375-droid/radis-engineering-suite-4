from django.contrib import admin

from .models import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderDowntime,
    WorkOrderFailure,
    WorkOrderLabor,
    WorkOrderStatusHistory,
    WorkRequest,
)


class WorkOrderAssignmentInline(admin.TabularInline):
    model = WorkOrderAssignment
    extra = 0
    autocomplete_fields = [
        "user",
        "assigned_by",
    ]
    fields = [
        "user",
        "role",
        "assigned_by",
        "assigned_at",
        "removed_at",
        "is_active",
        "notes",
    ]


class WorkOrderLaborInline(admin.TabularInline):
    model = WorkOrderLabor
    extra = 0
    autocomplete_fields = [
        "user",
    ]
    fields = [
        "user",
        "work_date",
        "started_at",
        "finished_at",
        "hours",
        "hourly_rate",
        "description",
    ]


class WorkOrderDowntimeInline(admin.TabularInline):
    model = WorkOrderDowntime
    extra = 0
    fields = [
        "started_at",
        "finished_at",
        "production_loss",
        "reason",
        "notes",
    ]


class WorkOrderStatusHistoryInline(admin.TabularInline):
    model = WorkOrderStatusHistory
    extra = 0
    autocomplete_fields = [
        "changed_by",
    ]
    fields = [
        "previous_status",
        "new_status",
        "changed_by",
        "changed_at",
        "notes",
    ]
    readonly_fields = [
        "previous_status",
        "new_status",
        "changed_by",
        "changed_at",
        "notes",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(WorkRequest)
class WorkRequestAdmin(admin.ModelAdmin):
    list_display = [
        "request_number",
        "title",
        "project",
        "asset",
        "maintenance_type",
        "priority",
        "status",
        "requested_by",
        "requested_at",
        "production_stopped",
        "is_active",
    ]

    list_filter = [
        "status",
        "priority",
        "maintenance_type",
        "production_stopped",
        "safety_risk",
        "environmental_risk",
        "is_active",
        "project",
        "requested_at",
    ]

    search_fields = [
        "request_number",
        "title",
        "description",
        "project__code",
        "project__name",
        "asset__code",
        "asset__name",
        "location__code",
        "location__name",
        "requested_by__username",
        "requested_by__email",
    ]

    ordering = [
        "-requested_at",
        "-id",
    ]

    autocomplete_fields = [
        "project",
        "asset",
        "location",
        "requested_by",
        "reviewed_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    date_hierarchy = "requested_at"

    list_select_related = [
        "project",
        "asset",
        "location",
        "requested_by",
        "reviewed_by",
    ]

    fieldsets = [
        (
            "اطلاعات اصلی",
            {
                "fields": [
                    "project",
                    "request_number",
                    "title",
                    "description",
                    "maintenance_type",
                    "priority",
                    "status",
                ]
            },
        ),
        (
            "تجهیز و موقعیت",
            {
                "fields": [
                    "asset",
                    "location",
                ]
            },
        ),
        (
            "اطلاعات درخواست",
            {
                "fields": [
                    "requested_by",
                    "requested_at",
                    "required_date",
                    "failure_observed_at",
                ]
            },
        ),
        (
            "ریسک و توقف",
            {
                "fields": [
                    "production_stopped",
                    "safety_risk",
                    "environmental_risk",
                ]
            },
        ),
        (
            "بررسی و تأیید",
            {
                "fields": [
                    "reviewed_by",
                    "reviewed_at",
                    "review_notes",
                    "rejection_reason",
                ]
            },
        ),
        (
            "وضعیت سیستمی",
            {
                "fields": [
                    "is_active",
                ]
            },
        ),
        (
            "اطلاعات ثبت",
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

    actions = [
        "mark_as_submitted",
        "mark_as_under_review",
        "mark_as_cancelled",
    ]

    @admin.action(description="تغییر وضعیت به ثبت‌شده")
    def mark_as_submitted(self, request, queryset):
        queryset.update(status="submitted")

    @admin.action(description="تغییر وضعیت به در حال بررسی")
    def mark_as_under_review(self, request, queryset):
        queryset.update(status="under_review")

    @admin.action(description="تغییر وضعیت به لغوشده")
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status="cancelled")


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = [
        "work_order_number",
        "title",
        "project",
        "asset",
        "maintenance_type",
        "priority",
        "status",
        "source",
        "supervisor",
        "planned_start",
        "planned_finish",
        "is_overdue_display",
        "is_active",
    ]

    list_filter = [
        "status",
        "priority",
        "maintenance_type",
        "source",
        "production_stopped",
        "permit_required",
        "lockout_tagout_required",
        "is_active",
        "project",
        "planned_start",
        "created_at",
    ]

    search_fields = [
        "work_order_number",
        "title",
        "description",
        "work_performed",
        "completion_notes",
        "project__code",
        "project__name",
        "asset__code",
        "asset__name",
        "location__code",
        "location__name",
        "work_request__request_number",
        "created_by__username",
        "supervisor__username",
    ]

    ordering = [
        "-created_at",
        "-id",
    ]

    autocomplete_fields = [
        "project",
        "work_request",
        "asset",
        "location",
        "created_by",
        "supervisor",
        "completed_by",
        "closed_by",
    ]

    readonly_fields = [
        "is_overdue_display",
        "planned_duration_hours_display",
        "actual_duration_hours_display",
        "created_at",
        "updated_at",
    ]

    date_hierarchy = "created_at"

    list_select_related = [
        "project",
        "work_request",
        "asset",
        "location",
        "created_by",
        "supervisor",
        "completed_by",
        "closed_by",
    ]

    inlines = [
        WorkOrderAssignmentInline,
        WorkOrderLaborInline,
        WorkOrderDowntimeInline,
        WorkOrderStatusHistoryInline,
    ]

    fieldsets = [
        (
            "اطلاعات اصلی",
            {
                "fields": [
                    "project",
                    "work_order_number",
                    "title",
                    "description",
                    "maintenance_type",
                    "priority",
                    "status",
                    "source",
                ]
            },
        ),
        (
            "منبع و ارتباطات",
            {
                "fields": [
                    "work_request",
                    "asset",
                    "location",
                ]
            },
        ),
        (
            "مسئولان",
            {
                "fields": [
                    "created_by",
                    "supervisor",
                    "completed_by",
                    "closed_by",
                ]
            },
        ),
        (
            "برنامه‌ریزی زمانی",
            {
                "fields": [
                    "planned_start",
                    "planned_finish",
                    "planned_duration_hours_display",
                    "is_overdue_display",
                ]
            },
        ),
        (
            "زمان‌های واقعی",
            {
                "fields": [
                    "actual_start",
                    "actual_finish",
                    "actual_duration_hours_display",
                    "closed_at",
                ]
            },
        ),
        (
            "نیروی انسانی و هزینه",
            {
                "fields": [
                    "estimated_labor_hours",
                    "actual_labor_hours",
                    "estimated_cost",
                    "actual_cost",
                ]
            },
        ),
        (
            "ایمنی و بهره‌برداری",
            {
                "fields": [
                    "production_stopped",
                    "permit_required",
                    "lockout_tagout_required",
                    "safety_notes",
                ]
            },
        ),
        (
            "نتیجه کار",
            {
                "fields": [
                    "work_performed",
                    "completion_notes",
                    "cancellation_reason",
                ]
            },
        ),
        (
            "وضعیت سیستمی",
            {
                "fields": [
                    "is_active",
                ]
            },
        ),
        (
            "اطلاعات ثبت",
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

    actions = [
        "mark_as_open",
        "mark_as_assigned",
        "mark_as_on_hold",
    ]

    @admin.display(
        boolean=True,
        description="سررسید گذشته",
    )
    def is_overdue_display(self, obj):
        return obj.is_overdue

    @admin.display(description="مدت برنامه‌ریزی‌شده")
    def planned_duration_hours_display(self, obj):
        if obj.planned_duration_hours is None:
            return "-"

        return f"{obj.planned_duration_hours} ساعت"

    @admin.display(description="مدت واقعی")
    def actual_duration_hours_display(self, obj):
        if obj.actual_duration_hours is None:
            return "-"

        return f"{obj.actual_duration_hours} ساعت"

    @admin.action(description="تغییر وضعیت به باز")
    def mark_as_open(self, request, queryset):
        queryset.update(status="open")

    @admin.action(description="تغییر وضعیت به تخصیص‌یافته")
    def mark_as_assigned(self, request, queryset):
        queryset.update(status="assigned")

    @admin.action(description="تغییر وضعیت به متوقف")
    def mark_as_on_hold(self, request, queryset):
        queryset.update(status="on_hold")


@admin.register(WorkOrderAssignment)
class WorkOrderAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "work_order",
        "user",
        "role",
        "assigned_by",
        "assigned_at",
        "removed_at",
        "is_active",
    ]

    list_filter = [
        "role",
        "is_active",
        "assigned_at",
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "user__username",
        "user__email",
        "assigned_by__username",
        "notes",
    ]

    autocomplete_fields = [
        "work_order",
        "user",
        "assigned_by",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "work_order",
        "user",
        "assigned_by",
    ]

    ordering = [
        "-assigned_at",
        "-id",
    ]


@admin.register(WorkOrderLabor)
class WorkOrderLaborAdmin(admin.ModelAdmin):
    list_display = [
        "work_order",
        "user",
        "work_date",
        "started_at",
        "finished_at",
        "hours",
        "hourly_rate",
        "labor_cost_display",
    ]

    list_filter = [
        "work_date",
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "user__username",
        "user__email",
        "description",
    ]

    autocomplete_fields = [
        "work_order",
        "user",
    ]

    readonly_fields = [
        "labor_cost_display",
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "work_order",
        "user",
    ]

    date_hierarchy = "work_date"

    ordering = [
        "-work_date",
        "-id",
    ]

    @admin.display(description="هزینه نیروی انسانی")
    def labor_cost_display(self, obj):
        return obj.labor_cost


@admin.register(WorkOrderDowntime)
class WorkOrderDowntimeAdmin(admin.ModelAdmin):
    list_display = [
        "work_order",
        "started_at",
        "finished_at",
        "duration_hours_display",
        "production_loss",
    ]

    list_filter = [
        "started_at",
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "reason",
        "notes",
    ]

    autocomplete_fields = [
        "work_order",
    ]

    readonly_fields = [
        "duration_hours_display",
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "work_order",
    ]

    date_hierarchy = "started_at"

    ordering = [
        "-started_at",
        "-id",
    ]

    @admin.display(description="مدت توقف")
    def duration_hours_display(self, obj):
        return f"{obj.duration_hours} ساعت"


@admin.register(WorkOrderFailure)
class WorkOrderFailureAdmin(admin.ModelAdmin):
    list_display = [
        "work_order",
        "failure_type",
        "failure_mode",
        "requires_follow_up",
        "follow_up_due_date",
        "updated_at",
    ]

    list_filter = [
        "failure_type",
        "requires_follow_up",
        "follow_up_due_date",
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "failure_mode",
        "symptom",
        "immediate_cause",
        "root_cause",
        "corrective_action",
        "preventive_action",
    ]

    autocomplete_fields = [
        "work_order",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    list_select_related = [
        "work_order",
    ]

    ordering = [
        "-updated_at",
        "-id",
    ]


@admin.register(WorkOrderStatusHistory)
class WorkOrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "work_order",
        "previous_status",
        "new_status",
        "changed_by",
        "changed_at",
    ]

    list_filter = [
        "previous_status",
        "new_status",
        "changed_at",
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "changed_by__username",
        "changed_by__email",
        "notes",
    ]

    autocomplete_fields = [
        "work_order",
        "changed_by",
    ]

    list_select_related = [
        "work_order",
        "changed_by",
    ]

    date_hierarchy = "changed_at"

    ordering = [
        "-changed_at",
        "-id",
    ]

    readonly_fields = [
        "work_order",
        "previous_status",
        "new_status",
        "changed_by",
        "changed_at",
        "notes",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
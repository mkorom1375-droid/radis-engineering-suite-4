from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderDowntime,
    WorkOrderFailure,
    WorkOrderLabor,
    WorkOrderSource,
    WorkOrderStatus,
    WorkOrderStatusHistory,
    WorkRequest,
    WorkRequestStatus,
)


class WorkRequestSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    asset_code = serializers.CharField(
        source="asset.code",
        read_only=True,
        allow_null=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
        allow_null=True,
    )

    location_code = serializers.CharField(
        source="location.code",
        read_only=True,
        allow_null=True,
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
    )

    requested_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    maintenance_type_display = serializers.CharField(
        source="get_maintenance_type_display",
        read_only=True,
    )

    priority_display = serializers.CharField(
        source="get_priority_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    work_order_id = serializers.SerializerMethodField()
    work_order_number = serializers.SerializerMethodField()

    class Meta:
        model = WorkRequest
        fields = [
            "id",
            "project",
            "project_name",
            "asset",
            "asset_code",
            "asset_name",
            "location",
            "location_code",
            "location_name",
            "request_number",
            "title",
            "description",
            "maintenance_type",
            "maintenance_type_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "required_date",
            "failure_observed_at",
            "production_stopped",
            "safety_risk",
            "environmental_risk",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "review_notes",
            "rejection_reason",
            "work_order_id",
            "work_order_number",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
            "work_order_id",
            "work_order_number",
        ]

    def get_requested_by_name(self, obj):
        user = obj.requested_by
        full_name = user.get_full_name().strip()

        return full_name or user.get_username()

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by_id:
            return None

        user = obj.reviewed_by
        full_name = user.get_full_name().strip()

        return full_name or user.get_username()

    def get_work_order_id(self, obj):
        try:
            return obj.work_order.id
        except WorkOrder.DoesNotExist:
            return None

    def get_work_order_number(self, obj):
        try:
            return obj.work_order.work_order_number
        except WorkOrder.DoesNotExist:
            return None

    def validate(self, attrs):
        instance = self.instance

        project = attrs.get(
            "project",
            getattr(instance, "project", None),
        )

        asset = attrs.get(
            "asset",
            getattr(instance, "asset", None),
        )

        location = attrs.get(
            "location",
            getattr(instance, "location", None),
        )

        requested_at = attrs.get(
            "requested_at",
            getattr(instance, "requested_at", None),
        )

        required_date = attrs.get(
            "required_date",
            getattr(instance, "required_date", None),
        )

        failure_observed_at = attrs.get(
            "failure_observed_at",
            getattr(instance, "failure_observed_at", None),
        )

        status = attrs.get(
            "status",
            getattr(instance, "status", WorkRequestStatus.DRAFT),
        )

        reviewed_by = attrs.get(
            "reviewed_by",
            getattr(instance, "reviewed_by", None),
        )

        reviewed_at = attrs.get(
            "reviewed_at",
            getattr(instance, "reviewed_at", None),
        )

        rejection_reason = attrs.get(
            "rejection_reason",
            getattr(instance, "rejection_reason", ""),
        )

        if project and not project.is_active:
            raise serializers.ValidationError(
                {
                    "project": (
                        "امکان ثبت درخواست تعمیرات در پروژه غیرفعال "
                        "وجود ندارد."
                    )
                }
            )

        if asset and project:
            if asset.project_id != project.id:
                raise serializers.ValidationError(
                    {
                        "asset": (
                            "تجهیز انتخاب‌شده باید متعلق به پروژه "
                            "درخواست باشد."
                        )
                    }
                )

            if not asset.is_active:
                raise serializers.ValidationError(
                    {
                        "asset": "تجهیز انتخاب‌شده غیرفعال است."
                    }
                )

        if location and project:
            if location.project_id != project.id:
                raise serializers.ValidationError(
                    {
                        "location": (
                            "موقعیت انتخاب‌شده باید متعلق به پروژه "
                            "درخواست باشد."
                        )
                    }
                )

            if not location.is_active:
                raise serializers.ValidationError(
                    {
                        "location": "موقعیت انتخاب‌شده غیرفعال است."
                    }
                )

        if asset and location:
            if (
                asset.location_id
                and asset.location_id != location.id
            ):
                raise serializers.ValidationError(
                    {
                        "location": (
                            "موقعیت درخواست با موقعیت ثبت‌شده برای "
                            "تجهیز مطابقت ندارد."
                        )
                    }
                )

        if (
            requested_at
            and required_date
            and required_date < requested_at
        ):
            raise serializers.ValidationError(
                {
                    "required_date": (
                        "تاریخ موردنیاز نمی‌تواند قبل از زمان "
                        "درخواست باشد."
                    )
                }
            )

        if (
            requested_at
            and failure_observed_at
            and failure_observed_at > requested_at
        ):
            raise serializers.ValidationError(
                {
                    "failure_observed_at": (
                        "زمان مشاهده خرابی نمی‌تواند بعد از زمان "
                        "درخواست باشد."
                    )
                }
            )

        if status == WorkRequestStatus.REJECTED:
            if not str(rejection_reason).strip():
                raise serializers.ValidationError(
                    {
                        "rejection_reason": (
                            "برای درخواست ردشده، ثبت دلیل رد الزامی است."
                        )
                    }
                )

        if status in {
            WorkRequestStatus.APPROVED,
            WorkRequestStatus.REJECTED,
            WorkRequestStatus.CONVERTED,
        }:
            if not reviewed_by:
                raise serializers.ValidationError(
                    {
                        "reviewed_by": (
                            "برای این وضعیت، تعیین بررسی‌کننده الزامی است."
                        )
                    }
                )

            if not reviewed_at:
                raise serializers.ValidationError(
                    {
                        "reviewed_at": (
                            "برای این وضعیت، ثبت زمان بررسی الزامی است."
                        )
                    }
                )

        return attrs


class WorkRequestSummarySerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
        allow_null=True,
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
    )

    priority_display = serializers.CharField(
        source="get_priority_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = WorkRequest
        fields = [
            "id",
            "request_number",
            "title",
            "project",
            "project_name",
            "asset",
            "asset_name",
            "location",
            "location_name",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "requested_at",
            "required_date",
            "production_stopped",
            "safety_risk",
            "is_active",
        ]


class WorkOrderAssignmentSerializer(serializers.ModelSerializer):
    work_order_number = serializers.CharField(
        source="work_order.work_order_number",
        read_only=True,
    )

    user_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()

    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    class Meta:
        model = WorkOrderAssignment
        fields = [
            "id",
            "work_order",
            "work_order_number",
            "user",
            "user_name",
            "role",
            "role_display",
            "assigned_by",
            "assigned_by_name",
            "assigned_at",
            "removed_at",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or obj.user.get_username()

    def get_assigned_by_name(self, obj):
        full_name = obj.assigned_by.get_full_name().strip()
        return full_name or obj.assigned_by.get_username()

    def validate(self, attrs):
        instance = self.instance

        assigned_at = attrs.get(
            "assigned_at",
            getattr(instance, "assigned_at", None),
        )

        removed_at = attrs.get(
            "removed_at",
            getattr(instance, "removed_at", None),
        )

        is_active = attrs.get(
            "is_active",
            getattr(instance, "is_active", True),
        )

        if (
            assigned_at
            and removed_at
            and removed_at < assigned_at
        ):
            raise serializers.ValidationError(
                {
                    "removed_at": (
                        "زمان حذف تخصیص نمی‌تواند قبل از زمان "
                        "تخصیص باشد."
                    )
                }
            )

        if not is_active and not removed_at:
            raise serializers.ValidationError(
                {
                    "removed_at": (
                        "برای تخصیص غیرفعال، ثبت زمان حذف الزامی است."
                    )
                }
            )

        if is_active and removed_at:
            raise serializers.ValidationError(
                {
                    "removed_at": (
                        "تخصیص فعال نمی‌تواند زمان حذف داشته باشد."
                    )
                }
            )

        return attrs


class WorkOrderLaborSerializer(serializers.ModelSerializer):
    work_order_number = serializers.CharField(
        source="work_order.work_order_number",
        read_only=True,
    )

    user_name = serializers.SerializerMethodField()
    labor_cost = serializers.DecimalField(
        max_digits=22,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = WorkOrderLabor
        fields = [
            "id",
            "work_order",
            "work_order_number",
            "user",
            "user_name",
            "work_date",
            "started_at",
            "finished_at",
            "hours",
            "hourly_rate",
            "labor_cost",
            "description",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
            "labor_cost",
        ]

    def get_user_name(self, obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or obj.user.get_username()

    def validate(self, attrs):
        instance = self.instance

        work_date = attrs.get(
            "work_date",
            getattr(instance, "work_date", None),
        )

        started_at = attrs.get(
            "started_at",
            getattr(instance, "started_at", None),
        )

        finished_at = attrs.get(
            "finished_at",
            getattr(instance, "finished_at", None),
        )

        if (
            started_at
            and finished_at
            and finished_at < started_at
        ):
            raise serializers.ValidationError(
                {
                    "finished_at": (
                        "زمان پایان نمی‌تواند قبل از زمان شروع باشد."
                    )
                }
            )

        if (
            started_at
            and work_date
            and started_at.date() != work_date
        ):
            raise serializers.ValidationError(
                {
                    "work_date": (
                        "تاریخ کار باید با زمان شروع ثبت‌شده "
                        "مطابقت داشته باشد."
                    )
                }
            )

        return attrs


class WorkOrderDowntimeSerializer(serializers.ModelSerializer):
    work_order_number = serializers.CharField(
        source="work_order.work_order_number",
        read_only=True,
    )

    duration_hours = serializers.FloatField(
        read_only=True,
    )

    class Meta:
        model = WorkOrderDowntime
        fields = [
            "id",
            "work_order",
            "work_order_number",
            "started_at",
            "finished_at",
            "duration_hours",
            "production_loss",
            "reason",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "duration_hours",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        started_at = attrs.get(
            "started_at",
            getattr(instance, "started_at", None),
        )

        finished_at = attrs.get(
            "finished_at",
            getattr(instance, "finished_at", None),
        )

        if (
            started_at
            and finished_at
            and finished_at < started_at
        ):
            raise serializers.ValidationError(
                {
                    "finished_at": (
                        "پایان توقف نمی‌تواند قبل از شروع توقف باشد."
                    )
                }
            )

        return attrs


class WorkOrderFailureSerializer(serializers.ModelSerializer):
    work_order_number = serializers.CharField(
        source="work_order.work_order_number",
        read_only=True,
    )

    failure_type_display = serializers.CharField(
        source="get_failure_type_display",
        read_only=True,
    )

    class Meta:
        model = WorkOrderFailure
        fields = [
            "id",
            "work_order",
            "work_order_number",
            "failure_type",
            "failure_type_display",
            "failure_mode",
            "symptom",
            "immediate_cause",
            "root_cause",
            "corrective_action",
            "preventive_action",
            "requires_follow_up",
            "follow_up_due_date",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        requires_follow_up = attrs.get(
            "requires_follow_up",
            getattr(instance, "requires_follow_up", False),
        )

        follow_up_due_date = attrs.get(
            "follow_up_due_date",
            getattr(instance, "follow_up_due_date", None),
        )

        if requires_follow_up and not follow_up_due_date:
            raise serializers.ValidationError(
                {
                    "follow_up_due_date": (
                        "برای خرابی نیازمند پیگیری، ثبت مهلت "
                        "پیگیری الزامی است."
                    )
                }
            )

        if not requires_follow_up and follow_up_due_date:
            raise serializers.ValidationError(
                {
                    "follow_up_due_date": (
                        "برای ثبت مهلت پیگیری، گزینه نیازمند "
                        "پیگیری را فعال کنید."
                    )
                }
            )

        return attrs


class WorkOrderStatusHistorySerializer(serializers.ModelSerializer):
    work_order_number = serializers.CharField(
        source="work_order.work_order_number",
        read_only=True,
    )

    changed_by_name = serializers.SerializerMethodField()

    previous_status_display = serializers.CharField(
        source="get_previous_status_display",
        read_only=True,
    )

    new_status_display = serializers.CharField(
        source="get_new_status_display",
        read_only=True,
    )

    class Meta:
        model = WorkOrderStatusHistory
        fields = [
            "id",
            "work_order",
            "work_order_number",
            "previous_status",
            "previous_status_display",
            "new_status",
            "new_status_display",
            "changed_by",
            "changed_by_name",
            "changed_at",
            "notes",
        ]

        read_only_fields = fields

    def get_changed_by_name(self, obj):
        full_name = obj.changed_by.get_full_name().strip()
        return full_name or obj.changed_by.get_username()


class WorkOrderSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    work_request_number = serializers.CharField(
        source="work_request.request_number",
        read_only=True,
        allow_null=True,
    )

    asset_code = serializers.CharField(
        source="asset.code",
        read_only=True,
        allow_null=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
        allow_null=True,
    )

    location_code = serializers.CharField(
        source="location.code",
        read_only=True,
        allow_null=True,
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
    )

    created_by_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()
    closed_by_name = serializers.SerializerMethodField()

    maintenance_type_display = serializers.CharField(
        source="get_maintenance_type_display",
        read_only=True,
    )

    priority_display = serializers.CharField(
        source="get_priority_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True,
    )

    is_overdue = serializers.BooleanField(
        read_only=True,
    )

    planned_duration_hours = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )

    actual_duration_hours = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )

    assignments = WorkOrderAssignmentSerializer(
        many=True,
        read_only=True,
    )

    labor_entries = WorkOrderLaborSerializer(
        many=True,
        read_only=True,
    )

    downtime_entries = WorkOrderDowntimeSerializer(
        many=True,
        read_only=True,
    )

    failure = WorkOrderFailureSerializer(
        read_only=True,
    )

    status_history = WorkOrderStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "project",
            "project_name",
            "work_request",
            "work_request_number",
            "asset",
            "asset_code",
            "asset_name",
            "location",
            "location_code",
            "location_name",
            "work_order_number",
            "title",
            "description",
            "maintenance_type",
            "maintenance_type_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "source",
            "source_display",
            "created_by",
            "created_by_name",
            "supervisor",
            "supervisor_name",
            "planned_start",
            "planned_finish",
            "actual_start",
            "actual_finish",
            "planned_duration_hours",
            "actual_duration_hours",
            "is_overdue",
            "estimated_labor_hours",
            "actual_labor_hours",
            "estimated_cost",
            "actual_cost",
            "production_stopped",
            "permit_required",
            "lockout_tagout_required",
            "safety_notes",
            "work_performed",
            "completion_notes",
            "cancellation_reason",
            "completed_by",
            "completed_by_name",
            "closed_by",
            "closed_by_name",
            "closed_at",
            "assignments",
            "labor_entries",
            "downtime_entries",
            "failure",
            "status_history",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "is_overdue",
            "planned_duration_hours",
            "actual_duration_hours",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        full_name = obj.created_by.get_full_name().strip()
        return full_name or obj.created_by.get_username()

    def get_supervisor_name(self, obj):
        if not obj.supervisor_id:
            return None

        full_name = obj.supervisor.get_full_name().strip()
        return full_name or obj.supervisor.get_username()

    def get_completed_by_name(self, obj):
        if not obj.completed_by_id:
            return None

        full_name = obj.completed_by.get_full_name().strip()
        return full_name or obj.completed_by.get_username()

    def get_closed_by_name(self, obj):
        if not obj.closed_by_id:
            return None

        full_name = obj.closed_by.get_full_name().strip()
        return full_name or obj.closed_by.get_username()

    def validate(self, attrs):
        instance = self.instance

        project = attrs.get(
            "project",
            getattr(instance, "project", None),
        )

        work_request = attrs.get(
            "work_request",
            getattr(instance, "work_request", None),
        )

        asset = attrs.get(
            "asset",
            getattr(instance, "asset", None),
        )

        location = attrs.get(
            "location",
            getattr(instance, "location", None),
        )

        source = attrs.get(
            "source",
            getattr(instance, "source", WorkOrderSource.MANUAL),
        )

        status = attrs.get(
            "status",
            getattr(instance, "status", WorkOrderStatus.DRAFT),
        )

        planned_start = attrs.get(
            "planned_start",
            getattr(instance, "planned_start", None),
        )

        planned_finish = attrs.get(
            "planned_finish",
            getattr(instance, "planned_finish", None),
        )

        actual_start = attrs.get(
            "actual_start",
            getattr(instance, "actual_start", None),
        )

        actual_finish = attrs.get(
            "actual_finish",
            getattr(instance, "actual_finish", None),
        )

        completed_by = attrs.get(
            "completed_by",
            getattr(instance, "completed_by", None),
        )

        closed_by = attrs.get(
            "closed_by",
            getattr(instance, "closed_by", None),
        )

        closed_at = attrs.get(
            "closed_at",
            getattr(instance, "closed_at", None),
        )

        work_performed = attrs.get(
            "work_performed",
            getattr(instance, "work_performed", ""),
        )

        cancellation_reason = attrs.get(
            "cancellation_reason",
            getattr(instance, "cancellation_reason", ""),
        )

        if project and not project.is_active:
            raise serializers.ValidationError(
                {
                    "project": (
                        "امکان ثبت دستورکار در پروژه غیرفعال وجود ندارد."
                    )
                }
            )

        if work_request and project:
            if work_request.project_id != project.id:
                raise serializers.ValidationError(
                    {
                        "work_request": (
                            "درخواست تعمیرات باید متعلق به همان پروژه باشد."
                        )
                    }
                )

            if source != WorkOrderSource.WORK_REQUEST:
                raise serializers.ValidationError(
                    {
                        "source": (
                            "منبع دستورکار مرتبط با درخواست باید "
                            "«درخواست تعمیرات» باشد."
                        )
                    }
                )

        if (
            source == WorkOrderSource.WORK_REQUEST
            and not work_request
        ):
            raise serializers.ValidationError(
                {
                    "work_request": (
                        "برای این منبع، انتخاب درخواست تعمیرات الزامی است."
                    )
                }
            )

        if asset and project:
            if asset.project_id != project.id:
                raise serializers.ValidationError(
                    {
                        "asset": (
                            "تجهیز انتخاب‌شده باید متعلق به پروژه "
                            "دستورکار باشد."
                        )
                    }
                )

            if not asset.is_active:
                raise serializers.ValidationError(
                    {
                        "asset": "تجهیز انتخاب‌شده غیرفعال است."
                    }
                )

        if location and project:
            if location.project_id != project.id:
                raise serializers.ValidationError(
                    {
                        "location": (
                            "موقعیت انتخاب‌شده باید متعلق به پروژه "
                            "دستورکار باشد."
                        )
                    }
                )

            if not location.is_active:
                raise serializers.ValidationError(
                    {
                        "location": "موقعیت انتخاب‌شده غیرفعال است."
                    }
                )

        if asset and location:
            if (
                asset.location_id
                and asset.location_id != location.id
            ):
                raise serializers.ValidationError(
                    {
                        "location": (
                            "موقعیت دستورکار با موقعیت ثبت‌شده برای "
                            "تجهیز مطابقت ندارد."
                        )
                    }
                )

        if (
            planned_start
            and planned_finish
            and planned_finish < planned_start
        ):
            raise serializers.ValidationError(
                {
                    "planned_finish": (
                        "پایان برنامه‌ریزی‌شده نمی‌تواند قبل از "
                        "شروع باشد."
                    )
                }
            )

        if (
            actual_start
            and actual_finish
            and actual_finish < actual_start
        ):
            raise serializers.ValidationError(
                {
                    "actual_finish": (
                        "پایان واقعی نمی‌تواند قبل از شروع واقعی باشد."
                    )
                }
            )

        if status == WorkOrderStatus.IN_PROGRESS:
            if not actual_start:
                raise serializers.ValidationError(
                    {
                        "actual_start": (
                            "برای دستورکار در حال انجام، ثبت زمان "
                            "شروع واقعی الزامی است."
                        )
                    }
                )

        if status in {
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CLOSED,
        }:
            completion_errors = {}

            if not actual_start:
                completion_errors["actual_start"] = (
                    "برای تکمیل دستورکار، ثبت زمان شروع واقعی الزامی است."
                )

            if not actual_finish:
                completion_errors["actual_finish"] = (
                    "برای تکمیل دستورکار، ثبت زمان پایان واقعی الزامی است."
                )

            if not completed_by:
                completion_errors["completed_by"] = (
                    "برای تکمیل دستورکار، تعیین تکمیل‌کننده الزامی است."
                )

            if not str(work_performed).strip():
                completion_errors["work_performed"] = (
                    "برای تکمیل دستورکار، شرح کار انجام‌شده الزامی است."
                )

            if completion_errors:
                raise serializers.ValidationError(completion_errors)

        if status == WorkOrderStatus.CLOSED:
            close_errors = {}

            if not closed_by:
                close_errors["closed_by"] = (
                    "برای بستن دستورکار، تعیین کاربر تأییدکننده الزامی است."
                )

            if not closed_at:
                close_errors["closed_at"] = (
                    "برای بستن دستورکار، ثبت زمان بسته‌شدن الزامی است."
                )

            if close_errors:
                raise serializers.ValidationError(close_errors)

        if status == WorkOrderStatus.CANCELLED:
            if not str(cancellation_reason).strip():
                raise serializers.ValidationError(
                    {
                        "cancellation_reason": (
                            "برای دستورکار لغوشده، ثبت دلیل لغو الزامی است."
                        )
                    }
                )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        previous_status = instance.status
        work_order = super().update(instance, validated_data)

        if previous_status != work_order.status:
            request = self.context.get("request")
            changed_by = None

            if request and request.user.is_authenticated:
                changed_by = request.user

            if changed_by:
                WorkOrderStatusHistory.objects.create(
                    work_order=work_order,
                    previous_status=previous_status,
                    new_status=work_order.status,
                    changed_by=changed_by,
                    changed_at=timezone.now(),
                    notes="Status changed through API",
                )

        return work_order


class WorkOrderSummarySerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
        allow_null=True,
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
    )

    supervisor_name = serializers.SerializerMethodField()

    priority_display = serializers.CharField(
        source="get_priority_display",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    maintenance_type_display = serializers.CharField(
        source="get_maintenance_type_display",
        read_only=True,
    )

    is_overdue = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "work_order_number",
            "title",
            "project",
            "project_name",
            "asset",
            "asset_name",
            "location",
            "location_name",
            "maintenance_type",
            "maintenance_type_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "supervisor",
            "supervisor_name",
            "planned_start",
            "planned_finish",
            "is_overdue",
            "production_stopped",
            "is_active",
            "created_at",
        ]

    def get_supervisor_name(self, obj):
        if not obj.supervisor_id:
            return None

        full_name = obj.supervisor.get_full_name().strip()
        return full_name or obj.supervisor.get_username()


class WorkRequestReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkRequest
        fields = [
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "rejection_reason",
        ]

    def validate_status(self, value):
        allowed_statuses = {
            WorkRequestStatus.UNDER_REVIEW,
            WorkRequestStatus.APPROVED,
            WorkRequestStatus.REJECTED,
            WorkRequestStatus.CANCELLED,
        }

        if value not in allowed_statuses:
            raise serializers.ValidationError(
                "وضعیت انتخاب‌شده برای عملیات بررسی مجاز نیست."
            )

        return value

    def validate(self, attrs):
        status = attrs.get(
            "status",
            getattr(self.instance, "status", None),
        )

        reviewed_by = attrs.get(
            "reviewed_by",
            getattr(self.instance, "reviewed_by", None),
        )

        reviewed_at = attrs.get(
            "reviewed_at",
            getattr(self.instance, "reviewed_at", None),
        )

        rejection_reason = attrs.get(
            "rejection_reason",
            getattr(self.instance, "rejection_reason", ""),
        )

        if status in {
            WorkRequestStatus.APPROVED,
            WorkRequestStatus.REJECTED,
        }:
            if not reviewed_by:
                raise serializers.ValidationError(
                    {
                        "reviewed_by": (
                            "تعیین بررسی‌کننده الزامی است."
                        )
                    }
                )

            if not reviewed_at:
                raise serializers.ValidationError(
                    {
                        "reviewed_at": (
                            "ثبت زمان بررسی الزامی است."
                        )
                    }
                )

        if status == WorkRequestStatus.REJECTED:
            if not str(rejection_reason).strip():
                raise serializers.ValidationError(
                    {
                        "rejection_reason": (
                            "برای رد درخواست، ثبت دلیل رد الزامی است."
                        )
                    }
                )

        return attrs


class WorkRequestConvertSerializer(serializers.Serializer):
    work_order_number = serializers.CharField(
        max_length=50,
    )

    title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    supervisor = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrder._meta.get_field(
            "supervisor"
        ).remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )

    planned_start = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    planned_finish = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    estimated_labor_hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default="0.00",
    )

    estimated_cost = serializers.DecimalField(
        max_digits=16,
        decimal_places=2,
        required=False,
        default="0.00",
    )

    permit_required = serializers.BooleanField(
        required=False,
        default=False,
    )

    lockout_tagout_required = serializers.BooleanField(
        required=False,
        default=False,
    )

    safety_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, attrs):
        work_request = self.context["work_request"]

        if work_request.status != WorkRequestStatus.APPROVED:
            raise serializers.ValidationError(
                "فقط درخواست تأییدشده قابل تبدیل به دستورکار است."
            )

        if hasattr(work_request, "work_order"):
            raise serializers.ValidationError(
                "برای این درخواست قبلاً دستورکار ایجاد شده است."
            )

        planned_start = attrs.get("planned_start")
        planned_finish = attrs.get("planned_finish")

        if (
            planned_start
            and planned_finish
            and planned_finish < planned_start
        ):
            raise serializers.ValidationError(
                {
                    "planned_finish": (
                        "پایان برنامه‌ریزی‌شده نمی‌تواند قبل از "
                        "شروع باشد."
                    )
                }
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        work_request = self.context["work_request"]
        created_by = self.context["created_by"]

        work_order = WorkOrder.objects.create(
            project=work_request.project,
            work_request=work_request,
            asset=work_request.asset,
            location=work_request.location,
            work_order_number=validated_data["work_order_number"],
            title=(
                validated_data.get("title")
                or work_request.title
            ),
            description=(
                validated_data.get("description")
                or work_request.description
            ),
            maintenance_type=work_request.maintenance_type,
            priority=work_request.priority,
            status=WorkOrderStatus.OPEN,
            source=WorkOrderSource.WORK_REQUEST,
            created_by=created_by,
            supervisor=validated_data.get("supervisor"),
            planned_start=validated_data.get("planned_start"),
            planned_finish=validated_data.get("planned_finish"),
            estimated_labor_hours=validated_data.get(
                "estimated_labor_hours",
                "0.00",
            ),
            estimated_cost=validated_data.get(
                "estimated_cost",
                "0.00",
            ),
            production_stopped=work_request.production_stopped,
            permit_required=validated_data.get(
                "permit_required",
                False,
            ),
            lockout_tagout_required=validated_data.get(
                "lockout_tagout_required",
                False,
            ),
            safety_notes=validated_data.get(
                "safety_notes",
                "",
            ),
        )

        work_request.status = WorkRequestStatus.CONVERTED
        work_request.reviewed_by = (
            work_request.reviewed_by or created_by
        )
        work_request.reviewed_at = (
            work_request.reviewed_at or timezone.now()
        )
        work_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        return work_order
from rest_framework import serializers

from .models import (
    PreventiveMaintenanceGeneration,
    PreventiveMaintenancePlan,
    PreventiveMaintenanceTask,
    PreventiveMaintenanceTaskResult,
)


class PreventiveMaintenanceTaskSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = PreventiveMaintenanceTask
        fields = [
            "id",
            "plan",
            "sequence",
            "task_type",
            "title",
            "description",
            "acceptance_criteria",
            "estimated_duration_minutes",
            "requires_shutdown",
            "requires_photo",
            "requires_measurement",
            "measurement_unit",
            "minimum_acceptable_value",
            "maximum_acceptable_value",
            "is_mandatory",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        requires_measurement = attrs.get(
            "requires_measurement",
            getattr(
                instance,
                "requires_measurement",
                False,
            ),
        )

        measurement_unit = attrs.get(
            "measurement_unit",
            getattr(
                instance,
                "measurement_unit",
                "",
            ),
        )

        minimum_value = attrs.get(
            "minimum_acceptable_value",
            getattr(
                instance,
                "minimum_acceptable_value",
                None,
            ),
        )

        maximum_value = attrs.get(
            "maximum_acceptable_value",
            getattr(
                instance,
                "maximum_acceptable_value",
                None,
            ),
        )

        if (
            minimum_value is not None
            and maximum_value is not None
            and maximum_value < minimum_value
        ):
            raise serializers.ValidationError(
                {
                    "maximum_acceptable_value": (
                        "حداکثر مقدار نمی‌تواند کمتر از "
                        "حداقل مقدار باشد."
                    )
                }
            )

        if (
            minimum_value is not None
            or maximum_value is not None
        ) and not requires_measurement:
            raise serializers.ValidationError(
                {
                    "requires_measurement": (
                        "برای ثبت حدود پذیرش، "
                        "اندازه‌گیری باید فعال باشد."
                    )
                }
            )

        if (
            requires_measurement
            and not str(measurement_unit).strip()
        ):
            raise serializers.ValidationError(
                {
                    "measurement_unit": (
                        "برای فعالیت اندازه‌گیری، "
                        "ثبت واحد الزامی است."
                    )
                }
            )

        return attrs


class PreventiveMaintenanceTaskNestedSerializer(
    PreventiveMaintenanceTaskSerializer
):
    class Meta(
        PreventiveMaintenanceTaskSerializer.Meta
    ):
        fields = [
            field
            for field in (
                PreventiveMaintenanceTaskSerializer
                .Meta
                .fields
            )
            if field != "plan"
        ]


class PreventiveMaintenancePlanListSerializer(
    serializers.ModelSerializer
):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
    )

    supervisor_name = serializers.SerializerMethodField()

    task_count = serializers.IntegerField(
        read_only=True,
    )

    is_due = serializers.BooleanField(
        read_only=True,
    )

    generation_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )

    is_ready_for_generation = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = PreventiveMaintenancePlan
        fields = [
            "id",
            "project",
            "project_name",
            "plan_number",
            "title",
            "asset",
            "asset_name",
            "location",
            "location_name",
            "status",
            "maintenance_type",
            "priority",
            "frequency",
            "start_date",
            "end_date",
            "last_due_date",
            "next_due_date",
            "generation_date",
            "generation_lead_days",
            "auto_generate_work_order",
            "supervisor",
            "supervisor_name",
            "task_count",
            "is_due",
            "is_ready_for_generation",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_due_date",
            "generation_date",
            "task_count",
            "is_due",
            "is_ready_for_generation",
            "created_at",
            "updated_at",
        ]

    def get_supervisor_name(self, obj):
        if not obj.supervisor:
            return None

        full_name = obj.supervisor.get_full_name()

        return (
            full_name.strip()
            or getattr(
                obj.supervisor,
                "username",
                str(obj.supervisor),
            )
        )


class PreventiveMaintenancePlanDetailSerializer(
    serializers.ModelSerializer
):
    tasks = PreventiveMaintenanceTaskNestedSerializer(
        many=True,
        read_only=True,
    )

    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
    )

    supervisor_name = serializers.SerializerMethodField()

    created_by_name = serializers.SerializerMethodField()

    is_due = serializers.BooleanField(
        read_only=True,
    )

    generation_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )

    is_ready_for_generation = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = PreventiveMaintenancePlan
        fields = [
            "id",
            "project",
            "project_name",
            "plan_number",
            "title",
            "description",
            "asset",
            "asset_name",
            "location",
            "location_name",
            "status",
            "maintenance_type",
            "priority",
            "frequency",
            "custom_interval_days",
            "start_date",
            "end_date",
            "last_due_date",
            "next_due_date",
            "generation_date",
            "generation_lead_days",
            "auto_generate_work_order",
            "allow_duplicate_open_orders",
            "estimated_duration_hours",
            "estimated_labor_hours",
            "estimated_cost",
            "supervisor",
            "supervisor_name",
            "safety_instructions",
            "required_tools",
            "required_materials",
            "permit_required",
            "lockout_tagout_required",
            "production_stop_required",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "is_active",
            "is_due",
            "is_ready_for_generation",
            "tasks",
        ]
        read_only_fields = [
            "id",
            "last_due_date",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "generation_date",
            "is_due",
            "is_ready_for_generation",
        ]

    def get_supervisor_name(self, obj):
        return self._get_user_display_name(
            obj.supervisor
        )

    def get_created_by_name(self, obj):
        return self._get_user_display_name(
            obj.created_by
        )

    @staticmethod
    def _get_user_display_name(user):
        if not user:
            return None

        full_name = user.get_full_name()

        return (
            full_name.strip()
            or getattr(
                user,
                "username",
                str(user),
            )
        )

    def validate(self, attrs):
        instance = self.instance

        frequency = attrs.get(
            "frequency",
            getattr(
                instance,
                "frequency",
                None,
            ),
        )

        custom_interval_days = attrs.get(
            "custom_interval_days",
            getattr(
                instance,
                "custom_interval_days",
                None,
            ),
        )

        start_date = attrs.get(
            "start_date",
            getattr(
                instance,
                "start_date",
                None,
            ),
        )

        end_date = attrs.get(
            "end_date",
            getattr(
                instance,
                "end_date",
                None,
            ),
        )

        if (
            frequency == "custom_days"
            and not custom_interval_days
        ):
            raise serializers.ValidationError(
                {
                    "custom_interval_days": (
                        "برای تناوب سفارشی، "
                        "تعداد روز باید مشخص شود."
                    )
                }
            )

        if (
            frequency != "custom_days"
            and custom_interval_days
        ):
            raise serializers.ValidationError(
                {
                    "custom_interval_days": (
                        "تعداد روز سفارشی فقط برای "
                        "تناوب سفارشی مجاز است."
                    )
                }
            )

        if (
            start_date
            and end_date
            and end_date < start_date
        ):
            raise serializers.ValidationError(
                {
                    "end_date": (
                        "تاریخ پایان نمی‌تواند قبل از "
                        "تاریخ شروع باشد."
                    )
                }
            )

        project = attrs.get(
            "project",
            getattr(
                instance,
                "project",
                None,
            ),
        )

        asset = attrs.get(
            "asset",
            getattr(
                instance,
                "asset",
                None,
            ),
        )

        location = attrs.get(
            "location",
            getattr(
                instance,
                "location",
                None,
            ),
        )

        if project and asset:
            asset_project_id = getattr(
                asset,
                "project_id",
                None,
            )

            if (
                asset_project_id is not None
                and asset_project_id != project.id
            ):
                raise serializers.ValidationError(
                    {
                        "asset": (
                            "تجهیز انتخاب‌شده متعلق به "
                            "این پروژه نیست."
                        )
                    }
                )

        if project and location:
            location_project_id = getattr(
                location,
                "project_id",
                None,
            )

            if (
                location_project_id is not None
                and location_project_id != project.id
            ):
                raise serializers.ValidationError(
                    {
                        "location": (
                            "موقعیت انتخاب‌شده متعلق به "
                            "این پروژه نیست."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")

        if (
            request
            and request.user
            and request.user.is_authenticated
        ):
            validated_data["created_by"] = request.user

        plan = PreventiveMaintenancePlan(
            **validated_data
        )

        plan.full_clean()
        plan.save()

        return plan

    def update(self, instance, validated_data):
        validated_data.pop(
            "created_by",
            None,
        )

        for field, value in validated_data.items():
            setattr(
                instance,
                field,
                value,
            )

        instance.full_clean()
        instance.save()

        return instance


class PreventiveMaintenanceGenerationSerializer(
    serializers.ModelSerializer
):
    plan_number = serializers.CharField(
        source="plan.plan_number",
        read_only=True,
    )

    plan_title = serializers.CharField(
        source="plan.title",
        read_only=True,
    )

    work_order_number = serializers.CharField(
        source="work_order.work_order_number",
        read_only=True,
        allow_null=True,
    )

    generated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PreventiveMaintenanceGeneration
        fields = [
            "id",
            "plan",
            "plan_number",
            "plan_title",
            "due_date",
            "scheduled_generation_date",
            "status",
            "work_order",
            "work_order_number",
            "generated_at",
            "generated_by",
            "generated_by_name",
            "error_message",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_generated_by_name(self, obj):
        if not obj.generated_by:
            return None

        full_name = obj.generated_by.get_full_name()

        return (
            full_name.strip()
            or getattr(
                obj.generated_by,
                "username",
                str(obj.generated_by),
            )
        )


class PreventiveMaintenanceTaskResultSerializer(
    serializers.ModelSerializer
):
    task_title = serializers.CharField(
        source="task.title",
        read_only=True,
    )

    task_sequence = serializers.IntegerField(
        source="task.sequence",
        read_only=True,
    )

    measurement_unit = serializers.CharField(
        source="task.measurement_unit",
        read_only=True,
    )

    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PreventiveMaintenanceTaskResult
        fields = [
            "id",
            "generation",
            "task",
            "task_sequence",
            "task_title",
            "is_completed",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "measured_value",
            "measurement_unit",
            "result_is_acceptable",
            "result_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "result_is_acceptable",
            "created_at",
            "updated_at",
        ]

    def get_completed_by_name(self, obj):
        if not obj.completed_by:
            return None

        full_name = obj.completed_by.get_full_name()

        return (
            full_name.strip()
            or getattr(
                obj.completed_by,
                "username",
                str(obj.completed_by),
            )
        )

    def validate(self, attrs):
        instance = self.instance

        task = attrs.get(
            "task",
            getattr(
                instance,
                "task",
                None,
            ),
        )

        generation = attrs.get(
            "generation",
            getattr(
                instance,
                "generation",
                None,
            ),
        )

        is_completed = attrs.get(
            "is_completed",
            getattr(
                instance,
                "is_completed",
                False,
            ),
        )

        measured_value = attrs.get(
            "measured_value",
            getattr(
                instance,
                "measured_value",
                None,
            ),
        )

        if (
            task
            and generation
            and task.plan_id != generation.plan_id
        ):
            raise serializers.ValidationError(
                {
                    "task": (
                        "فعالیت انتخاب‌شده متعلق به "
                        "برنامه این سابقه تولید نیست."
                    )
                }
            )

        if (
            task
            and task.requires_measurement
            and is_completed
            and measured_value is None
        ):
            raise serializers.ValidationError(
                {
                    "measured_value": (
                        "ثبت مقدار اندازه‌گیری‌شده "
                        "الزامی است."
                    )
                }
            )

        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")

        is_completed = validated_data.get(
            "is_completed",
            instance.is_completed,
        )

        measured_value = validated_data.get(
            "measured_value",
            instance.measured_value,
        )

        result_notes = validated_data.get(
            "result_notes",
            instance.result_notes,
        )

        if is_completed:
            user = None

            if (
                request
                and request.user
                and request.user.is_authenticated
            ):
                user = request.user

            instance.mark_completed(
                user=user,
                measured_value=measured_value,
                notes=result_notes,
            )

            return instance

        instance.is_completed = False
        instance.completed_at = None
        instance.completed_by = None
        instance.measured_value = measured_value
        instance.result_notes = str(
            result_notes
        ).strip()

        instance.evaluate_result()
        instance.full_clean()
        instance.save()

        return instance
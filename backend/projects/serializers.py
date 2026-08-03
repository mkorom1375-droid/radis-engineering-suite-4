from rest_framework import serializers

from .models import (
    Project,
    ProjectNumberingSettings,
    ProjectStage,
)
 

class ProjectNumberingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectNumberingSettings
        fields = [
            "id",
            "organization",
            "prefix",
            "separator",
            "next_number",
            "padding",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "updated_at",
        ]

    def validate_prefix(self, value):
        return value.strip().upper()

    def validate_separator(self, value):
        value = value.strip()
        if len(value) > 3:
            raise serializers.ValidationError(
                "جداکننده نمی‌تواند بیشتر از سه نویسه باشد."
            )
        return value

    def validate_next_number(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "شماره بعدی باید حداقل یک باشد."
            )
        return value

    def validate_padding(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError(
                "تعداد رقم‌های شماره باید بین ۱ و ۱۰ باشد."
            )
        return value


class ProjectStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStage
        fields = [
            "id",
            "project",
            "code",
            "name",
            "description",
            "order",
            "status",
            "weight",
            "planned_start",
            "planned_end",
            "actual_start",
            "actual_end",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "code": {
                "required": False,
                "allow_blank": True,
            },
            "order": {
                "required": False,
            },
            "weight": {
                "required": False,
            },
        }

    def validate(self, attrs):
        planned_start = attrs.get(
            "planned_start",
            getattr(self.instance, "planned_start", None),
        )
        planned_end = attrs.get(
            "planned_end",
            getattr(self.instance, "planned_end", None),
        )
        actual_start = attrs.get(
            "actual_start",
            getattr(self.instance, "actual_start", None),
        )
        actual_end = attrs.get(
            "actual_end",
            getattr(self.instance, "actual_end", None),
        )
        if planned_start and planned_end and planned_end < planned_start:
            raise serializers.ValidationError(
                {"planned_end": "پایان برنامه‌ریزی‌شده قبل از شروع است."}
            )
        if actual_start and actual_end and actual_end < actual_start:
            raise serializers.ValidationError(
                {"actual_end": "پایان واقعی قبل از شروع است."}
            )
        if attrs.get("weight", getattr(self.instance, "weight", 1)) <= 0:
            raise serializers.ValidationError(
                {"weight": "وزن مرحله باید بزرگ‌تر از صفر باشد."}
            )
        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()
    stage_count = serializers.SerializerMethodField()
    completed_stage_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "organization",
            "code",
            "name",
            "description",
            "start_date",
            "end_date",
            "is_active",
            "progress_percent",
            "stage_count",
            "completed_stage_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "progress_percent",
            "stage_count",
            "completed_stage_count",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "code": {
                "required": False,
                "allow_blank": True,
            },
        }

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "تاریخ پایان پروژه قبل از تاریخ شروع است."}
            )
        return attrs

    def get_progress_percent(self, obj):
        return str(obj.progress_percent)

    def get_stage_count(self, obj):
        return obj.stages.filter(is_active=True).count()

    def get_completed_stage_count(self, obj):
        return obj.completed_stage_count

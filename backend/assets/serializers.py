from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from locations.models import Location

from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
        label="نام پروژه",
    )

    project_code = serializers.CharField(
        source="project.code",
        read_only=True,
        label="کد پروژه",
    )

    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True,
        label="نام موقعیت",
    )

    location_code = serializers.CharField(
        source="location.code",
        read_only=True,
        allow_null=True,
        label="کد موقعیت",
    )

    location_full_name = serializers.CharField(
        source="location.full_name",
        read_only=True,
        allow_null=True,
        label="مسیر کامل موقعیت",
    )

    asset_type_display = serializers.CharField(
        source="get_asset_type_display",
        read_only=True,
        label="نوع تجهیز",
    )

    documents_count = serializers.SerializerMethodField(
        label="تعداد مدارک",
    )

    class Meta:
        model = Asset
        fields = [
            "id",
            "project",
            "project_name",
            "project_code",
            "location",
            "location_name",
            "location_code",
            "location_full_name",
            "code",
            "name",
            "asset_type",
            "asset_type_display",
            "manufacturer",
            "model",
            "serial_number",
            "description",
            "commission_date",
            "documents_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "project": {
                "label": "پروژه",
                "error_messages": {
                    "required": "انتخاب پروژه الزامی است.",
                    "does_not_exist": "پروژه انتخاب‌شده معتبر نیست.",
                    "incorrect_type": "شناسه پروژه نامعتبر است.",
                    "null": "پروژه نمی‌تواند خالی باشد.",
                },
            },
            "location": {
                "label": "موقعیت",
                "required": False,
                "allow_null": True,
                "error_messages": {
                    "does_not_exist": "موقعیت انتخاب‌شده معتبر نیست.",
                    "incorrect_type": "شناسه موقعیت نامعتبر است.",
                },
            },
            "code": {
                "label": "کد تجهیز",
                "error_messages": {
                    "required": "وارد کردن کد تجهیز الزامی است.",
                    "blank": "کد تجهیز نمی‌تواند خالی باشد.",
                    "max_length": "کد تجهیز بیش از حد مجاز طولانی است.",
                },
            },
            "name": {
                "label": "نام تجهیز",
                "error_messages": {
                    "required": "وارد کردن نام تجهیز الزامی است.",
                    "blank": "نام تجهیز نمی‌تواند خالی باشد.",
                    "max_length": "نام تجهیز بیش از حد مجاز طولانی است.",
                },
            },
            "asset_type": {
                "label": "نوع تجهیز",
                "error_messages": {
                    "required": "انتخاب نوع تجهیز الزامی است.",
                    "invalid_choice": "نوع تجهیز انتخاب‌شده معتبر نیست.",
                },
            },
            "manufacturer": {
                "label": "سازنده",
            },
            "model": {
                "label": "مدل",
            },
            "serial_number": {
                "label": "شماره سریال",
            },
            "description": {
                "label": "توضیحات",
            },
            "commission_date": {
                "label": "تاریخ راه‌اندازی",
                "error_messages": {
                    "invalid": "تاریخ راه‌اندازی معتبر نیست.",
                },
            },
            "is_active": {
                "label": "فعال",
            },
        }

    def get_documents_count(self, obj):
        annotated_value = getattr(obj, "documents_count", None)

        if annotated_value is not None:
            return annotated_value

        try:
            return obj.documents.count()
        except (AttributeError, ObjectDoesNotExist):
            return 0

    def validate_project(self, project):
        if not project.is_active:
            raise serializers.ValidationError(
                "امکان ثبت یا انتقال تجهیز به پروژه غیرفعال وجود ندارد."
            )

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            user = request.user

            if not user.is_superuser:
                organization_id = getattr(user, "organization_id", None)

                if organization_id is not None:
                    project_organization_id = getattr(
                        project,
                        "organization_id",
                        None,
                    )

                    if project_organization_id != organization_id:
                        raise serializers.ValidationError(
                            "شما به این پروژه دسترسی ندارید."
                        )

        return project

    def validate_location(self, location):
        if location is None:
            return location

        if not location.is_active:
            raise serializers.ValidationError(
                "امکان انتخاب موقعیت غیرفعال وجود ندارد."
            )

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            user = request.user

            if not user.is_superuser:
                organization_id = getattr(user, "organization_id", None)

                if organization_id is not None:
                    location_organization_id = getattr(
                        location.project,
                        "organization_id",
                        None,
                    )

                    if location_organization_id != organization_id:
                        raise serializers.ValidationError(
                            "شما به این موقعیت دسترسی ندارید."
                        )

        return location

    def validate_code(self, value):
        value = value.strip().upper()

        if not value:
            raise serializers.ValidationError(
                "کد تجهیز نمی‌تواند خالی باشد."
            )

        return value

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "نام تجهیز نمی‌تواند خالی باشد."
            )

        return value

    def validate_manufacturer(self, value):
        return value.strip()

    def validate_model(self, value):
        return value.strip()

    def validate_serial_number(self, value):
        return value.strip()

    def validate_description(self, value):
        return value.strip()

    def validate(self, attrs):
        instance = self.instance

        project = attrs.get(
            "project",
            getattr(instance, "project", None),
        )

        location = attrs.get(
            "location",
            getattr(instance, "location", None),
        )

        code = attrs.get(
            "code",
            getattr(instance, "code", None),
        )

        if location and project and location.project_id != project.pk:
            raise serializers.ValidationError(
                {
                    "location": (
                        "موقعیت انتخاب‌شده باید متعلق به همان پروژه تجهیز باشد."
                    )
                }
            )

        if project and code:
            duplicate_queryset = Asset.objects.filter(
                project=project,
                code__iexact=code,
            )

            if instance:
                duplicate_queryset = duplicate_queryset.exclude(
                    pk=instance.pk
                )

            if duplicate_queryset.exists():
                raise serializers.ValidationError(
                    {
                        "code": (
                            "تجهیزی با این کد در پروژه انتخاب‌شده وجود دارد."
                        )
                    }
                )

        return attrs


class AssetListSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        fields = [
            "id",
            "project",
            "project_name",
            "project_code",
            "location",
            "location_name",
            "location_code",
            "location_full_name",
            "code",
            "name",
            "asset_type",
            "asset_type_display",
            "manufacturer",
            "model",
            "serial_number",
            "commission_date",
            "documents_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
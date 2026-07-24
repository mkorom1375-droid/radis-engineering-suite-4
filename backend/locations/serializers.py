from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from projects.models import Project

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
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

    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True,
        label="نام موقعیت والد",
    )

    parent_code = serializers.CharField(
        source="parent.code",
        read_only=True,
        allow_null=True,
        label="کد موقعیت والد",
    )

    location_type_display = serializers.CharField(
        source="get_location_type_display",
        read_only=True,
        label="نوع موقعیت",
    )

    full_name = serializers.CharField(
        read_only=True,
        label="مسیر کامل موقعیت",
    )

    full_code = serializers.CharField(
        read_only=True,
        label="مسیر کامل کد",
    )

    children_count = serializers.SerializerMethodField(
        label="تعداد زیرمجموعه‌ها",
    )

    assets_count = serializers.SerializerMethodField(
        label="تعداد تجهیزات",
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "project",
            "project_name",
            "project_code",
            "parent",
            "parent_name",
            "parent_code",
            "code",
            "name",
            "location_type",
            "location_type_display",
            "description",
            "full_name",
            "full_code",
            "children_count",
            "assets_count",
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
            "parent": {
                "label": "موقعیت والد",
                "required": False,
                "allow_null": True,
                "error_messages": {
                    "does_not_exist": "موقعیت والد انتخاب‌شده معتبر نیست.",
                    "incorrect_type": "شناسه موقعیت والد نامعتبر است.",
                },
            },
            "code": {
                "label": "کد موقعیت",
                "error_messages": {
                    "required": "وارد کردن کد موقعیت الزامی است.",
                    "blank": "کد موقعیت نمی‌تواند خالی باشد.",
                    "max_length": "کد موقعیت بیش از حد مجاز طولانی است.",
                },
            },
            "name": {
                "label": "نام موقعیت",
                "error_messages": {
                    "required": "وارد کردن نام موقعیت الزامی است.",
                    "blank": "نام موقعیت نمی‌تواند خالی باشد.",
                    "max_length": "نام موقعیت بیش از حد مجاز طولانی است.",
                },
            },
            "location_type": {
                "label": "نوع موقعیت",
                "error_messages": {
                    "required": "انتخاب نوع موقعیت الزامی است.",
                    "invalid_choice": "نوع موقعیت انتخاب‌شده معتبر نیست.",
                },
            },
            "description": {
                "label": "توضیحات",
            },
            "is_active": {
                "label": "فعال",
            },
        }

    def get_children_count(self, obj):
        annotated_value = getattr(obj, "children_count", None)

        if annotated_value is not None:
            return annotated_value

        return obj.children.count()

    def get_assets_count(self, obj):
        annotated_value = getattr(obj, "assets_count", None)

        if annotated_value is not None:
            return annotated_value

        try:
            return obj.assets.count()
        except (AttributeError, ObjectDoesNotExist):
            return 0

    def validate_project(self, project):
        if not project.is_active:
            raise serializers.ValidationError(
                "امکان ایجاد یا انتقال موقعیت به پروژه غیرفعال وجود ندارد."
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

    def validate_code(self, value):
        value = value.strip().upper()

        if not value:
            raise serializers.ValidationError(
                "کد موقعیت نمی‌تواند خالی باشد."
            )

        return value

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "نام موقعیت نمی‌تواند خالی باشد."
            )

        return value

    def validate_description(self, value):
        return value.strip()

    def validate(self, attrs):
        instance = self.instance

        project = attrs.get(
            "project",
            getattr(instance, "project", None),
        )

        parent = attrs.get(
            "parent",
            getattr(instance, "parent", None),
        )

        code = attrs.get(
            "code",
            getattr(instance, "code", None),
        )

        if parent:
            if instance and parent.pk == instance.pk:
                raise serializers.ValidationError(
                    {
                        "parent": (
                            "یک موقعیت نمی‌تواند به‌عنوان والد خودش انتخاب شود."
                        )
                    }
                )

            if project and parent.project_id != project.pk:
                raise serializers.ValidationError(
                    {
                        "parent": (
                            "موقعیت والد باید متعلق به همان پروژه باشد."
                        )
                    }
                )

            current = parent
            visited_ids = set()

            while current is not None:
                if current.pk in visited_ids:
                    raise serializers.ValidationError(
                        {
                            "parent": (
                                "ساختار سلسله‌مراتبی موقعیت‌ها دارای چرخه است."
                            )
                        }
                    )

                visited_ids.add(current.pk)

                if instance and current.pk == instance.pk:
                    raise serializers.ValidationError(
                        {
                            "parent": (
                                "انتخاب این والد باعث ایجاد چرخه در ساختار "
                                "موقعیت‌ها می‌شود."
                            )
                        }
                    )

                current = current.parent

        if project and code:
            duplicate_queryset = Location.objects.filter(
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
                            "موقعیتی با این کد در پروژه انتخاب‌شده "
                            "وجود دارد."
                        )
                    }
                )

        return attrs


class LocationListSerializer(LocationSerializer):
    class Meta(LocationSerializer.Meta):
        fields = [
            "id",
            "project",
            "project_name",
            "project_code",
            "parent",
            "parent_name",
            "parent_code",
            "code",
            "name",
            "location_type",
            "location_type_display",
            "full_name",
            "full_code",
            "children_count",
            "assets_count",
            "is_active",
            "created_at",
            "updated_at",
        ]


class LocationTreeSerializer(serializers.ModelSerializer):
    location_type_display = serializers.CharField(
        source="get_location_type_display",
        read_only=True,
        label="نوع موقعیت",
    )

    children = serializers.SerializerMethodField(
        label="زیرمجموعه‌ها",
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "project",
            "parent",
            "code",
            "name",
            "location_type",
            "location_type_display",
            "description",
            "is_active",
            "children",
        ]

    def get_children(self, obj):
        prefetched_children = getattr(obj, "_prefetched_objects_cache", {}).get(
            "children"
        )

        if prefetched_children is not None:
            children = [
                child
                for child in prefetched_children
                if child.is_active
            ]
        else:
            children = obj.children.filter(
                is_active=True
            ).order_by("code")

        return LocationTreeSerializer(
            children,
            many=True,
            context=self.context,
        ).data
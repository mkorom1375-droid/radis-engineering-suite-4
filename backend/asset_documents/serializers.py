import os

from rest_framework import serializers

from .models import AssetDocument


class AssetDocumentSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(
        source="asset.code",
        read_only=True,
    )

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )

    project_id = serializers.IntegerField(
        source="asset.project_id",
        read_only=True,
    )

    project_code = serializers.CharField(
        source="asset.project.code",
        read_only=True,
    )

    project_name = serializers.CharField(
        source="asset.project.name",
        read_only=True,
    )

    document_type_display = serializers.CharField(
        source="get_document_type_display",
        read_only=True,
    )

    uploaded_by_name = serializers.SerializerMethodField()

    file_name = serializers.SerializerMethodField()

    file_size = serializers.SerializerMethodField()

    class Meta:
        model = AssetDocument

        fields = [
            "id",
            "asset",
            "asset_code",
            "asset_name",
            "project_id",
            "project_code",
            "project_name",
            "title",
            "document_type",
            "document_type_display",
            "document_number",
            "revision",
            "document_date",
            "file",
            "file_name",
            "file_size",
            "description",
            "uploaded_by",
            "uploaded_by_name",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "asset_code",
            "asset_name",
            "project_id",
            "project_code",
            "project_name",
            "document_type_display",
            "file_name",
            "file_size",
            "uploaded_by",
            "uploaded_by_name",
            "is_active",
            "created_at",
            "updated_at",
        ]

        extra_kwargs = {
            "asset": {
                "error_messages": {
                    "required": "انتخاب تجهیز الزامی است.",
                    "does_not_exist": "تجهیز انتخاب‌شده وجود ندارد.",
                    "incorrect_type": "شناسه تجهیز نامعتبر است.",
                }
            },
            "title": {
                "error_messages": {
                    "required": "وارد کردن عنوان سند الزامی است.",
                    "blank": "عنوان سند نمی‌تواند خالی باشد.",
                    "max_length": "عنوان سند بیش از حد مجاز طولانی است.",
                }
            },
            "document_type": {
                "error_messages": {
                    "invalid_choice": "نوع سند انتخاب‌شده معتبر نیست.",
                }
            },
            "file": {
                "error_messages": {
                    "required": "انتخاب فایل الزامی است.",
                    "invalid": "فایل انتخاب‌شده معتبر نیست.",
                    "empty": "فایل انتخاب‌شده خالی است.",
                }
            },
            "document_date": {
                "error_messages": {
                    "invalid": "فرمت تاریخ سند معتبر نیست.",
                }
            },
        }

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return None

        full_name = obj.uploaded_by.get_full_name().strip()

        if full_name:
            return full_name

        return obj.uploaded_by.username

    def get_file_name(self, obj):
        if not obj.file:
            return None

        return os.path.basename(obj.file.name)

    def get_file_size(self, obj):
        if not obj.file:
            return None

        try:
            return obj.file.size
        except (FileNotFoundError, OSError):
            return None

    def validate_asset(self, asset):
        request = self.context.get("request")

        if not asset.is_active:
            raise serializers.ValidationError(
                "تجهیز انتخاب‌شده غیرفعال است."
            )

        if not asset.project.is_active:
            raise serializers.ValidationError(
                "پروژه مرتبط با تجهیز غیرفعال است."
            )

        if request is None:
            return asset

        user = request.user

        if user.is_superuser:
            return asset

        if not user.organization_id:
            raise serializers.ValidationError(
                "حساب کاربری شما به هیچ سازمانی متصل نیست."
            )

        if asset.project.organization_id != user.organization_id:
            raise serializers.ValidationError(
                "شما اجازه دسترسی به این تجهیز را ندارید."
            )

        return asset

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "عنوان سند نمی‌تواند خالی باشد."
            )

        return value

    def validate_document_number(self, value):
        return value.strip()

    def validate_revision(self, value):
        return value.strip()

    def validate_file(self, value):
        maximum_size = 25 * 1024 * 1024

        if value.size > maximum_size:
            raise serializers.ValidationError(
                "حجم فایل نباید بیشتر از ۲۵ مگابایت باشد."
            )

        allowed_extensions = {
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".dwg",
            ".dxf",
            ".txt",
            ".zip",
        }

        extension = os.path.splitext(value.name)[1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "پسوند فایل انتخاب‌شده مجاز نیست."
            )

        return value

    def validate(self, attrs):
        asset = attrs.get(
            "asset",
            getattr(self.instance, "asset", None),
        )

        document_number = attrs.get(
            "document_number",
            getattr(self.instance, "document_number", ""),
        )

        revision = attrs.get(
            "revision",
            getattr(self.instance, "revision", ""),
        )

        if asset and document_number:
            queryset = AssetDocument.objects.filter(
                asset=asset,
                document_number__iexact=document_number.strip(),
                revision__iexact=revision.strip(),
            )

            if self.instance:
                queryset = queryset.exclude(
                    pk=self.instance.pk,
                )

            if queryset.exists():
                raise serializers.ValidationError(
                    {
                        "document_number": (
                            "سندی با این شماره و ویرایش قبلاً برای "
                            "این تجهیز ثبت شده است."
                        )
                    }
                )

        return attrs
from rest_framework.exceptions import PermissionDenied


class OrganizationQuerysetMixin:
    organization_lookup = "organization_id"

    def get_user_organization_id(self):
        user = self.request.user

        if user.is_superuser:
            return None

        organization_id = getattr(
            user,
            "organization_id",
            None,
        )

        if not organization_id:
            raise PermissionDenied(
                "حساب کاربری شما به هیچ سازمانی متصل نیست."
            )

        return organization_id

    def filter_queryset_by_organization(self, queryset):
        user = self.request.user

        if user.is_superuser:
            return queryset

        organization_id = self.get_user_organization_id()

        return queryset.filter(
            **{
                self.organization_lookup: organization_id,
            }
        )


class SoftDeleteMixin:
    soft_delete_field = "is_active"

    def perform_destroy(self, instance):
        setattr(
            instance,
            self.soft_delete_field,
            False,
        )

        update_fields = [
            self.soft_delete_field,
        ]

        if hasattr(instance, "updated_at"):
            update_fields.append("updated_at")

        instance.save(
            update_fields=update_fields,
        )


class ActiveQuerysetMixin:
    active_field = "is_active"

    def filter_active_queryset(self, queryset):
        return queryset.filter(
            **{
                self.active_field: True,
            }
        )
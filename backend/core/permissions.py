from rest_framework.permissions import BasePermission


class IsAuthenticatedAndActive(BasePermission):
    message = "حساب کاربری شما فعال نیست."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
        )


class IsSuperuserOrOrganizationMember(BasePermission):
    message = "شما اجازه دسترسی به اطلاعات این سازمان را ندارید."

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser:
            return True

        user_organization_id = getattr(
            user,
            "organization_id",
            None,
        )

        if not user_organization_id:
            return False

        object_organization_id = self.get_object_organization_id(obj)

        return object_organization_id == user_organization_id

    def get_object_organization_id(self, obj):
        if hasattr(obj, "organization_id"):
            return obj.organization_id

        project = getattr(
            obj,
            "project",
            None,
        )

        if project is not None:
            return getattr(
                project,
                "organization_id",
                None,
            )

        asset = getattr(
            obj,
            "asset",
            None,
        )

        if asset is not None:
            asset_project = getattr(
                asset,
                "project",
                None,
            )

            if asset_project is not None:
                return getattr(
                    asset_project,
                    "organization_id",
                    None,
                )

        return None
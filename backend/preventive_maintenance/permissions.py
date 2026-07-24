from rest_framework.permissions import BasePermission


class BaseModelActionPermission(BasePermission):
    """
    Base permission class that maps DRF ViewSet actions to Django
    model permissions.

    Default mappings:
        list/retrieve               -> view
        create                      -> add
        update/partial_update       -> change
        destroy                     -> delete
    """

    message = "شما مجوز انجام این عملیات را ندارید."

    action_permission_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        model = self.get_model(view)

        if model is None:
            return False

        permission_action = self.get_permission_action(view)

        if permission_action is None:
            return False

        permission_name = self.build_permission_name(
            model=model,
            permission_action=permission_action,
        )

        return user.has_perm(permission_name)

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        model = obj.__class__

        permission_action = self.get_permission_action(view)

        if permission_action is None:
            return False

        permission_name = self.build_permission_name(
            model=model,
            permission_action=permission_action,
        )

        return (
            user.has_perm(
                permission_name,
                obj,
            )
            or user.has_perm(permission_name)
        )

    def get_model(self, view):
        queryset = getattr(
            view,
            "queryset",
            None,
        )

        if queryset is not None:
            return queryset.model

        try:
            queryset = view.get_queryset()
        except (
            AttributeError,
            AssertionError,
            TypeError,
        ):
            return None

        return getattr(
            queryset,
            "model",
            None,
        )

    def get_permission_action(self, view):
        action = getattr(
            view,
            "action",
            None,
        )

        if action in self.action_permission_map:
            return self.action_permission_map[action]

        return self.get_custom_action_permission(view)

    def get_custom_action_permission(self, view):
        return None

    @staticmethod
    def build_permission_name(
        model,
        permission_action,
    ):
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        return (
            f"{app_label}."
            f"{permission_action}_{model_name}"
        )


class PreventiveMaintenancePlanPermission(
    BaseModelActionPermission
):
    """
    Permissions for preventive maintenance plans.

    Custom plan actions require change permission:
        activate
        suspend
        complete
        cancel
        generate_work_order

    Reading plan generations requires view permission.
    """

    custom_action_permission_map = {
        "activate": "change",
        "suspend": "change",
        "complete": "change",
        "cancel": "change",
        "generate_work_order": "change",
        "generations": "view",
    }

    def get_custom_action_permission(self, view):
        return self.custom_action_permission_map.get(
            getattr(
                view,
                "action",
                None,
            )
        )


class PreventiveMaintenanceTaskPermission(
    BaseModelActionPermission
):
    """
    Permissions for preventive maintenance tasks.
    """

    pass


class PreventiveMaintenanceGenerationPermission(
    BaseModelActionPermission
):
    """
    Permissions for preventive maintenance generation records.

    Generation records are normally read-only through the API.
    """

    custom_action_permission_map = {
        "task_results": "view",
    }

    def get_custom_action_permission(self, view):
        return self.custom_action_permission_map.get(
            getattr(
                view,
                "action",
                None,
            )
        )


class PreventiveMaintenanceTaskResultPermission(
    BaseModelActionPermission
):
    """
    Permissions for preventive maintenance task results.

    Completing or reopening a task result requires change permission.
    """

    custom_action_permission_map = {
        "complete": "change",
        "reopen": "change",
    }

    def get_custom_action_permission(self, view):
        return self.custom_action_permission_map.get(
            getattr(
                view,
                "action",
                None,
            )
        )


class CanGeneratePreventiveMaintenanceWorkOrder(
    BasePermission
):
    """
    Additional permission for manually generating a work order.

    The user must have:
        preventive_maintenance.change_preventivemaintenanceplan
        work_orders.add_workorder
    """

    message = (
        "برای تولید دستورکار باید مجوز ویرایش برنامه نگهداری "
        "و ایجاد دستورکار را داشته باشید."
    )

    required_permissions = (
        (
            "preventive_maintenance."
            "change_preventivemaintenanceplan"
        ),
        "work_orders.add_workorder",
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return all(
            user.has_perm(permission_name)
            for permission_name in self.required_permissions
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        return self.has_permission(
            request=request,
            view=view,
        )


class CanManagePreventiveMaintenancePlanStatus(
    BasePermission
):
    """
    Permission for changing the lifecycle status of a PM plan.
    """

    message = (
        "شما مجوز تغییر وضعیت برنامه نگهداری پیشگیرانه را ندارید."
    )

    permission_name = (
        "preventive_maintenance."
        "change_preventivemaintenanceplan"
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.has_perm(
            self.permission_name
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return (
            user.has_perm(
                self.permission_name,
                obj,
            )
            or user.has_perm(
                self.permission_name
            )
        )


class CanCompletePreventiveMaintenanceTaskResult(
    BasePermission
):
    """
    Permission for completing or reopening a PM task result.
    """

    message = (
        "شما مجوز ثبت یا تغییر نتیجه فعالیت نگهداری را ندارید."
    )

    permission_name = (
        "preventive_maintenance."
        "change_preventivemaintenancetaskresult"
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.has_perm(
            self.permission_name
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return (
            user.has_perm(
                self.permission_name,
                obj,
            )
            or user.has_perm(
                self.permission_name
            )
        )
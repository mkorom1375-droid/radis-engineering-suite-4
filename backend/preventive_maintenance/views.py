from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    GenerationStatus,
    PreventiveMaintenanceGeneration,
    PreventiveMaintenancePlan,
    PreventiveMaintenanceStatus,
    PreventiveMaintenanceTask,
    PreventiveMaintenanceTaskResult,
)
from .permissions import (
    CanCompletePreventiveMaintenanceTaskResult,
    CanGeneratePreventiveMaintenanceWorkOrder,
    CanManagePreventiveMaintenancePlanStatus,
    PreventiveMaintenanceGenerationPermission,
    PreventiveMaintenancePlanPermission,
    PreventiveMaintenanceTaskPermission,
    PreventiveMaintenanceTaskResultPermission,
)
from .serializers import (
    PreventiveMaintenanceGenerationSerializer,
    PreventiveMaintenancePlanDetailSerializer,
    PreventiveMaintenancePlanListSerializer,
    PreventiveMaintenanceTaskResultSerializer,
    PreventiveMaintenanceTaskSerializer,
)
from .services import (
    PreventiveMaintenanceGenerationError,
    PreventiveMaintenanceService,
)


class BooleanQueryParameterMixin:
    TRUE_VALUES = {
        "true",
        "1",
        "yes",
        "on",
    }

    FALSE_VALUES = {
        "false",
        "0",
        "no",
        "off",
    }

    @classmethod
    def parse_boolean(cls, value, field_name):
        if isinstance(value, bool):
            return value

        normalized_value = str(value).strip().lower()

        if normalized_value in cls.TRUE_VALUES:
            return True

        if normalized_value in cls.FALSE_VALUES:
            return False

        raise ValidationError(
            {
                field_name: (
                    "مقدار باید یکی از true یا false باشد."
                )
            }
        )


class PreventiveMaintenancePlanViewSet(
    BooleanQueryParameterMixin,
    viewsets.ModelViewSet,
):
    permission_classes = [
        IsAuthenticated,
        PreventiveMaintenancePlanPermission,
    ]

    queryset = (
        PreventiveMaintenancePlan.objects
        .select_related(
            "project",
            "asset",
            "location",
            "supervisor",
            "created_by",
        )
        .prefetch_related(
            "tasks",
        )
        .annotate(
            task_count=Count(
                "tasks",
                filter=Q(tasks__is_active=True),
                distinct=True,
            )
        )
        .order_by(
            F("next_due_date").asc(
                nulls_last=True,
            ),
            "plan_number",
            "id",
        )
    )

    def get_permissions(self):
        permission_classes = [
            IsAuthenticated,
            PreventiveMaintenancePlanPermission,
        ]

        if self.action in {
            "activate",
            "suspend",
            "complete",
            "cancel",
        }:
            permission_classes.append(
                CanManagePreventiveMaintenancePlanStatus
            )

        if self.action == "generate_work_order":
            permission_classes.append(
                CanGeneratePreventiveMaintenanceWorkOrder
            )

        return [
            permission()
            for permission in permission_classes
        ]

    def get_serializer_class(self):
        if self.action == "list":
            return PreventiveMaintenancePlanListSerializer

        return PreventiveMaintenancePlanDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        project_id = self.request.query_params.get(
            "project"
        )
        asset_id = self.request.query_params.get(
            "asset"
        )
        location_id = self.request.query_params.get(
            "location"
        )
        status_value = self.request.query_params.get(
            "status"
        )
        frequency = self.request.query_params.get(
            "frequency"
        )
        priority = self.request.query_params.get(
            "priority"
        )
        is_active = self.request.query_params.get(
            "is_active"
        )
        auto_generate = self.request.query_params.get(
            "auto_generate_work_order"
        )
        ready_for_generation = (
            self.request.query_params.get(
                "ready_for_generation"
            )
        )
        search = self.request.query_params.get(
            "search"
        )

        if project_id:
            queryset = queryset.filter(
                project_id=project_id,
            )

        if asset_id:
            queryset = queryset.filter(
                asset_id=asset_id,
            )

        if location_id:
            queryset = queryset.filter(
                location_id=location_id,
            )

        if status_value:
            queryset = queryset.filter(
                status=status_value,
            )

        if frequency:
            queryset = queryset.filter(
                frequency=frequency,
            )

        if priority:
            queryset = queryset.filter(
                priority=priority,
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=self.parse_boolean(
                    is_active,
                    field_name="is_active",
                )
            )

        if auto_generate is not None:
            queryset = queryset.filter(
                auto_generate_work_order=(
                    self.parse_boolean(
                        auto_generate,
                        field_name=(
                            "auto_generate_work_order"
                        ),
                    )
                )
            )

        if ready_for_generation is not None:
            ready_value = self.parse_boolean(
                ready_for_generation,
                field_name="ready_for_generation",
            )

            queryset = self._filter_ready_for_generation(
                queryset=queryset,
                ready_value=ready_value,
            )

        if search:
            search = search.strip()

            if search:
                queryset = queryset.filter(
                    Q(plan_number__icontains=search)
                    | Q(title__icontains=search)
                    | Q(description__icontains=search)
                    | Q(asset__name__icontains=search)
                    | Q(location__name__icontains=search)
                )

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
    )
    @transaction.atomic
    def activate(self, request, pk=None):
        plan = self._get_locked_plan()

        if not plan.is_active:
            raise ValidationError(
                {
                    "is_active": (
                        "برنامه غیرفعال است و ابتدا باید "
                        "فعال‌سازی سیستمی شود."
                    )
                }
            )

        if plan.status == PreventiveMaintenanceStatus.CANCELLED:
            raise ValidationError(
                {
                    "status": (
                        "برنامه لغوشده قابل فعال‌سازی نیست."
                    )
                }
            )

        if plan.status == PreventiveMaintenanceStatus.COMPLETED:
            raise ValidationError(
                {
                    "status": (
                        "برنامه تکمیل‌شده قابل فعال‌سازی نیست."
                    )
                }
            )

        if not plan.next_due_date:
            plan.initialize_next_due_date()

        plan.status = PreventiveMaintenanceStatus.ACTIVE

        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "next_due_date",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(plan)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="suspend",
    )
    @transaction.atomic
    def suspend(self, request, pk=None):
        plan = self._get_locked_plan()

        if plan.status == PreventiveMaintenanceStatus.CANCELLED:
            raise ValidationError(
                {
                    "status": (
                        "برنامه لغوشده قابل تعلیق نیست."
                    )
                }
            )

        if plan.status == PreventiveMaintenanceStatus.COMPLETED:
            raise ValidationError(
                {
                    "status": (
                        "برنامه تکمیل‌شده قابل تعلیق نیست."
                    )
                }
            )

        plan.status = PreventiveMaintenanceStatus.SUSPENDED
        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(plan)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    @transaction.atomic
    def complete(self, request, pk=None):
        plan = self._get_locked_plan()

        if plan.status == PreventiveMaintenanceStatus.CANCELLED:
            raise ValidationError(
                {
                    "status": (
                        "برنامه لغوشده قابل تکمیل نیست."
                    )
                }
            )

        plan.status = PreventiveMaintenanceStatus.COMPLETED
        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(plan)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    @transaction.atomic
    def cancel(self, request, pk=None):
        plan = self._get_locked_plan()

        if plan.status == PreventiveMaintenanceStatus.COMPLETED:
            raise ValidationError(
                {
                    "status": (
                        "برنامه تکمیل‌شده قابل لغو نیست."
                    )
                }
            )

        plan.status = PreventiveMaintenanceStatus.CANCELLED
        plan.full_clean()
        plan.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(plan)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="generate-work-order",
    )
    def generate_work_order(self, request, pk=None):
        plan = self.get_object()

        force = self.parse_boolean(
            request.data.get(
                "force",
                False,
            ),
            field_name="force",
        )

        try:
            generation = (
                PreventiveMaintenanceService
                .generate_plan_work_order(
                    plan_id=plan.id,
                    generated_by=request.user,
                    force=force,
                )
            )

        except PreventiveMaintenanceGenerationError as exc:
            raise ValidationError(
                {
                    "detail": str(exc),
                }
            ) from exc

        except Exception as exc:
            raise ValidationError(
                {
                    "detail": (
                        "تولید دستورکار با خطا مواجه شد: "
                        f"{exc}"
                    )
                }
            ) from exc

        if generation is None:
            return Response(
                {
                    "detail": (
                        "هنوز زمان تولید دستورکار این "
                        "برنامه فرا نرسیده است."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = (
            PreventiveMaintenanceGenerationSerializer(
                generation,
                context={
                    "request": request,
                },
            )
        )

        if generation.status == GenerationStatus.FAILED:
            response_status = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        elif generation.status == GenerationStatus.SKIPPED:
            response_status = status.HTTP_200_OK

        else:
            response_status = status.HTTP_201_CREATED

        return Response(
            serializer.data,
            status=response_status,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="generations",
    )
    def generations(self, request, pk=None):
        plan = self.get_object()

        queryset = (
            plan.generations
            .select_related(
                "plan",
                "work_order",
                "generated_by",
            )
            .order_by(
                "-due_date",
                "-id",
            )
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = (
                PreventiveMaintenanceGenerationSerializer(
                    page,
                    many=True,
                    context={
                        "request": request,
                    },
                )
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = (
            PreventiveMaintenanceGenerationSerializer(
                queryset,
                many=True,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def _get_locked_plan(self):
        queryset = (
            self.filter_queryset(
                self.get_queryset()
            )
            .select_for_update()
        )

        plan = get_object_or_404(
            queryset,
            pk=self.kwargs.get(
                self.lookup_field,
            ),
        )

        self.check_object_permissions(
            self.request,
            plan,
        )

        return plan

    @staticmethod
    def _filter_ready_for_generation(
        queryset,
        ready_value,
    ):
        today = timezone.localdate()

        ready_query = Q(
            status=PreventiveMaintenanceStatus.ACTIVE,
            is_active=True,
            auto_generate_work_order=True,
            next_due_date__isnull=False,
        )

        maximum_lead_days = (
            PreventiveMaintenancePlan.objects
            .order_by(
                "-generation_lead_days",
            )
            .values_list(
                "generation_lead_days",
                flat=True,
            )
            .first()
            or 0
        )

        ready_query &= Q(
            next_due_date__lte=(
                today
                + timedelta(
                    days=maximum_lead_days,
                )
            )
        )

        if ready_value:
            return queryset.filter(ready_query)

        return queryset.exclude(ready_query)


class PreventiveMaintenanceTaskViewSet(
    BooleanQueryParameterMixin,
    viewsets.ModelViewSet,
):
    permission_classes = [
        IsAuthenticated,
        PreventiveMaintenanceTaskPermission,
    ]

    serializer_class = (
        PreventiveMaintenanceTaskSerializer
    )

    queryset = (
        PreventiveMaintenanceTask.objects
        .select_related(
            "plan",
            "plan__project",
            "plan__asset",
        )
        .order_by(
            "plan_id",
            "sequence",
            "id",
        )
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        plan_id = self.request.query_params.get(
            "plan"
        )
        task_type = self.request.query_params.get(
            "task_type"
        )
        is_active = self.request.query_params.get(
            "is_active"
        )
        is_mandatory = self.request.query_params.get(
            "is_mandatory"
        )
        requires_shutdown = (
            self.request.query_params.get(
                "requires_shutdown"
            )
        )
        requires_measurement = (
            self.request.query_params.get(
                "requires_measurement"
            )
        )
        search = self.request.query_params.get(
            "search"
        )

        if plan_id:
            queryset = queryset.filter(
                plan_id=plan_id,
            )

        if task_type:
            queryset = queryset.filter(
                task_type=task_type,
            )

        boolean_filters = {
            "is_active": is_active,
            "is_mandatory": is_mandatory,
            "requires_shutdown": requires_shutdown,
            "requires_measurement": (
                requires_measurement
            ),
        }

        for field_name, value in boolean_filters.items():
            if value is not None:
                queryset = queryset.filter(
                    **{
                        field_name: self.parse_boolean(
                            value,
                            field_name=field_name,
                        )
                    }
                )

        if search:
            search = search.strip()

            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search)
                    | Q(description__icontains=search)
                    | Q(
                        acceptance_criteria__icontains=(
                            search
                        )
                    )
                )

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        task = serializer.save()
        task.full_clean()
        task.save()

    @transaction.atomic
    def perform_update(self, serializer):
        task = serializer.save()
        task.full_clean()
        task.save()


class PreventiveMaintenanceGenerationViewSet(
    BooleanQueryParameterMixin,
    viewsets.ReadOnlyModelViewSet,
):
    permission_classes = [
        IsAuthenticated,
        PreventiveMaintenanceGenerationPermission,
    ]

    serializer_class = (
        PreventiveMaintenanceGenerationSerializer
    )

    queryset = (
        PreventiveMaintenanceGeneration.objects
        .select_related(
            "plan",
            "plan__project",
            "plan__asset",
            "work_order",
            "generated_by",
        )
        .prefetch_related(
            "task_results",
            "task_results__task",
        )
        .order_by(
            "-due_date",
            "-id",
        )
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        plan_id = self.request.query_params.get(
            "plan"
        )
        project_id = self.request.query_params.get(
            "project"
        )
        generation_status = (
            self.request.query_params.get(
                "status"
            )
        )
        due_date_from = (
            self.request.query_params.get(
                "due_date_from"
            )
        )
        due_date_to = self.request.query_params.get(
            "due_date_to"
        )
        has_work_order = (
            self.request.query_params.get(
                "has_work_order"
            )
        )

        if plan_id:
            queryset = queryset.filter(
                plan_id=plan_id,
            )

        if project_id:
            queryset = queryset.filter(
                plan__project_id=project_id,
            )

        if generation_status:
            queryset = queryset.filter(
                status=generation_status,
            )

        if due_date_from:
            queryset = queryset.filter(
                due_date__gte=due_date_from,
            )

        if due_date_to:
            queryset = queryset.filter(
                due_date__lte=due_date_to,
            )

        if has_work_order is not None:
            has_work_order_value = self.parse_boolean(
                has_work_order,
                field_name="has_work_order",
            )

            queryset = queryset.filter(
                work_order__isnull=(
                    not has_work_order_value
                )
            )

        return queryset

    @action(
        detail=True,
        methods=["get"],
        url_path="task-results",
    )
    def task_results(self, request, pk=None):
        generation = self.get_object()

        queryset = (
            generation.task_results
            .select_related(
                "task",
                "completed_by",
                "generation",
            )
            .order_by(
                "task__sequence",
                "id",
            )
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = (
                PreventiveMaintenanceTaskResultSerializer(
                    page,
                    many=True,
                    context={
                        "request": request,
                    },
                )
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = (
            PreventiveMaintenanceTaskResultSerializer(
                queryset,
                many=True,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class PreventiveMaintenanceTaskResultViewSet(
    BooleanQueryParameterMixin,
    viewsets.ModelViewSet,
):
    permission_classes = [
        IsAuthenticated,
        PreventiveMaintenanceTaskResultPermission,
    ]

    serializer_class = (
        PreventiveMaintenanceTaskResultSerializer
    )

    http_method_names = [
        "get",
        "patch",
        "post",
        "head",
        "options",
    ]

    queryset = (
        PreventiveMaintenanceTaskResult.objects
        .select_related(
            "generation",
            "generation__plan",
            "generation__work_order",
            "task",
            "completed_by",
        )
        .order_by(
            "generation_id",
            "task__sequence",
            "id",
        )
    )

    def get_permissions(self):
        permission_classes = [
            IsAuthenticated,
            PreventiveMaintenanceTaskResultPermission,
        ]

        if self.action in {
            "complete",
            "reopen",
        }:
            permission_classes.append(
                CanCompletePreventiveMaintenanceTaskResult
            )

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):
        queryset = super().get_queryset()

        generation_id = (
            self.request.query_params.get(
                "generation"
            )
        )
        plan_id = self.request.query_params.get(
            "plan"
        )
        project_id = self.request.query_params.get(
            "project"
        )
        work_order_id = (
            self.request.query_params.get(
                "work_order"
            )
        )
        is_completed = (
            self.request.query_params.get(
                "is_completed"
            )
        )
        acceptable = self.request.query_params.get(
            "result_is_acceptable"
        )

        if generation_id:
            queryset = queryset.filter(
                generation_id=generation_id,
            )

        if plan_id:
            queryset = queryset.filter(
                generation__plan_id=plan_id,
            )

        if project_id:
            queryset = queryset.filter(
                generation__plan__project_id=(
                    project_id
                ),
            )

        if work_order_id:
            queryset = queryset.filter(
                generation__work_order_id=work_order_id,
            )

        if is_completed is not None:
            queryset = queryset.filter(
                is_completed=self.parse_boolean(
                    is_completed,
                    field_name="is_completed",
                )
            )

        if acceptable is not None:
            acceptable_value = self.parse_boolean(
                acceptable,
                field_name="result_is_acceptable",
            )

            queryset = queryset.filter(
                result_is_acceptable=acceptable_value,
            )

        return queryset

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    @transaction.atomic
    def complete(self, request, pk=None):
        task_result = self._get_locked_task_result()

        measured_value = request.data.get(
            "measured_value"
        )
        notes = request.data.get(
            "result_notes",
            "",
        )

        if task_result.is_completed:
            raise ValidationError(
                {
                    "is_completed": (
                        "این فعالیت قبلاً تکمیل شده است."
                    )
                }
            )

        if (
            task_result.task.requires_measurement
            and measured_value is None
        ):
            raise ValidationError(
                {
                    "measured_value": (
                        "ثبت مقدار اندازه‌گیری‌شده "
                        "برای این فعالیت الزامی است."
                    )
                }
            )

        if measured_value not in (None, ""):
            try:
                measured_value = Decimal(str(measured_value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValidationError(
                    {
                        "measured_value": (
                            "مقدار اندازه‌گیری‌شده باید عدد معتبر باشد."
                        )
                    }
                ) from exc
        else:
            measured_value = None

        task_result.mark_completed(
            user=request.user,
            measured_value=measured_value,
            notes=notes,
        )

        serializer = self.get_serializer(
            task_result
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reopen",
    )
    @transaction.atomic
    def reopen(self, request, pk=None):
        task_result = self._get_locked_task_result()

        if not task_result.is_completed:
            raise ValidationError(
                {
                    "is_completed": (
                        "این فعالیت در حال حاضر باز است."
                    )
                }
            )

        task_result.is_completed = False
        task_result.completed_at = None
        task_result.completed_by = None
        task_result.result_is_acceptable = None

        task_result.full_clean()
        task_result.save(
            update_fields=[
                "is_completed",
                "completed_at",
                "completed_by",
                "result_is_acceptable",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(
            task_result
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def _get_locked_task_result(self):
        queryset = (
            self.filter_queryset(
                self.get_queryset()
            )
            .select_for_update()
        )

        task_result = get_object_or_404(
            queryset,
            pk=self.kwargs.get(
                self.lookup_field,
            ),
        )

        self.check_object_permissions(
            self.request,
            task_result,
        )

        return task_result
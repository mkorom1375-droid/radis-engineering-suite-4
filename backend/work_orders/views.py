from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderDowntime,
    WorkOrderFailure,
    WorkOrderLabor,
    WorkOrderStatus,
    WorkRequest,
    WorkRequestStatus,
)
from .serializers import (
    WorkOrderAssignmentSerializer,
    WorkOrderDowntimeSerializer,
    WorkOrderFailureSerializer,
    WorkOrderLaborSerializer,
    WorkOrderSerializer,
    WorkOrderSummarySerializer,
    WorkRequestConvertSerializer,
    WorkRequestReviewSerializer,
    WorkRequestSerializer,
    WorkRequestSummarySerializer,
)


class WorkRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "request_number",
        "title",
        "description",
        "project__code",
        "project__name",
        "asset__code",
        "asset__name",
        "location__code",
        "location__name",
        "requested_by__username",
        "requested_by__first_name",
        "requested_by__last_name",
        "reviewed_by__username",
    ]

    ordering_fields = [
        "request_number",
        "title",
        "priority",
        "status",
        "requested_at",
        "required_date",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-requested_at",
        "-id",
    ]

    def get_queryset(self):
        queryset = (
            WorkRequest.objects.select_related(
                "project",
                "asset",
                "location",
                "requested_by",
                "reviewed_by",
            )
            .all()
        )

        project_id = self.request.query_params.get("project")
        asset_id = self.request.query_params.get("asset")
        location_id = self.request.query_params.get("location")
        status_value = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        maintenance_type = self.request.query_params.get(
            "maintenance_type"
        )
        requested_by = self.request.query_params.get("requested_by")
        reviewed_by = self.request.query_params.get("reviewed_by")
        production_stopped = self.request.query_params.get(
            "production_stopped"
        )
        safety_risk = self.request.query_params.get("safety_risk")
        environmental_risk = self.request.query_params.get(
            "environmental_risk"
        )
        is_active = self.request.query_params.get("is_active")
        requested_from = self.request.query_params.get("requested_from")
        requested_to = self.request.query_params.get("requested_to")
        required_from = self.request.query_params.get("required_from")
        required_to = self.request.query_params.get("required_to")
        overdue = self.request.query_params.get("overdue")
        unconverted = self.request.query_params.get("unconverted")

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        if status_value:
            statuses = [
                value.strip()
                for value in status_value.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(status__in=statuses)

        if priority:
            priorities = [
                value.strip()
                for value in priority.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(priority__in=priorities)

        if maintenance_type:
            maintenance_types = [
                value.strip()
                for value in maintenance_type.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(
                maintenance_type__in=maintenance_types
            )

        if requested_by:
            queryset = queryset.filter(requested_by_id=requested_by)

        if reviewed_by:
            queryset = queryset.filter(reviewed_by_id=reviewed_by)

        if production_stopped is not None:
            queryset = queryset.filter(
                production_stopped=self._parse_boolean(
                    production_stopped
                )
            )

        if safety_risk is not None:
            queryset = queryset.filter(
                safety_risk=self._parse_boolean(safety_risk)
            )

        if environmental_risk is not None:
            queryset = queryset.filter(
                environmental_risk=self._parse_boolean(
                    environmental_risk
                )
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=self._parse_boolean(is_active)
            )

        if requested_from:
            queryset = queryset.filter(
                requested_at__date__gte=requested_from
            )

        if requested_to:
            queryset = queryset.filter(
                requested_at__date__lte=requested_to
            )

        if required_from:
            queryset = queryset.filter(
                required_date__date__gte=required_from
            )

        if required_to:
            queryset = queryset.filter(
                required_date__date__lte=required_to
            )

        if overdue is not None:
            now = timezone.now()

            if self._parse_boolean(overdue):
                queryset = queryset.filter(
                    required_date__lt=now,
                ).exclude(
                    status__in=[
                        WorkRequestStatus.REJECTED,
                        WorkRequestStatus.CONVERTED,
                        WorkRequestStatus.CANCELLED,
                    ]
                )
            else:
                queryset = queryset.filter(
                    Q(required_date__gte=now)
                    | Q(required_date__isnull=True)
                    | Q(
                        status__in=[
                            WorkRequestStatus.REJECTED,
                            WorkRequestStatus.CONVERTED,
                            WorkRequestStatus.CANCELLED,
                        ]
                    )
                )

        if unconverted is not None:
            if self._parse_boolean(unconverted):
                queryset = queryset.filter(
                    work_order__isnull=True
                )
            else:
                queryset = queryset.filter(
                    work_order__isnull=False
                )

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return WorkRequestSummarySerializer

        if self.action == "review":
            return WorkRequestReviewSerializer

        if self.action == "convert":
            return WorkRequestConvertSerializer

        return WorkRequestSerializer

    def perform_create(self, serializer):
        serializer.save(
            requested_by=self.request.user,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(self, request, pk=None):
        work_request = self.get_object()

        if work_request.status != WorkRequestStatus.DRAFT:
            return Response(
                {
                    "detail": (
                        "فقط درخواست پیش‌نویس قابل ثبت نهایی است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        work_request.status = WorkRequestStatus.SUBMITTED
        work_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = WorkRequestSerializer(
            work_request,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start-review",
    )
    def start_review(self, request, pk=None):
        work_request = self.get_object()

        if work_request.status != WorkRequestStatus.SUBMITTED:
            return Response(
                {
                    "detail": (
                        "فقط درخواست ثبت‌شده قابل ورود به مرحله "
                        "بررسی است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        work_request.status = WorkRequestStatus.UNDER_REVIEW
        work_request.reviewed_by = request.user
        work_request.reviewed_at = timezone.now()
        work_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        serializer = WorkRequestSerializer(
            work_request,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post", "patch"],
        url_path="review",
    )
    def review(self, request, pk=None):
        work_request = self.get_object()

        if work_request.status not in {
            WorkRequestStatus.SUBMITTED,
            WorkRequestStatus.UNDER_REVIEW,
        }:
            return Response(
                {
                    "detail": (
                        "این درخواست در وضعیت قابل بررسی قرار ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()

        if not data.get("reviewed_by"):
            data["reviewed_by"] = request.user.pk

        if not data.get("reviewed_at"):
            data["reviewed_at"] = timezone.now()

        serializer = WorkRequestReviewSerializer(
            work_request,
            data=data,
            partial=True,
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        result_serializer = WorkRequestSerializer(
            work_request,
            context=self.get_serializer_context(),
        )

        return Response(
            result_serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        work_request = self.get_object()

        if work_request.status not in {
            WorkRequestStatus.SUBMITTED,
            WorkRequestStatus.UNDER_REVIEW,
        }:
            return Response(
                {
                    "detail": (
                        "این درخواست در وضعیت قابل تأیید قرار ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        work_request.status = WorkRequestStatus.APPROVED
        work_request.reviewed_by = request.user
        work_request.reviewed_at = timezone.now()
        work_request.review_notes = str(
            request.data.get("review_notes", "")
        ).strip()
        work_request.rejection_reason = ""
        work_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
                "rejection_reason",
                "updated_at",
            ]
        )

        serializer = WorkRequestSerializer(
            work_request,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    def reject(self, request, pk=None):
        work_request = self.get_object()
        rejection_reason = str(
            request.data.get("rejection_reason", "")
        ).strip()

        if work_request.status not in {
            WorkRequestStatus.SUBMITTED,
            WorkRequestStatus.UNDER_REVIEW,
        }:
            return Response(
                {
                    "detail": (
                        "این درخواست در وضعیت قابل رد قرار ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not rejection_reason:
            return Response(
                {
                    "rejection_reason": [
                        "ثبت دلیل رد الزامی است."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        work_request.status = WorkRequestStatus.REJECTED
        work_request.reviewed_by = request.user
        work_request.reviewed_at = timezone.now()
        work_request.review_notes = str(
            request.data.get("review_notes", "")
        ).strip()
        work_request.rejection_reason = rejection_reason
        work_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_notes",
                "rejection_reason",
                "updated_at",
            ]
        )

        serializer = WorkRequestSerializer(
            work_request,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        work_request = self.get_object()

        if work_request.status in {
            WorkRequestStatus.CONVERTED,
            WorkRequestStatus.CANCELLED,
        }:
            return Response(
                {
                    "detail": (
                        "این درخواست قابل لغو نیست."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        work_request.status = WorkRequestStatus.CANCELLED
        work_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        serializer = WorkRequestSerializer(
            work_request,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="convert",
    )
    def convert(self, request, pk=None):
        work_request = self.get_object()

        serializer = WorkRequestConvertSerializer(
            data=request.data,
            context={
                "request": request,
                "work_request": work_request,
                "created_by": request.user,
            },
        )

        serializer.is_valid(raise_exception=True)
        work_order = serializer.save()

        result_serializer = WorkOrderSerializer(
            work_order,
            context=self.get_serializer_context(),
        )

        return Response(
            result_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _parse_boolean(value):
        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


class WorkOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "work_order_number",
        "title",
        "description",
        "work_performed",
        "completion_notes",
        "project__code",
        "project__name",
        "asset__code",
        "asset__name",
        "location__code",
        "location__name",
        "work_request__request_number",
        "created_by__username",
        "created_by__first_name",
        "created_by__last_name",
        "supervisor__username",
        "supervisor__first_name",
        "supervisor__last_name",
    ]

    ordering_fields = [
        "work_order_number",
        "title",
        "priority",
        "status",
        "planned_start",
        "planned_finish",
        "actual_start",
        "actual_finish",
        "estimated_labor_hours",
        "actual_labor_hours",
        "estimated_cost",
        "actual_cost",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_at",
        "-id",
    ]

    def get_queryset(self):
        queryset = (
            WorkOrder.objects.select_related(
                "project",
                "work_request",
                "asset",
                "location",
                "created_by",
                "supervisor",
                "completed_by",
                "closed_by",
            )
            .prefetch_related(
                "assignments__user",
                "assignments__assigned_by",
                "labor_entries__user",
                "downtime_entries",
                "status_history__changed_by",
            )
            .all()
        )

        project_id = self.request.query_params.get("project")
        work_request_id = self.request.query_params.get(
            "work_request"
        )
        asset_id = self.request.query_params.get("asset")
        location_id = self.request.query_params.get("location")
        status_value = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        maintenance_type = self.request.query_params.get(
            "maintenance_type"
        )
        source = self.request.query_params.get("source")
        created_by = self.request.query_params.get("created_by")
        supervisor = self.request.query_params.get("supervisor")
        assigned_user = self.request.query_params.get(
            "assigned_user"
        )
        production_stopped = self.request.query_params.get(
            "production_stopped"
        )
        permit_required = self.request.query_params.get(
            "permit_required"
        )
        lockout_required = self.request.query_params.get(
            "lockout_tagout_required"
        )
        is_active = self.request.query_params.get("is_active")
        planned_from = self.request.query_params.get("planned_from")
        planned_to = self.request.query_params.get("planned_to")
        actual_from = self.request.query_params.get("actual_from")
        actual_to = self.request.query_params.get("actual_to")
        overdue = self.request.query_params.get("overdue")

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        if work_request_id:
            queryset = queryset.filter(
                work_request_id=work_request_id
            )

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        if status_value:
            statuses = [
                value.strip()
                for value in status_value.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(status__in=statuses)

        if priority:
            priorities = [
                value.strip()
                for value in priority.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(priority__in=priorities)

        if maintenance_type:
            maintenance_types = [
                value.strip()
                for value in maintenance_type.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(
                maintenance_type__in=maintenance_types
            )

        if source:
            sources = [
                value.strip()
                for value in source.split(",")
                if value.strip()
            ]
            queryset = queryset.filter(source__in=sources)

        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        if supervisor:
            queryset = queryset.filter(supervisor_id=supervisor)

        if assigned_user:
            queryset = queryset.filter(
                assignments__user_id=assigned_user,
                assignments__is_active=True,
            )

        if production_stopped is not None:
            queryset = queryset.filter(
                production_stopped=self._parse_boolean(
                    production_stopped
                )
            )

        if permit_required is not None:
            queryset = queryset.filter(
                permit_required=self._parse_boolean(
                    permit_required
                )
            )

        if lockout_required is not None:
            queryset = queryset.filter(
                lockout_tagout_required=self._parse_boolean(
                    lockout_required
                )
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=self._parse_boolean(is_active)
            )

        if planned_from:
            queryset = queryset.filter(
                planned_start__date__gte=planned_from
            )

        if planned_to:
            queryset = queryset.filter(
                planned_start__date__lte=planned_to
            )

        if actual_from:
            queryset = queryset.filter(
                actual_start__date__gte=actual_from
            )

        if actual_to:
            queryset = queryset.filter(
                actual_start__date__lte=actual_to
            )

        if overdue is not None:
            now = timezone.now()
            terminal_statuses = [
                WorkOrderStatus.COMPLETED,
                WorkOrderStatus.CLOSED,
                WorkOrderStatus.CANCELLED,
            ]

            if self._parse_boolean(overdue):
                queryset = queryset.filter(
                    planned_finish__lt=now,
                ).exclude(
                    status__in=terminal_statuses
                )
            else:
                queryset = queryset.filter(
                    Q(planned_finish__gte=now)
                    | Q(planned_finish__isnull=True)
                    | Q(status__in=terminal_statuses)
                )

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return WorkOrderSummarySerializer

        return WorkOrderSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="open",
    )
    def open_order(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status != WorkOrderStatus.DRAFT:
            return Response(
                {
                    "detail": (
                        "فقط دستورکار پیش‌نویس قابل بازکردن است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._change_status(
            work_order=work_order,
            new_status=WorkOrderStatus.OPEN,
            user=request.user,
            notes=request.data.get("notes", ""),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="assign",
    )
    def assign(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status not in {
            WorkOrderStatus.OPEN,
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.ON_HOLD,
        }:
            return Response(
                {
                    "detail": (
                        "دستورکار در وضعیت قابل تخصیص قرار ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WorkOrderAssignmentSerializer(
            data={
                **request.data,
                "work_order": work_order.pk,
                "assigned_by": request.user.pk,
            },
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

            if work_order.status != WorkOrderStatus.ASSIGNED:
                self._set_status(
                    work_order=work_order,
                    new_status=WorkOrderStatus.ASSIGNED,
                    user=request.user,
                    notes="Assignment created",
                )

        result_serializer = WorkOrderSerializer(
            work_order,
            context=self.get_serializer_context(),
        )

        return Response(
            result_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start",
    )
    def start(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status not in {
            WorkOrderStatus.OPEN,
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.ON_HOLD,
        }:
            return Response(
                {
                    "detail": (
                        "دستورکار در وضعیت قابل شروع قرار ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        actual_start = request.data.get("actual_start")

        if actual_start:
            serializer = WorkOrderSerializer(
                work_order,
                data={
                    "status": WorkOrderStatus.IN_PROGRESS,
                    "actual_start": actual_start,
                },
                partial=True,
                context=self.get_serializer_context(),
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            work_order.actual_start = (
                work_order.actual_start or timezone.now()
            )
            work_order.status = WorkOrderStatus.IN_PROGRESS
            work_order.save(
                update_fields=[
                    "actual_start",
                    "status",
                    "updated_at",
                ]
            )

            self._create_status_history(
                work_order=work_order,
                previous_status=(
                    WorkOrder.objects.only("status")
                    .get(pk=work_order.pk)
                    .status
                ),
                new_status=WorkOrderStatus.IN_PROGRESS,
                user=request.user,
                notes=request.data.get("notes", ""),
            )

        work_order.refresh_from_db()

        result_serializer = WorkOrderSerializer(
            work_order,
            context=self.get_serializer_context(),
        )

        return Response(
            result_serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="hold",
    )
    def hold(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status not in {
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.IN_PROGRESS,
        }:
            return Response(
                {
                    "detail": (
                        "فقط دستورکار تخصیص‌یافته یا در حال انجام "
                        "قابل توقف است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._change_status(
            work_order=work_order,
            new_status=WorkOrderStatus.ON_HOLD,
            user=request.user,
            notes=request.data.get("notes", ""),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="resume",
    )
    def resume(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status != WorkOrderStatus.ON_HOLD:
            return Response(
                {
                    "detail": (
                        "فقط دستورکار متوقف‌شده قابل ادامه است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not work_order.actual_start:
            work_order.actual_start = timezone.now()

        previous_status = work_order.status
        work_order.status = WorkOrderStatus.IN_PROGRESS
        work_order.save(
            update_fields=[
                "actual_start",
                "status",
                "updated_at",
            ]
        )

        self._create_status_history(
            work_order=work_order,
            previous_status=previous_status,
            new_status=work_order.status,
            user=request.user,
            notes=request.data.get("notes", ""),
        )

        serializer = WorkOrderSerializer(
            work_order,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status not in {
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.ON_HOLD,
        }:
            return Response(
                {
                    "detail": (
                        "دستورکار در وضعیت قابل تکمیل قرار ندارد."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["status"] = WorkOrderStatus.COMPLETED
        data["completed_by"] = request.user.pk

        if not data.get("actual_start"):
            data["actual_start"] = (
                work_order.actual_start or timezone.now()
            )

        if not data.get("actual_finish"):
            data["actual_finish"] = timezone.now()

        serializer = WorkOrderSerializer(
            work_order,
            data=data,
            partial=True,
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="close",
    )
    def close(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status != WorkOrderStatus.COMPLETED:
            return Response(
                {
                    "detail": (
                        "فقط دستورکار تکمیل‌شده قابل بستن است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["status"] = WorkOrderStatus.CLOSED
        data["closed_by"] = request.user.pk
        data["closed_at"] = timezone.now()

        serializer = WorkOrderSerializer(
            work_order,
            data=data,
            partial=True,
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        work_order = self.get_object()

        if work_order.status in {
            WorkOrderStatus.CLOSED,
            WorkOrderStatus.CANCELLED,
        }:
            return Response(
                {
                    "detail": (
                        "این دستورکار قابل لغو نیست."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cancellation_reason = str(
            request.data.get("cancellation_reason", "")
        ).strip()

        if not cancellation_reason:
            return Response(
                {
                    "cancellation_reason": [
                        "ثبت دلیل لغو الزامی است."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WorkOrderSerializer(
            work_order,
            data={
                "status": WorkOrderStatus.CANCELLED,
                "cancellation_reason": cancellation_reason,
            },
            partial=True,
            context=self.get_serializer_context(),
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="assignments",
    )
    def assignments(self, request, pk=None):
        work_order = self.get_object()
        queryset = work_order.assignments.select_related(
            "user",
            "assigned_by",
        ).all()

        serializer = WorkOrderAssignmentSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path="labor",
    )
    def labor(self, request, pk=None):
        work_order = self.get_object()
        queryset = work_order.labor_entries.select_related(
            "user"
        ).all()

        serializer = WorkOrderLaborSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path="downtime",
    )
    def downtime(self, request, pk=None):
        work_order = self.get_object()
        queryset = work_order.downtime_entries.all()

        serializer = WorkOrderDowntimeSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path="history",
    )
    def history(self, request, pk=None):
        work_order = self.get_object()
        queryset = work_order.status_history.select_related(
            "changed_by"
        ).all()

        from .serializers import WorkOrderStatusHistorySerializer

        serializer = WorkOrderStatusHistorySerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)

    @staticmethod
    def _parse_boolean(value):
        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _change_status(
        self,
        work_order,
        new_status,
        user,
        notes="",
    ):
        previous_status = work_order.status

        work_order.status = new_status
        work_order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        self._create_status_history(
            work_order=work_order,
            previous_status=previous_status,
            new_status=new_status,
            user=user,
            notes=notes,
        )

        serializer = WorkOrderSerializer(
            work_order,
            context=self.get_serializer_context(),
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def _set_status(
        self,
        work_order,
        new_status,
        user,
        notes="",
    ):
        previous_status = work_order.status

        work_order.status = new_status
        work_order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        self._create_status_history(
            work_order=work_order,
            previous_status=previous_status,
            new_status=new_status,
            user=user,
            notes=notes,
        )

    @staticmethod
    def _create_status_history(
        work_order,
        previous_status,
        new_status,
        user,
        notes="",
    ):
        from .models import WorkOrderStatusHistory

        WorkOrderStatusHistory.objects.create(
            work_order=work_order,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=user,
            changed_at=timezone.now(),
            notes=str(notes).strip(),
        )


class WorkOrderAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrderAssignmentSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "user__username",
        "user__first_name",
        "user__last_name",
        "assigned_by__username",
        "notes",
    ]

    ordering_fields = [
        "assigned_at",
        "removed_at",
        "role",
        "is_active",
        "created_at",
    ]

    ordering = [
        "-assigned_at",
        "-id",
    ]

    def get_queryset(self):
        queryset = WorkOrderAssignment.objects.select_related(
            "work_order",
            "work_order__project",
            "user",
            "assigned_by",
        ).all()

        work_order_id = self.request.query_params.get("work_order")
        user_id = self.request.query_params.get("user")
        role = self.request.query_params.get("role")
        is_active = self.request.query_params.get("is_active")

        if work_order_id:
            queryset = queryset.filter(
                work_order_id=work_order_id
            )

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if role:
            queryset = queryset.filter(role=role)

        if is_active is not None:
            queryset = queryset.filter(
                is_active=self._parse_boolean(is_active)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            assigned_by=self.request.user,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="remove",
    )
    def remove_assignment(self, request, pk=None):
        assignment = self.get_object()

        if not assignment.is_active:
            return Response(
                {
                    "detail": (
                        "این تخصیص قبلاً غیرفعال شده است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.is_active = False
        assignment.removed_at = timezone.now()
        assignment.notes = str(
            request.data.get("notes", assignment.notes)
        ).strip()
        assignment.save(
            update_fields=[
                "is_active",
                "removed_at",
                "notes",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(assignment)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _parse_boolean(value):
        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


class WorkOrderLaborViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrderLaborSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "user__username",
        "user__first_name",
        "user__last_name",
        "description",
    ]

    ordering_fields = [
        "work_date",
        "started_at",
        "finished_at",
        "hours",
        "hourly_rate",
        "created_at",
    ]

    ordering = [
        "-work_date",
        "-id",
    ]

    def get_queryset(self):
        queryset = WorkOrderLabor.objects.select_related(
            "work_order",
            "work_order__project",
            "user",
        ).all()

        work_order_id = self.request.query_params.get("work_order")
        user_id = self.request.query_params.get("user")
        work_date_from = self.request.query_params.get(
            "work_date_from"
        )
        work_date_to = self.request.query_params.get(
            "work_date_to"
        )

        if work_order_id:
            queryset = queryset.filter(
                work_order_id=work_order_id
            )

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if work_date_from:
            queryset = queryset.filter(
                work_date__gte=work_date_from
            )

        if work_date_to:
            queryset = queryset.filter(
                work_date__lte=work_date_to
            )

        return queryset


class WorkOrderDowntimeViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrderDowntimeSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "reason",
        "notes",
    ]

    ordering_fields = [
        "started_at",
        "finished_at",
        "production_loss",
        "created_at",
    ]

    ordering = [
        "-started_at",
        "-id",
    ]

    def get_queryset(self):
        queryset = WorkOrderDowntime.objects.select_related(
            "work_order",
            "work_order__project",
        ).all()

        work_order_id = self.request.query_params.get("work_order")
        started_from = self.request.query_params.get(
            "started_from"
        )
        started_to = self.request.query_params.get("started_to")
        open_only = self.request.query_params.get("open_only")

        if work_order_id:
            queryset = queryset.filter(
                work_order_id=work_order_id
            )

        if started_from:
            queryset = queryset.filter(
                started_at__date__gte=started_from
            )

        if started_to:
            queryset = queryset.filter(
                started_at__date__lte=started_to
            )

        if open_only is not None:
            if self._parse_boolean(open_only):
                queryset = queryset.filter(finished_at__isnull=True)
            else:
                queryset = queryset.filter(
                    finished_at__isnull=False
                )

        return queryset

    @action(
        detail=True,
        methods=["post"],
        url_path="finish",
    )
    def finish(self, request, pk=None):
        downtime = self.get_object()

        if downtime.finished_at:
            return Response(
                {
                    "detail": (
                        "این توقف قبلاً خاتمه یافته است."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        finished_at = request.data.get(
            "finished_at",
            timezone.now(),
        )

        serializer = self.get_serializer(
            downtime,
            data={
                "finished_at": finished_at,
                "production_loss": request.data.get(
                    "production_loss",
                    downtime.production_loss,
                ),
                "notes": request.data.get(
                    "notes",
                    downtime.notes,
                ),
            },
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _parse_boolean(value):
        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


class WorkOrderFailureViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrderFailureSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "work_order__work_order_number",
        "work_order__title",
        "failure_mode",
        "symptom",
        "immediate_cause",
        "root_cause",
        "corrective_action",
        "preventive_action",
    ]

    ordering_fields = [
        "failure_type",
        "requires_follow_up",
        "follow_up_due_date",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-updated_at",
        "-id",
    ]

    def get_queryset(self):
        queryset = WorkOrderFailure.objects.select_related(
            "work_order",
            "work_order__project",
            "work_order__asset",
        ).all()

        work_order_id = self.request.query_params.get("work_order")
        failure_type = self.request.query_params.get(
            "failure_type"
        )
        requires_follow_up = self.request.query_params.get(
            "requires_follow_up"
        )
        due_from = self.request.query_params.get("due_from")
        due_to = self.request.query_params.get("due_to")
        overdue = self.request.query_params.get("overdue")

        if work_order_id:
            queryset = queryset.filter(
                work_order_id=work_order_id
            )

        if failure_type:
            queryset = queryset.filter(
                failure_type=failure_type
            )

        if requires_follow_up is not None:
            queryset = queryset.filter(
                requires_follow_up=self._parse_boolean(
                    requires_follow_up
                )
            )

        if due_from:
            queryset = queryset.filter(
                follow_up_due_date__gte=due_from
            )

        if due_to:
            queryset = queryset.filter(
                follow_up_due_date__lte=due_to
            )

        if overdue is not None:
            today = timezone.localdate()

            if self._parse_boolean(overdue):
                queryset = queryset.filter(
                    requires_follow_up=True,
                    follow_up_due_date__lt=today,
                )
            else:
                queryset = queryset.filter(
                    Q(requires_follow_up=False)
                    | Q(follow_up_due_date__gte=today)
                    | Q(follow_up_due_date__isnull=True)
                )

        return queryset

    @staticmethod
    def _parse_boolean(value):
        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
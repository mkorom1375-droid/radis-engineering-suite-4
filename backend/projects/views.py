from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Project,
    ProjectNumberingSettings,
    ProjectStage,
)
from .serializers import (
    ProjectNumberingSettingsSerializer,
    ProjectSerializer,
    ProjectStageSerializer,
)
from .services import (
    ProjectNumberingService,
    ProjectStageService,
)


def projects_for_user(user, include_inactive=False):
    queryset = Project.objects.select_related("organization")
    if not user.is_superuser:
        organization_id = getattr(user, "organization_id", None)
        if not organization_id:
            return queryset.none()
        queryset = queryset.filter(organization_id=organization_id)
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset


def validation_detail(error):
    if getattr(error, "message_dict", None):
        return error.message_dict
    return error.messages


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return projects_for_user(self.request.user)

    def perform_create(self, serializer):
        organization = getattr(self.request.user, "organization", None)
        if organization is None:
            raise ValidationError(
                {
                    "organization": (
                        "Your user account is not assigned "
                        "to an organization."
                    )
                }
            )
        try:
            code = ProjectNumberingService.resolve_code(
                organization=organization,
                requested_code=serializer.validated_data.get("code"),
            )
        except DjangoValidationError as error:
            raise ValidationError(validation_detail(error)) from error
        try:
            serializer.save(organization=organization, code=code)
        except IntegrityError as error:
            raise ValidationError(
                {"code": "کد پروژه در همین سازمان تکراری است."}
            ) from error

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        project = get_object_or_404(
            projects_for_user(request.user, include_inactive=True),
            pk=pk,
        )
        if project.is_active:
            return Response(
                {"detail": "Project is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.is_active = True
        project.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(project).data)


class ProjectNumberingSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_organization(self, request):
        organization = getattr(request.user, "organization", None)
        if organization is None:
            raise ValidationError(
                {
                    "organization": (
                        "Your user account is not assigned "
                        "to an organization."
                    )
                }
            )
        return organization

    def get_or_create_settings(self, organization):
        settings, _ = ProjectNumberingSettings.objects.get_or_create(
            organization=organization,
            defaults={"prefix": organization.code},
        )
        return settings

    def get(self, request):
        organization = self.get_organization(request)
        settings = self.get_or_create_settings(organization)
        return Response(ProjectNumberingSettingsSerializer(settings).data)

    def patch(self, request):
        organization = self.get_organization(request)
        with transaction.atomic():
            locked = ProjectNumberingSettings.objects.select_for_update().filter(
                organization=organization,
            ).first()
            if locked is None:
                locked = ProjectNumberingSettings.objects.create(
                    organization=organization,
                    prefix=organization.code,
                )
            serializer = ProjectNumberingSettingsSerializer(
                locked,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)


class ProjectStageViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectStageSerializer
    permission_classes = [IsAuthenticated]

    def get_project_queryset(self, include_inactive=False):
        return projects_for_user(
            self.request.user,
            include_inactive=include_inactive,
        )

    def get_project(self, include_inactive=False):
        return get_object_or_404(
            self.get_project_queryset(include_inactive=include_inactive),
            pk=self.kwargs["project_pk"],
        )

    def get_queryset(self):
        return ProjectStage.objects.filter(
            project=self.get_project(),
            is_active=True,
        ).select_related("project")

    def perform_create(self, serializer):
        project = self.get_project()
        if "order" not in serializer.initial_data:
            order = ProjectStageService.next_order(project)
        else:
            order = serializer.validated_data["order"]
        if ProjectStage.objects.filter(
            project=project,
            order=order,
            is_active=True,
        ).exists():
            raise ValidationError(
                {"order": "این ترتیب مرحله قبلاً برای پروژه استفاده شده است."}
            )
        try:
            code = ProjectStageService.resolve_code(
                project=project,
                requested_code=serializer.validated_data.get("code"),
                order=order,
            )
        except DjangoValidationError as error:
            raise ValidationError(validation_detail(error)) from error
        try:
            serializer.save(project=project, order=order, code=code)
        except IntegrityError as error:
            raise ValidationError(
                {"detail": "کد یا ترتیب مرحله تکراری است."}
            ) from error

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, project_pk=None, pk=None):
        project = self.get_project_queryset(include_inactive=True).filter(
            pk=project_pk,
        ).first()
        if project is None:
            return Response(
                {"detail": "No Project matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )
        stage = get_object_or_404(
            ProjectStage.objects.filter(project=project),
            pk=pk,
        )
        if stage.is_active:
            return Response(
                {"detail": "Project stage is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ProjectStage.objects.filter(
            project=project,
            order=stage.order,
            is_active=True,
        ).exists():
            return Response(
                {"order": "ترتیب مرحله در حال حاضر استفاده شده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stage.is_active = True
        stage.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(stage).data)

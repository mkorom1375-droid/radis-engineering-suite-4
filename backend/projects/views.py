from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Project.objects.filter(is_active=True)

        if not user.organization:
            return Project.objects.none()

        return Project.objects.filter(
            organization=user.organization,
            is_active=True,
        )

    def perform_create(self, serializer):
        organization = self.request.user.organization

        if organization is None:
            raise ValidationError(
                {
                    "organization": (
                        "Your user account is not assigned "
                        "to an organization."
                    )
                }
            )

        serializer.save(organization=organization)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        user = request.user

        if user.is_superuser:
            queryset = Project.objects.all()
        elif user.organization:
            queryset = Project.objects.filter(
                organization=user.organization,
            )
        else:
            queryset = Project.objects.none()

        project = queryset.filter(pk=pk).first()

        if project is None:
            return Response(
                {
                    "detail": (
                        "No Project matches the given query."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if project.is_active:
            return Response(
                {
                    "detail": "Project is already active."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        project.is_active = True
        project.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(project)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
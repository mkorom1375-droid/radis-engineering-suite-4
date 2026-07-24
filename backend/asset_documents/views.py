from django.shortcuts import get_object_or_404
from rest_framework import filters, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import OrganizationQuerysetMixin, SoftDeleteMixin
from core.permissions import (
    IsAuthenticatedAndActive,
    IsSuperuserOrOrganizationMember,
)

from .models import AssetDocument
from .serializers import AssetDocumentSerializer


class AssetDocumentViewSet(
    OrganizationQuerysetMixin,
    SoftDeleteMixin,
    viewsets.ModelViewSet,
):
    serializer_class = AssetDocumentSerializer

    permission_classes = [
        IsAuthenticatedAndActive,
        IsSuperuserOrOrganizationMember,
    ]

    parser_classes = [
        parsers.MultiPartParser,
        parsers.FormParser,
        parsers.JSONParser,
    ]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "title",
        "document_number",
        "revision",
        "description",
        "asset__code",
        "asset__name",
        "asset__project__code",
        "asset__project__name",
    ]

    ordering_fields = [
        "title",
        "document_type",
        "document_number",
        "revision",
        "document_date",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_at",
    ]

    organization_lookup = "asset__project__organization_id"

    def get_queryset(self):
        queryset = (
            AssetDocument.objects.select_related(
                "asset",
                "asset__project",
                "asset__project__organization",
                "uploaded_by",
            )
            .filter(
                is_active=True,
                asset__is_active=True,
                asset__project__is_active=True,
            )
        )

        queryset = self.filter_queryset_by_organization(queryset)

        asset_id = self.request.query_params.get("asset")
        project_id = self.request.query_params.get("project")
        document_type = self.request.query_params.get("document_type")
        document_number = self.request.query_params.get("document_number")

        if asset_id:
            queryset = queryset.filter(
                asset_id=asset_id,
            )

        if project_id:
            queryset = queryset.filter(
                asset__project_id=project_id,
            )

        if document_type:
            queryset = queryset.filter(
                document_type=document_type,
            )

        if document_number:
            queryset = queryset.filter(
                document_number__icontains=document_number,
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            uploaded_by=self.request.user,
        )

    @action(
        detail=True,
        methods=[
            "post",
        ],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        queryset = AssetDocument.objects.select_related(
            "asset",
            "asset__project",
            "asset__project__organization",
            "uploaded_by",
        )

        queryset = self.filter_queryset_by_organization(queryset)

        document = get_object_or_404(
            queryset,
            pk=pk,
        )

        self.check_object_permissions(
            request,
            document,
        )

        if document.is_active:
            return Response(
                {
                    "success": False,
                    "message": "این سند در حال حاضر فعال است.",
                    "errors": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not document.asset.is_active:
            return Response(
                {
                    "success": False,
                    "message": (
                        "تجهیز مرتبط با این سند غیرفعال است. "
                        "ابتدا تجهیز را فعال کنید."
                    ),
                    "errors": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not document.asset.project.is_active:
            return Response(
                {
                    "success": False,
                    "message": (
                        "پروژه مرتبط با این سند غیرفعال است. "
                        "ابتدا پروژه را فعال کنید."
                    ),
                    "errors": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.is_active = True
        document.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(document)

        return Response(
            {
                "success": True,
                "message": "سند با موفقیت بازیابی شد.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
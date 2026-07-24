from django.db.models import Count
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Asset
from .serializers import AssetListSerializer, AssetSerializer


class AssetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "code",
        "name",
        "manufacturer",
        "model",
        "serial_number",
        "description",
        "location__code",
        "location__name",
    ]

    ordering_fields = [
        "code",
        "name",
        "asset_type",
        "manufacturer",
        "model",
        "commission_date",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "code",
    ]

    def get_queryset(self):
        queryset = (
            Asset.objects.select_related(
                "project",
                "location",
            )
            .annotate(
                documents_count=Count(
                    "documents",
                    distinct=True,
                )
            )
        )

        user = self.request.user

        if not user.is_superuser:
            organization_id = getattr(
                user,
                "organization_id",
                None,
            )

            if organization_id:
                queryset = queryset.filter(
                    project__organization_id=organization_id
                )

        project_id = self.request.query_params.get("project")

        if project_id:
            queryset = queryset.filter(
                project_id=project_id
            )

        location_id = self.request.query_params.get("location")

        if location_id == "null":
            queryset = queryset.filter(
                location__isnull=True
            )

        elif location_id:
            queryset = queryset.filter(
                location_id=location_id
            )

        asset_type = self.request.query_params.get("asset_type")

        if asset_type:
            queryset = queryset.filter(
                asset_type=asset_type
            )

        is_active = self.request.query_params.get("is_active")

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return AssetListSerializer

        return AssetSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(
        detail=True,
        methods=["post"],
    )
    def restore(self, request, pk=None):
        asset = self.get_object()

        asset.is_active = True
        asset.save(update_fields=["is_active"])

        serializer = self.get_serializer(asset)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
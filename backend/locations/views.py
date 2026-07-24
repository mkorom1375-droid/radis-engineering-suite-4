from django.db.models import Count, Prefetch
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Location
from .serializers import (
    LocationListSerializer,
    LocationSerializer,
    LocationTreeSerializer,
)


class LocationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "code",
        "name",
        "description",
    ]

    ordering_fields = [
        "code",
        "name",
        "location_type",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "code",
    ]

    def get_queryset(self):
        queryset = (
            Location.objects.select_related(
                "project",
                "parent",
            )
            .annotate(
                children_count=Count(
                    "children",
                    distinct=True,
                ),
                assets_count=Count(
                    "assets",
                    distinct=True,
                ),
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

        parent_id = self.request.query_params.get("parent")

        if parent_id == "null":
            queryset = queryset.filter(
                parent__isnull=True
            )

        elif parent_id:
            queryset = queryset.filter(
                parent_id=parent_id
            )

        location_type = self.request.query_params.get(
            "location_type"
        )

        if location_type:
            queryset = queryset.filter(
                location_type=location_type
            )

        is_active = self.request.query_params.get(
            "is_active"
        )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return LocationListSerializer

        if self.action == "tree":
            return LocationTreeSerializer

        return LocationSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(
        detail=True,
        methods=["post"],
    )
    def restore(self, request, pk=None):
        location = self.get_object()

        location.is_active = True
        location.save(update_fields=["is_active"])

        serializer = self.get_serializer(location)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
    )
    def tree(self, request):
        queryset = self.get_queryset().filter(
            parent__isnull=True,
            is_active=True,
        ).prefetch_related(
            Prefetch(
                "children",
                queryset=Location.objects.filter(
                    is_active=True
                ).order_by("code"),
            )
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)
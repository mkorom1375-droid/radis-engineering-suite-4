from django.core.exceptions import ValidationError
from django.db import transaction

from organizations.models import Organization

from .models import (
    Project,
    ProjectNumberingSettings,
    ProjectStage,
)


class ProjectNumberingService:
    """Allocate project codes without race conditions inside an organization."""

    @staticmethod
    def normalize_code(value):
        return str(value or "").strip().upper()

    @classmethod
    def resolve_code(cls, organization, requested_code=None):
        requested = cls.normalize_code(requested_code)
        if requested:
            if Project.objects.filter(
                organization=organization,
                code=requested,
            ).exists():
                raise ValidationError(
                    {"code": "این کد پروژه قبلاً در همین سازمان استفاده شده است."}
                )
            return requested

        with transaction.atomic():
            locked_organization = (
                Organization.objects.select_for_update().get(pk=organization.pk)
            )
            settings, _ = ProjectNumberingSettings.objects.select_for_update().get_or_create(
                organization=locked_organization,
                defaults={"prefix": locked_organization.code},
            )
            prefix = (settings.prefix or locked_organization.code).strip().upper()
            separator = settings.separator
            number = settings.next_number
            while True:
                code = f"{prefix}{separator}{number:0{settings.padding}d}"
                if not Project.objects.filter(
                    organization=locked_organization,
                    code=code,
                ).exists():
                    break
                number += 1
            settings.next_number = number + 1
            settings.save(update_fields=["next_number", "updated_at"])
            return code


class ProjectStageService:
    """Keep stage ordering and generated stage codes deterministic."""

    @staticmethod
    def next_order(project):
        return (
            ProjectStage.objects.filter(project=project)
            .order_by("-order")
            .values_list("order", flat=True)
            .first()
            or 0
        ) + 1

    @classmethod
    def resolve_code(cls, project, requested_code=None, order=None):
        requested = str(requested_code or "").strip().upper()
        if requested:
            if ProjectStage.objects.filter(
                project=project,
                code=requested,
            ).exists():
                raise ValidationError(
                    {"code": "این کد مرحله قبلاً برای پروژه استفاده شده است."}
                )
            return requested

        stage_order = order or cls.next_order(project)
        candidate = f"STG-{stage_order:02d}"
        suffix = 2
        while ProjectStage.objects.filter(
            project=project,
            code=candidate,
        ).exists():
            candidate = f"STG-{stage_order:02d}-{suffix}"
            suffix += 1
        return candidate

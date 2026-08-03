from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from organizations.models import Organization

from .models import (
    Project,
    ProjectNumberingSettings,
    ProjectStage,
    ProjectStageStatus,
)


User = get_user_model()


class ProjectNumberingAndStageApiTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="RADIS Engineering",
            code="radis",
        )
        self.user = User.objects.create_user(
            username="engineer",
            email="engineer@example.com",
            password="strong-test-password",
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)
        self.projects_url = reverse("projects-list")
        self.numbering_url = reverse("project-numbering")

    def create_project(self, **payload):
        response = self.client.post(
            self.projects_url,
            {
                "name": payload.pop("name", "Conveyor design"),
                **payload,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def stage_url(self, project_id, suffix=""):
        return f"/api/projects/{project_id}/stages/{suffix}"

    def test_project_code_is_generated_atomically_from_organization_settings(self):
        first = self.create_project(name="First project")
        second = self.create_project(name="Second project")

        self.assertEqual(first.data["code"], "RADIS-0001")
        self.assertEqual(second.data["code"], "RADIS-0002")
        settings = ProjectNumberingSettings.objects.get(
            organization=self.organization,
        )
        self.assertEqual(settings.next_number, 3)

    def test_numbering_settings_can_be_configured_for_future_projects(self):
        response = self.client.patch(
            self.numbering_url,
            {
                "prefix": "eng",
                "separator": "/",
                "padding": 3,
                "next_number": 7,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["prefix"], "ENG")
        self.assertEqual(response.data["padding"], 3)

        created = self.create_project(name="Configured project")
        self.assertEqual(created.data["code"], "ENG/007")

    def test_explicit_project_code_is_normalized_and_scoped(self):
        response = self.create_project(
            name="Manual code",
            code="  custom-42  ",
        )
        self.assertEqual(response.data["code"], "CUSTOM-42")
        self.assertEqual(
            Project.objects.filter(
                organization=self.organization,
                code="CUSTOM-42",
            ).count(),
            1,
        )

        duplicate = self.client.post(
            self.projects_url,
            {"name": "Duplicate", "code": "custom-42"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", duplicate.data)

    def test_stage_routes_generate_codes_and_project_progress(self):
        project = self.create_project().data
        project_id = project["id"]

        first = self.client.post(
            self.stage_url(project_id),
            {
                "name": "Calculations",
                "weight": "2.000",
                "planned_start": "2026-08-01",
                "planned_end": "2026-08-10",
            },
            format="json",
        )
        second = self.client.post(
            self.stage_url(project_id),
            {"name": "Design", "weight": "1.000"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["code"], "STG-01")
        self.assertEqual(second.data["code"], "STG-02")

        completed = self.client.patch(
            self.stage_url(project_id, f"{first.data['id']}/"),
            {
                "status": ProjectStageStatus.COMPLETED,
                "actual_start": "2026-08-01",
                "actual_end": "2026-08-05",
            },
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)

        project_response = self.client.get(
            reverse("projects-detail", kwargs={"pk": project_id}),
        )
        self.assertEqual(project_response.status_code, status.HTTP_200_OK)
        self.assertEqual(project_response.data["stage_count"], 2)
        self.assertEqual(project_response.data["completed_stage_count"], 1)
        self.assertEqual(project_response.data["progress_percent"], "66.67")

    def test_stage_date_and_order_errors_are_returned_as_400(self):
        project = self.create_project().data
        project_id = project["id"]

        invalid_dates = self.client.post(
            self.stage_url(project_id),
            {
                "name": "Invalid dates",
                "planned_start": "2026-08-10",
                "planned_end": "2026-08-01",
            },
            format="json",
        )
        self.assertEqual(
            invalid_dates.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("planned_end", invalid_dates.data)

        self.create_stage = self.client.post(
            self.stage_url(project_id),
            {"name": "First", "order": 4},
            format="json",
        )
        self.assertEqual(
            self.create_stage.status_code,
            status.HTTP_201_CREATED,
        )
        duplicate_order = self.client.post(
            self.stage_url(project_id),
            {"name": "Duplicate order", "order": 4},
            format="json",
        )
        self.assertEqual(
            duplicate_order.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("order", duplicate_order.data)

    def test_stage_delete_is_soft_and_restore_is_scoped(self):
        project = self.create_project().data
        created = self.client.post(
            self.stage_url(project["id"]),
            {"name": "Manufacturing"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        deleted = self.client.delete(
            self.stage_url(project["id"], f"{created.data['id']}/"),
        )
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(
            ProjectStage.objects.filter(
                pk=created.data["id"],
                is_active=False,
            ).exists()
        )

        restored = self.client.post(
            self.stage_url(
                project["id"],
                f"{created.data['id']}/restore/",
            ),
            {},
            format="json",
        )
        self.assertEqual(restored.status_code, status.HTTP_200_OK)
        self.assertTrue(restored.data["is_active"])

    def test_anonymous_project_and_numbering_access_returns_bearer_401(self):
        self.client.force_authenticate(user=None)
        project_response = self.client.get(self.projects_url)
        numbering_response = self.client.get(self.numbering_url)

        self.assertEqual(project_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(numbering_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Bearer", project_response["WWW-Authenticate"])

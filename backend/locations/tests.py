from django.test import TestCase

from locations.models import Location
from organizations.models import Organization
from projects.models import Project


class LocationModelTest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            code="ORG001",
            name="Test Organization",
        )

        self.project = Project.objects.create(
            organization=self.organization,
            code="PRJ001",
            name="Test Project",
        )

    def test_create_location(self):
        location = Location.objects.create(
            project=self.project,
            code="AREA-01",
            name="Area 01",
        )

        self.assertEqual(location.code, "AREA-01")
        self.assertEqual(location.name, "Area 01")
        self.assertTrue(location.is_active)

    def test_create_child_location(self):
        parent = Location.objects.create(
            project=self.project,
            code="AREA",
            name="Area",
        )

        child = Location.objects.create(
            project=self.project,
            parent=parent,
            code="LINE-01",
            name="Line 01",
        )

        self.assertEqual(child.parent, parent)
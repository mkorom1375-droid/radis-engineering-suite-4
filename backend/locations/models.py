from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Location(models.Model):
    class LocationType(models.TextChoices):
        SITE = "site", "Site"
        AREA = "area", "Area"
        PLANT = "plant", "Plant"
        BUILDING = "building", "Building"
        FLOOR = "floor", "Floor"
        ROOM = "room", "Room"
        LINE = "line", "Production Line"
        SECTION = "section", "Section"
        UNIT = "unit", "Unit"
        WAREHOUSE = "warehouse", "Warehouse"
        YARD = "yard", "Yard"
        OTHER = "other", "Other"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="locations",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=255,
    )

    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.AREA,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["project_id", "code"]
        indexes = [
            models.Index(fields=["project", "code"]),
            models.Index(fields=["project", "name"]),
            models.Index(fields=["project", "location_type"]),
            models.Index(fields=["project", "is_active"]),
            models.Index(fields=["parent"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "code"],
                name="unique_location_code_per_project",
            ),
            models.CheckConstraint(
                condition=~Q(parent=models.F("id")),
                name="location_parent_cannot_be_self",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def full_name(self):
        names = []
        current = self
        visited_ids = set()

        while current is not None:
            if current.pk and current.pk in visited_ids:
                break

            if current.pk:
                visited_ids.add(current.pk)

            names.append(current.name)
            current = current.parent

        return " / ".join(reversed(names))

    @property
    def full_code(self):
        codes = []
        current = self
        visited_ids = set()

        while current is not None:
            if current.pk and current.pk in visited_ids:
                break

            if current.pk:
                visited_ids.add(current.pk)

            codes.append(current.code)
            current = current.parent

        return " / ".join(reversed(codes))

    def clean(self):
        errors = {}

        if self.project_id and not self.project.is_active:
            errors["project"] = "Location cannot belong to an inactive project."

        if self.parent_id:
            if self.pk and self.parent_id == self.pk:
                errors["parent"] = "A location cannot be its own parent."

            if self.project_id and self.parent.project_id != self.project_id:
                errors["parent"] = (
                    "Parent location must belong to the same project."
                )

            ancestor = self.parent
            visited_ids = set()

            while ancestor is not None:
                if ancestor.pk in visited_ids:
                    errors["parent"] = (
                        "The selected parent contains an invalid circular hierarchy."
                    )
                    break

                visited_ids.add(ancestor.pk)

                if self.pk and ancestor.pk == self.pk:
                    errors["parent"] = (
                        "The selected parent would create a circular hierarchy."
                    )
                    break

                ancestor = ancestor.parent

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip()
        self.name = self.name.strip()
        self.description = self.description.strip()

        self.full_clean()
        super().save(*args, **kwargs)
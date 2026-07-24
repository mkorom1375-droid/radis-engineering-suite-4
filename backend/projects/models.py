from django.db import models


class Project(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="projects",
    )

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
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
        ordering = ["organization", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_project_code_per_org",
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
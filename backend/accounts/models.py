from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    employee_code = models.CharField(
    max_length=50,
    blank=True,
    null=True,
    )
    job_title = models.CharField(
    max_length=150,
    blank=True,
    null=True,
    )

    def __str__(self):
        return self.username
from django.db import models


class Permission(models.Model):
    code = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(
        max_length=200,
    )

    module = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    is_system_permission = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["module", "name"]

    def __str__(self):
        return f"{self.module} | {self.name}"


class Role(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="roles",
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=50,
    )

    description = models.TextField(
        blank=True,
    )

    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_system_role = models.BooleanField(
        default=False,
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
                name="unique_role_code_per_organization",
            ),
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_role_name_per_organization",
            ),
        ]

    def __str__(self):
        return f"{self.organization.code} - {self.name}"
class UserRole(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="user_roles",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="unique_user_role",
            )
        ]

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"
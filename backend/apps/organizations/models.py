"""
Organizations — Department, Sub-department, and Branch structure.
Each company can have a hierarchy of organizational units with assigned heads and members.
"""
import uuid
from django.conf import settings
from django.db import models
from apps.tenants.models import TenantManager


class Department(models.Model):
    """
    Represents a department, sub-department, or branch within a company.
    Hierarchy is achieved through the self-referential `parent` FK.
    """

    class Type(models.TextChoices):
        HEAD_OFFICE = "head_office", "Head Office"
        DEPARTMENT  = "department",  "Department"
        BRANCH      = "branch",      "Branch"

    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "tenants.Company",
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name   = models.CharField(max_length=200)
    type   = models.CharField(max_length=20, choices=Type.choices, default=Type.DEPARTMENT)
    parent = models.ForeignKey(
        "self",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
    )
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        verbose_name        = "Department"
        verbose_name_plural = "Departments"
        ordering            = ["name"]
        unique_together     = [("company", "name", "parent")]
        constraints         = [
            # Only one Head Office per company
            models.UniqueConstraint(
                fields=["company"],
                condition=models.Q(type="head_office"),
                name="unique_head_office_per_company",
            ),
        ]

    def __str__(self):
        return self.name

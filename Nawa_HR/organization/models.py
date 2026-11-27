from django.db import models

from core.models import PublicIdModel


class Department(PublicIdModel):
    """
    A part of the company, such as Engineering or Finance.

    Departments are never deleted: roles and their history point to them.
    """

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Role(PublicIdModel):
    """
    A position inside a department, such as "Backend Developer".

    Employees hold roles over time through role assignments, and an
    employee's department comes from their current role. ``access`` says
    what the role is allowed to do in the system.
    """

    class Access(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        HR = "hr", "HR"
        ADMIN = "admin", "Admin"

    name = models.CharField(max_length=100)
    # A department with roles can't be deleted
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="roles",
    )
    access = models.CharField(
        max_length=20,
        choices=Access.choices,
        default=Access.EMPLOYEE,
    )

    class Meta:
        ordering = ["department__name", "name"]
        constraints = [
            # The same role name can exist in different departments, but not twice in one
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_role_name_per_department",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.department})"

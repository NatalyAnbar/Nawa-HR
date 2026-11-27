from django.conf import settings
from django.db import models

from core.models import PublicIdModel
from organization.models import Role


class Employee(PublicIdModel):
    """
    A person's HR record: when they were hired, whether they still work
    here, and how they are employed.

    Every employee has exactly one user account for logging in. The
    department isn't stored here: it comes from the employee's current
    role assignment, so there is a single source of truth.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TERMINATED = "terminated", "Terminated"

    class EmploymentType(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        CONTRACTOR = "contractor", "Contractor"

    # Deleting the user deletes the employee, unless HR records protect it
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee",
    )
    # Indexed for "recent hires" filters and ordering by seniority
    hire_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.EMPLOYEE,
    )

    termination_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.email

    class Meta:
        constraints = [
            # An employee can't leave before they were hired (same day is allowed)
            models.CheckConstraint(
                condition=models.Q(hire_date__lt=models.F("termination_date")),
                name="employee_hired_before_terminated",
            )
        ]


class RoleAssignment(PublicIdModel):
    """
    A period during which an employee holds a role.

    An employee's history is a chain of assignments. The current one has
    no end date, and it also gives the employee's department, so the
    department is stored in one place only.

    Changing someone's role ends the current assignment and opens a new
    one; old assignments are kept as history.
    """

    # An employee or role with history can't be deleted
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    started_at = models.DateField()
    # Empty while the assignment is current
    ended_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            # An assignment lasts at least one day: it ends after the day it started
            models.CheckConstraint(
                condition=models.Q(ended_at__gt=models.F("started_at")),
                name="role_assignment_ends_after_start",
            ),
            # An employee holds one current role at a time
            models.UniqueConstraint(
                fields=["employee"],
                condition=models.Q(ended_at__isnull=True),
                name="one_current_role_per_employee",
            ),
        ]

    def __str__(self):
        end = self.ended_at or "now"
        return f"{self.employee} as {self.role}, {self.started_at} to {end}"

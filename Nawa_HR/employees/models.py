from django.conf import settings
from django.db import models

from core.models import PublicIdModel


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

from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserSerializer
from core.serializers import PublicIdSerializer

from . import models


class TerminateSerializer(serializers.ModelSerializer):
    """
    Input for ending someone's employment.

    HR gives the last working day. It can't be in the future, or before
    the employee was hired.
    """

    class Meta:
        model = models.Employee
        fields = ["termination_date"]
        extra_kwargs = {
            # The model allows an empty date (active employees), but terminating needs one
            "termination_date": {"required": True, "allow_null": False},
        }

    def validate_termination_date(self, value):
        """Check the date against today and the employee's hire date."""
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "The termination date can't be in the future."
            )
        # self.instance is the employee being terminated, passed in by the view
        if value <= self.instance.hire_date:
            raise serializers.ValidationError(
                "The termination date can't be before the hire date."
            )
        return value

    def validate(self, attrs):
        """Refuse to terminate someone who has already left."""
        if self.instance.status == models.Employee.Status.TERMINATED:
            raise serializers.ValidationError("This employee is already terminated.")
        return attrs


class EmployeeSerializer(PublicIdSerializer):
    """
    An employee as HR sees them: the person's account details and their
    employment record.

    The employee is identified by ``public_id``, shown to clients as ``id``;
    the internal database id never leaves the API.
    """

    # Read-only for now: creating the user and employee together comes next
    user = UserSerializer()

    termination_date = serializers.DateField(default=None)

    class Meta:
        model = models.Employee
        fields = [
            "id",
            "user",
            "status",
            "employment_type",
            "hire_date",
            "termination_date",
        ]
        # Changed only through the terminate endpoint
        read_only_fields = ["status"]


class RoleAssignmentSerializer(PublicIdSerializer):
    """
    A period during which an employee held a role.

    The employee and role are sent and shown as their public UUIDs; the
    role and department names are included for display.
    """

    employee = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=models.Employee.objects.all(),
    )
    role = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=models.Role.objects.all(),
    )
    role_name = serializers.CharField(source="role.name", read_only=True)
    department_name = serializers.CharField(
        source="role.department.name", read_only=True
    )

    class Meta:
        model = models.RoleAssignment
        fields = [
            "id",
            "employee",
            "role",
            "role_name",
            "department_name",
            "started_at",
            "ended_at",
        ]


def validate(self, attrs):
    """
    Check the period, then make sure it comes after the employee's latest
    role, so an employee's roles never overlap.
    """
    ended_at = attrs.get("ended_at")
    if ended_at is not None and ended_at <= attrs["started_at"]:
        raise serializers.ValidationError(
            {"ended_at": "A role must end after the day it started."}
        )

    latest = attrs["employee"].assignments.order_by("-started_at").first()
    if latest and (latest.ended_at is None or attrs["started_at"] < latest.ended_at):
        raise serializers.ValidationError(
            "A new role must start after the current one has ended."
        )
    return attrs

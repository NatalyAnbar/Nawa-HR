from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserSerializer

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


class EmployeeSerializer(serializers.ModelSerializer):
    """
    An employee as HR sees them: the person's account details and their
    employment record.

    The employee is identified by ``public_id``, shown to clients as ``id``;
    the internal database id never leaves the API.
    """

    # The public UUID, shown to clients as "id"
    id = serializers.UUIDField(source="public_id", read_only=True)
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

from rest_framework import serializers

from . import models
from accounts.serializers import UserSerializer


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

    class Meta:
        model = models.Employee
        fields = ["id", "user", "status", "employment_type", "hire_date"]
        # Changed only through the terminate endpoint
        read_only_fields = ["status"]
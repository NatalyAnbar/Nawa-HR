from rest_framework import serializers

from core.serializers import PublicIdSerializer

from . import models


class DepartmentSerializer(PublicIdSerializer):
    """A department, identified by its public UUID."""

    class Meta:
        model = models.Department
        fields = ["id", "name"]


class RoleSerializer(PublicIdSerializer):
    """
    A role and the department it belongs to.

    The department is sent and shown as its public UUID; its name is
    included for display.
    """

    department = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=models.Department.objects.all(),
    )
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = models.Role
        fields = ["id", "name", "department", "department_name", "access"]

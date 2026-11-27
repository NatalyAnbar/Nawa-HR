from rest_framework import permissions, viewsets

from . import models, serializers


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    HR creates, lists, views and renames departments.

    Departments are never deleted, since roles and their history point
    to them.
    """

    queryset = models.Department.objects.all()
    serializer_class = serializers.DepartmentSerializer
    # Replaced by IsHR once roles exist
    permission_classes = [permissions.IsAdminUser]
    # Departments are addressed by their public UUID, never the internal id
    lookup_field = "public_id"
    # No DELETE: departments are never deleted
    http_method_names = ["get", "post", "patch", "head", "options"]


class RoleViewSet(viewsets.ModelViewSet):
    """
    HR creates, lists, views and updates roles.

    Roles are never deleted, since role assignments keep employees'
    history in them.
    """

    queryset = models.Role.objects.select_related("department")
    serializer_class = serializers.RoleSerializer
    # Replaced by IsHR once roles exist
    permission_classes = [permissions.IsAdminUser]
    # Roles are addressed by their public UUID, never the internal id
    lookup_field = "public_id"
    # No DELETE: roles are never deleted
    http_method_names = ["get", "post", "patch", "head", "options"]

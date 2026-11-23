from rest_framework import permissions, viewsets

from . import models, serializers


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    HR lists, views and updates employees.

    Employees are never deleted: when someone leaves, HR terminates them
    instead, so their records are kept.
    """

    queryset = models.Employee.objects.select_related("user")
    serializer_class = serializers.EmployeeSerializer
    # Replaced by IsHR once roles exist
    permission_classes = [permissions.IsAdminUser]
    # Employees are addressed by their public UUID, never the internal id
    lookup_field = "public_id"
    # POST comes with the create flow; DELETE never: employees are terminated
    http_method_names = ["get", "patch", "head", "options"]
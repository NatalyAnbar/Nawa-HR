from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import emails

from . import models, serializers

User = get_user_model()


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
    http_method_names = ["get", "post", "patch", "head", "options"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee_data = serializer.validated_data
        user_data = employee_data.pop("user")

        with transaction.atomic():
            user = User.objects.create_user(**user_data)
            employee = models.Employee.objects.create(user=user, **employee_data)
            transaction.on_commit(lambda: emails.send_reset_password_mail(user))

        return Response(
            self.get_serializer(employee).data, status=status.HTTP_201_CREATED
        )

    @action(methods=["post"], detail=True)
    def terminate(self, request, public_id):
        employee = self.get_object()
        serializer = serializers.TerminateSerializer(employee, data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            employee.user.is_active = False
            employee.status = models.Employee.Status.TERMINATED
            employee.termination_date = serializer.validated_data["termination_date"]

            employee.save(update_fields=["status", "termination_date"])
            employee.user.save(update_fields=["is_active"])

        return Response(
            serializers.EmployeeSerializer(employee).data, status=status.HTTP_200_OK
        )

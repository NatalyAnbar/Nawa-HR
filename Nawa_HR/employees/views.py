from rest_framework import permissions, viewsets
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from . import models, serializers
from accounts import emails

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
        user_data = employee_data.pop('user')

        with transaction.atomic():
            user = User.objects.create_user(**user_data)
            employee = models.Employee.objects.create(user=user, **employee_data)
            transaction.on_commit(lambda: emails.send_reset_password_mail(user))

        return Response(self.get_serializer(employee).data, status=status.HTTP_201_CREATED)

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from employees.models import Employee

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "Test-password-123"


def today():
    return timezone.localdate()


@pytest.fixture
def employee():
    """An active employee hired 30 days ago, whose user can log in."""
    user = User.objects.create_user(
        email="sara@nawa.com",
        password=PASSWORD,
        first_name="Sara",
        last_name="Haddad",
    )
    return Employee.objects.create(user=user, hire_date=today() - timedelta(days=30))


def terminate_url(employee):
    return reverse("employee-terminate", kwargs={"public_id": employee.public_id})


def terminate(client, employee, termination_date):
    return client.post(
        terminate_url(employee),
        {"termination_date": termination_date.isoformat()},
        format="json",
    )


def login(client, email, password=PASSWORD):
    return client.post(
        reverse("login"), {"email": email, "password": password}, format="json"
    )


class TestTerminate:
    # --- Who can terminate ---

    def test_non_hr_user_cannot_terminate(self, api_client, user, employee):
        api_client.force_authenticate(user=user)

        response = terminate(api_client, employee, today())

        assert response.status_code == 403

    # --- Successful termination ---

    def test_hr_terminates_employee(self, superuser_client, employee):
        response = terminate(superuser_client, employee, today())

        assert response.status_code == 200
        employee.refresh_from_db()
        employee.user.refresh_from_db()
        assert employee.status == Employee.Status.TERMINATED
        assert employee.termination_date == today()
        assert not employee.user.is_active

    def test_response_shows_the_updated_employee(self, superuser_client, employee):
        response = terminate(superuser_client, employee, today())

        assert response.data["status"] == Employee.Status.TERMINATED
        assert response.data["termination_date"] == today().isoformat()

    # --- Rejected termination ---

    def test_future_date_is_rejected(self, superuser_client, employee):
        response = terminate(superuser_client, employee, today() + timedelta(days=1))

        assert response.status_code == 400
        assert "termination_date" in response.data

    def test_date_before_hire_is_rejected(self, superuser_client, employee):
        response = terminate(
            superuser_client, employee, employee.hire_date - timedelta(days=1)
        )

        assert response.status_code == 400
        assert "termination_date" in response.data

    def test_missing_date_is_rejected(self, superuser_client, employee):
        response = superuser_client.post(terminate_url(employee), {}, format="json")

        assert response.status_code == 400
        assert "termination_date" in response.data

    def test_already_terminated_employee_is_rejected(self, superuser_client, employee):
        terminate(superuser_client, employee, today())

        response = terminate(superuser_client, employee, today())

        assert response.status_code == 400

    def test_rejected_termination_changes_nothing(self, superuser_client, employee):
        terminate(superuser_client, employee, today() + timedelta(days=1))

        employee.refresh_from_db()
        employee.user.refresh_from_db()
        assert employee.status == Employee.Status.ACTIVE
        assert employee.termination_date is None
        assert employee.user.is_active

    # --- After termination, the account is locked out ---

    def test_terminated_employee_cannot_log_in(
        self, api_client, superuser_client, employee
    ):
        terminate(superuser_client, employee, today())

        response = login(api_client, employee.user.email)

        assert response.status_code == 401

    def test_old_access_token_stops_working(
        self, api_client, superuser_client, employee
    ):
        access = login(api_client, employee.user.email).data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert api_client.get(reverse("me")).status_code == 200

        terminate(superuser_client, employee, today())

        # Simple JWT checks that the user is still active on every request
        assert api_client.get(reverse("me")).status_code == 401

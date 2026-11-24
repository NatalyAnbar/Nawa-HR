import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from employees import models

User = get_user_model()

pytestmark = pytest.mark.django_db


def invite_url():
    """Return the URL for inviting a new user."""
    return reverse("employee-list")


def invite_data(email="test@nawa.com", **extra_fields):
    """Build a valid payload for inviting a user."""
    return {
        "user": {
            "email": email,
            "first_name": "Nawa",
            "last_name": "HR",
        },
        "employment_type": "employee",
        "hire_date": "2026-11-01"
    } | extra_fields


@pytest.fixture
def superuser():
    """Create and return a superuser account."""
    return User.objects.create_superuser(
        email="superuser@gmail.com",
        password="password-123",
    )


@pytest.fixture
def superuser_client(superuser):
    """Return an APIClient authenticated as a superuser."""
    client = APIClient()
    client.force_authenticate(user=superuser)
    return client


@pytest.fixture
def invited_user(superuser_client):
    """Invite a new user via the API and return the created User instance."""
    response = superuser_client.post(invite_url(), invite_data(), format="json")
    assert response.status_code == 201
    return User.objects.get(email=response.data["email"])


class TestInviteUser:
    """Test suite for the user invitation endpoint."""

    def test_create_emp_user_without_password(self, superuser_client):
        """Ensure a superuser can invite a user who starts with no usable password."""
        response = superuser_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 201
        assert models.Employee.objects.filter(public_id=response.data["id"]).exists()
        user = User.objects.get(email=response.data["user"]["email"])
        assert not user.has_usable_password()


    def test_anonymous_user_cannot_invite(self, api_client):
        """Ensure unauthenticated requests are rejected with 401 Unauthorized."""
        response = api_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 401
        assert User.objects.count() == 0
        assert models.Employee.objects.count() == 0


    def test_regular_user_cannot_invite(self, api_client):
        """Ensure non-admin authenticated users cannot send invitations."""
        regular_user = User.objects.create_user(
            email="regular@nawa.com",
            password="password-123",
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 403


    def test_send_email_after_create_user(self, superuser_client, mailoutbox, django_capture_on_commit_callbacks):
        """Ensure an invitation email containing the user's name is sent on creation."""
        with django_capture_on_commit_callbacks(execute=True):
            response = superuser_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 201
        user = User.objects.get(email=response.data["user"]["email"])
        assert len(mailoutbox) == 1
        assert user.first_name in mailoutbox[0].body
        assert mailoutbox[0].to == [user.email]


    @pytest.mark.parametrize("email", [None, "", "invalid-email"])
    def test_invalid_email_not_create_or_send_mail(
        self, superuser_client, mailoutbox, email
    ):
        """Ensure invalid or empty emails return 400 and do not create users or send mail."""
        response = superuser_client.post(
            invite_url(),
            invite_data(email),
            format="json",
        )

        assert response.status_code == 400
        assert User.objects.count() == 1
        assert len(mailoutbox) == 0


    def test_duplicate_email_fails(self, superuser_client, mailoutbox):
        """Ensure inviting an email that already exists fails with 400 Bad Request."""
        mailoutbox.clear()

        response1 = superuser_client.post(invite_url(), invite_data(), format="json")
        response2 = superuser_client.post(invite_url(), invite_data(), format="json")
        
        assert response1.status_code == 201
        assert response2.status_code == 400
        assert User.objects.count() == 2
        assert models.Employee.objects.count() == 1
        assert len(mailoutbox) == 0



"""
End-to-end tests for journeys that cross several apps.

Each test walks through a flow the way a real user would, using only the
API and the emails the system sends.
"""

import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "Test-password-123"


@pytest.fixture
def anonymous_client():
    """A client with no logged-in user, like an employee opening an email link."""
    return APIClient()


@pytest.fixture
def superuser_client():
    """A client logged in as a superuser, standing in for HR until roles exist."""
    admin = User.objects.create_superuser(email="admin@nawa.com", password=PASSWORD)
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


def link_params(message):
    """Return the uid and token from the link in an email."""
    url = re.search(r"https?://\S+", message.body).group()
    params = parse_qs(urlparse(url).query)
    return params["uid"][0], params["token"][0]


class TestOnboardingFlow:
    def test_hr_adds_employee_who_sets_password_and_logs_in(
        self,
        anonymous_client,
        superuser_client,
        mailoutbox,
        django_capture_on_commit_callbacks,
    ):
        """
        The whole onboarding journey: HR adds an employee, the invite
        email arrives, the employee sets a password from its link, and
        can then log in.
        """
        # HR adds the employee
        with django_capture_on_commit_callbacks(execute=True):
            response = superuser_client.post(
                reverse("employee-list"),
                {
                    "user": {
                        "email": "sara@nawa.com",
                        "first_name": "Sara",
                        "last_name": "Haddad",
                    },
                    "hire_date": "2026-11-01",
                    "employment_type": "employee",
                },
                format="json",
            )
        assert response.status_code == 201
        email = response.data["user"]["email"]

        # The invite email arrives
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [email]
        uid, token = link_params(mailoutbox[0])

        # The employee sets a password from the link
        response = anonymous_client.post(
            reverse("accept-invite"),
            {
                "uid": uid,
                "token": token,
                "new_password": PASSWORD,
                "confirm_new_password": PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200

        # And can now log in
        response = anonymous_client.post(
            reverse("login"),
            {"email": email, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data

    def test_invite_link_works_only_once(
        self,
        anonymous_client,
        superuser_client,
        mailoutbox,
        django_capture_on_commit_callbacks,
    ):
        """The link from the invite email can't be used a second time."""
        with django_capture_on_commit_callbacks(execute=True):
            superuser_client.post(
                reverse("employee-list"),
                {
                    "user": {
                        "email": "omar@nawa.com",
                        "first_name": "Omar",
                        "last_name": "Khalil",
                    },
                    "hire_date": "2026-11-01",
                    "employment_type": "employee",
                },
                format="json",
            )
        uid, token = link_params(mailoutbox[0])
        payload = {
            "uid": uid,
            "token": token,
            "new_password": PASSWORD,
            "confirm_new_password": PASSWORD,
        }

        first = anonymous_client.post(reverse("accept-invite"), payload, format="json")
        second = anonymous_client.post(reverse("accept-invite"), payload, format="json")

        assert first.status_code == 200
        assert second.status_code == 400
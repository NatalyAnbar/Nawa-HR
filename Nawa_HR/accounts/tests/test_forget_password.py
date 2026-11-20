"""Tests for POST /accounts/forget-password/ and POST /accounts/reset-password/."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts import emails

from . import helper

User = get_user_model()

pytestmark = pytest.mark.django_db

EMAIL = "test@nawa.com"
OLD_PASSWORD = "Old-password-123"
NEW_PASSWORD = "New-password-123"


def forget_password_url():
    """Return the URL for requesting a password reset email."""
    return reverse("forget-password")


def reset_password_url():
    """Return the URL for confirming a password reset with uid and token."""
    return reverse("reset-password")


def reset_password_data(user, **overrides):
    """Build a valid password reset confirmation payload from a real link."""
    return {
        **helper.params_from_link(emails.build_reset_link(user)),
        "new_password": NEW_PASSWORD,
        "confirm_new_password": NEW_PASSWORD,
    } | overrides


@pytest.fixture
def active_user():
    """Create and return an active user with a known password."""
    return User.objects.create_user(email=EMAIL, password=OLD_PASSWORD)


class TestForgetPassword:
    """Test suite for requesting a password reset link."""

    def test_valid_email_sends_reset_link(self, api_client, active_user, mailoutbox):
        """Ensure an active user receives a password reset email containing a link."""
        response = api_client.post(
            forget_password_url(),
            {"email": EMAIL},
            format="json",
        )

        assert response.status_code == 200
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [EMAIL]
        assert "/reset-password?" in mailoutbox[0].body

    @pytest.mark.parametrize("email", ["TEST@NAWA.COM", "Test@nawa.com"])
    def test_email_lookup_is_case_insensitive(
        self, api_client, active_user, mailoutbox, email
    ):
        """Ensure uppercase or mixed-case emails still match the user and send mail."""
        response = api_client.post(
            forget_password_url(),
            {"email": email},
            format="json",
        )

        assert response.status_code == 200
        assert len(mailoutbox) == 1

    def test_unknown_email_is_rejected(self, api_client, mailoutbox):
        """Ensure non-existent emails fail validation and send no email."""
        response = api_client.post(
            forget_password_url(),
            {"email": "unknown@nawa.com"},
            format="json",
        )

        assert response.status_code == 400
        assert len(mailoutbox) == 0

    def test_inactive_user_is_rejected(self, api_client, active_user, mailoutbox):
        """Ensure disabled accounts cannot request password reset links."""
        active_user.is_active = False
        active_user.save(update_fields=["is_active"])

        response = api_client.post(
            forget_password_url(),
            {"email": EMAIL},
            format="json",
        )

        assert response.status_code == 400
        assert len(mailoutbox) == 0


class TestResetPassword:
    """Test suite for confirming a password reset using uid and token."""

    def test_valid_link_resets_password(self, api_client, active_user):
        """Ensure valid uid and token update the user's password successfully."""
        response = api_client.post(
            reset_password_url(),
            reset_password_data(active_user),
            format="json",
        )
        print(response.data)
        assert response.status_code == 200
        active_user.refresh_from_db()
        assert active_user.check_password(NEW_PASSWORD)

    def test_reusing_token_after_reset_fails(self, api_client, active_user):
        """Ensure a password reset link works only once."""
        payload = reset_password_data(active_user)

        first_response = api_client.post(reset_password_url(), payload, format="json")
        assert first_response.status_code == 200

        second_response = api_client.post(reset_password_url(), payload, format="json")
        assert second_response.status_code == 400

    def test_invalid_token_fails(self, api_client, active_user):
        """Ensure a tampered or invalid token is rejected without changing password."""
        payload = reset_password_data(active_user, token="invalid-token-123")
        response = api_client.post(reset_password_url(), payload, format="json")

        assert response.status_code == 400
        active_user.refresh_from_db()
        assert active_user.check_password(OLD_PASSWORD)

    def test_invalid_uid_fails(self, api_client, active_user):
        """Ensure a malformed or non-existent uid is rejected."""
        payload = reset_password_data(active_user, uid="invalid-uid")
        response = api_client.post(reset_password_url(), payload, format="json")

        assert response.status_code == 400

    def test_mismatched_passwords_fails(self, api_client, active_user):
        """Ensure mismatched new_password and confirm_new_password fail validation."""
        payload = reset_password_data(
            active_user,
            confirm_new_password="Different-password-123",
        )
        response = api_client.post(reset_password_url(), payload, format="json")

        assert response.status_code == 400
        active_user.refresh_from_db()
        assert active_user.check_password(OLD_PASSWORD)

    def test_weak_password_fails(self, api_client, active_user):
        """Ensure Django's password strength validators reject weak passwords."""
        payload = reset_password_data(
            active_user,
            new_password="123",
            confirm_new_password="123",
        )
        response = api_client.post(reset_password_url(), payload, format="json")

        assert response.status_code == 400
        active_user.refresh_from_db()
        assert active_user.check_password(OLD_PASSWORD)

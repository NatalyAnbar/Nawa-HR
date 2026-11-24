import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts import emails

from . import helper

pytestmark = pytest.mark.django_db

User = get_user_model()

PASSWORD = "password-123"


def accept_invite_url():
    """Return the URL for accepting an invitation and setting a password."""
    return reverse("accept-invite")


def accept_invite_data(account, **extra_fields):
    """Build a valid accept-invite payload from a generated invite link."""
    return {
        **helper.params_from_link(emails.build_invite_link(account)),
        "new_password": PASSWORD,
        "confirm_new_password": PASSWORD,
    } | extra_fields


@pytest.fixture
def superuser():
    """Create and return a superuser account."""
    return User.objects.create_superuser(
        email="superuser@gmail.com",
        password="password-123",
    )


@pytest.fixture
def invited_user():
    """A user who was invited but hasn't set a password yet."""
    return User.objects.create_user(
        email="new@nawa.com",
        first_name="Sara",
        last_name="Haddad",
    )


@pytest.fixture
def superuser_client(superuser):
    """Return an APIClient authenticated as a superuser."""
    client = APIClient()
    client.force_authenticate(user=superuser)
    return client


class TestAcceptInvite:
    """Test suite for accepting an invitation and setting an initial password."""

    def test_correct_token_and_uid_set_password(self, api_client, invited_user):
        """Ensure valid uid and token set the user's password successfully."""
        payload = accept_invite_data(invited_user)
        response = api_client.post(accept_invite_url(), payload, format="json")

        assert response.status_code == 200
        invited_user.refresh_from_db()
        assert invited_user.has_usable_password()
        assert invited_user.check_password(PASSWORD)

    def test_mismatched_passwords_fails(self, api_client, invited_user):
        """Ensure non-matching password fields are rejected."""
        payload = accept_invite_data(
            invited_user,
            confirm_new_password="Different-password-123",
        )
        response = api_client.post(accept_invite_url(), payload, format="json")

        assert response.status_code == 400
        invited_user.refresh_from_db()
        assert not invited_user.has_usable_password()

    def test_invalid_token_fails(self, api_client, invited_user):
        """Ensure an invalid or tampered token returns 400 Bad Request."""
        payload = accept_invite_data(invited_user, token="invalid-token-123")
        response = api_client.post(accept_invite_url(), payload, format="json")

        assert response.status_code == 400
        invited_user.refresh_from_db()
        assert not invited_user.has_usable_password()

    def test_invalid_uid_fails(self, api_client, invited_user):
        """Ensure a non-existent or malformed uid returns 400 Bad Request."""
        payload = accept_invite_data(invited_user, uid="invalid-uid")
        response = api_client.post(accept_invite_url(), payload, format="json")

        assert response.status_code == 400

    def test_reusing_token_after_accept_fails(self, api_client, invited_user):
        """Ensure an invite link cannot be used a second time once accepted."""
        payload = accept_invite_data(invited_user)

        first_response = api_client.post(accept_invite_url(), payload, format="json")
        assert first_response.status_code == 200

        second_response = api_client.post(accept_invite_url(), payload, format="json")
        assert second_response.status_code == 400

    # def test_full_invite_and_accept_flow(
    #     self, api_client, superuser_client, mailoutbox
    # ):
    #     """End-to-end test covering invitation creation, email delivery, and acceptance."""
    #     invite_response = superuser_client.post(
    #         invite_url(),
    #         invite_data(),
    #         format="json",
    #     )
    #     assert invite_response.status_code == 201

    #     user = User.objects.get(email=invite_response.data["email"])
    #     assert not user.has_usable_password()
    #     assert len(mailoutbox) == 1
    #     assert user.first_name in mailoutbox[0].body
    #     assert mailoutbox[0].to == [user.email]

    #     accept_response = api_client.post(
    #         accept_invite_url(),
    #         accept_invite_data(user),
    #         format="json",
    #     )
    #     assert accept_response.status_code == 200

    #     user.refresh_from_db()
    #     assert user.has_usable_password()
    #     assert user.check_password(PASSWORD)

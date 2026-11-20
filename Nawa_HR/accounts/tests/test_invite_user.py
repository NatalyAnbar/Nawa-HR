"""Tests for POST /accounts/invite/ and POST /accounts/accept-invite/."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts import emails

from . import helper

User = get_user_model()

pytestmark = pytest.mark.django_db

EMAIL = "test@nawa.com"
PASSWORD = "Test-password-123"
FIRST_NAME = "Nawa"
LAST_NAME = "HR"


def invite_url():
    """Return the URL for inviting a new user."""
    return reverse("invite")


def accept_invite_url():
    """Return the URL for accepting an invitation and setting a password."""
    return reverse("accept-invite")


def invite_data(**extra_fields):
    """Build a valid payload for inviting a user."""
    return {
        "email": EMAIL,
        "first_name": FIRST_NAME,
        "last_name": LAST_NAME,
    } | extra_fields


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
        password=PASSWORD,
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

    def test_create_user_without_password(self, superuser_client):
        """Ensure a superuser can invite a user who starts with no usable password."""
        response = superuser_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 201
        user = User.objects.get(email=response.data["email"])
        assert not user.has_usable_password()

    def test_invite_user_with_valid_photo(self, superuser_client, mailoutbox):
        """Ensure HR can optionally upload a valid profile photo when inviting a user."""
        photo = helper.make_photo()
        response = superuser_client.post(
            invite_url(),
            invite_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 201
        user = User.objects.get(email=response.data["email"])
        assert bool(user.photo) is True
        assert response.data["photo"] is not None
        assert len(mailoutbox) == 1

    def test_invite_user_with_invalid_photo_rejected(self, superuser_client, mailoutbox):
        """Ensure an oversized photo rejects the invite without creating a user."""
        oversized_photo = helper.make_photo(size_mb=6)
        response = superuser_client.post(
            invite_url(),
            invite_data(photo=oversized_photo),
            format="multipart",
        )

        assert response.status_code == 400
        assert "photo" in response.data
        assert User.objects.count() == 1
        assert len(mailoutbox) == 0

    def test_anonymous_user_cannot_invite(self, api_client):
        """Ensure unauthenticated requests are rejected with 401 Unauthorized."""
        response = api_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 401
        assert User.objects.count() == 0

    def test_regular_user_cannot_invite(self, api_client):
        """Ensure non-admin authenticated users cannot send invitations."""
        regular_user = User.objects.create_user(
            email="regular@nawa.com",
            password=PASSWORD,
        )
        api_client.force_authenticate(user=regular_user)

        response = api_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 403

    def test_send_email_after_create_user(self, superuser_client, mailoutbox):
        """Ensure an invitation email containing the user's name is sent on creation."""
        response = superuser_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 201
        user = User.objects.get(email=response.data["email"])
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
            invite_data(email=email),
            format="json",
        )

        assert response.status_code == 400
        assert User.objects.count() == 1
        assert len(mailoutbox) == 0

    def test_duplicate_email_fails(self, superuser_client, invited_user, mailoutbox):
        """Ensure inviting an email that already exists fails with 400 Bad Request."""
        mailoutbox.clear()

        response = superuser_client.post(invite_url(), invite_data(), format="json")

        assert response.status_code == 400
        assert User.objects.count() == 2
        assert len(mailoutbox) == 0


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

    def test_full_invite_and_accept_flow(
        self, api_client, superuser_client, mailoutbox
    ):
        """End-to-end test covering invitation creation, email delivery, and acceptance."""
        invite_response = superuser_client.post(
            invite_url(),
            invite_data(),
            format="json",
        )
        assert invite_response.status_code == 201

        user = User.objects.get(email=invite_response.data["email"])
        assert not user.has_usable_password()
        assert len(mailoutbox) == 1
        assert user.first_name in mailoutbox[0].body
        assert mailoutbox[0].to == [user.email]

        accept_response = api_client.post(
            accept_invite_url(),
            accept_invite_data(user),
            format="json",
        )
        assert accept_response.status_code == 200

        user.refresh_from_db()
        assert user.has_usable_password()
        assert user.check_password(PASSWORD)

"""Tests for PUT /accounts/change-password/."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

pytestmark = pytest.mark.django_db

OLD_PASSWORD = "test@1234"
NEW_PASSWORD = "1234@test"

# Each case breaks exactly one validation rule while keeping the rest valid,
# ensuring the 400 response is triggered solely by that specific rule.
INVALID_CHANGES = [
    (
        {"old_password": "wrong-password"},
        "old_password",
    ),
    (
        {"confirm_new_password": "mismatched-password"},
        "confirm_new_password",
    ),
    (
        # Both new password fields match, so only Django's password strength check fails
        {"new_password": "1234", "confirm_new_password": "1234"},
        "new_password",
    ),
]


def change_password_url():
    """Return the URL for the authenticated user's password change endpoint."""
    return reverse("change-password")


def change_password_data(**extra_fields):
    """Build a valid password change payload, overriding any specified fields."""
    return {
        "old_password": OLD_PASSWORD,
        "new_password": NEW_PASSWORD,
        "confirm_new_password": NEW_PASSWORD,
    } | extra_fields


def create_test_user():
    """Create and return an active user with OLD_PASSWORD properly hashed."""
    return User.objects.create_user(
        email="test@gmail.com",
        password=OLD_PASSWORD,
    )


@pytest.fixture
def authenticated_user(api_client):
    """Authenticate the API client with a newly created user and return the user."""
    user = create_test_user()
    api_client.force_authenticate(user=user)
    return user


class TestChangePassword:
    """Test suite for changing the authenticated user's password."""

    def test_user_can_change_password(self, api_client, authenticated_user):
        """Ensure a logged-in user can update their password with valid credentials."""
        response = api_client.put(
            change_password_url(),
            change_password_data(),
            format="json",
        )

        assert response.status_code == 200
        authenticated_user.refresh_from_db()
        assert authenticated_user.check_password(NEW_PASSWORD)

    def test_anonymous_user_cannot_change_password(self, api_client):
        """Ensure unauthenticated requests return 401 and leave the password intact."""
        user = create_test_user()

        response = api_client.put(
            change_password_url(),
            change_password_data(),
            format="json",
        )

        assert response.status_code == 401
        user.refresh_from_db()
        assert user.check_password(OLD_PASSWORD)

    def test_patch_method_not_allowed(self, api_client, authenticated_user):
        """
        Ensure PATCH is disabled (405 Method Not Allowed).

        All password fields are required together, so only full PUT updates are allowed.
        """
        response = api_client.patch(
            change_password_url(),
            change_password_data(),
            format="json",
        )

        assert response.status_code == 405
        authenticated_user.refresh_from_db()
        assert authenticated_user.check_password(OLD_PASSWORD)

    @pytest.mark.parametrize("overrides, error_field", INVALID_CHANGES)
    def test_invalid_change_is_rejected(
        self, api_client, authenticated_user, overrides, error_field
    ):
        """Ensure invalid old password, mismatched confirmation, or weak passwords fail."""
        response = api_client.put(
            change_password_url(),
            change_password_data(**overrides),
            format="json",
        )

        assert response.status_code == 400
        assert error_field in response.data
        authenticated_user.refresh_from_db()
        assert authenticated_user.check_password(OLD_PASSWORD)

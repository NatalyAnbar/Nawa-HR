import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

pytestmark = pytest.mark.django_db

EMAIL = "test@nawa.com"
PASSWORD = "Test-password-123"
WRONG_PASSWORD = "Wrong-password-123"


def login(client, email=EMAIL, password=PASSWORD):
    """Send a login request with the given credentials."""
    return client.post(
        reverse("login"),
        {"email": email, "password": password},
        format="json",
    )


def refresh(client, token):
    """Request a new access and refresh token pair using a refresh token."""
    return client.post(
        reverse("refresh-token"),
        {"refresh": token},
        format="json",
    )


def logout(client, token):
    """Blacklist the given refresh token to log the user out."""
    return client.post(
        reverse("logout"),
        {"refresh": token},
        format="json",
    )


class TestUser:
    """Test suite for User model integrity and password storage."""

    def test_password_is_stored_hashed(self, user):
        """Ensure user passwords are hashed in the database rather than plain text."""
        user.refresh_from_db()

        assert user.password != PASSWORD
        assert user.check_password(PASSWORD)


@pytest.mark.usefixtures("user")
class TestLogin:
    """Test suite for the user authentication (login) endpoint."""

    # --- Successful login ---

    def test_returns_access_and_refresh_tokens(self, api_client):
        """Ensure valid credentials return both access and refresh JWT tokens."""
        response = login(api_client)

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    @pytest.mark.parametrize(
        "email",
        ["TEST@NAWA.COM", "Test@nawa.com", "test@NAWA.COM"],
    )
    def test_email_is_case_insensitive(self, api_client, email):
        """Ensure users can log in regardless of email letter casing."""
        response = login(api_client, email=email)

        assert response.status_code == 200

    # --- Rejected login ---

    @pytest.mark.parametrize("email", ["", None])
    def test_missing_email_is_rejected(self, api_client, email):
        """Ensure blank or null email values fail validation with 400 Bad Request."""
        response = login(api_client, email=email)

        assert response.status_code == 400

    @pytest.mark.parametrize("password", ["", None])
    def test_missing_password_is_rejected(self, api_client, password):
        """Ensure blank or null passwords fail validation with 400 Bad Request."""
        response = login(api_client, password=password)

        assert response.status_code == 400

    @pytest.mark.parametrize("email", ["99999999", "sara@nawa.com"])
    def test_unknown_or_malformed_email_is_rejected(self, api_client, email):
        """Ensure non-existent or malformed emails return 401 Unauthorized."""
        response = login(api_client, email=email)

        assert response.status_code == 401

    def test_wrong_password_is_rejected(self, api_client):
        """Ensure an incorrect password returns 401 Unauthorized."""
        response = login(api_client, password=WRONG_PASSWORD)

        assert response.status_code == 401

    def test_disabled_account_is_rejected(self, user, api_client):
        """Ensure inactive accounts cannot log in even with valid credentials."""
        user.is_active = False
        user.save(update_fields=["is_active"])

        response = login(api_client)

        assert response.status_code == 401

    def test_invited_user_without_a_password_is_rejected(self, api_client):
        """Ensure invited users who have not set a password yet cannot log in."""
        User.objects.create_user(email="new@nawa.com")

        response = login(api_client, email="new@nawa.com", password="")
        assert response.status_code == 400

        response = login(api_client, email="new@nawa.com", password="anything")
        assert response.status_code == 401


@pytest.mark.usefixtures("user")
class TestTokenRefresh:
    """Test suite for JWT token refresh and rotation behavior."""

    def test_returns_new_tokens(self, api_client):
        """Ensure a valid refresh token issues a new access and refresh token pair."""
        tokens = login(api_client).data

        response = refresh(api_client, tokens["refresh"])

        assert response.status_code == 200
        assert response.data["access"] != tokens["access"]
        assert response.data["refresh"] != tokens["refresh"]

    def test_old_token_stops_working_after_rotation(self, api_client):
        """Ensure a rotated refresh token is blacklisted and cannot be reused."""
        old_refresh = login(api_client).data["refresh"]
        refresh(api_client, old_refresh)

        response = refresh(api_client, old_refresh)

        assert response.status_code == 401


@pytest.mark.usefixtures("user")
class TestLoginThrottling:
    """Test suite for brute-force rate limiting on the login endpoint."""

    def test_login_is_limited_to_five_attempts_per_minute(self, api_client):
        """Ensure the sixth consecutive failed login attempt is throttled with 429."""
        for _ in range(5):
            assert login(api_client, password=WRONG_PASSWORD).status_code == 401

        response = login(api_client, password=WRONG_PASSWORD)

        assert response.status_code == 429


@pytest.mark.usefixtures("user")
class TestLogout:
    """Test suite for logging out and blacklisting refresh tokens."""

    def test_refresh_token_stops_working_after_logout(self, api_client):
        """Ensure a refresh token cannot be used to obtain tokens after logout."""
        refresh_token = login(api_client).data["refresh"]

        logout_response = logout(api_client, refresh_token)
        assert logout_response.status_code == 200

        response = refresh(api_client, refresh_token)

        assert response.status_code == 401

    def test_logging_out_twice_with_the_same_token_is_rejected(self, api_client):
        """Ensure attempting to blacklist an already logged-out token returns 401."""
        refresh_token = login(api_client).data["refresh"]
        logout(api_client, refresh_token)

        response = logout(api_client, refresh_token)

        assert response.status_code == 401

    @pytest.mark.parametrize("token", ["", None])
    def test_missing_refresh_token_is_rejected(self, api_client, token):
        """Ensure blank or null refresh tokens fail validation with 400 Bad Request."""
        response = logout(api_client, token)

        assert response.status_code == 400

    def test_invalid_refresh_token_is_rejected(self, api_client):
        """Ensure malformed or fabricated refresh tokens return 401 Unauthorized."""
        response = logout(api_client, "not-a-real-token")

        assert response.status_code == 401

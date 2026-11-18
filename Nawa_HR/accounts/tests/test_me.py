import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from . import helper

User = get_user_model()

pytestmark = pytest.mark.django_db

OLD_FIRST_NAME = "old-first-name"
OLD_LAST_NAME = "old-last-name"
OLD_EMAIL = "test@nawa.com"

NEW_FIRST_NAME = "Nawa"
NEW_LAST_NAME = "HR"


@pytest.fixture
def auth_client(api_client, user):
    """Return an APIClient authenticated as the default test user."""
    api_client.force_authenticate(user=user)
    return api_client


def me_url():
    """Return the URL for the authenticated user's profile endpoint."""
    return reverse("me")


def profile_data(**extra_fields):
    """Build a valid payload for updating the user's profile."""
    return {
        "first_name": NEW_FIRST_NAME,
        "last_name": NEW_LAST_NAME,
    } | extra_fields


class TestMe:
    """Test suite for retrieving and updating the authenticated user's profile."""

    def test_unauthenticated_user_rejected(self, api_client):
        """Ensure unauthenticated requests to /me/ return 401 Unauthorized."""
        response = api_client.get(me_url())

        assert response.status_code == 401

    def test_retrieve_profile_info(self, auth_client, user):
        """Ensure an authenticated user can retrieve their own profile details."""
        response = auth_client.get(me_url())

        assert response.status_code == 200
        assert response.data["email"] == user.email
        assert response.data["first_name"] == user.first_name
        assert response.data["last_name"] == user.last_name

    def test_patch_updates_allowed_fields(self, auth_client, user):
        """Ensure PATCH updates mutable fields such as first_name and last_name."""
        response = auth_client.patch(me_url(), profile_data(), format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == NEW_FIRST_NAME
        assert user.last_name == NEW_LAST_NAME

    def test_patch_ignores_read_only_email(self, auth_client, user):
        """Ensure attempting to change the read-only email field via PATCH leaves it unchanged."""
        response = auth_client.patch(
            me_url(),
            profile_data(email="new@gmail.com"),
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.email == OLD_EMAIL

    def test_put_method_not_allowed(self, auth_client):
        """Ensure PUT is disallowed (405 Method Not Allowed)."""
        response = auth_client.put(me_url(), profile_data(), format="json")

        assert response.status_code == 405


class TestPhoto:
    """Test suite for profile photo upload, validation, and removal."""

    @pytest.mark.parametrize("size_mb", [2, 3, 4])
    def test_valid_photo_size_accepted(self, auth_client, user, size_mb):
        """Ensure photos within the 5 MB limit are accepted and saved."""
        photo = helper.make_photo(size_mb=size_mb)
        response = auth_client.patch(
            me_url(),
            profile_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 200
        assert response.data["photo"] is not None
        user.refresh_from_db()
        assert bool(user.photo)

    def test_oversized_photo_rejected(self, auth_client):
        """Ensure photos exceeding the 5 MB limit fail validation with 400 Bad Request."""
        photo = helper.make_photo(size_mb=6)
        response = auth_client.patch(
            me_url(),
            profile_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 400

    @pytest.mark.parametrize("extension", ["jpg", "jpeg", "png", "webp"])
    def test_allowed_photo_extensions_accepted(self, auth_client, extension):
        """Ensure supported image extensions (jpg, jpeg, png, webp) are accepted."""
        photo = helper.make_photo(extension=extension)
        response = auth_client.patch(
            me_url(),
            profile_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 200

    @pytest.mark.parametrize("extension", ["gif", "bmp", "tiff"])
    def test_disallowed_photo_extensions_rejected(self, auth_client, extension):
        """Ensure unsupported image extensions are rejected with 400 Bad Request."""
        photo = helper.make_photo(extension=extension)
        response = auth_client.patch(
            me_url(),
            profile_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 400

    @pytest.mark.parametrize(
        "dimensions",
        [
            {"width": 100, "height": 100},
            {"width": 100, "height": 150},
            {"width": 100, "height": 200},
        ],
    )
    def test_valid_aspect_ratio_accepted(self, auth_client, dimensions):
        """Ensure photos within the 2:1 aspect ratio limit are accepted."""
        photo = helper.make_photo(**dimensions)
        response = auth_client.patch(
            me_url(),
            profile_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "dimensions",
        [
            {"width": 100, "height": 300},
            {"width": 200, "height": 500},
        ],
    )
    def test_excessive_aspect_ratio_rejected(self, auth_client, dimensions):
        """Ensure photos exceeding the 2:1 aspect ratio limit fail with 400 Bad Request."""
        photo = helper.make_photo(**dimensions)
        response = auth_client.patch(
            me_url(),
            profile_data(photo=photo),
            format="multipart",
        )

        assert response.status_code == 400

    def test_remove_photo(self, auth_client, user):
        """Ensure setting photo to null removes the existing profile photo."""
        user.photo = helper.make_photo()
        user.save(update_fields=["photo"])

        response = auth_client.patch(me_url(), {"photo": None}, format="json")

        assert response.status_code == 200
        user.refresh_from_db()
        assert not user.photo

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

EMAIL = 'test@nawa.com'
PASSWORD = 'Test-password-123'
FIRST_NAME = 'old-first-name'
LAST_NAME = 'old-last-name'

@pytest.fixture
def user():
    """An active user with a known email and password."""
    return User.objects.create_user(email=EMAIL, password=PASSWORD, first_name=FIRST_NAME, last_name=LAST_NAME)


@pytest.fixture(autouse=True)
def temp_media_root(settings, tmp_path):
    """Save uploaded files to a temporary folder so tests don't fill the real media folder."""
    settings.MEDIA_ROOT = tmp_path
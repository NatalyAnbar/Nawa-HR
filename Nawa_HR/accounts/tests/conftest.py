import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

EMAIL = 'test@nawa.com'
PASSWORD = 'Test-password-123'

@pytest.fixture
def user():
    """An active user with a known email and password."""
    return User.objects.create_user(email=EMAIL, password=PASSWORD)
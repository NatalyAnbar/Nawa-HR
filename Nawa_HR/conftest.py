import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture()
def api_client():
    return APIClient()


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


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Rate limits count in the cache; reset them so each test starts fresh."""
    cache.clear()


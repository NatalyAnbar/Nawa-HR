import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Rate limits count in the cache; reset them so each test starts fresh."""
    cache.clear()
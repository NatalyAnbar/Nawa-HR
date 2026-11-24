import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

from employees import models

User = get_user_model()

pytestmark = pytest.mark.django_db


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


@pytest.fixture
def user():
    return User.objects.create_user(email="test@gmail.com", password="password-123")


@pytest.fixture
def employee(user):
    return baker.make(models.Employee, hire_date="2026-1-1", user=user)

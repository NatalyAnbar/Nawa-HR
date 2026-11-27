import pytest
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from organization.models import Department, Role

User = get_user_model()

pytestmark = pytest.mark.django_db


def list_url():
    return reverse("department-list")


def detail_url(department):
    return reverse("department-detail", kwargs={"public_id": department.public_id})


@pytest.fixture
def user():
    """A regular user with no HR rights."""
    return User.objects.create_user(email="test@nawa.com", password="Test-password-123")


@pytest.fixture
def department():
    return baker.make(Department, name="Engineering")


class TestCreateDepartment:
    def test_non_hr_user_cannot_create_department(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(list_url(), {"name": "Finance"}, format="json")

        assert response.status_code == 403
        assert not Department.objects.exists()

    def test_hr_creates_department(self, superuser_client):
        response = superuser_client.post(list_url(), {"name": "Finance"}, format="json")

        assert response.status_code == 201
        assert Department.objects.get().name == "Finance"

    def test_response_uses_public_id(self, superuser_client):
        response = superuser_client.post(list_url(), {"name": "Finance"}, format="json")

        assert response.data["id"] == str(Department.objects.get().public_id)

    def test_duplicate_name_is_rejected(self, superuser_client, department):
        response = superuser_client.post(list_url(), {"name": department.name}, format="json")

        assert response.status_code == 400
        assert "name" in response.data
        assert Department.objects.count() == 1

    def test_missing_name_is_rejected(self, superuser_client):
        response = superuser_client.post(list_url(), {}, format="json")

        assert response.status_code == 400
        assert "name" in response.data


class TestReadDepartments:
    def test_hr_lists_departments(self, superuser_client):
        baker.make(Department, name="Finance")
        baker.make(Department, name="Engineering")

        response = superuser_client.get(list_url())

        assert response.status_code == 200
        names = [item["name"] for item in response.data]
        # Departments are ordered by name
        assert names == ["Engineering", "Finance"]

    def test_hr_views_one_department(self, superuser_client, department):
        response = superuser_client.get(detail_url(department))

        assert response.status_code == 200
        assert response.data["name"] == "Engineering"


class TestUpdateDepartment:
    def test_hr_renames_department(self, superuser_client, department):
        response = superuser_client.patch(detail_url(department), {"name": "R&D"}, format="json")

        assert response.status_code == 200
        department.refresh_from_db()
        assert department.name == "R&D"

    def test_saving_with_its_own_name_is_allowed(self, superuser_client, department):
        response = superuser_client.patch(detail_url(department), {"name": department.name}, format="json")

        assert response.status_code == 200

    def test_renaming_to_an_existing_name_is_rejected(self, superuser_client, department):
        finance = baker.make(Department, name="Finance")

        response = superuser_client.patch(detail_url(finance), {"name": department.name}, format="json")

        assert response.status_code == 400


class TestDeleteDepartment:
    def test_departments_cannot_be_deleted_through_the_api(self, superuser_client, department):
        response = superuser_client.delete(detail_url(department))

        assert response.status_code == 405
        assert Department.objects.filter(pk=department.pk).exists()

    def test_department_with_roles_cannot_be_deleted(self, department):
        # Even outside the API, the database refuses
        baker.make(Role, department=department)

        with pytest.raises(ProtectedError):
            department.delete()
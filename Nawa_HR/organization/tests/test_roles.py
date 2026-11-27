import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker

from organization.models import Department, Role

User = get_user_model()

pytestmark = pytest.mark.django_db


def list_url():
    return reverse("role-list")


def detail_url(role):
    return reverse("role-detail", kwargs={"public_id": role.public_id})


def role_data(department, name="Manager"):
    return {"name": name, "department": str(department.public_id)}


@pytest.fixture
def user():
    """A regular user with no HR rights."""
    return User.objects.create_user(email="test@nawa.com", password="Test-password-123")


@pytest.fixture
def department():
    return baker.make(Department, name="Engineering")


@pytest.fixture
def role(department):
    return baker.make(Role, name="Manager", department=department)


class TestCreateRole:
    def test_non_hr_user_cannot_create_role(self, api_client, user, department):
        api_client.force_authenticate(user=user)

        response = api_client.post(list_url(), role_data(department), format="json")

        assert response.status_code == 403
        assert not Role.objects.exists()

    def test_hr_creates_role(self, superuser_client, department):
        response = superuser_client.post(list_url(), role_data(department), format="json")

        assert response.status_code == 201
        role = Role.objects.get()
        assert role.name == "Manager"
        assert role.department == department

    def test_new_role_has_employee_access_by_default(self, superuser_client, department):
        superuser_client.post(list_url(), role_data(department), format="json")

        assert Role.objects.get().access == Role.Access.EMPLOYEE

    def test_response_uses_public_ids_only(self, superuser_client, department):
        response = superuser_client.post(list_url(), role_data(department), format="json")

        role = Role.objects.get()
        assert str(response.data["id"]) == str(role.public_id)
        assert str(response.data["department"]) == str(department.public_id)
        assert response.data["department_name"] == "Engineering"

    def test_duplicate_name_in_same_department_is_rejected(self, superuser_client, role):
        response = superuser_client.post(list_url(), role_data(role.department), format="json")

        assert response.status_code == 400
        assert Role.objects.count() == 1

    def test_same_name_in_another_department_is_allowed(self, superuser_client, role):
        finance = baker.make(Department, name="Finance")

        response = superuser_client.post(list_url(), role_data(finance), format="json")

        assert response.status_code == 201
        assert Role.objects.count() == 2

    def test_unknown_department_is_rejected(self, superuser_client):
        payload = {"name": "Manager", "department": "00000000-0000-0000-0000-000000000000"}

        response = superuser_client.post(list_url(), payload, format="json")

        assert response.status_code == 400
        assert "department" in response.data

    def test_invalid_access_is_rejected(self, superuser_client, department):
        payload = {**role_data(department), "access": "boss"}

        response = superuser_client.post(list_url(), payload, format="json")

        assert response.status_code == 400
        assert "access" in response.data


class TestUpdateRole:
    def test_hr_renames_role(self, superuser_client, role):
        response = superuser_client.patch(detail_url(role), {"name": "Team Lead"}, format="json")

        assert response.status_code == 200
        role.refresh_from_db()
        assert role.name == "Team Lead"

    def test_saving_with_its_own_name_is_allowed(self, superuser_client, role):
        # The duplicate check must not compare the role with itself
        response = superuser_client.patch(detail_url(role), {"name": role.name}, format="json")

        assert response.status_code == 200

    def test_renaming_to_an_existing_name_is_rejected(self, superuser_client, role):
        other = baker.make(Role, name="Team Lead", department=role.department)

        response = superuser_client.patch(detail_url(other), {"name": role.name}, format="json")

        assert response.status_code == 400


class TestDeleteRole:
    def test_roles_cannot_be_deleted(self, superuser_client, role):
        response = superuser_client.delete(detail_url(role))

        assert response.status_code == 405
        assert Role.objects.filter(pk=role.pk).exists()
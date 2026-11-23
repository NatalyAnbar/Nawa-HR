from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Admin pages for employee records."""

    list_display = ["__str__", "hire_date", "status", "employment_type"]
    list_filter = ["status", "employment_type"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    # Fetch each employee's user in the same query (avoids N+1)
    list_select_related = ["user"]

    fields = ["public_id", "user", "status", "employment_type", "hire_date"]
    readonly_fields = ["public_id"]
    # Search for the user instead of loading every account into a dropdown
    autocomplete_fields = ["user"]
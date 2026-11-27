from django.contrib import admin

from .models import Department, Role


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    fields = ["name"]


@admin.register(Role)
class DepartmentAdmin(admin.ModelAdmin):
    fields = ["name", "department"]

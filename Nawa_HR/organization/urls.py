from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()

router.register("departments", views.DepartmentViewSet, basename="department")
router.register("roles", views.RoleViewSet, basename="role")

urlpatterns = router.urls

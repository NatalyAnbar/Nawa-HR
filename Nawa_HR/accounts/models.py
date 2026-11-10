from django.db import models
from django.contrib.auth.models import AbstractUser
from .manager import UserManager

class User(AbstractUser):
    """
    An account that can sign in, identified by email instead of a username.

    HR details live on `employees.Employee`, so an account doesn't have to be
    an employee (the developer, or an external auditor).
    """

    username = None

    # Each account needs its own email: it's the login and where invites are sent
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'

    # Asked by createsuperuser besides the login field and password; nothing else is required
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


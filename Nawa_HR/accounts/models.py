from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.functions import Lower
from .manager import UserManager
from . import photo_validators

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

    # Optional profile photo; validated for file size, extension, and aspect ratio
    photo = models.ImageField(upload_to="photos/", null=True, blank=True, 
                              validators=photo_validators.PHOTO_VALIDATORS)

    def __str__(self):
        return self.email

    class Meta:
        constraints = [
            models.CheckConstraint(
                # Every write path must store emails in lowercase
                condition=models.Q(email=Lower('email')),
                name='user_email_lowercase'
                )
        ]


from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Creates users with an email as the login, since the model has no username."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email is required.")

        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        # With no password this stores an unusable one, so an invited user can't log in yet
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        # Regular accounts can't open the Django admin
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_staff", False)

        if extra_fields["is_superuser"]:
            raise ValueError("Use create_superuser to create a superuser.")

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):

        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)

        if not extra_fields["is_superuser"] or not extra_fields["is_staff"]:
            raise ValueError(
                "A superuser must have is_staff=True and is_superuser=True."
            )

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Emails are stored in lowercase, so match the login input the same way
        return self.get(email=email.lower())

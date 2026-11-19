from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from django.core.exceptions import ValidationError

from .models import User


INVALID_INVITE_LINK = 'This invite link is invalid or has expired.'


class InviteUserSerializer(serializers.ModelSerializer):
    """
    Input for HR to invite a new employee.

    HR enters the employee's email, name, and an optional profile photo.
    """

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'photo']
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False},
        }

    def validate_email(self, value):
        """Store emails in lowercase and reject ones already in use, in any letter case."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return email


class AcceptInviteSerializer(serializers.Serializer):
    """
    Let an invited employee set their password from the invite link.

    The link carries two values:

    - ``uid``: the user's id, base64-encoded.
    - ``token``: made by Django's ``default_token_generator``.

    The token depends on the user's current password hash, so it stops
    working as soon as the new password is saved. Each invite link can be
    used only once, and it expires after ``PASSWORD_RESET_TIMEOUT``.

    Validation only: on success, ``validated_data['user']`` holds the
    invited user, and the view sets the password.
    """

    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        """Check the invite link first, then the new password."""
        user = self._get_invited_user(attrs['uid'], attrs['token'])

        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})

        try:
            validate_password(attrs['password'], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})

        attrs['user'] = user
        return attrs

    @staticmethod
    def _get_invited_user(uid, token):
        """
        Return the user the link belongs to.

        Every problem (bad uid, unknown or disabled user, wrong or expired
        token) raises the same error, so the response doesn't reveal which
        part of the link was wrong.
        """
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, DjangoValidationError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            raise serializers.ValidationError(INVALID_INVITE_LINK)

        return user


class MeSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating the authenticated user's profile.

    Email and join date are read-only. Photo validation rules are inherited
    automatically from the User model's ``photo`` field.
    """

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "photo", "date_joined"]
        read_only_fields = ["date_joined", "email"]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Allow an authenticated user to change their current password.

    Requires the current password for verification, along with the new password
    and its confirmation. Validation runs in three stages:
    1. Verify ``old_password`` against the user's stored password hash.
    2. Validate ``new_password`` strength against Django's password validators.
    3. Ensure ``new_password`` and ``confirm_new_password`` match.
    """

    old_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    confirm_new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_old_password(self, value):
        """Make sure the user changing the password knows the current one."""
        if not self.instance.check_password(value):
            raise serializers.ValidationError("The old password is incorrect.")
        return value

    def validate_new_password(self, value):
        """Run Django's configured password strength validators against the user."""
        try:
            validate_password(value, self.instance)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate(self, attrs):
        """Compare the two new password fields to ensure they match."""
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "The passwords do not match."}
            )
        return attrs

    def update(self, instance, validated_data):
        """Hash and store the new password in the database."""
        instance.set_password(validated_data["new_password"])
        instance.save(update_fields=["password"])
        return instance

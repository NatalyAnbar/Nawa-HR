from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_link(user, path):
    """
    Build a one-time frontend link carrying the user's encoded ID and token.

    The token becomes invalid once the user's password changes or after
    ``PASSWORD_RESET_TIMEOUT`` expires.
    """
    params = urlencode(
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
    )
    return f"{settings.FRONTEND_URL}/{path}?{params}"


def build_invite_link(user):
    """Return the frontend URL where an invited employee sets their password."""
    return build_link(user, "accept-invite")


def build_reset_link(user):
    """Return the frontend URL where a user resets their forgotten password."""
    return build_link(user, "reset-password")


def send_invite_mail(user):
    """Email a newly invited employee their account activation link."""
    valid_days = settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24)

    send_mail(
        subject="Welcome to Nawa HR: set your password",
        message=(
            f"Hi {user.first_name},\n\n"
            "An account has been created for you on Nawa HR.\n"
            "Open this link to set your password:\n\n"
            f"{build_invite_link(user)}\n\n"
            f"The link works once and expires in {valid_days} days.\n"
            "If you weren't expecting this email, you can ignore it."
        ),
        # None uses DEFAULT_FROM_EMAIL from settings
        from_email=None,
        recipient_list=[user.email],
    )


def send_reset_password_mail(user):
    """Email a user a one-time link to reset their password."""
    valid_days = settings.PASSWORD_RESET_TIMEOUT // (60 * 60 * 24)

    send_mail(
        subject="Nawa HR: reset your password",
        message=(
            f"Hi {user.first_name},\n\n"
            "We received a request to reset your Nawa HR password.\n"
            "Open this link to choose a new password:\n\n"
            f"{build_reset_link(user)}\n\n"
            f"The link works once and expires in {valid_days} days.\n"
            "If you didn't request a password reset, you can ignore this email."
        ),
        # None uses DEFAULT_FROM_EMAIL from settings
        from_email=None,
        recipient_list=[user.email],
    )

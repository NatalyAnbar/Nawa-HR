from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_invite_link(user):
    """
    Return the frontend link where an invited employee sets their password.

    The link carries the user's id (base64-encoded) and a one-time token.
    The token stops working once the password is set, or after
    ``PASSWORD_RESET_TIMEOUT``.
    """
    params = urlencode({
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    return f'{settings.FRONTEND_URL}/accept-invite?{params}'


def send_invite_mail(user):
    """Email a new employee their invite link."""
    valid_days = settings.PASSWORD_RESET_TIMEOUT   // (60 * 60 * 24)

    send_mail(
        subject='Welcome to Nawa HR: set your password',
        message=(
            f'Hi {user.first_name},\n\n'
            'An account has been created for you on Nawa HR.\n'
            'Open this link to set your password:\n\n'
            f'{build_invite_link(user)}\n\n'
            f'The link works once and expires in {valid_days} days.\n'
            'If you weren\'t expecting this email, you can ignore it.'
        ),
        # None uses DEFAULT_FROM_EMAIL from settings
        from_email=None,
        recipient_list=[user.email],
    )
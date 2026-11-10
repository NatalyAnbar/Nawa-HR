from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import ScopedRateThrottle


class LoginView(TokenObtainPairView):
    """
    Log in with email and password and get an access and refresh token.

    Simple JWT checks the password and that the account is active, and gives the
    same answer for every failure, so nobody can learn which emails have an account.
    """

    # Low on purpose, to slow down password guessing
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

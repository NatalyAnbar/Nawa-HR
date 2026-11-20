from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from . import emails
from .models import User
from .serializers import (
    AcceptInviteSerializer,
    ChangePasswordSerializer,
    ForgetPasswordSerializer,
    InviteUserSerializer,
    MeSerializer,
    ResetPasswordSerializer,
)


class LoginView(TokenObtainPairView):
    """
    Log in with email and password and get an access and refresh token.

    Rate-limited to five attempts per minute per IP address.
    """

    # Low on purpose, to slow down password guessing
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class InviteUserView(generics.GenericAPIView):
    """
    HR creates an account for a new employee and emails them an invite link.

    There is no public sign-up: every account starts here.
    """

    serializer_class = InviteUserSerializer
    # Replaced by IsHR once roles exist
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # No password given, so the account gets an unusable one
        user = User.objects.create_user(**serializer.validated_data)
        emails.send_invite_mail(user)

        return Response(
            self.get_serializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ForgetPasswordView(generics.GenericAPIView):
    """Send a one-time password reset link to an active user's email address."""

    serializer_class = ForgetPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(email=serializer.validated_data["email"])
        emails.send_reset_password_mail(user)

        return Response(
            {"detail": "Password reset link has been sent to your email."},
            status=status.HTTP_200_OK,
        )


class BasePasswordTokenView(generics.GenericAPIView):
    """Set a user's password from a one-time uid + token link."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Saving a new password also invalidates the one-time token
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Your password has been set. You can now log in."},
            status=status.HTTP_200_OK,
        )


class AcceptInviteView(BasePasswordTokenView):
    """Set an initial password from an invite link so the employee can log in."""

    serializer_class = AcceptInviteSerializer


class ResetPasswordView(BasePasswordTokenView):
    """Set a new password from a password reset link."""

    serializer_class = ResetPasswordSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or partially update the authenticated user's profile.

    Only GET and PATCH are allowed; PUT is disabled so clients aren't forced
    to resend read-only fields (like email) or re-upload their profile photo
    on every edit.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MeSerializer
    # Disable PUT: email is read-only and photo shouldn't be re-uploaded on every edit
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        """Return the currently authenticated user instead of looking up by pk."""
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """
    Allow an authenticated user to change their current password.

    Only PUT is allowed; PATCH is disabled so all password fields remain
    required together as a single atomic replacement.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Disable PATCH: changing a password requires all fields together
    http_method_names = ["put", "head", "options"]

    def get_object(self):
        """Return the currently authenticated user whose password is being changed."""
        return self.request.user

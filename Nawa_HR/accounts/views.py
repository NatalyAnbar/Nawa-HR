from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from . import emails
from .serializers import AcceptInviteSerializer, InviteUserSerializer, MeSerializer, ChangePasswordSerializer
from .models import User


class LoginView(TokenObtainPairView):
    """
    Log in with email and password and get an access and refresh token.

    Simple JWT checks the password and that the account is active, and gives the
    same answer for every failure, so nobody can learn which emails have an account.
    """

    # Low on purpose, to slow down password guessing
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class InviteUserView(generics.GenericAPIView):
    """
    HR creates an account for a new employee and emails them an invite link.

    There is no public sign-up: every account starts here.
    """

    serializer_class = InviteUserSerializer
    # Replaced by IsHR once roles exist
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        # Rejects emails that are already in use
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
    
        # No password given, so the account gets an unusable one
        user = User.objects.create_user(**serializer.validated_data)
        emails.send_invite_mail(user)

        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)


class AcceptInviteView(generics.GenericAPIView):
    """Set a password from the invite link, so the employee can log in."""

    serializer_class = AcceptInviteSerializer
    permission_classes = [permissions.AllowAny]


    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Saving a new password also uses up the invite link
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])

        return Response(
            {'detail': 'Your password has been set. You can now log in.'},
            status=status.HTTP_200_OK,
        )


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

    Only PUT is allowed; PATCH is disabled because partial updates would
    make the password fields optional, whereas changing a password requires
    sending all three fields together (old_password, new_password, and
    confirm_new_password) as a single atomic replacement.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Disable PATCH: changing a password is an all-or-nothing operation requiring all fields
    http_method_names = ["put", "head", "options"]

    def get_object(self):
        """Return the currently authenticated user whose password is being changed."""
        return self.request.user

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from . import emails
from .serializers import AcceptInviteSerializer, InviteUserSerializer
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
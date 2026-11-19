from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,     
    TokenRefreshView,      
)
from . import views


urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    # Returns a new access token and a new refresh token; the old refresh token is blacklisted
    path('refresh/', TokenRefreshView.as_view(), name='refresh-token'),
    # Blacklists the refresh token, so it can't be used again
    path('logout/', TokenBlacklistView.as_view(), name='logout'),

    path('invite/', views.InviteUserView.as_view(), name='invite'),

    path('accept_invite/', views.AcceptInviteView.as_view(), name='accept-invite'),

    path('me/', views.MeView.as_view(), name='me'),

    path('change_password/', views.ChangePasswordView.as_view(), name='change-password')
]
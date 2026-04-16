from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .views import (
    RegisterView,
    LoginView,
    MeView,
    TeamView,
    InviteMemberView,
    AcceptInvitationView,
)

urlpatterns = [
    path("register/",           RegisterView.as_view(),          name="auth-register"),
    path("login/",              LoginView.as_view(),             name="auth-login"),
    path("token/refresh/",      TokenRefreshView.as_view(),      name="auth-token-refresh"),
    path("logout/",             TokenBlacklistView.as_view(),    name="auth-logout"),
    path("me/",                 MeView.as_view(),                name="auth-me"),
    path("team/",               TeamView.as_view(),              name="auth-team"),
    path("team/invite/",        InviteMemberView.as_view(),      name="auth-invite"),
    path("team/accept-invite/", AcceptInvitationView.as_view(),  name="auth-accept-invite"),
]

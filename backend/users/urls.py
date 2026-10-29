from django.urls import path

from .views import current_user, csrf_token, session_login, session_logout


urlpatterns = [
    path("csrf/", csrf_token, name="auth-csrf"),
    path("login/", session_login, name="auth-login"),
    path("logout/", session_logout, name="auth-logout"),
    path("me/", current_user, name="auth-current-user"),
]

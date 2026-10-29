import json

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
@csrf_protect
def session_login(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    username = payload.get("username", "")
    password = payload.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
        return JsonResponse({"detail": "Username and password are required."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return JsonResponse({"detail": "Invalid username or password."}, status=400)

    auth_login(request, user)
    return JsonResponse({"id": user.pk, "username": user.get_username()})


@require_GET
def current_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
    return JsonResponse({"id": request.user.pk, "username": request.user.get_username()})


@require_POST
@csrf_protect
def session_logout(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
    auth_logout(request)
    return JsonResponse({"detail": "Signed out."})

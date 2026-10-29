"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/auth/", include("users.urls")),
    path('admin/', admin.site.urls),
    path("api/", include("documents.urls")),
    path('api/search/', include("documents.urls")),  # legacy alias kept
]

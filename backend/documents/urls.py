from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet  

# Add parentheses here to instantiate the router
router = DefaultRouter()

router.register(
    "documents",
    DocumentViewSet,
    basename="document"
)

urlpatterns = [
    path("", include(router.urls)),
]

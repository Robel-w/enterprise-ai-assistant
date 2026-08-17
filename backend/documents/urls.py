from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet  
from documents.views import AskDocumentView

# Add parentheses here to instantiate the router
router = DefaultRouter()

router.register(
    "documents",
    DocumentViewSet,
    basename="document"
)

urlpatterns = [
    path("", include(router.urls)),
     path("ask/", AskDocumentView.as_view(), name="ask-document"),
]

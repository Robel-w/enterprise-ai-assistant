from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet,
    SearchView,
    AskDocumentView,
    AskMultiDocumentView,
    AgentAskView,
)

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
    # Legacy
    path("ask/", AskDocumentView.as_view(), name="ask-document"),
    # New endpoints
    path("ask-multi/", AskMultiDocumentView.as_view(), name="ask-multi-document"),
    path("agent/ask/", AgentAskView.as_view(), name="agent-ask"),
]

"""
URL configuration for event_platform project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # DRF browsable API login/logout (convenient for development)
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # Event app endpoints
    path("api/", include("events.urls")),
    # ── OpenAPI Schema & Interactive Docs ─────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

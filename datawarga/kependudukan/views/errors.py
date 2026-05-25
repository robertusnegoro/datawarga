"""
Custom HTTP error views for DataWarga.

These views replace Django's default plain-text error responses with
branded, user-friendly HTML pages that match the application's design.

Handler registration is in ``datawarga/urls.py``:
    handler403 = error_views.permission_denied_view
    handler404 = error_views.not_found_view

Django only activates these handlers in production (DEBUG=False).
In development (DEBUG=True / WG_ENV=dev) Django shows its own debug pages.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def permission_denied_view(
    request: HttpRequest,
    exception: Exception | None = None,
) -> HttpResponse:
    """
    Renders a branded 403 Forbidden page.

    Called by Django when a PermissionDenied exception is raised or when
    a view explicitly returns HttpResponseForbidden.  Also used by the
    ``kas_access_required`` decorator so that rejected users see a
    consistent, styled error page instead of a plain-text response.

    The optional ``reason`` attribute on the exception is forwarded to
    the template so that feature-specific explanations can be displayed.
    """
    logger.warning(
        "permission_denied",
        extra={
            "path": request.path,
            "user": getattr(request.user, "username", "anonymous"),
            "reason": str(exception) if exception else "",
        },
    )

    reason: str | None = str(exception) if exception else None

    return render(
        request,
        "403.html",
        {"reason": reason},
        status=403,
    )


def not_found_view(
    request: HttpRequest,
    exception: Exception | None = None,
) -> HttpResponse:
    """
    Renders a branded 404 Not Found page.

    Called by Django when no URL pattern matches the incoming request or
    when a view raises Http404 / calls get_object_or_404 on a missing object.
    """
    logger.warning(
        "not_found",
        extra={
            "path": request.path,
            "user": getattr(request.user, "username", "anonymous"),
        },
    )

    return render(
        request,
        "404.html",
        {},
        status=404,
    )

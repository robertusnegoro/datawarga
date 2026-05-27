from functools import wraps
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


def is_admin_or_petugas(user) -> bool:
    """
    Check if the user is a backoffice admin or designated petugas.
    Fail-closed: Returns False if user is not authenticated or is associated with a citizen profile.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Check if the user is linked to a Warga record. Warga users cannot access administrative areas.
    try:
        if user.warga is not None:
            return False
    except AttributeError:
        pass

    if user.is_staff:
        return True

    # Check UserPermission model. Users with a designated permission group are allowed.
    from kependudukan.models import UserPermission

    return UserPermission.objects.filter(user=user).exists()


def admin_or_petugas_required(view_func):
    """
    Decorator that checks if the logged-in user is an admin or petugas.
    Fails closed by raising a PermissionDenied (403 Forbidden) exception.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if is_admin_or_petugas(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Anda tidak memiliki hak akses untuk halaman ini.")

    return _wrapped_view


class IsAdminOrPetugas(BasePermission):
    """
    Allows access only to backoffice admin or designated petugas users.
    """

    def has_permission(self, request, view) -> bool:
        return is_admin_or_petugas(request.user)

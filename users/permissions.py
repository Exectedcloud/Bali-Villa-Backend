from rest_framework.permissions import BasePermission


class HasHostRole(BasePermission):
    """Check if user has 'host' role."""
    message = 'This account is not registered as a host. Sign up as a host first.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        return 'host' in (request.user.roles or [])


class HasAdminRole(BasePermission):
    """Check if user has 'admin' role, is staff, or is superuser."""
    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        return 'admin' in (request.user.roles or [])


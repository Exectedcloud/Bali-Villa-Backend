from rest_framework.permissions import BasePermission


class HasHostRole(BasePermission):
    """Check if user has 'host' role."""
    message = 'This account is not registered as a host. Sign up as a host first.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return 'host' in (request.user.roles or [])

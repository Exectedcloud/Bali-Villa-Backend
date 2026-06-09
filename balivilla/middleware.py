from django.middleware.csrf import CsrfViewMiddleware


class CustomCsrfMiddleware(CsrfViewMiddleware):
    """
    Custom CSRF middleware that exempts /api/ paths from CSRF protection.
    REST APIs use token-based authentication, not CSRF tokens.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip CSRF entirely for /api/ endpoints
        if request.path.startswith('/api/'):
            return None
        # For non-API views, apply normal CSRF protection
        return super().process_view(request, view_func, view_args, view_kwargs)

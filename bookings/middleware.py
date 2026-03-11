# backend/bookings/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser

class PublicBypassMiddleware(MiddlewareMixin):
    """
    Completely bypass authentication for public booking endpoints
    """
    def process_request(self, request):
        if request.path.startswith('/api/bookings/public/'):
            # Set a flag to skip all authentication
            request._dont_enforce_csrf_checks = True
            # Ensure user is anonymous
            request.user = AnonymousUser()
            # Remove authorization header if present
            if 'HTTP_AUTHORIZATION' in request.META:
                del request.META['HTTP_AUTHORIZATION']
        return None
import logging
from django.http import HttpRequest


class TrailingSlashMiddleware:
    """
    Middleware to handle trailing slash normalization for NinjaAPI endpoints.

    This middleware intercepts 404/405 responses for API requests without trailing slashes
    and retries the request with a trailing slash, since NinjaAPI treats /endpoint and /endpoint/
    as completely different routes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Handle 404s and 405s for NinjaAPI endpoints (both GET and POST)
        if (response.status_code in [404, 405] and
            request.method in ['GET', 'POST', 'OPTIONS'] and
            not request.path.endswith('/') and
            self._is_api_request(request)):

            # Create a new request with trailing slash
            new_request = self._create_request_with_trailing_slash(request)

            # Try the request again with trailing slash
            try:
                new_response = self.get_response(new_request)
                # Only return the new response if it's successful (not 404/405)
                if new_response.status_code not in [404, 405]:
                    return new_response
            except Exception as e:
                # Log the error but continue with original response
                logger = logging.getLogger(__name__)
                logger.warning(f"Trailing slash retry failed: {e}")

        return response

    def _is_api_request(self, request):
        """Check if this is an API request that should have trailing slash handling"""
        return (request.path.startswith('/api/') or
                request.path.startswith('/agent/') or
                'application/json' in request.META.get('CONTENT_TYPE', ''))

    def _create_request_with_trailing_slash(self, request):
        """Create a new request object with trailing slash"""
        from django.http import HttpRequest

        # Create new request
        new_request = HttpRequest()
        new_request.method = request.method
        new_request.path = request.path + '/'
        new_request.path_info = request.path_info + '/'

        # Copy META data
        new_request.META = request.META.copy()
        new_request.META['PATH_INFO'] = request.path_info + '/'

        # Handle query parameters
        if hasattr(request, 'GET') and request.GET:
            new_request.GET = request.GET.copy()

        # Handle POST data and body
        if request.method == 'POST':
            # Copy POST data
            if hasattr(request, 'POST') and request.POST:
                new_request.POST = request.POST.copy()

            # Copy FILES
            if hasattr(request, 'FILES') and request.FILES:
                new_request.FILES = request.FILES.copy()

            # Copy raw body for JSON requests
            if hasattr(request, '_body'):
                new_request._body = request._body
            elif hasattr(request, 'body'):
                new_request._body = request.body

        # Handle OPTIONS requests
        if request.method == 'OPTIONS':
            new_request.META['REQUEST_METHOD'] = 'OPTIONS'

        return new_request

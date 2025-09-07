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

        # Debug logging
        logger = logging.getLogger(__name__)
        logger.info(f"MIDDLEWARE: {request.method} {request.path} -> {response.status_code}")

        # Handle 404s and 405s for NinjaAPI endpoints
        # Client is sending requests WITH trailing slash, so we need to retry WITHOUT slash
        if (response.status_code in [404, 405] and
            request.method in ['GET', 'POST', 'OPTIONS'] and
            request.path.endswith('/') and  # Handle requests WITH trailing slash
            self._is_api_request(request)):

            logger.info(f"MIDDLEWARE: Retrying {request.method} {request.path} without trailing slash")

            # Create a new request WITHOUT trailing slash
            new_request = self._create_request_without_trailing_slash(request)

            # Try the request again without trailing slash
            try:
                new_response = self.get_response(new_request)
                logger.info(f"MIDDLEWARE: Retry result: {new_response.status_code}")

                # Only return the new response if it's successful (not 404/405)
                if new_response.status_code not in [404, 405]:
                    logger.info(f"MIDDLEWARE: Successfully redirected to {new_request.path}")
                    return new_response
            except Exception as e:
                logger.warning(f"MIDDLEWARE: Trailing slash retry failed: {e}")

        return response

    def _is_api_request(self, request):
        """Check if this is an API request that should have trailing slash handling"""
        return (request.path.startswith('/api/') or
                request.path.startswith('/agent/') or
                'application/json' in request.META.get('CONTENT_TYPE', ''))

    def _create_request_without_trailing_slash(self, request):
        """Create a new request object without trailing slash"""
        from django.http import HttpRequest

        # Create new request
        new_request = HttpRequest()
        new_request.method = request.method
        new_request.path = request.path.rstrip('/')  # Remove trailing slash
        new_request.path_info = request.path_info.rstrip('/')  # Remove trailing slash

        # Copy META data
        new_request.META = request.META.copy()
        new_request.META['PATH_INFO'] = request.path_info.rstrip('/')

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

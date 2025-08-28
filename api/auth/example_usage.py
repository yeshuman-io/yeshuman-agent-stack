"""
Example usage of the new Django authentication backends.

This file shows how to update your existing API endpoints to use
the proper Django authentication pattern instead of the old middleware.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ninja import NinjaAPI
from auth.middleware_django import require_a2a_auth, require_mcp_auth, require_api_key
from auth.backends import APIKeyUser

# Example NinjaAPI setup
example_api = NinjaAPI(title="Example API with Django Auth")


# ============================================================================
# Example 1: Using decorator with Django Ninja
# ============================================================================

@example_api.post("/a2a/endpoint")
@require_a2a_auth
async def example_a2a_endpoint(request, payload):
    """
    Example A2A endpoint using the new authentication decorator.
    
    The @require_a2a_auth decorator automatically:
    1. Checks if request.user is an APIKeyUser
    2. Verifies the API key type is 'a2a'
    3. Returns 401/403 errors if authentication fails
    """
    # At this point, request.user is guaranteed to be an authenticated APIKeyUser
    client_name = request.user.client_name
    
    return {
        "success": True,
        "authenticated_client": client_name,
        "message": "A2A authentication successful"
    }


@example_api.post("/mcp/endpoint")
@require_mcp_auth
async def example_mcp_endpoint(request, payload):
    """
    Example MCP endpoint using the new authentication decorator.
    """
    return {
        "success": True,
        "authenticated_client": request.user.client_name,
        "message": "MCP authentication successful"
    }


@example_api.post("/universal/endpoint")
@require_api_key(['a2a', 'mcp'])  # Allow both A2A and MCP keys
async def example_universal_endpoint(request, payload):
    """
    Example endpoint that accepts both A2A and MCP API keys.
    """
    return {
        "success": True,
        "authenticated_client": request.user.client_name,
        "api_key_type": request.user.api_key_type,
        "message": f"Authentication successful via {request.user.api_key_type}"
    }


# ============================================================================
# Example 2: Manual authentication checking (for more control)
# ============================================================================

@example_api.post("/manual/endpoint")
async def example_manual_auth_endpoint(request, payload):
    """
    Example of manual authentication checking for more control.
    
    This approach gives you full control over the authentication logic
    and error messages.
    """
    # Check if user is authenticated via API key
    if not isinstance(request.user, APIKeyUser):
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Valid X-API-Key header required for this endpoint'
        }, status=401)
    
    # Custom logic based on API key type
    if request.user.api_key_type == 'a2a':
        # A2A-specific logic
        result = f"A2A client '{request.user.client_name}' authenticated"
    elif request.user.api_key_type == 'mcp':
        # MCP-specific logic
        result = f"MCP client '{request.user.client_name}' authenticated"
    else:
        return JsonResponse({
            'error': 'Unauthorized',
            'message': f'Unknown API key type: {request.user.api_key_type}'
        }, status=403)
    
    return {
        "success": True,
        "result": result,
        "user_info": {
            "client_name": request.user.client_name,
            "api_key_type": request.user.api_key_type,
            "is_authenticated": request.user.is_authenticated,
            "is_anonymous": request.user.is_anonymous
        }
    }


# ============================================================================
# Example 3: How to update existing A2A API endpoints
# ============================================================================

# OLD WAY (what you currently have):
"""
@a2a_api.post("/", summary="A2A JSON-RPC endpoint (message/send)")
async def a2a_jsonrpc_handler(request, payload: JSONRPCRequest):
    # Check authentication
    from auth.middleware import auth
    is_authenticated, error_message = auth.authenticate_a2a(request)
    if not is_authenticated:
        from django.http import JsonResponse
        response = JsonResponse({
            'error': 'Authentication failed',
            'message': error_message
        }, status=401)
        return response
    
    # ... rest of the logic
"""

# NEW WAY (using Django authentication backends):
"""
@a2a_api.post("/", summary="A2A JSON-RPC endpoint (message/send)")
@require_a2a_auth
async def a2a_jsonrpc_handler(request, payload: JSONRPCRequest):
    # No need for manual authentication checking!
    # request.user is automatically an authenticated APIKeyUser
    
    # Access authenticated client info
    client_name = request.user.client_name
    
    # ... rest of the logic (unchanged)
"""


# ============================================================================
# Example 4: Testing the authentication
# ============================================================================

def test_authentication_example():
    """
    Example of how to test the new authentication system.
    
    This would be used in your test files.
    """
    from django.test import RequestFactory
    from django.contrib.auth import authenticate
    
    # Create a test request with API key
    factory = RequestFactory()
    request = factory.post('/test/', HTTP_X_API_KEY='your-test-api-key')
    
    # Test authentication
    user = authenticate(request)
    
    if user:
        print(f"Authentication successful: {user.client_name} ({user.api_key_type})")
        print(f"Is authenticated: {user.is_authenticated}")
        print(f"Is anonymous: {user.is_anonymous}")
    else:
        print("Authentication failed")


# ============================================================================
# Migration Guide
# ============================================================================
"""
MIGRATION STEPS:

1. Add 'auth' to INSTALLED_APPS in settings.py (if not already)

2. Add authentication backends to settings.py:
   AUTHENTICATION_BACKENDS = [
       'auth.backends.UniversalAPIKeyBackend',
       'django.contrib.auth.backends.ModelBackend',
   ]

3. Add the middleware to settings.py:
   MIDDLEWARE = [
       ...
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'auth.middleware_django.APIKeyAuthenticationMiddleware',
       ...
   ]

4. Update your API endpoints:
   
   REPLACE:
   ```python
   from auth.middleware import auth
   is_authenticated, error_message = auth.authenticate_a2a(request)
   if not is_authenticated:
       return error_response
   ```
   
   WITH:
   ```python
   from auth.middleware_django import require_a2a_auth
   
   @require_a2a_auth
   def your_view(request, ...):
       # request.user is now an APIKeyUser instance
       client_name = request.user.client_name
   ```

5. Update your tests to use the new authentication pattern

6. Remove the old auth/middleware.py file once migration is complete
"""


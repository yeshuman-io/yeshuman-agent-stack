"""
Server-Sent Events (SSE) utilities for YesHuman Agent Stack.

This module provides proper SSE HTTP response handling with correct headers
for web compatibility, following best practices from production systems.
"""
from django.http import StreamingHttpResponse


class SSEHttpResponse(StreamingHttpResponse):
    """
    A StreamingHttpResponse subclass that sets the appropriate headers for SSE.
    
    This class configures the HTTP response with the correct headers for
    Server-Sent Events (SSE) according to the specification and production
    best practices for web compatibility.
    """
    
    def __init__(self, streaming_content, **kwargs):
        """
        Initialize the SSE HTTP response with appropriate headers.
        
        Args:
            streaming_content: An async generator that yields SSE events
            **kwargs: Additional keyword arguments for StreamingHttpResponse
        """
        # Ensure content_type is set to text/event-stream
        kwargs.setdefault('content_type', 'text/event-stream')
        
        super().__init__(streaming_content, **kwargs)
        
        # Set SSE specific headers for proper browser/client compatibility
        self.headers['Cache-Control'] = 'no-cache'
        self.headers['Connection'] = 'keep-alive'
        self.headers['Access-Control-Allow-Origin'] = '*'
        self.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
        self.headers['Access-Control-Expose-Headers'] = 'Cache-Control'
        
        # Optional: Add additional headers for better client compatibility
        self.headers['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering

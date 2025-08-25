import json
import asyncio
import uuid
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List, Callable
from django.http import StreamingHttpResponse

logger = logging.getLogger(__name__)

class SSEHttpResponse(StreamingHttpResponse):
    """
    A StreamingHttpResponse subclass that sets the appropriate headers for SSE.
    
    This class configures the HTTP response with the correct headers for
    Server-Sent Events (SSE) according to the specification.
    """
    def __init__(self, streaming_content, **kwargs):
        """
        Initialize the SSE HTTP response with appropriate headers.
        
        Args:
            streaming_content: An async generator that yields SSE events
            **kwargs: Additional keyword arguments for StreamingHttpResponse
        """
        super().__init__(
            streaming_content,
            content_type='text/event-stream',
            **kwargs
        )
        # Set SSE specific headers
        self.headers['Cache-Control'] = 'no-cache'
        self.headers['Connection'] = 'keep-alive'
        self.headers['Access-Control-Allow-Origin'] = '*'


class SSEGenerator:
    """
    SSE Generator for BookedAI that returns a stream of events following
    the Anthropic SSE specification.
    
    This class dynamically transforms any chunk type from LangGraph's stream writer
    into a format that matches Anthropic's SSE event structure.
    """
    def __init__(self, token_counter: Optional[Callable[[str], int]] = None):
        """
        Initialize the SSE Generator.
        
        Args:
            token_counter: Optional function that counts tokens in a string.
                           If None, a simple whitespace-based counter is used.
        """
        self.last_heartbeat = 0
        self.heartbeat_interval = 15  # seconds
        self.content_blocks = {}  # Track active content blocks by type
        self.token_counter = token_counter or (lambda text: len(text.split()))
        self.tool_use_detected = False
        self.current_tool_name = None
        self.current_tool_input = {}
        self.tool_input_buffer = ""

    async def format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Format data as an SSE event with the specified type.
        
        Args:
            event_type: The type of SSE event (e.g., "message_start", "content_block_delta")
            data: The data to include in the event
            
        Returns:
            A formatted SSE event string
        """
        try:
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        except (TypeError, ValueError) as e:
            logger.error(f"Error formatting SSE event: {str(e)}")
            # Return a fallback error event - using double braces to escape
            return f"event: error\ndata: {{\"type\": \"error\", \"error\": {{\"type\": \"formatting_error\", \"message\": \"Failed to format event data\"}}}}\n\n"

    def get_block_index_for_type(self, chunk_type: str) -> int:
        """
        Get or create a content block index for a given chunk type.
        This ensures each chunk type gets its own content block.
        
        Args:
            chunk_type: The type of chunk (e.g., "message", "thinking", "voice")
            
        Returns:
            The index for the content block
        """
        if chunk_type not in self.content_blocks:
            # Assign a new index for this chunk type
            self.content_blocks[chunk_type] = len(self.content_blocks)
        return self.content_blocks[chunk_type]

    async def detect_tool_use(self, chunk: Dict[str, Any]) -> bool:
        """
        Detect if a chunk represents a tool use request.
        
        This method is async to allow for potential future I/O operations
        during tool detection, such as checking a database or calling an external service.
        
        Args:
            chunk: The chunk from the stream generator
            
        Returns:
            bool: True if the chunk represents a tool use, False otherwise
        """
        # Check for explicit tool_use type
        if chunk.get("type") == "tool_use":
            self.current_tool_name = chunk.get("name")
            self.current_tool_input = chunk.get("input", {})
            return True
            
        # Check for function_call type (OpenAI style)
        if chunk.get("type") == "function_call" or "function_call" in chunk:
            function_data = chunk.get("function_call", {})
            if isinstance(function_data, dict):
                self.current_tool_name = function_data.get("name")
                # The input might be in arguments or already parsed
                arguments = function_data.get("arguments", "{}")
                if isinstance(arguments, str):
                    try:
                        self.current_tool_input = json.loads(arguments)
                    except json.JSONDecodeError:
                        self.current_tool_input = {"raw_arguments": arguments}
                else:
                    self.current_tool_input = arguments
                return True
                
        # Check for tool_input fragments that might be streamed
        if chunk.get("type") == "tool_input_fragment":
            if not self.tool_use_detected:
                self.tool_use_detected = True
                self.current_tool_name = chunk.get("name")
            
            # Accumulate the input fragment
            self.tool_input_buffer += chunk.get("content", "")
            
            # If this is the last fragment, parse the complete input
            if chunk.get("is_last", False):
                try:
                    self.current_tool_input = json.loads(self.tool_input_buffer)
                except json.JSONDecodeError:
                    self.current_tool_input = {"raw_input": self.tool_input_buffer}
                self.tool_input_buffer = ""
                return True
                
        return False

    async def process_tool_use(self, block_index: int) -> List[bytes]:
        """
        Process a tool use and generate the appropriate SSE events.
        
        Args:
            block_index: The content block index for the tool use
            
        Returns:
            List[bytes]: The SSE events for the tool use
        """
        events = []
        
        # Generate a unique tool ID
        tool_id = f"toolu_{uuid.uuid4().hex[:16]}"
        
        try:
            # Start tool use content block
            events.append((await self.format_sse_event("content_block_start", {
                "type": "content_block_start",
                "index": block_index,
                "content_block": {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": self.current_tool_name,
                    "input": {}
                }
            })).encode('utf-8'))
            
            # Convert tool input to JSON
            try:
                tool_input_json = json.dumps(self.current_tool_input)
                
                # Stream the tool input as JSON deltas
                # For large inputs, break into smaller chunks
                chunk_size = 100  # characters
                for i in range(0, len(tool_input_json), chunk_size):
                    chunk = tool_input_json[i:i+chunk_size]
                    events.append((await self.format_sse_event("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_index,
                        "delta": {"type": "input_json_delta", "partial_json": chunk}
                    })).encode('utf-8'))
                    
            except (TypeError, ValueError) as e:
                logger.error(f"Error serializing tool input: {str(e)}")
                # Send error as the input - using double braces to escape
                error_json = f"{{\"error\": \"{str(e)}\"}}"
                events.append((await self.format_sse_event("content_block_delta", {
                    "type": "content_block_delta",
                    "index": block_index,
                    "delta": {"type": "input_json_delta", "partial_json": error_json}
                })).encode('utf-8'))
                
            # End the tool use content block
            events.append((await self.format_sse_event("content_block_stop", {
                "type": "content_block_stop",
                "index": block_index
            })).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error processing tool use: {str(e)}")
            # Add error event
            events.append((await self.format_sse_event("error", {
                "type": "error",
                "error": {"type": "tool_processing_error", "message": str(e)}
            })).encode('utf-8'))
            
        return events

    async def generate_sse(self, stream_generator) -> AsyncGenerator[bytes, None]:
        """
        Transform a LangGraph stream into Anthropic-style SSE events.
        
        Dynamically handles any chunk type from the stream generator,
        including tool use detection and error handling.
        
        Args:
            stream_generator: The async generator from LangGraph's stream writer
            
        Yields:
            Bytes formatted as SSE events following Anthropic's specification
        """
        # Send message_start event
        try:
            yield (await self.format_sse_event("message_start", {
                "type": "message_start",
                "message": {"content": []}
            })).encode('utf-8')
            
            # Track active content blocks and accumulated content by type
            active_blocks = set()
            accumulated_content = {}
            
            # Track the last heartbeat time
            self.last_heartbeat = asyncio.get_event_loop().time()
            
            # Reset tool use state
            self.tool_use_detected = False
            self.current_tool_name = None
            self.current_tool_input = {}
            self.tool_input_buffer = ""
            
            # Process the stream
            try:
                async for chunk in stream_generator:
                    # Send heartbeat if needed
                    current_time = asyncio.get_event_loop().time()
                    if current_time - self.last_heartbeat >= self.heartbeat_interval:
                        yield b": heartbeat\n\n"
                        self.last_heartbeat = current_time
                    
                    # Check for tool use
                    if await self.detect_tool_use(chunk):
                        # Get block index for tool use
                        tool_block_index = self.get_block_index_for_type("tool_use")
                        
                        # Process tool use and yield events
                        for event in await self.process_tool_use(tool_block_index):
                            yield event
                        
                        # Mark tool_use block as active
                        active_blocks.add("tool_use")
                        
                        # For tool use, we might want to end the message here
                        # or continue processing other chunks
                        # For now, we'll continue to allow mixed content
                        continue
                    
                    # Extract chunk type and content
                    chunk_type = chunk.get("type", "message")
                    content = chunk.get("content", "")
                    
                    # Skip empty chunks
                    if not content and chunk_type not in ["done", "stop"]:
                        continue
                    
                    # Handle special "done" or "stop" chunk types
                    if chunk_type in ["done", "stop"]:
                        # Close all active blocks and end the message
                        break
                    
                    # Get the block index for this chunk type
                    block_index = self.get_block_index_for_type(chunk_type)
                    
                    # Initialize accumulated content for this type if needed
                    if chunk_type not in accumulated_content:
                        accumulated_content[chunk_type] = ""
                    
                    # Start a content block if this is the first chunk of this type
                    if chunk_type not in active_blocks:
                        active_blocks.add(chunk_type)
                        
                        # Determine the content block type based on chunk_type
                        content_block_type = chunk_type
                        
                        # Special case mappings
                        if chunk_type == "message":
                            content_block_type = "text"
                        elif chunk_type == "error":
                            content_block_type = "error"
                        # Add more mappings as needed
                        
                        yield (await self.format_sse_event("content_block_start", {
                            "type": "content_block_start",
                            "index": block_index,
                            "content_block": {"type": content_block_type, "id": f"{content_block_type}_{uuid.uuid4().hex[:8]}"}
                        })).encode('utf-8')
                    
                    # Accumulate content
                    accumulated_content[chunk_type] += content
                    
                    # Send content delta with appropriate delta type
                    delta_type = f"{chunk_type}_delta"
                    
                    # Special case mappings for different content types
                    if chunk_type == "message":
                        delta_type = "text_delta"
                    elif chunk_type == "thinking":
                        delta_type = "thinking_delta"
                    elif chunk_type == "voice":
                        delta_type = "voice_delta"
                    elif chunk_type == "tool":
                        delta_type = "tool_delta"
                    elif chunk_type == "knowledge":
                        delta_type = "knowledge_delta"
                    
                    yield (await self.format_sse_event("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_index,
                        "delta": {"type": delta_type, "text": content}
                    })).encode('utf-8')
                    
                    # Special handling for error chunks - close all blocks and end the message
                    if chunk_type == "error":
                        # We'll let the normal flow handle closing blocks
                        break
                
            except Exception as e:
                logger.error(f"Error processing stream: {str(e)}")
                # Create an error content block
                error_index = self.get_block_index_for_type("error")
                
                # Start error block if not already active
                if "error" not in active_blocks:
                    active_blocks.add("error")
                    yield (await self.format_sse_event("content_block_start", {
                        "type": "content_block_start",
                        "index": error_index,
                        "content_block": {"type": "error", "id": f"error_{uuid.uuid4().hex[:8]}"}
                    })).encode('utf-8')
                
                # Send error content
                yield (await self.format_sse_event("content_block_delta", {
                    "type": "content_block_delta",
                    "index": error_index,
                    "delta": {"type": "error_delta", "text": f"Error: {str(e)}"}
                })).encode('utf-8')
                
                # Add to accumulated content
                if "error" not in accumulated_content:
                    accumulated_content["error"] = ""
                accumulated_content["error"] += f"Error: {str(e)}"
            
            # Close all active blocks
            for chunk_type in active_blocks:
                block_index = self.get_block_index_for_type(chunk_type)
                yield (await self.format_sse_event("content_block_stop", {
                    "type": "content_block_stop",
                    "index": block_index
                })).encode('utf-8')
            
            # Determine stop reason
            stop_reason = "end_turn"  # default
            
            if "error" in active_blocks:
                stop_reason = "error"
            elif self.tool_use_detected:
                stop_reason = "tool_use"
            
            # Calculate total tokens
            total_tokens = 0
            for content_type, content in accumulated_content.items():
                if content:
                    try:
                        total_tokens += self.token_counter(content)
                    except Exception as e:
                        logger.warning(f"Error counting tokens for {content_type}: {str(e)}")
            
            # Send message_delta with appropriate stop reason
            yield (await self.format_sse_event("message_delta", {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": total_tokens}
            })).encode('utf-8')
            
            # End the message
            yield (await self.format_sse_event("message_stop", {
                "type": "message_stop"
            })).encode('utf-8')
            
        except Exception as e:
            logger.error(f"Critical error in SSE generation: {str(e)}")
            # Send a basic error event as a last resort - using double braces to escape
            error_event = f"event: error\ndata: {{\"type\": \"error\", \"error\": {{\"type\": \"critical_error\", \"message\": \"{str(e)}\"}}}}\n\n"
            yield error_event.encode('utf-8')
            yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n".encode('utf-8')
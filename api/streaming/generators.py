"""
Anthropic SSE Generator for YesHuman Agent Stack.

Copied and adapted from server/agent/generators.py to provide
Anthropic-compatible SSE streaming for custom UI consumers.
"""
import json
import asyncio
import uuid
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)


class AnthropicSSEGenerator:
    """
    SSE Generator that transforms LangGraph stream events into
    Anthropic-compatible SSE format for custom UI consumption.
    
    This class dynamically handles any chunk type from LangGraph's stream writer
    and converts it to match Anthropic's SSE event structure.
    """
    def __init__(self, token_counter: Optional[Callable[[str], int]] = None):
        """
        Initialize the SSE Generator.
        
        Args:
            token_counter: Optional function that counts tokens in a string.
                           If None, a simple whitespace-based counter is used.
        """
        self.last_heartbeat = 0
        self.heartbeat_interval = 5  # seconds (reduced for testing)
        self.content_blocks = {}  # Track active content blocks by type
        self.token_counter = token_counter or (lambda text: len(text.split()))

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
            # Ensure JSON is single-line (no pretty printing)
            json_data = json.dumps(data, separators=(',', ':'))
            return f"event: {event_type}\ndata: {json_data}\n\n"
        except (TypeError, ValueError) as e:
            logger.error(f"Error formatting SSE event: {str(e)}")
            # Return a fallback error event
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
                # Send error as the input
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
            

            
            # Process the stream
            try:
                async for chunk in stream_generator:
                    # Send heartbeat if needed
                    current_time = asyncio.get_event_loop().time()
                    if current_time - self.last_heartbeat >= self.heartbeat_interval:
                        yield b": heartbeat\n\n"
                        self.last_heartbeat = current_time
                    

                    
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
                    
                    # Voice chunks are now handled directly from stream_mode="custom"
                    
                    # Map chunk types to proper delta types
                    delta_type_mapping = {
                        "message": "message_delta",
                        "thinking": "thinking_delta", 
                        "tool": "tool_delta",
                        "json": "json_delta",
                        "system": "system_delta",
                        "voice": "voice_delta",
                        "voice_complete": "voice_complete",
                        "error": "error"
                    }
                    delta_type = delta_type_mapping.get(chunk_type, "message_delta")
                    
                    # Handle special metadata for voice events
                    delta_data = {"type": delta_type, "text": content}
                    if chunk_type == "voice":
                        style = chunk.get("style", "encouraging")
                        progress = chunk.get("progress", "")
                        delta_data.update({"style": style, "progress": progress})
                    elif chunk_type == "voice_complete":
                        delta_data = {"type": delta_type, "message": chunk.get("message", "")}
                    
                    yield (await self.format_sse_event("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_index,
                        "delta": delta_data
                    })).encode('utf-8')
                    
                    # Special handling for error chunks - close all blocks and end the message
                    if chunk_type == "error":
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
            
            # Send a heartbeat before ending (helps detect connection issues)
            yield b": heartbeat\n\n"
            
            # End the message (but keep connection alive)
            yield (await self.format_sse_event("message_stop", {
                "type": "message_stop"
            })).encode('utf-8')
            
            # Keep connection alive with periodic heartbeats
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                yield b": heartbeat\n\n"
            
        except Exception as e:
            logger.error(f"Critical error in SSE generation: {str(e)}")
            # Send a basic error event as a last resort
            error_event = f"event: error\ndata: {{\"type\": \"error\", \"error\": {{\"type\": \"critical_error\", \"message\": \"{str(e)}\"}}}}\n\n"
            yield error_event.encode('utf-8')
            yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n".encode('utf-8')


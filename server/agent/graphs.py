"""
BookedAI Graph Module

This module implements the LangGraph-based workflow for processing user queries
through a thinking-centric architecture. The graph uses specialized instructors
for different types of responses (thinking, message, voice) with structured outputs.
"""
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional, Literal, TypeVar, Generic, Union, cast
from pydantic import BaseModel, Field, ConfigDict
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer

from .instructors import (
    create_instructor,
    ThinkingInstructor, MessageInstructor, VoiceInstructor,
    ThinkingResponse, MessageResponse, VoiceResponse
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graph State Management
# ---------------------------------------------------------------------------

class GraphState(BaseModel):
    """
    State object for BookedAI response graph with a thinking-centric architecture.
    
    The graph uses structured output from instructors to make decisions about
    the flow of information processing and tool execution.
    """
    model_config = ConfigDict(extra="forbid")
    
    # Input context
    query: str = ""
    message_obj: Optional[Any] = None
    system_message: str = ""
    chat_id: Optional[str] = None
    
    # Thinking state
    thinking_response: Optional[ThinkingResponse] = None
    thinking_complete: bool = False
    
    # Tool execution state
    tool_execution_required: bool = False
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    tool_execution_complete: bool = False
    
    # Response state
    message_response: Optional[MessageResponse] = None
    voice_response: Optional[VoiceResponse] = None
    
    # Response execution tracking
    message_executed: bool = False
    voice_executed: bool = False
    parallel_executed: bool = False
    
    # Error state
    error: Optional[str] = None
    error_type: Optional[str] = None  # 'thinking', 'tool', 'response', or 'general'

# ---------------------------------------------------------------------------
# Node Implementations
# ---------------------------------------------------------------------------

async def thinking_node(state: GraphState) -> GraphState:
    """
    Think through the query and determine the required actions.
    
    This node focuses on:
    1. Interpreting the user's query
    2. Determining if tool execution is needed
    3. Planning the response approach
    """
    writer = get_stream_writer()
    
    logger.info(f"Thinking node started with query: {state.query}")
    
    try:
        # Create the thinking instructor
        instructor = create_instructor("thinking")
        
        # Assemble the query with any additional context needed
        query_with_context = state.query
        if state.tool_result:
            query_with_context = f"{state.query}\n\nPrevious tool result: {state.tool_result}"
        
        # Reset thinking state if starting fresh
        if not state.thinking_complete:
            state.thinking_response = None
        
        # Process the response chunks
        async for chunk in instructor.generate(
            query_with_context,
            message_executed=state.message_executed,
            parallel_executed=state.parallel_executed
        ):
            # Stream the thinking portion for UI feedback
            writer({"type": "thinking", "content": chunk.thinking})
            
            # Update the state with the latest response
            state.thinking_response = chunk
            
            # Check if thinking indicates tool execution is needed
            if "tool" in chunk.thinking.lower():
                state.tool_execution_required = True
                # Extract tool details from thinking if possible
                # This would be enhanced with more sophisticated parsing
                if "tool:" in chunk.thinking.lower():
                    tool_info = chunk.thinking.lower().split("tool:")[1].split("\n")[0].strip()
                    state.tool_name = tool_info
        
        # Mark thinking as complete
        state.thinking_complete = True
        
        logger.info(f"Thinking completed. Tool execution required: {state.tool_execution_required}")
        return state
            
    except Exception as e:
        logger.error(f"Error in thinking node: {e}")
        state.error = str(e)
        state.error_type = "thinking"
        
        # Send error message to the client
        writer({"type": "error", "content": f"Error in thinking: {str(e)}"})
        
        return state


async def voice_node(state: GraphState) -> GraphState:
    """
    Generate and emit a voice response using the VoiceInstructor.
    """
    writer = get_stream_writer()
    
    logger.info("Voice node started")
    
    try:
        # Indicate voice processing has started
        writer({"type": "voice", "content": "VOICE_START"})
        
        # Create the voice instructor
        instructor = create_instructor("voice")
        
        # Initialize or reset the voice response
        state.voice_response = None
        
        # Process voice response chunks
        async for chunk in instructor.generate(state.query):
            # Each chunk is a VoiceResponse object
            # Map the text field to content for the writer
            writer({"type": "voice", "content": chunk.text})
            
            # Update the state with the latest response
            state.voice_response = chunk
            
            # Brief pause to simulate natural speech rhythm
            await asyncio.sleep(0.05)
        
        # Mark voice execution as complete
        state.voice_executed = True
        
        logger.info("Voice node completed successfully")
        return state
        
    except Exception as e:
        logger.error(f"Error in voice node: {e}")
        state.error = str(e)
        
        # Send error message to the client
        writer({"type": "error", "content": f"Error generating voice: {str(e)}"})
        
        return state


async def message_node(state: GraphState) -> GraphState:
    """
    Generate a detailed message response using the MessageInstructor.
    """
    writer = get_stream_writer()
    
    logger.info("Message node started")
    
    try:
        # Create the message instructor
        instructor = create_instructor("message")
        
        # Add thinking analysis as context if available
        query_with_context = state.query
        if state.thinking_response:
            query_with_context = f"{state.query}\n\nMy thinking: {state.thinking_response.thinking}"
        
        # Initialize or reset the message response
        state.message_response = None
        
        # Process message response chunks
        async for chunk in instructor.generate(query_with_context):
            # Each chunk is a MessageResponse object
            writer({"type": "message", "content": chunk.text})
            
            # Update the state with the latest response
            state.message_response = chunk
        
        # Mark message execution as complete
        state.message_executed = True
        
        logger.info("Message node completed successfully")
        return state
        
    except Exception as e:
        logger.error(f"Error in message node: {e}")
        state.error = str(e)
        
        # Send error message to the client
        writer({"type": "error", "content": f"Error generating message: {str(e)}"})
        
        return state


async def parallel_node(state: GraphState) -> GraphState:
    """
    Execute voice and message nodes in parallel using asyncio.
    """
    writer = get_stream_writer()
    
    logger.info("Parallel node started")
    
    try:
        # Create tasks for both nodes
        voice_task = asyncio.create_task(voice_node(state.copy()))
        message_task = asyncio.create_task(message_node(state.copy()))
        
        # Wait for both tasks to complete
        voice_state, message_state = await asyncio.gather(
            voice_task, message_task, return_exceptions=True
        )
        
        # Handle any exceptions
        if isinstance(voice_state, Exception):
            logger.error(f"Error in voice task: {voice_state}")
            writer({"type": "error", "content": f"Voice error: {str(voice_state)}"})
        else:
            state.voice_response = voice_state.voice_response
            state.voice_executed = True
            
        if isinstance(message_state, Exception):
            logger.error(f"Error in message task: {message_state}")
            writer({"type": "error", "content": f"Message error: {str(message_state)}"})
        else:
            state.message_response = message_state.message_response
            state.message_executed = True
        
        # Mark parallel execution as complete
        state.parallel_executed = True
        
        logger.info("Parallel node completed successfully")
        return state
        
    except Exception as e:
        logger.error(f"Error in parallel node: {e}")
        state.error = str(e)
        
        # Send error message to the client
        writer({"type": "error", "content": f"Error in parallel processing: {str(e)}"})
        
        return state


async def error_handling_node(state: GraphState) -> GraphState:
    """Handle errors in the graph execution."""
    writer = get_stream_writer()
    
    error_message = state.error or "An unknown error occurred"
    logger.error(f"Error handling node: {error_message}")
    
    # Send error notification
    writer({"type": "error", "content": f"Error: {error_message}"})
    
    # Send user-friendly message
    friendly_message = f"I'm sorry, I encountered a problem: {error_message}. Please try again."
    writer({"type": "message", "content": friendly_message})
    
    return state


async def tool_execution_node(state: GraphState) -> GraphState:
    """
    Execute tools based on analysis results.
    
    This node:
    1. Executes the required tool
    2. Processes the tool result
    3. Updates state with results
    """
    writer = get_stream_writer()
    
    logger.info("Tool execution node started")
    
    try:
        if not state.tool_execution_required or not state.tool_name:
            logger.info("No tool execution required")
            return state
            
        # Log tool execution start
        writer({"type": "tool_start", "content": f"Executing tool: {state.tool_name}"})
        
        # TODO: Implement actual tool execution logic
        # This is a placeholder for the actual tool execution
        # In a real implementation, this would:
        # 1. Look up the tool by name
        # 2. Validate tool inputs
        # 3. Execute the tool
        # 4. Process results
        
        # For now, we'll simulate a tool result
        state.tool_result = f"Simulated result from {state.tool_name}"
        
        # Mark tool execution as complete
        state.tool_execution_complete = True
        
        # Log tool completion
        writer({"type": "tool_complete", "content": f"Tool {state.tool_name} completed successfully"})
        
        return state
        
    except Exception as e:
        logger.error(f"Error in tool execution: {e}")
        state.error = str(e)
        state.error_type = "tool"
        
        # Send error message to the client
        writer({"type": "error", "content": f"Error executing tool: {str(e)}"})
        
        return state

# ---------------------------------------------------------------------------
# Graph Routing Logic
# ---------------------------------------------------------------------------

def route_from_thinking(state: GraphState) -> str:
    """
    Determine the next node based on thinking results or error state.
    
    Args:
        state: Current graph state
        
    Returns:
        Name of the next node to execute
    """
    # Handle errors first
    if state.error:
        return "error_handler"
        
    # If thinking hasn't produced a response yet, that's an error
    if not state.thinking_response:
        logger.error("Thinking node did not produce a response")
        state.error = "No thinking response produced"
        state.error_type = "thinking"
        return "error_handler"
    
    # If tool execution is required and not complete
    if state.tool_execution_required and not state.tool_execution_complete:
        return "tool_execution"
    
    # Check if we've already completed the main response
    if state.message_executed or state.parallel_executed:
        logger.info("Main response already executed, completing")
        return END
    
    # Route based on the next_action field from the thinking response
    next_action = state.thinking_response.next_action
    
    # Handle voice updates separately since they don't indicate completion
    if next_action == "voice":
        if state.voice_executed:
            logger.info("Voice already executed, continuing with main response")
            next_action = "message"  # Default to message after voice
        return "voice"
    
    # Handle main response types
    if next_action == "message":
        return "message"
    elif next_action == "voice_and_message":
        return "parallel"  # Use parallel node for concurrent execution
    elif next_action == "complete":
        return END
    else:
        # Default to message if action is invalid
        logger.warning(f"Unknown next_action: {next_action}, defaulting to message")
        return "message"


def route_from_tool(state: GraphState) -> str:
    """
    Determine the next node after tool execution.
    
    Args:
        state: Current graph state
        
    Returns:
        Name of the next node to execute
    """
    # Handle errors first
    if state.error:
        return "error_handler"
    
    # After tool execution, return to thinking to incorporate results
    return "thinking"


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

def create_thinking_centric_graph() -> StateGraph:
    """
    Create a thinking-centric graph where thinking node decides the flow.
    
    Returns:
        The compiled graph
    """
    # Build the graph
    builder = StateGraph(GraphState)
    
    # Add nodes
    builder.add_node("thinking", thinking_node)
    builder.add_node("tool_execution", tool_execution_node)
    builder.add_node("voice", voice_node)
    builder.add_node("message", message_node)
    builder.add_node("parallel", parallel_node)
    builder.add_node("error_handler", error_handling_node)
    
    # Define edges
    
    # Always start with thinking
    builder.add_edge(START, "thinking")
    
    # Use the routing functions to determine next node
    builder.add_conditional_edges("thinking", route_from_thinking, {
        "tool_execution": "tool_execution",
        "voice": "voice",
        "message": "message",
        "parallel": "parallel",
        "error_handler": "error_handler",
        END: END
    })
    
    # Route from tool execution back to thinking
    builder.add_conditional_edges("tool_execution", route_from_tool, {
        "thinking": "thinking",
        "error_handler": "error_handler"
    })
    
    # Voice and message go back to thinking for next decision
    builder.add_edge("voice", "thinking")
    builder.add_edge("message", "thinking")
    builder.add_edge("parallel", "thinking")
    
    # Error ends the graph
    builder.add_edge("error_handler", END)
    
    # Compile the graph
    return builder.compile()


# ---------------------------------------------------------------------------
# Main Interface Function
# ---------------------------------------------------------------------------

async def async_graph_streaming_response(
    message_obj: Optional[Any] = None, 
    system_message: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream responses using the thinking-centric graph.
    
    This function initializes and executes the graph, which orchestrates the flow 
    through thinking, voice, and message nodes. Each node emits events that are 
    captured and yielded by this generator.
    
    Args:
        message_obj: Message object to respond to
        system_message: System message (required if message_obj is not provided)
    
    Returns:
        AsyncGenerator yielding dictionaries with "type" and "content" keys
    
    Raises:
        ValueError: If neither message_obj nor system_message is provided
    """
    # Validate inputs
    if message_obj is None and not system_message:
        raise ValueError("Either message_obj or system_message must be provided")

    try:
        # Create the graph
        graph = create_thinking_centric_graph()
        
        # Extract query and chat_id
        query = ""
        chat_id = None
        
        if message_obj:
            # Extract from message object
            if hasattr(message_obj, 'text'):
                query = message_obj.text
            elif isinstance(message_obj, dict) and 'message' in message_obj:
                query = message_obj['message']
            
            # Get chat ID
            if hasattr(message_obj, 'chat') and hasattr(message_obj.chat, 'id'):
                chat_id = str(message_obj.chat.id)
        else:
            # Use system message as query
            query = system_message or ""
        
        logger.info(f"Executing graph with query: {query[:50]}...")
        
        # Initialize state
        initial_state = GraphState(
            query=query,
            message_obj=message_obj,
            system_message=system_message or "",
            chat_id=chat_id
        )
        
        # Execute graph with streaming
        async for event in graph.astream(initial_state, stream_mode="custom"):
            yield event
            
    except Exception as e:
        logger.error(f"Error in graph execution: {e}")
        yield {"type": "error", "content": f"Graph execution error: {str(e)}"}
#!/usr/bin/env python3
"""
Standalone LangGraph application for testing with LangGraph Studio.

This module provides a clean entry point for your LangGraph workflows 
that can be used independently of Django for development and testing.
"""

import os
import sys
from pathlib import Path

# Add the server directory to Python path to import Django modules
server_dir = Path(__file__).parent
sys.path.insert(0, str(server_dir))

# Set up minimal Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookedai.settings')

# Import Django and configure
import django
django.setup()

# Now import your graph components
from agent.graphs import create_thinking_centric_graph, GraphState
from agent.instructors import ThinkingResponse
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph


def create_app() -> StateGraph:
    """
    Create the LangGraph application for Studio.
    
    Returns:
        Compiled StateGraph ready for LangGraph Studio
    """
    return create_thinking_centric_graph()


def create_test_state(query: str = "Plan a weekend trip to Paris") -> GraphState:
    """
    Create a test state for development.
    
    Args:
        query: Test query to process
        
    Returns:
        GraphState configured for testing
    """
    return GraphState(
        query=query,
        message_obj=None,
        system_message="You are a helpful travel planning assistant.",
        chat_id="test_chat_001"
    )


# LangGraph Studio expects these exports
graph = create_app()

# Optional: Create some test configurations for Studio
test_configs = {
    "travel_planning": {
        "query": "Plan a 3-day trip to Tokyo with a $2000 budget",
        "system_message": "You are a travel planning expert."
    },
    "simple_query": {
        "query": "What's the weather like?",
        "system_message": "You are a helpful assistant."
    },
    "error_test": {
        "query": "This should trigger an error for testing",
        "system_message": "Test error handling."
    }
}


if __name__ == "__main__":
    # This allows running the graph directly for quick testing
    import asyncio
    
    async def test_run():
        """Quick test run of the graph."""
        test_state = create_test_state()
        print(f"Testing with query: {test_state.query}")
        
        result = await graph.ainvoke(test_state)
        print(f"Result: {result}")
    
    asyncio.run(test_run()) 
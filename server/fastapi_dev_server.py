#!/usr/bin/env python3
"""
FastAPI development server for LangGraph testing.

Alternative to LangGraph Studio for more customized testing needs.
"""

import os
import sys
from pathlib import Path

# Setup Django environment
server_dir = Path(__file__).parent
sys.path.insert(0, str(server_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookedai.settings')

import django
django.setup()

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import asyncio

from agent.graphs import create_thinking_centric_graph, GraphState
from langgraph_app import test_configs


app = FastAPI(title="BookedAI Graph Development Server")
graph = create_thinking_centric_graph()


class TestRequest(BaseModel):
    query: str
    system_message: Optional[str] = "You are a helpful travel planning assistant."
    chat_id: Optional[str] = "dev_test"
    config_name: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "BookedAI Graph Development Server",
        "version": "1.0.0",
        "endpoints": {
            "/test": "Test graph execution",
            "/stream": "Stream graph execution", 
            "/configs": "Get available test configurations",
            "/graph": "Get graph structure"
        }
    }


@app.get("/configs")
async def get_configs():
    """Get available test configurations."""
    return {"configs": test_configs}


@app.get("/graph")
async def get_graph_info():
    """Get information about the graph structure."""
    graph_def = graph.get_graph()
    return {
        "nodes": list(graph_def.nodes.keys()),
        "edges": [
            {"source": edge.source, "target": edge.target} 
            for edge in graph_def.edges
        ]
    }


@app.post("/test")
async def test_graph(request: TestRequest):
    """Test graph execution with a simple request/response."""
    try:
        # Use predefined config if specified
        if request.config_name and request.config_name in test_configs:
            config = test_configs[request.config_name]
            query = config["query"]
            system_message = config["system_message"]
        else:
            query = request.query
            system_message = request.system_message
        
        # Create initial state
        initial_state = GraphState(
            query=query,
            system_message=system_message,
            chat_id=request.chat_id or "dev_test"
        )
        
        # Execute graph
        result = await graph.ainvoke(initial_state)
        
        return {
            "success": True,
            "query": query,
            "result": {
                "thinking_complete": getattr(result, 'thinking_complete', False),
                "message_executed": getattr(result, 'message_executed', False),
                "voice_executed": getattr(result, 'voice_executed', False),
                "error": getattr(result, 'error', None),
                "thinking_response": getattr(result, 'thinking_response', None),
                "message_response": getattr(result, 'message_response', None)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream")
async def stream_graph(request: TestRequest):
    """Stream graph execution for real-time updates."""
    
    async def generate_events():
        try:
            # Use predefined config if specified
            if request.config_name and request.config_name in test_configs:
                config = test_configs[request.config_name]
                query = config["query"]
                system_message = config["system_message"]
            else:
                query = request.query
                system_message = request.system_message
            
            # Create initial state
            initial_state = GraphState(
                query=query,
                system_message=system_message,
                chat_id=request.chat_id or "dev_test"
            )
            
            # Stream graph execution
            async for event in graph.astream(initial_state, stream_mode="updates"):
                # Format as Server-Sent Events
                yield f"data: {json.dumps(event)}\n\n"
                
            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting BookedAI Graph Development Server...")
    print("📋 Available endpoints:")
    print("   - http://localhost:8001/docs (Swagger UI)")
    print("   - http://localhost:8001/test (Test execution)")
    print("   - http://localhost:8001/stream (Stream execution)")
    print("   - http://localhost:8001/configs (Test configurations)")
    
    uvicorn.run(
        "fastapi_dev_server:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=[str(server_dir)]
    ) 
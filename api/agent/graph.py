"""
Yes Human Agent - Simple ReAct Implementation with LangGraph.

Clean design following LangGraph patterns:
- Standard AgentState with messages + add_messages reducer
- Simple nodes: context preparation, agent, tools
- Built-in ToolNode for tool execution
- Proper streaming integration
"""
import os
import logging
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer

from .mapper import get_tool_event_config, create_ui_event
from .services import memory, prompt, events, tools, voice

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger('agent')


# UI events are emitted directly in agent_node




class AgentState(TypedDict):
    """Simple state following LangGraph patterns."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]
    user: Optional[Any]  # Django User object
    tools_done: Optional[bool]
    voice_messages: Optional[List[str]]
    last_voice_sig: Optional[str]
    tool_call_count: Optional[int]  # Prevent infinite tool loops
    context_memories: Optional[List[Dict[str, Any]]]


async def context_preparation_node(state: AgentState) -> AgentState:
    """Add system prompt to start conversation and retrieve memories."""
    print("🧠 DEBUG: context_preparation_node called")
    logger.info("🧠 Context preparation node started")

    # Try to refresh system prompt from Django settings if available
    try:
        current_prompt = prompt.get_system_prompt()
        logger.debug("Updated system prompt for client configuration")
    except Exception:
        # Keep existing prompt if update fails
        current_prompt = prompt.get_fallback_prompt()

    # Retrieve memories first
    user_id = state.get("user_id")
    last_user_text = ""
    for _m in reversed(state.get("messages", [])):
        if isinstance(_m, HumanMessage) and _m.content:
            last_user_text = _m.content
            break

    context_memories = []
    if last_user_text and user_id:
        logger.info(f"🧠 Memory retrieval: user_id={user_id}, query='{last_user_text[:50]}...'")
        try:
            context_memories = await memory.retrieve_context_memories(user_id, last_user_text, k=5)
            logger.info(f"🧠 Memory retrieval: found {len(context_memories)} memories")

            # Emit SSE memory.retrieved
            writer = get_stream_writer()
            if writer and context_memories:
                top_similarity = context_memories[0]["metadata"].get("similarity") if context_memories else None
                await events.emit_memory_retrieved(writer, len(context_memories), top_similarity)
        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")

    # Always enhance system prompt with memories if available
    enhanced_prompt = prompt.inject_memories_into_prompt(current_prompt, context_memories)

    if not state["messages"]:
        # No messages at all - create new system message
        system_message = SystemMessage(content=enhanced_prompt)
        if context_memories:
            logger.info(f"🧠 Enhanced system prompt with {len(context_memories)} memories: {[m.get('memory', m.get('content', ''))[:50] for m in context_memories[:3]]}")
            print(f"🧠 DEBUG: System prompt enhanced with {len(context_memories)} memories")
        return {"messages": [system_message], "context_memories": context_memories}

    elif isinstance(state["messages"][0], SystemMessage):
        # System message exists - enhance it with memories
        existing_prompt = state["messages"][0].content
        if context_memories:
            # Check if memories are already included (avoid duplication)
            if "## Relevant Memories" not in existing_prompt:
                enhanced_prompt = prompt.inject_memories_into_prompt(existing_prompt, context_memories)
                logger.info(f"🧠 Enhanced existing system prompt with {len(context_memories)} memories")
                print(f"🧠 DEBUG: Enhanced existing system prompt with {len(context_memories)} memories")
            else:
                enhanced_prompt = existing_prompt

        # Replace the existing system message
        enhanced_system_message = SystemMessage(content=enhanced_prompt)
        updated_messages = [enhanced_system_message] + state["messages"][1:]
        return {"messages": updated_messages, "context_memories": context_memories}

    else:
        # No system message - prepend one
        system_message = SystemMessage(content=enhanced_prompt)
        if context_memories:
            logger.info(f"🧠 Enhanced system prompt with {len(context_memories)} memories: {[m.get('memory', m.get('content', ''))[:50] for m in context_memories[:3]]}")
            print(f"🧠 DEBUG: System prompt enhanced with {len(context_memories)} memories")
        # Prepend system message to existing messages
        existing_messages = state.get("messages", [])
        return {"messages": [system_message] + existing_messages, "context_memories": context_memories}




def should_continue(state: AgentState) -> str:
    """Decide whether to continue to tools or finish."""
    logger.info("🔀 should_continue called")

    if not state["messages"]:
        logger.debug("❌ No messages in state, ending")
        return END

    # Allow iterative tool usage - no loop prevention

    last_message = state["messages"][-1]
    logger.debug(f"📨 Last message type: {type(last_message).__name__}")
    logger.debug(f"📨 Last message content preview: {str(last_message.content)[:100] if hasattr(last_message, 'content') and last_message.content else 'No content'}")

    tool_calls = getattr(last_message, 'tool_calls', None) or []
    if tool_calls:
        tool_names = [tc.get('name', 'unknown') for tc in tool_calls]
        logger.info(f"🔧 Tool calls found ({len(tool_calls)}): {tool_names}")
        logger.info("➡️ Routing to tools node")
        return "tools"

    logger.info("💬 No tool calls found, routing to END")
    return END


async def agent_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Single LLM call that can both call tools and generate responses."""
    writer = get_stream_writer()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not configured")
        if writer:
            writer({"type": "error", "content": "Configuration error occurred"})
        return state

    try:
        # Extract user and focus from config for dynamic tool loading
        configurable = config.get("configurable", {})
        user = configurable.get("user")
        focus = configurable.get("focus")
        protocol = configurable.get("protocol", "graph")

        logger.info(f"Agent node started - user: {user.username if user else 'none'}, focus: {focus}")

        # Dynamically load tools based on user/focus context
        tool_list = await tools.get_tools_for_request(user, focus, protocol)

        if not tool_list:
            logger.warning("No tools available for this context - agent will not be able to call any tools!")
        else:
            tool_names = [tool.name for tool in tool_list]
            logger.info(f"🎉 Agent ready with {len(tool_list)} tools: {tool_names}")


        # Check for tool results and emit UI events
        if state.get("messages"):
            # If there are tool results, emit UI events for successful operations
            tool_results = [msg for msg in state["messages"] if hasattr(msg, 'tool_call_id')]
            if tool_results:
                # Find the tool calls that led to these results
                tool_calls = []
                for msg in reversed(state["messages"]):
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tool_calls = msg.tool_calls
                        break

                if tool_calls and writer:
                    user_id = state.get("user_id", "unknown")
                    # Emit UI events directly for each successful tool result
                    for result_msg in tool_results:
                        if not hasattr(result_msg, 'tool_call_id'):
                            continue

                        tool_call_id = result_msg.tool_call_id
                        tool_call = next((tc for tc in tool_calls if tc.get("id") == tool_call_id), None)

                        if not tool_call:
                            continue

                        tool_name = tool_call.get("name", "unknown")
                        result_content = getattr(result_msg, 'content', '')

                        # Emit UI events for tools that have event configuration
                        config = get_tool_event_config(tool_name)
                        if config:
                            try:
                                # Create and emit the UI event
                                ui_event = create_ui_event(tool_name, tool_call, result_content, user_id)
                                writer(ui_event)
                                logger.info(f"📡 Emitted UI event for {tool_name}")
                            except Exception as e:
                                logger.error(f"❌ Failed to emit UI event for {tool_name}: {e}")


        # Check if agent has tools available
        if not tool_list:
            logger.warning("⚠️ Agent node executing without tools - agent cannot call any functions!")

        # -----------------------------------------------
        # Semantic Voice Generation
        await voice.run_semantic_voice(writer, state)
        # -----------------------------------------------

        # Single LLM call with tools bound - can call tools OR generate response
        logger.info(f"🧠 Creating LLM with {len(tool_list)} tools bound")


        # Log context
        logger.debug(f"Messages being sent to LLM: {len(state.get('messages', []))} messages")


        # Check for tool call loops to prevent infinite recursion
        tool_call_count = state.get("tool_call_count", 0)
        if tool_call_count > 5:  # Allow up to 5 tool calls per conversation
            logger.warning(f"Tool call limit reached ({tool_call_count}), forcing final response")
            # Force a final response instead of more tool calls
            final_response = AIMessage(content="I've reached the maximum number of tool calls. Let me provide a summary based on what I've found so far.")
            logger.info("Agent response completed (tool limit reached)")
            return {
                "messages": [final_response],
                "writer": writer,
                "voice_messages": state.get("voice_messages", []),
                "last_voice_sig": state.get("last_voice_sig"),
                "tool_call_count": tool_call_count
            }

        # PIPELINE ARCHITECTURE: Industry Standard Approach
        # Phase 1: Tool Detection (Non-streaming, reliable)
        logger.info("🔍 Phase 1: Tool Detection Agent")
        tool_detector = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,  # Low temperature for consistent tool detection
            api_key=api_key,
            streaming=False,  # Non-streaming for reliability
        ).bind_tools(tool_list)

        tool_response = await tool_detector.ainvoke(state["messages"])

        # Phase 2: Tool Execution (if needed)
        if hasattr(tool_response, 'tool_calls') and tool_response.tool_calls:
            logger.info(f"🔧 Phase 2: Tool Execution - {len(tool_response.tool_calls)} tools detected")

            # Inject user context into tool calls
            user_id = state.get("user_id")
            tools.inject_user_id_into_calls(tool_response.tool_calls, user_id)

            # Log tool calls
            for i, tc in enumerate(tool_response.tool_calls):
                tool_name = tc.get("name", "unknown")
                tool_args = tc.get("args", tc.get("arguments", {}))
                logger.info(f"Tool call {i+1}: {tool_name} with args: {tool_args}")

            # Voice message for tool execution
            tool_names = [tc.get("name", "unknown") for tc in tool_response.tool_calls]
            if writer:
                writer({"type": "tool", "content": f"🔧 Calling tools: {', '.join(tool_names)}"})

            return {
                "messages": state["messages"] + [tool_response],  # Preserve full conversation history
                "writer": writer,  # Pass writer to tools node
                "tools_done": False,  # Allow tool execution
                "tool_call_count": tool_call_count + 1
            }

        # Phase 3: Response Generation (streaming)
        logger.info("💬 Phase 3: Response Generation Agent (streaming)")

        response_generator = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,  # Normal temperature for creative responses
            api_key=api_key,
            streaming=True,  # Streaming for UX
        )

        # Stream the response
        response_chunks = []
        async for chunk in response_generator.astream(state["messages"]):
            response_chunks.append(chunk)

            # Stream content to UI
            if chunk.content and writer:
                writer({"type": "message", "content": chunk.content})

        # Create final response
        final_content = "".join([c.content for c in response_chunks if c.content])
        final_response = AIMessage(content=final_content)

        logger.info("✅ Pipeline completed successfully")

        # Handle thread operations asynchronously (like voice)
        thread_id = configurable.get("thread_id")
        if thread_id and writer:
            # Create async task for thread operations
            async def _thread_operations_task():
                try:
                    logger.info(f"🧵 [THREAD OPS] Starting async thread operations for {thread_id}")

                    # Emit thread update event
                    from .mapper import create_thread_ui_event
                    message_count = len(state.get("messages", [])) + 1  # +1 for the new response
                    ui_event = create_thread_ui_event("updated", thread_id, {"message_count": message_count})
                    writer(ui_event)
                    logger.info(f"🔄 [THREAD OPS] Emitted thread update event for {thread_id} (messages: {message_count})")

                    # Check for title generation (async background task)
                    if message_count >= 3:  # Same criteria as before
                        async def _title_generation_task():
                            try:
                                from apps.threads.services import generate_thread_title_with_llm, update_thread_title

                                title = await generate_thread_title_with_llm(thread_id)
                                if title:
                                    success = await update_thread_title(thread_id, title)
                                    if success:
                                        # Emit title update event
                                        title_event = create_thread_ui_event("title_updated", thread_id, {"subject": title})
                                        writer(title_event)
                                        logger.info(f"🎯 [THREAD OPS] Generated and emitted title: '{title}' for thread {thread_id}")
                                    else:
                                        logger.warning(f"❌ [THREAD OPS] Failed to update title for thread {thread_id}")
                                else:
                                    logger.warning(f"❌ [THREAD OPS] LLM failed to generate title for thread {thread_id}")
                            except Exception as e:
                                logger.error(f"Error in title generation task: {e}")

                        # Run title generation as separate async task
                        import asyncio
                        asyncio.create_task(_title_generation_task())

                except Exception as e:
                    logger.error(f"Error in thread operations task: {e}")

            # Run thread operations as background task (non-blocking)
            import asyncio
            asyncio.create_task(_thread_operations_task())

        # -----------------------------------------------
        # Ambient Memory Store (async background)
        # -----------------------------------------------
        try:
            user_id = state.get("user_id")
            logger.info(f"🧠 Memory storage: checking user_id={user_id}")
            if user_id:
                # Snapshot last human message for classification
                last_user_text = ""
                for _m in reversed(state.get("messages", [])):
                    if isinstance(_m, HumanMessage) and _m.content:
                        last_user_text = _m.content
                        break

                logger.info(f"🧠 Memory storage: found user text='{last_user_text[:50]}...', scheduling async task")
                if last_user_text:
                    await memory.schedule_memory_storage(user_id, last_user_text, writer)
        except Exception as e:
            logger.error(f"Scheduling memory store task failed: {e}")

        return {
            "messages": state["messages"] + [final_response],  # Preserve full conversation history
            "writer": writer,
            "voice_messages": state.get("voice_messages", []),
            "last_voice_sig": state.get("last_voice_sig"),
            "tool_call_count": tool_call_count
        }

    except Exception as e:
        logger.error(f"Agent node failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        if writer:
            writer({"type": "system", "content": "Error occurred during processing"})
        return state


async def create_agent(client: str = 'talentco', role: str = 'admin', protocol: str = 'graph', user=None, focus=None):
    """Create and return the simple ReAct agent with context-appropriate tools.

    Args:
        client: Client name (legacy parameter)
        role: Role name (legacy parameter)
        protocol: Protocol type ('graph', 'mcp', 'a2a')
        user: Django User object (preferred for authenticated sessions)
        focus: Current user focus ('candidate', 'employer', 'admin') - overrides group logic
    """
    logger.info(f"🎯 Creating agent with params: client={client}, role={role}, protocol={protocol}, user={user.username if user else None}, focus={focus}")
    logger.info("🔧 Agent will load tools dynamically based on user/focus context")

    # Delegate to unified workflow builder
    from .workflow import create_agent as create_agent_from_workflow
    return await create_agent_from_workflow()


# Keep the existing API functions for compatibility
async def ainvoke_agent(message: str, messages: Optional[List[BaseMessage]] = None, agent=None, user=None, focus=None):
    """Async invoke the agent with a message."""
    if agent is None:
        agent = await create_agent(user=user, focus=focus)

    # Use provided messages or create new message list
    if messages:
        state_messages = messages + [HumanMessage(content=message)]
    else:
        state_messages = [HumanMessage(content=message)]

    state = {
        "messages": state_messages,
        "user_id": None
    }

    result = await agent.ainvoke(state)
    return result


async def ainvoke_agent_sync(message: str, messages: Optional[List[BaseMessage]] = None):
    """Synchronous version of agent for thread API - returns complete response."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not configured")

    # Use provided messages or create new message list
    if messages:
        state_messages = messages + [HumanMessage(content=message)]
    else:
        state_messages = [HumanMessage(content=message)]

    # Add system message if not present
    if not state_messages or not isinstance(state_messages[0], SystemMessage):
        system_prompt = prompt.get_system_prompt()
        system_message = SystemMessage(content=system_prompt)
        state_messages = [system_message] + state_messages

    # Create a synchronous LLM for complete responses
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=1,
        api_key=api_key,
        streaming=False,  # No streaming for complete responses
    )

    # Get the complete response
    response = await llm.ainvoke(state_messages)

    # Return in the same format as the graph agent
    return {
        "messages": [response],
        "user_id": None,
        "tools_done": True,
        "voice_messages": [],
        "last_voice_sig": None
    }


async def astream_agent(message: str, agent=None, user=None, focus=None):
    """Async stream the agent response."""
    if agent is None:
        agent = await create_agent(user=user, focus=focus)
    
    state = {
        "messages": [HumanMessage(content=message)],
        "user_id": None
    }
    
    async for chunk in agent.astream(state, stream_mode="updates"):
        yield chunk


async def astream_agent_tokens(message: str, messages: Optional[List[BaseMessage]] = None, agent=None, user=None, focus=None, thread_id: Optional[str] = None):
    """Stream agent tokens - unified writer() approach."""
    logger.info(f"🚀 astream_agent_tokens called with: message='{message[:50]}...', messages_count={len(messages) if messages else 0}, agent_provided={agent is not None}, user={user.username if user else None}, focus={focus}, thread_id={thread_id}")

    if agent is None:
        logger.info("🏗️ Creating new agent...")
        agent = await create_agent(user=user, focus=focus)
        logger.info("✅ Agent created (tools verified during creation)")
    else:
        logger.info("♻️ Using provided agent")

    # With checkpointer, we only need the new message - checkpointer loads history
    logger.info("📝 Creating minimal state with new message (checkpointer handles history)")
    state_messages = [HumanMessage(content=message)]

    logger.info("📤 State has 1 new message (checkpointer will load conversation history)")

    user_id_value = str(user.id) if user else None
    state = {
        "messages": state_messages,
        "user_id": user_id_value,
        "user": user,  # Pass user object for memory operations
        "tool_call_count": 0  # Initialize tool call counter
    }
    logger.info(f"📝 Created initial state with user_id={user_id_value}, user={user.username if user else None}")

    # Config for checkpointer with thread_id and user/focus for dynamic tool loading
    config = {
        "configurable": {
            "thread_id": thread_id or "default",
            "user_id": user.id if user else None,
            "user": user,  # Pass user object for dynamic tool loading
            "focus": focus,  # Pass focus for dynamic tool loading
            "protocol": "graph"  # Default protocol
        }
    }

    # Always run context_preparation_node first to retrieve memories and enhance prompt
    logger.info("🧠 Running context_preparation_node first")
    try:
        prepared_state = await context_preparation_node(state)
        state = prepared_state
        logger.info("🧠 Context preparation completed")
    except Exception as e:
        logger.error(f"🧠 Context preparation failed: {e}")

    # Only use custom stream mode - everything flows through writer()
    async for chunk in agent.astream(state, config=config, stream_mode="custom"):
        if isinstance(chunk, dict) and "type" in chunk:
            yield chunk

    # Signal end of stream
    yield {
        "type": "done",
        "content": ""
    }
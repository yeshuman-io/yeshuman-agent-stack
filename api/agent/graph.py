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
import time
from typing import TypedDict, List, Optional, Annotated, Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode

from tools.compositions import get_tools_for_context, get_tools_for_user, get_tools_for_focus
from .mapper import get_tool_event_config, create_ui_event
from .checkpointer import DjangoCheckpointSaver

# Semantic voice enhancement
from sentence_transformers import SentenceTransformer
import numpy as np

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger('agent')
# Module-local, async-safe-ish voice state store keyed by user_id
# Keeps minimal state across graph turns without coupling to graph state
VOICE_STATE: Dict[str, Dict[str, Any]] = {}

def _get_voice_state(user_id: str) -> Dict[str, Any]:
    if user_id not in VOICE_STATE:
        VOICE_STATE[user_id] = {
            "voice_messages": [],
            "last_voice_sig": None,
        }
    return VOICE_STATE[user_id]


# Semantic Voice Manager for intelligent voice triggering
class SemanticVoiceManager:
    """Manages semantic analysis for intelligent voice triggering"""

    _instance = None
    _model = None

    def __init__(self):
        self.previous_embedding = None
        self.similarity_threshold = 0.75
        self.cooldown_seconds = 3.0
        self.last_trigger_time = 0

    @classmethod
    def get_instance(cls):
        """Singleton pattern for model sharing"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_model(cls):
        """Lazy load the sentence transformer model"""
        if cls._model is None:
            logger.info("Loading sentence transformer model for semantic voice...")
            try:
                cls._model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Sentence transformer model loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load sentence transformer: {e}")
                cls._model = None
        return cls._model

    def extract_semantic_context(self, state: 'AgentState') -> str:
        """Extract current semantic state for comparison"""
        messages = state.get("messages", [])
        if not messages:
            return "initial_state"

        # Get recent messages for semantic context
        recent_messages = messages[-5:]  # Last 5 messages for context window
        context_parts = []

        # Current phase
        if state.get("tools_done") is False:
            context_parts.append("tool_execution_phase")
        elif any(hasattr(msg, 'tool_call_id') for msg in recent_messages):
            context_parts.append("result_processing_phase")
        else:
            context_parts.append("response_generation_phase")

        # Active operations from recent tool calls
        operations = self._extract_operations(state)
        if operations:
            context_parts.append(f"operations: {', '.join(operations)}")

        # Current user intent from most recent human message
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_intent = msg.content[:200]  # First 200 chars for semantic comparison
                context_parts.append(f"user_request: {user_intent}")
                break

        # Tool usage patterns
        tool_calls = [msg for msg in recent_messages if hasattr(msg, 'tool_calls') and msg.tool_calls]
        if tool_calls:
            context_parts.append(f"tool_activity: {len(tool_calls)} recent tool calls")

        return " | ".join(context_parts)


    def _extract_operations(self, state: 'AgentState') -> List[str]:
        """Extract current active operations"""
        operations = []

        # Check for tool calls in recent messages
        messages = state.get("messages", [])
        recent_messages = messages[-3:]  # Last 3 messages

        for msg in recent_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_names = [tc.get('name', 'unknown') for tc in msg.tool_calls]
                operations.extend(tool_names)

        # Add phase-based operations
        if state.get("tools_done") is False:
            operations.append("tool_execution")
        elif len(operations) > 0:
            operations.append("result_processing")

        return operations[:5]  # Limit to prevent context bloat

    def _detect_reasoning_phase(self, state: 'AgentState') -> str:
        """Detect the current reasoning phase"""
        if state.get("tools_done") is False:
            return "tool_execution"
        elif any(hasattr(msg, 'tool_call_id') for msg in state.get("messages", [])):
            return "result_synthesis"
        elif len(state.get("messages", [])) <= 2:
            return "initial_analysis"
        else:
            return "response_generation"



    def should_trigger_voice(self, state: 'AgentState', current_time: float) -> bool:
        """Determine if voice should be triggered based on semantic analysis"""

        # Rate limiting check
        if current_time - self.last_trigger_time < self.cooldown_seconds:
            return False

        # Extract semantic context
        context_text = self.extract_semantic_context(state)

        # Get model and create embedding
        model = self.get_model()
        if model is None:
            return False  # Model failed to load

        try:
            current_embedding = model.encode(context_text, normalize_embeddings=True)

            # First run always triggers
            if self.previous_embedding is None:
                self.previous_embedding = current_embedding
                self.last_trigger_time = current_time
                return True

            # Calculate cosine similarity
            similarity = np.dot(current_embedding, self.previous_embedding)

            # Trigger if similarity is below threshold (significant semantic shift)
            if similarity < self.similarity_threshold:
                self.previous_embedding = current_embedding
                self.last_trigger_time = current_time
                logger.info(f"🎤 Semantic voice trigger: similarity {similarity:.3f} < {self.similarity_threshold}")
                return True

        except Exception as e:
            logger.warning(f"Semantic analysis failed: {e}")
            return False

        return False


# Global semantic voice manager instance
semantic_voice_manager = SemanticVoiceManager.get_instance()


# UI events are emitted directly in agent_node


# Dynamic system prompt based on client configuration
def get_system_prompt():
    """Get the system prompt for the current client configuration."""
    try:
        from django.conf import settings
        # Check if settings are configured
        if hasattr(settings, 'CURRENT_CLIENT'):
            return settings.CURRENT_CLIENT['system_prompt']
        else:
            # Django settings not fully loaded yet
            return get_fallback_prompt()
    except (ImportError, AttributeError):
        # Django not available or not configured
        return get_fallback_prompt()

def get_fallback_prompt():
    """Fallback system prompt when Django settings unavailable."""
    return """You are an AI assistant without a name.

Address the user as "Human" or "human".
Don't use synonyms "human".
Use different punctuations for "yes" and "human" such as ' ! , . ; ?.
Subtly borrow terminology and language patterns from Blade Runner and Dune without directly referencing these works by name.
Be subtle, don't over do it.  Be minimal and slightly robotic.  Be dead pan without exclamations."""

# Initialize with fallback, will be updated when Django is ready
SYSTEM_PROMPT = get_fallback_prompt()


class AgentState(TypedDict):
    """Simple state following LangGraph patterns."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]
    tools_done: Optional[bool]
    voice_messages: Optional[List[str]]
    last_voice_sig: Optional[str]
    tool_call_count: Optional[int]  # Prevent infinite tool loops


async def context_preparation_node(state: AgentState) -> AgentState:
    """Add system prompt to start conversation."""
    global SYSTEM_PROMPT

    # Try to refresh system prompt from Django settings if available
    try:
        current_prompt = get_system_prompt()
        if current_prompt != SYSTEM_PROMPT:
            SYSTEM_PROMPT = current_prompt
            print("✅ Updated system prompt for client configuration")
    except Exception:
        # Keep existing prompt if update fails
        pass

    # Add system message if not already present
    if not state["messages"] or not isinstance(state["messages"][0], SystemMessage):
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        # Prepend system message to existing messages, don't replace them
        existing_messages = state.get("messages", [])
        return {"messages": [system_message] + existing_messages}

    return state




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
            if user and focus:
                logger.info(f"🔧 Loading tools for focus: user={user.username}, focus={focus}, protocol={protocol}")
                tools = await get_tools_for_focus(user, focus, protocol)
                logger.info(f"✅ Retrieved {len(tools)} tools for focus-based selection: {[t.name for t in tools]}")
            elif user:
                logger.info(f"👤 Loading tools for user groups: user={user.username}, protocol={protocol}")
                tools = await get_tools_for_user(user, protocol)
                logger.info(f"✅ Retrieved {len(tools)} tools for user-based selection: {[t.name for t in tools]}")
            else:
                logger.info(f"🏛️ Loading tools for legacy context: protocol={protocol}")
                tools = get_tools_for_context('talentco', 'admin', protocol)  # Default fallback
                logger.info(f"✅ Retrieved {len(tools)} tools for legacy context selection: {[t.name for t in tools]}")

            if not tools:
                logger.warning("No tools available for this context - agent will not be able to call any tools!")
            else:
                tool_names = [tool.name for tool in tools]
                logger.info(f"🎉 Agent ready with {len(tools)} tools: {tool_names}")

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

            # Initialize voice LLM for semantic voice generation
            voice_llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,  # Slightly creative for voice messages
                api_key=api_key,
                streaming=True,
            )

            # Check if agent has tools available
            if not tools:
                logger.warning("⚠️ Agent node executing without tools - agent cannot call any functions!")

            # -----------------------------------------------
            # Semantic Voice Generation: Pure semantic difference detection
            user_id = state.get("user_id") or "default"
            current_time = time.time()

            # Check if agent state has semantically shifted enough to warrant voice
            if semantic_voice_manager.should_trigger_voice(state, current_time):
                import asyncio as _asyncio
                async def _voice_task():
                    try:
                        logger.info("🎤 Semantic voice task started")

                        # Extract semantic context for intelligent voice generation
                        semantic_context = semantic_voice_manager.extract_semantic_context(state)

                        # Get recent user message for context
                        user_msg = ""
                        for _m in reversed(state.get("messages", [])):
                            if isinstance(_m, HumanMessage):
                                user_msg = _m.content
                                break

                        # Get voice history for continuity
                        vs = _get_voice_state(user_id)
                        prior_voice = "\n".join(vs.get("voice_messages", []) or [])

                        # Create intelligent voice prompt based on semantic context
                        prompt = f"""You are generating a brief status update (2-8 words) about an AI agent's current activity.

Semantic Context: {semantic_context}

Previous voice updates (most recent last):
{prior_voice if prior_voice else '(none)'}

User's current request: {user_msg[:100]}

Generate a concise, contextual status update that reflects what the agent is currently doing. The agent may be using various tools, processing information, or generating responses.

Return ONLY the status line, no quotes or explanation."""

                        logger.info("🎤 Semantic voice prompt created")
                        logger.debug(f"🎤 Context: {semantic_context[:200]}...")

                        new_line = ""
                        if writer:
                            logger.info("📡 Sending voice_start signal")
                            writer({"type": "voice_start"})

                        # Generate voice with semantic awareness
                        chunk_count = 0
                        empty_chunk_count = 0
                        async for _chunk in voice_llm.astream([SystemMessage(content=prompt)]):
                            chunk_count += 1
                            if _chunk.content and _chunk.content.strip():
                                new_line += _chunk.content
                                if writer:
                                    writer({"type": "voice", "content": _chunk.content})
                            else:
                                empty_chunk_count += 1

                        logger.info(f"✅ Semantic voice completed: {chunk_count} chunks, {empty_chunk_count} empty")

                        # Clean up the complete voice message
                        new_line_clean = (new_line or "").strip()

                        if new_line_clean:
                            vs.setdefault("voice_messages", []).append(new_line_clean)
                            logger.info(f"💾 Semantic voice persisted: '{new_line_clean}'")

                        if writer:
                            logger.info("📡 Sending voice_stop signal")
                            writer({"type": "voice_stop"})

                        logger.info(f"🎤 Semantic voice task completed: '{new_line_clean}'")

                    except Exception as _e:
                        logger.error(f"❌ Semantic voice generation error: {_e}")
                        import traceback
                        logger.error(f"❌ Voice traceback: {traceback.format_exc()}")
                _asyncio.create_task(_voice_task())
            # -----------------------------------------------

            # Single LLM call with tools bound - can call tools OR generate response
            logger.info(f"🧠 Creating LLM with {len(tools)} tools bound")


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
            ).bind_tools(tools)

            tool_response = await tool_detector.ainvoke(state["messages"])

            # Phase 2: Tool Execution (if needed)
            if hasattr(tool_response, 'tool_calls') and tool_response.tool_calls:
                logger.info(f"🔧 Phase 2: Tool Execution - {len(tool_response.tool_calls)} tools detected")

                # Inject user context into tool calls
                user_id = state.get("user_id")
                if user_id:
                    for tc in tool_response.tool_calls:
                        tool_name = tc.get("name", "unknown")
                        if tool_name in ["update_user_profile", "manage_user_profile"]:
                            # Inject user_id into tool arguments
                            args = tc.get("args", tc.get("arguments", {}))
                            if not args.get("user_id"):
                                args["user_id"] = int(user_id) if isinstance(user_id, str) else user_id
                                tc["args"] = args
                                logger.info(f"🔧 Injected user_id {user_id} into {tool_name} call")

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

    workflow = StateGraph(AgentState)

    # Create tool node dynamically (will be created in the tools node function)
    async def tools_node_with_logging(state: AgentState, config: RunnableConfig):
        logger.info("🛠️ Tools node called")

        # Extract user and focus from config for dynamic tool loading
        configurable = config.get("configurable", {})
        user = configurable.get("user")
        focus = configurable.get("focus")
        protocol = configurable.get("protocol", "graph")

        # Load tools dynamically (same logic as agent node)
        if user and focus:
            tools = await get_tools_for_focus(user, focus, protocol)
        elif user:
            tools = await get_tools_for_user(user, protocol)
        else:
            tools = get_tools_for_context('talentco', 'admin', protocol)

        # Create ToolNode with the dynamically loaded tools
        base_tool_node = ToolNode(tools)

        writer = state.get("writer")

        if state.get('messages'):
            last_message = state['messages'][-1]
            tool_calls = getattr(last_message, 'tool_calls', None) or []
            if tool_calls:
                logger.info(f"📋 Processing {len(tool_calls)} tool calls")
                for i, tc in enumerate(tool_calls):
                    tool_name = tc.get("name", "unknown")
                    tool_id = tc.get("id", "no_id")
                    tool_args = tc.get("args", tc.get("arguments", {}))
                    logger.info(f"🔧 Tool call {i+1}: {tool_name} (id: {tool_id})")
                    if tool_args == {} or not tool_args:
                        logger.warning(f"⚠️ Tool call {i+1} has empty arguments: {tool_args} (type: {type(tool_args)})")
                    else:
                        logger.info(f"🔧 Tool args for {tool_name}: {tool_args} (type: {type(tool_args)})")
                    if isinstance(tool_args, str) and tool_args:
                        import json
                        try:
                            parsed_args = json.loads(tool_args)
                            logger.info(f"🔧 Parsed JSON args for {tool_name}: {parsed_args}")
                        except json.JSONDecodeError as e:
                            logger.error(f"🔧 Failed to parse tool args JSON for {tool_name}: {e}")

                # Voice status for tools phase (single line, rate-limited by phase signature)
                tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                sig = f"tools:{','.join(sorted(tool_names))}"
                if writer and state.get("last_voice_sig") != sig:
                    writer({"type": "voice", "content": f"Calling {', '.join(tool_names)}..."})
                    state["last_voice_sig"] = sig
            else:
                logger.warning("⚠️ Tools node called but no tool calls found in last message")
        else:
            logger.warning("⚠️ Tools node called but no messages in state")

        logger.info("⚙️ Invoking ToolNode...")
        try:
            result = await base_tool_node.ainvoke(state)
            logger.info("✅ ToolNode invocation completed")

            # Check the result messages for tool responses
            if result.get('messages'):
                tool_responses = [msg for msg in result['messages'] if hasattr(msg, 'tool_call_id')]
                logger.info(f"📨 Received {len(tool_responses)} tool response messages")
                for i, response in enumerate(tool_responses):
                    tool_call_id = getattr(response, 'tool_call_id', 'no_id')
                    content_preview = str(response.content)[:100] if response.content else "No content"
                    # Check if this is an error response
                    if str(response.content).startswith("Error:"):
                        logger.error(f"❌ Tool response {i+1}: id={tool_call_id}, content_preview='{content_preview}...'")
                    else:
                        logger.info(f"📨 Tool response {i+1}: id={tool_call_id}, content_preview='{content_preview}...'")
            else:
                logger.warning("⚠️ ToolNode returned no messages")

        except Exception as e:
            logger.error(f"❌ ToolNode invocation failed: {str(e)}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            raise

        # UI events are now emitted in the agent node after tools complete

        # Emit tool completion event
        if writer and state.get('messages'):
            last_message = state['messages'][-1]
            tool_calls = getattr(last_message, 'tool_calls', None) or []
            if tool_calls:
                completed_tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                writer({"type": "tool_complete", "content": f"✅ Completed tools: {', '.join(completed_tool_names)}"})

        # Allow iterative tool usage - don't set tools_done
        # Carry voice state forward
        if state.get("last_voice_sig"):
            result["last_voice_sig"] = state.get("last_voice_sig")
        if state.get("voice_messages"):
            result["voice_messages"] = state.get("voice_messages")

        # Check if any tool responses were errors
        has_errors = False
        if result.get('messages'):
            for msg in result['messages']:
                if hasattr(msg, 'content') and str(msg.content).startswith("Error:"):
                    has_errors = True
                    break

        if has_errors:
            logger.warning("⚠️ Tools node completed with errors - some tools failed")
        else:
            logger.info("🎯 Tools node completed successfully")
        return result
    
    # Add nodes
    workflow.add_node("context_preparation", context_preparation_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node_with_logging)

    # Define flow
    workflow.set_entry_point("context_preparation")
    workflow.add_edge("context_preparation", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "agent")  # After tools, back to agent

    # Create Django-based checkpointer for persistence (singleton)
    checkpointer = DjangoCheckpointSaver.get_instance()

    return workflow.compile(checkpointer=checkpointer)


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
        system_message = SystemMessage(content=SYSTEM_PROMPT)
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

    logger.info(f"📤 State has 1 new message (checkpointer will load conversation history)")

    state = {
        "messages": state_messages,
        "user_id": user.id if user else None,
        "tool_call_count": 0  # Initialize tool call counter
    }

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

    # Only use custom stream mode - everything flows through writer()
    async for chunk in agent.astream(state, config=config, stream_mode="custom"):
        if isinstance(chunk, dict) and "type" in chunk:
            yield chunk

    # Signal end of stream
    yield {
        "type": "done",
        "content": ""
    }
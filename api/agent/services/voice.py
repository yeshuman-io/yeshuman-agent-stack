"""
Voice services for the agent.

Handles semantic voice generation and management.
"""

import os
import time
import logging
from typing import Dict, Any, List
import asyncio
from sentence_transformers import SentenceTransformer
import numpy as np
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

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

    def extract_semantic_context(self, state) -> str:
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

    def _extract_operations(self, state) -> List[str]:
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

    def _detect_reasoning_phase(self, state) -> str:
        """Detect the current reasoning phase"""
        if state.get("tools_done") is False:
            return "tool_execution"
        elif any(hasattr(msg, 'tool_call_id') for msg in state.get("messages", [])):
            return "result_synthesis"
        elif len(state.get("messages", [])) <= 2:
            return "initial_analysis"
        else:
            return "response_generation"

    def should_trigger_voice(self, state, current_time: float) -> bool:
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


async def run_semantic_voice(writer, state) -> None:
    """
    Run semantic voice generation if conditions are met.

    Args:
        writer: Stream writer function
        state: Agent state dict
    """
    user_id = state.get("user_id") or "default"
    current_time = time.time()

    # Check if agent state has semantically shifted enough to warrant voice
    if semantic_voice_manager.should_trigger_voice(state, current_time):
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
                api_key = os.getenv("OPENAI_API_KEY")
                voice_llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.3,  # Slightly creative for voice messages
                    api_key=api_key,
                    streaming=True,
                )

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

        asyncio.create_task(_voice_task())

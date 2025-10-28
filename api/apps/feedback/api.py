"""
Feedback API for LangSmith integration.
Handles both explicit UI feedback and agent-inferred feedback.
"""
import os
import logging
import time
from typing import Optional, List
from ninja import Router, Schema
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

feedback_router = Router()

# Simple in-memory rate limiting (production: use Redis)
_rate_limits = {}


class FeedbackRequest(BaseModel):
    run_id: str
    score: Optional[float] = None
    tags: Optional[List[str]] = None
    comment: Optional[str] = None


class FeedbackResponse(Schema):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


@feedback_router.post("/", response=FeedbackResponse)
async def submit_feedback(request, payload: FeedbackRequest):
    """Submit user feedback on agent responses to LangSmith."""
    try:
        # Get user from request (optional)
        user = getattr(request, 'auth', None)
        user_id = str(user.id) if user and hasattr(user, 'id') else None
        
        # Get environment config
        ls_endpoint = os.getenv("LANGSMITH_ENDPOINT", "default")
        ls_project = os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT", "unset")
        
        # Entry log
        logger.info(
            f"[FB] IN: user_id={user_id} run_id={payload.run_id} "
            f"score={payload.score} tags_count={len(payload.tags) if payload.tags else 0} "
            f"comment_len={len(payload.comment) if payload.comment else 0} "
            f"endpoint={ls_endpoint} project_env={ls_project}"
        )
        
        # Validate run_id format
        import re
        if not re.match(r'^[a-f0-9\-]{36}$', payload.run_id) and not payload.run_id.startswith('run-'):
            logger.warning(f"[FB] INVALID: run_id format: {payload.run_id}")
            return FeedbackResponse(success=False, error="Invalid run_id format")
        
        # Validate score range
        if payload.score is not None and not (0.0 <= payload.score <= 1.0):
            logger.warning(f"[FB] INVALID: score out of range: {payload.score}")
            return FeedbackResponse(success=False, error="Score must be between 0.0 and 1.0")
        
        # Validate comment length
        if payload.comment and len(payload.comment) > 1000:
            logger.warning("[FB] INVALID: comment too long")
            return FeedbackResponse(success=False, error="Comment too long (max 1000 chars)")
        
        # Validate tags
        if payload.tags:
            allowed_tags = {
                'Helpful', 'Clear', 'Grounded', 'Actionable', 'Respectful',
                'Incorrect', 'Off-topic', 'Unhelpful', 'Hallucinated', 'Unsafe'
            }
            invalid_tags = set(payload.tags) - allowed_tags
            if invalid_tags:
                logger.warning(f"[FB] INVALID: invalid tags: {invalid_tags}")
                return FeedbackResponse(success=False, error=f"Invalid tags: {', '.join(invalid_tags)}")
        
        # Rate limiting
        rate_limit_key = f"feedback_{payload.run_id}_{user_id or 'anon'}"
        current_time = time.time()
        last_submit = _rate_limits.get(rate_limit_key, 0)
        if current_time - last_submit < 3600:  # 1 hour
            logger.warning(f"[FB] RATE_LIMIT: key={rate_limit_key}")
            return FeedbackResponse(success=False, error="Rate limited: one feedback per run per hour")
        _rate_limits[rate_limit_key] = current_time
        
        # Forward to LangSmith
        try:
            from langsmith import Client
            ls_client = Client()
            
            logger.info(f"[FB] LS CALL: project_env={ls_project} run_id={payload.run_id}")
            
            # Build feedback source (must be 'api' or 'model')
            feedback_source = "api"
            
            # Build combined comment with tags and user info
            full_comment = payload.comment or ""
            if payload.tags:
                tags_str = ", ".join(payload.tags)
                full_comment = f"{full_comment}\nTags: {tags_str}".strip()
            
            # Add user info to comment
            user_info = f"user_id={user_id}" if user_id else "anonymous"
            full_comment = f"[{user_info}] {full_comment}".strip()
            
            # Submit feedback (single call with all info)
            if payload.score is not None or payload.comment or payload.tags:
                ls_client.create_feedback(
                    run_id=payload.run_id,
                    key="user_feedback",
                    score=payload.score,
                    comment=full_comment,
                    feedback_source_type=feedback_source
                )
                logger.info(f"[FB] LS OK: created feedback score={payload.score} tags={payload.tags} comment_len={len(payload.comment or '')}")
            
            # Verify the run exists (proof of attachment)
            try:
                run = ls_client.read_run(payload.run_id)
                run_name = getattr(run, 'name', 'unknown')
                logger.info(f"[FB] LS OK: run verified name={run_name} project={ls_project}")
            except Exception as e:
                logger.warning(f"[FB] LS WARN: read_run failed (project mismatch?): {e}")
            
            logger.info(f"[FB] OK: submitted feedback run_id={payload.run_id} user_id={user_id}")
            return FeedbackResponse(success=True, message="Feedback submitted successfully")
            
        except Exception as e:
            logger.error(f"[FB] LS ERROR: {e}")
            import traceback
            logger.error(f"[FB] LS ERROR traceback: {traceback.format_exc()}")
            return FeedbackResponse(success=False, error=f"Failed to submit feedback: {str(e)}")
    
    except Exception as e:
        logger.error(f"[FB] ERROR: {e}")
        import traceback
        logger.error(f"[FB] ERROR traceback: {traceback.format_exc()}")
        return FeedbackResponse(success=False, error="Internal server error")


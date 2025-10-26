"""
Custom Mem0 storage backend using Django models with PostgreSQL + pgvector.
"""
import uuid
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import Memory, MemorySearch
from openai import OpenAI
import numpy as np

# Optional LangSmith tracing
try:
    from langsmith.run_helpers import traceable
except Exception:  # pragma: no cover
    def traceable(*args, **kwargs):  # type: ignore
        def _decorator(fn):
            return fn
        return _decorator

# Set up logger for memory operations
logger = logging.getLogger('apps.memories')


class DjangoMemoryBackend:
    """
    Custom Mem0 storage backend using Django models.
    Async-first implementation for LangGraph integration.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.openai_client = OpenAI()
        logger.info("Initialized DjangoMemoryBackend with config: %s", self.config)
        # Simple per-user LRU of recent hashes to limit duplicates
        self._recent_hashes: Dict[str, List[str]] = {}
        
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI's text-embedding-3-small"""
        start_time = time.time()
        
        # Validate input
        if not text or not isinstance(text, str):
            logger.warning("Invalid text input for embedding: %s (type: %s)", text, type(text))
            return None
            
        # Clean and validate text
        text = text.strip()
        if not text:
            logger.warning("Empty text after stripping whitespace")
            return None
            
        logger.debug("Generating embedding for text: %s", text[:100] + "..." if len(text) > 100 else text)
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = response.data[0].embedding
            duration = time.time() - start_time
            logger.info("Generated embedding successfully in %.2fs (dimension: %d)", duration, len(embedding))
            return embedding
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Failed to generate embedding after %.2fs: %s", duration, str(e))
            logger.error("Text that caused error: %r", text)
            return None
    
    @traceable(name="mem.add", run_type="tool")
    async def add(self, messages: List[Dict], user_id: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Add a new memory to the Django backend.
        
        Args:
            messages: List of message dicts (we'll use the first one)
            user_id: User identifier
            metadata: Additional metadata for categorization
            
        Returns:
            Dict with memory_id and success status
        """
        return await sync_to_async(self._add_impl)(messages, user_id, metadata)
    
    def _add_impl(self, messages: List[Dict], user_id: str, metadata: Optional[Dict] = None) -> Dict:
        """Internal implementation of add method."""
        start_time = time.time()
        logger.info("Adding memory for user_id: %s", user_id)
        
        if not messages or not messages[0].get('content'):
            logger.warning("No content provided in messages for user_id: %s", user_id)
            return {"error": "No content provided"}
            
        content = messages[0]['content']
        
        # Validate content
        if not isinstance(content, str):
            logger.warning("Content is not a string for user_id: %s (type: %s)", user_id, type(content))
            return {"error": "Content must be a string"}
            
        content = content.strip()
        if not content:
            logger.warning("Empty content after stripping whitespace for user_id: %s", user_id)
            return {"error": "Content cannot be empty"}
            
        metadata = metadata or {}
        
        logger.debug("Memory content: %s", content[:200] + "..." if len(content) > 200 else content)
        logger.debug("Memory metadata: %s", metadata)
        
        try:
            with transaction.atomic():
                logger.debug("Starting memory creation transaction")
                
                # Generate embedding
                embedding = self._get_embedding(content)
                if embedding is None:
                    logger.error("Failed to generate embedding, aborting memory creation")
                    return {"error": "Failed to generate embedding"}
                
                # Create memory record
                memory = Memory.objects.create(
                    user_id=user_id,
                    content=content,
                    embedding=embedding,
                    memory_type=metadata.get('memory_type', 'factual'),
                    interaction_type=metadata.get('interaction_type', 'conversation'),
                    category=metadata.get('category', 'general'),
                    subcategory=metadata.get('subcategory', ''),
                    importance=metadata.get('importance', 'medium'),
                    session_id=metadata.get('session_id'),
                    source=metadata.get('source', 'mem0_client'),
                    requires_followup=metadata.get('requires_followup', False),
                    metadata=metadata
                )
                
                duration = time.time() - start_time
                logger.info("Memory created successfully (ID: %s) in %.2fs", memory.id, duration)
                
                return {
                    "memory_id": str(memory.id),
                    "message": "Memory added successfully"
                }
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Failed to add memory for user_id %s after %.2fs: %s", user_id, duration, str(e))
            return {"error": f"Failed to add memory: {e}"}
    
    @traceable(name="mem.search", run_type="retriever")
    async def search(self, query: str, user_id: str, limit: int = 5) -> Dict:
        """
        Search memories using vector similarity.
        
        Args:
            query: Search query text
            user_id: User identifier  
            limit: Maximum number of results
            
        Returns:
            Dict with results list
        """
        return await sync_to_async(self._search_impl)(query, user_id, limit)
    
    def _search_impl(self, query: str, user_id: str, limit: int = 5) -> Dict:
        """Internal implementation of search method."""
        start_time = time.time()
        logger.info("Searching memories for user_id: %s, query: %s, limit: %d", user_id, query[:100] if query else "(empty)", limit)
        
        # Validate query input
        if not query or not isinstance(query, str):
            logger.warning("Invalid query for search: %s (type: %s)", query, type(query))
            return {"results": [], "error": "Invalid or empty query"}
            
        query = query.strip()
        if not query:
            logger.warning("Empty query after stripping whitespace")
            return {"results": [], "error": "Empty query"}
        
        try:
            # Generate query embedding
            embedding_start = time.time()
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding for search")
                return {"results": [], "error": "Failed to generate query embedding"}
            
            embedding_duration = time.time() - embedding_start
            logger.debug("Query embedding generated in %.2fs", embedding_duration)
            
            # Track the search
            search_record = MemorySearch.objects.create(
                user_id=user_id,
                query=query,
                query_embedding=query_embedding,
                search_type='semantic'
            )
            logger.debug("Created search record (ID: %s)", search_record.id)
            
            # Convert to numpy array for distance calculation
            query_vector = np.array(query_embedding)
            
            # Get user memories with embeddings
            memory_query_start = time.time()
            memories = Memory.objects.filter(
                user_id=user_id,
                is_archived=False,
                embedding__isnull=False
            ).order_by('-created_at')
            
            memory_count = memories.count()
            memory_query_duration = time.time() - memory_query_start
            logger.debug("Retrieved %d memories in %.2fs", memory_count, memory_query_duration)
            
            # Calculate similarities
            similarity_start = time.time()
            results = []
            similarities_calculated = 0
            
            for memory in memories:
                if memory.embedding is not None and len(memory.embedding) > 0:
                    try:
                        memory_vector = np.array(memory.embedding)
                        
                        # Ensure vectors are same length
                        if len(query_vector) != len(memory_vector):
                            logger.debug("Skipping memory %s due to dimension mismatch (%d vs %d)", 
                                       memory.id, len(query_vector), len(memory_vector))
                            continue
                            
                        # Cosine similarity
                        dot_product = np.dot(query_vector, memory_vector)
                        query_norm = np.linalg.norm(query_vector)
                        memory_norm = np.linalg.norm(memory_vector)
                        
                        if query_norm == 0 or memory_norm == 0:
                            logger.debug("Skipping memory %s due to zero norm", memory.id)
                            continue
                            
                        similarity = dot_product / (query_norm * memory_norm)
                        similarities_calculated += 1
                        
                        # Include results with reasonable similarity (0.3+ for semantic relevance)
                        if similarity > 0.3:
                            results.append({
                                'memory_id': str(memory.id),
                                'memory': memory.content,
                                'metadata': {
                                    'category': memory.category,
                                    'subcategory': memory.subcategory,
                                    'memory_type': memory.memory_type,
                                    'importance': memory.importance,
                                    'created_at': memory.created_at.isoformat(),
                                    'similarity': float(similarity),
                                    **memory.metadata
                                }
                            })
                            logger.debug("Found relevant memory (ID: %s, similarity: %.3f): %s", 
                                       memory.id, similarity, memory.content[:100])
                    except Exception as e:
                        logger.warning("Error calculating similarity for memory %s: %s", memory.id, str(e))
                        continue
            
            similarity_duration = time.time() - similarity_start
            logger.debug("Calculated %d similarities in %.2fs", similarities_calculated, similarity_duration)
            
            # Sort by similarity and limit results
            results.sort(key=lambda x: x['metadata']['similarity'], reverse=True)
            results = results[:limit]
            
            # Update search record with results count
            search_record.results_count = len(results)
            search_record.save()
            
            duration = time.time() - start_time
            logger.info("Search completed in %.2fs: found %d relevant memories from %d total", 
                       duration, len(results), memory_count)
            
            if results:
                logger.debug("Top result similarity: %.3f", results[0]['metadata']['similarity'])
            
            return {"results": results}
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Search failed for user_id %s after %.2fs: %s", user_id, duration, str(e))
            return {"results": [], "error": f"Search failed: {e}"}

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        return " ".join(text.lower().strip().split())

    def _hash_text(self, text: str) -> str:
        import hashlib
        return hashlib.sha256(self._normalize_text(text).encode("utf-8")).hexdigest()

    def recent_lru_check(self, user_id: str, text_hash: str, max_keep: int = 32) -> bool:
        """Return True if hash was seen recently; otherwise add and return False."""
        bucket = self._recent_hashes.setdefault(user_id, [])
        if text_hash in bucket:
            return True
        bucket.append(text_hash)
        if len(bucket) > max_keep:
            del bucket[0: len(bucket) - max_keep]
        return False

    def is_near_duplicate(self, user_id: str, text: str, threshold: float = 0.9, recent_n: int = 20) -> Tuple[bool, float]:
        """Vector near-duplicate check against user's recent memories.

        Returns (is_dup, max_similarity).
        """
        try:
            emb = self._get_embedding(text)
            if not emb:
                return False, 0.0
            q = np.array(emb)
            memories = (
                Memory.objects.filter(user_id=user_id, embedding__isnull=False, is_archived=False)
                .order_by("-created_at")[:recent_n]
            )
            max_sim = 0.0
            for m in memories:
                try:
                    v = np.array(m.embedding)
                    dot = float(np.dot(q, v))
                    qn = float(np.linalg.norm(q)) or 1.0
                    vn = float(np.linalg.norm(v)) or 1.0
                    sim = dot / (qn * vn)
                    if sim > max_sim:
                        max_sim = sim
                        if max_sim >= threshold:
                            return True, max_sim
                except Exception:
                    continue
            return max_sim >= threshold, max_sim
        except Exception:
            return False, 0.0
    
    async def get_all(self, user_id: str, limit: int = 10) -> Dict:
        """
        Get all memories for a user (most recent first).
        
        Args:
            user_id: User identifier
            limit: Maximum number of memories to return
            
        Returns:
            Dict with results list
        """
        return await sync_to_async(self._get_all_impl)(user_id, limit)
    
    def _get_all_impl(self, user_id: str, limit: int = 10) -> Dict:
        """Internal implementation of get_all method."""
        start_time = time.time()
        logger.info("Getting all memories for user_id: %s, limit: %d", user_id, limit)
        
        try:
            memories = Memory.objects.filter(
                user_id=user_id,
                is_archived=False
            ).order_by('-created_at')[:limit]
            
            memory_count = len(memories)
            logger.debug("Retrieved %d memories from database", memory_count)
            
            results = []
            for memory in memories:
                results.append({
                    'memory_id': str(memory.id),
                    'memory': memory.content,
                    'metadata': {
                        'category': memory.category,
                        'subcategory': memory.subcategory,
                        'memory_type': memory.memory_type,
                        'importance': memory.importance,
                        'created_at': memory.created_at.isoformat(),
                        **memory.metadata
                    }
                })
            
            duration = time.time() - start_time
            logger.info("Retrieved %d memories in %.2fs", memory_count, duration)
            
            return {"results": results}
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Failed to get memories for user_id %s after %.2fs: %s", user_id, duration, str(e))
            return {"results": [], "error": f"Failed to get memories: {e}"}
    
    async def update(self, memory_id: str, data: Dict) -> Dict:
        """Update an existing memory."""
        return await sync_to_async(self._update_impl)(memory_id, data)
    
    def _update_impl(self, memory_id: str, data: Dict) -> Dict:
        """Internal implementation of update method."""
        start_time = time.time()
        logger.info("Updating memory (ID: %s) with data: %s", memory_id, data)
        
        try:
            memory = Memory.objects.get(id=memory_id)
            logger.debug("Found memory to update: %s", memory.content[:100])
            
            if 'content' in data:
                old_content = memory.content
                memory.content = data['content']
                memory.embedding = self._get_embedding(data['content'])
                logger.info("Updated memory content and regenerated embedding")
                logger.debug("Old content: %s", old_content[:100])
                logger.debug("New content: %s", data['content'][:100])
            
            if 'metadata' in data:
                old_metadata = memory.metadata.copy()
                memory.metadata.update(data['metadata'])
                memory.save()
                logger.debug("Updated metadata from %s to %s", old_metadata, memory.metadata)
            
            duration = time.time() - start_time
            logger.info("Memory updated successfully in %.2fs", duration)
            
            return {"message": "Memory updated successfully"}
            
        except Memory.DoesNotExist:
            duration = time.time() - start_time
            logger.warning("Memory not found for update (ID: %s) after %.2fs", memory_id, duration)
            return {"error": "Memory not found"}
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Failed to update memory (ID: %s) after %.2fs: %s", memory_id, duration, str(e))
            return {"error": f"Failed to update memory: {e}"}
    
    async def delete(self, memory_id: str) -> Dict:
        """Delete a memory (actually archives it)."""
        return await sync_to_async(self._delete_impl)(memory_id)
    
    def _delete_impl(self, memory_id: str) -> Dict:
        """Internal implementation of delete method."""
        start_time = time.time()
        logger.info("Archiving memory (ID: %s)", memory_id)
        
        try:
            memory = Memory.objects.get(id=memory_id)
            logger.debug("Found memory to archive: %s", memory.content[:100])
            
            memory.is_archived = True
            memory.save()
            
            duration = time.time() - start_time
            logger.info("Memory archived successfully in %.2fs", duration)
            
            return {"message": "Memory archived successfully"}
            
        except Memory.DoesNotExist:
            duration = time.time() - start_time
            logger.warning("Memory not found for deletion (ID: %s) after %.2fs", memory_id, duration)
            return {"error": "Memory not found"}
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Failed to delete memory (ID: %s) after %.2fs: %s", memory_id, duration, str(e))
            return {"error": f"Failed to delete memory: {e}"} 
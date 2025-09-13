"""
Embedding generation services for TalentCo semantic matching.
Handles OpenAI text-embedding-3-small integration with batch processing.
"""

import openai
import logging
from typing import List, Optional, Union
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings using OpenAI text-embedding-3-small.
    Provides both single and batch embedding generation.
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"  # 1536 dimensions
        self.max_batch_size = 2048  # OpenAI limit
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate single embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of 1536 floats representing the embedding
            
        Raises:
            Exception: If OpenAI API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
            
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding for text length: {len(text)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed (max 2048)
            
        Returns:
            List of embeddings in same order as input texts
            
        Raises:
            ValueError: If batch too large
            Exception: If OpenAI API call fails
        """
        if not texts:
            return []
            
        if len(texts) > self.max_batch_size:
            raise ValueError(f"Batch size {len(texts)} exceeds maximum {self.max_batch_size}")
        
        # Filter out empty texts but preserve indices
        valid_texts = []
        text_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                text_indices.append(i)
        
        if not valid_texts:
            return [[] for _ in texts]  # Return empty embeddings for all
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=valid_texts,
                encoding_format="float"
            )
            
            # Reconstruct results in original order
            embeddings = [[] for _ in texts]
            for valid_idx, original_idx in enumerate(text_indices):
                embeddings[original_idx] = response.data[valid_idx].embedding
            
            logger.info(f"Generated {len(valid_texts)} embeddings from {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def generate_embeddings_for_instances(self, instances: List, batch_size: int = 100):
        """
        Generate embeddings for model instances in batches.
        
        Args:
            instances: List of model instances with get_embedding_text() method
            batch_size: Size of each batch for processing
        """
        if not instances:
            return
        
        # Process in chunks to respect API limits
        for i in range(0, len(instances), min(batch_size, self.max_batch_size)):
            batch = instances[i:i + min(batch_size, self.max_batch_size)]
            
            # Generate embedding texts
            texts = []
            valid_instances = []
            
            for instance in batch:
                try:
                    text = instance.get_embedding_text()
                    if text and text.strip():
                        texts.append(text)
                        valid_instances.append(instance)
                except Exception as e:
                    logger.warning(f"Failed to get embedding text for {instance}: {e}")
            
            if not texts:
                continue
            
            # Generate embeddings
            try:
                embeddings = self.generate_batch_embeddings(texts)
                
                # Update instances in a transaction
                with transaction.atomic():
                    for instance, embedding in zip(valid_instances, embeddings):
                        if embedding:  # Skip empty embeddings
                            instance.embedding = embedding
                    
                    # Bulk update
                    if valid_instances:
                        type(valid_instances[0]).objects.bulk_update(
                            valid_instances, ['embedding']
                        )
                
                logger.info(f"Updated embeddings for {len(valid_instances)} instances")
                
            except Exception as e:
                logger.error(f"Failed to process batch: {e}")
                # Continue with next batch rather than failing completely


# Convenience functions for common operations
def generate_embeddings_for_model(model_class, force_regenerate: bool = False, batch_size: int = 100):
    """
    Generate embeddings for all instances of a model class.
    
    Args:
        model_class: Django model class
        force_regenerate: If True, regenerate all embeddings. If False, only generate missing ones.
        batch_size: Batch size for processing
    """
    service = EmbeddingService()
    
    # Get instances without embeddings (or all if force regenerating)
    if force_regenerate:
        instances = list(model_class.objects.all())
        logger.info(f"Force regenerating embeddings for {len(instances)} {model_class.__name__} instances")
    else:
        instances = list(model_class.objects.filter(embedding__isnull=True))
        logger.info(f"Generating embeddings for {len(instances)} {model_class.__name__} instances without embeddings")
    
    if instances:
        service.generate_embeddings_for_instances(instances, batch_size)
    else:
        logger.info(f"No {model_class.__name__} instances need embedding generation")


def generate_all_embeddings(force_regenerate: bool = False):
    """
    Generate embeddings for all models that support them.
    
    Args:
        force_regenerate: If True, regenerate all embeddings
    """
    from apps.profiles.models import ProfileSkill, ProfileExperience, ProfileExperienceSkill
    from apps.opportunities.models import OpportunitySkill, OpportunityExperience
    
    models_to_process = [
        ProfileSkill,
        ProfileExperience, 
        ProfileExperienceSkill,
        OpportunitySkill,
        OpportunityExperience
    ]
    
    logger.info(f"Starting embedding generation for {len(models_to_process)} model types")
    
    for model_class in models_to_process:
        try:
            generate_embeddings_for_model(model_class, force_regenerate)
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {model_class.__name__}: {e}")
    
    logger.info("Completed embedding generation for all models")
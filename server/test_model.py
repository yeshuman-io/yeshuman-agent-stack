#!/usr/bin/env python
"""
Test script to list available Anthropic models.
"""
import os
import logging
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def list_models():
    """List available Anthropic models."""
    try:
        # Initialize client
        client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # Get available models
        response = await client.models.list()
        
        # Print models
        print("\nAvailable Anthropic Models:")
        print("===========================")
        print("Raw response data:")
        print(response)
        print("\nModel objects:")
        for model in response.data:
            print(f"\nModel info:")
            print(model)
            
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        logger.exception("Full traceback:")

if __name__ == "__main__":
    import asyncio
    asyncio.run(list_models()) 
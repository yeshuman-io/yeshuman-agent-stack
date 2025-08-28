#!/usr/bin/env python3
"""
Test script to examine what GPT-5 thinking responses look like.
"""
import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

async def test_gpt5_thinking():
    """Test what GPT-5 thinking responses look like."""
    
    api_key = os.environ.get("OPENAI_API_KEY")
    print(f"🔑 API Key found: {'Yes' if api_key else 'No'}")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return
    
    # Test models that might have reasoning tokens
    models_to_test = [
        "o1-preview",  # OpenAI's reasoning model
        "o1-mini",     # Smaller reasoning model
        "gpt-4o",      # Latest GPT-4
        "gpt-4o-mini"  # Fallback
    ]
    
    print("🧠 Testing Models for Thinking Tokens")
    print("=" * 50)
    
    message = HumanMessage(content="What's 2+2? Think step by step.")
    
    for model_name in models_to_test:
        print(f"\n🤖 Testing {model_name}")
        print("-" * 30)
        
        try:
            llm = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                streaming=True,
                temperature=0.1
            )
            
            print("📡 Sending request...")
            
            # Test streaming
            async for chunk in llm.astream([message]):
                print(f"Chunk: {chunk}")
                if hasattr(chunk, 'content') and chunk.content:
                    print(f"Content: '{chunk.content}'")
                if hasattr(chunk, 'reasoning'):
                    print(f"🧠 Reasoning: {chunk.reasoning}")
                if hasattr(chunk, 'additional_kwargs') and chunk.additional_kwargs:
                    print(f"Additional: {chunk.additional_kwargs}")
                if hasattr(chunk, 'response_metadata') and chunk.response_metadata:
                    print(f"Metadata: {chunk.response_metadata}")
                print("-" * 15)
                
            print(f"✅ {model_name} worked!")
            break  # Stop after first successful model
            
        except Exception as e:
            print(f"❌ {model_name} failed: {e}")
            continue

if __name__ == "__main__":
    asyncio.run(test_gpt5_thinking())

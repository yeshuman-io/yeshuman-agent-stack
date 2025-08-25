#!/usr/bin/env python
"""
Demo script to visualize the streaming output from ThinkingInstructor.
"""
import asyncio
import sys
import time
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ThinkingDemo")

# Load env variables
load_dotenv()

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.instructors import ThinkingInstructor


async def demo_thinking_instructor():
    """Demonstrate the streaming behavior of ThinkingInstructor."""
    
    # Create a ThinkingInstructor instance
    instructor = ThinkingInstructor()
    
    # A simpler question that should generate a shorter response
    query = "What are three key benefits of AI in business? Keep your answer brief."
    
    print("\n🧠 ThinkingInstructor Streaming Demo 🧠")
    print("=" * 80)
    print(f"Query: {query}")
    print("=" * 80)
    print("\nStreaming thinking process (watch how it updates):\n")
    
    # Track timing for analytics
    start_time = time.time()
    chunk_times = []
    chunk_lengths = []
    
    # Process the streaming response
    previous_content_length = 0
    last_significant_update = 0
    chunk_count = 0
    last_analysis = ""
    
    logger.info("Starting instructor.generate call")
    async for chunk in instructor.generate(query):
        chunk_count += 1
        analysis_text = chunk.analysis or ""
        logger.info(f"Received chunk #{chunk_count}: analysis_text={analysis_text}, analysis_length={len(analysis_text)}, next_action={chunk.next_action}")
        
        # Record timing
        chunk_time = time.time() - start_time
        chunk_times.append(chunk_time)
        
        # Record content length
        chunk_lengths.append(len(analysis_text))
        
        # Only print if there's meaningful change to reduce output volume
        if len(analysis_text) > len(last_analysis):
            # For cleaner display, only show the new words/tokens
            new_content = analysis_text[len(last_analysis):]
            if new_content.strip():  # Only print if there's non-whitespace content
                print(f"\033[32m{new_content}\033[0m", end="", flush=True)
                last_significant_update = chunk_count
                
            last_analysis = analysis_text
        
        # Occasionally print next_action update
        if chunk.next_action and chunk_count % 20 == 0:
            print(f"\n[Current next_action: {chunk.next_action}]")
        
        # Small delay for readability if needed
        # await asyncio.sleep(0.05)
    
    # Final statistics
    print("\n\n" + "=" * 80)
    print(f"Final next_action: {chunk.next_action}")
    print("=" * 80)
    
    # Print stats about the streaming
    total_time = time.time() - start_time
    total_chunks = len(chunk_times)
    content_chunks = sum(1 for i in range(1, total_chunks) if chunk_lengths[i] > chunk_lengths[i-1])
    
    print(f"\n📊 Streaming Stats:")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Total chunks: {total_chunks}")
    print(f"Content-adding chunks: {content_chunks} ({(content_chunks/total_chunks*100):.1f}%)")
    
    if total_chunks > 0:
        print(f"Average time between chunks: {(chunk_times[-1] / total_chunks):.2f} seconds")
        print(f"Final content length: {chunk_lengths[-1]} characters")
        print(f"Last meaningful update at chunk: {last_significant_update} of {total_chunks}")
    
    if total_chunks > 1:
        print(f"Content growth rate: {chunk_lengths[-1]/total_time:.2f} chars/second")
        
    print("\nCheck the logs for more detailed information.")


if __name__ == "__main__":
    asyncio.run(demo_thinking_instructor()) 
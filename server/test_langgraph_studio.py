#!/usr/bin/env python3
"""
Test script to verify LangGraph Studio setup.

Run this before starting LangGraph Studio to ensure everything is configured correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the standalone app
from langgraph_app import graph, create_test_state, test_configs


async def test_graph_functionality():
    """Test that the graph works correctly in isolation."""
    print("🧪 Testing LangGraph Studio setup...")
    print("=" * 50)
    
    try:
        # Test basic graph creation
        print("✅ Graph creation: SUCCESS")
        print(f"   Graph type: {type(graph)}")
        print(f"   Graph nodes: {list(graph.get_graph().nodes.keys())}")
        
        # Test state creation
        test_state = create_test_state()
        print("✅ State creation: SUCCESS")
        print(f"   Test query: {test_state.query}")
        
        # Test graph execution (with timeout)
        print("\n🚀 Testing graph execution...")
        
        try:
            # Use asyncio.wait_for with timeout to prevent hanging
            result = await asyncio.wait_for(
                graph.ainvoke(test_state), 
                timeout=30.0
            )
            print("✅ Graph execution: SUCCESS")
            print(f"   Final state keys: {list(result.keys()) if hasattr(result, 'keys') else 'Not dict-like'}")
            
            # Check for expected fields
            if hasattr(result, 'thinking_complete'):
                print(f"   Thinking complete: {result.thinking_complete}")
            if hasattr(result, 'message_executed'):
                print(f"   Message executed: {result.message_executed}")
            if hasattr(result, 'error'):
                if result.error:
                    print(f"   ⚠️  Error occurred: {result.error}")
                else:
                    print("   No errors detected")
                    
        except asyncio.TimeoutError:
            print("❌ Graph execution: TIMEOUT (>30s)")
            print("   This might indicate an infinite loop or hanging process")
            return False
        except Exception as e:
            print(f"❌ Graph execution: FAILED - {e}")
            return False
        
        # Test configuration
        print(f"\n📋 Test configurations available: {len(test_configs)}")
        for name, config in test_configs.items():
            print(f"   - {name}: {config['query'][:50]}...")
        
        print("\n🎉 All tests passed! LangGraph Studio should work correctly.")
        print("\n📝 Next steps:")
        print("   1. cd server")
        print("   2. langgraph dev")
        print("   3. Open the Studio URL in your browser")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup test FAILED: {e}")
        print("\n🔧 Troubleshooting:")
        print("   - Check that all dependencies are installed")
        print("   - Ensure Django settings are correct")
        print("   - Verify database connections if needed")
        return False


async def test_streaming():
    """Test streaming functionality."""
    print("\n🌊 Testing streaming (for Studio real-time updates)...")
    
    try:
        test_state = create_test_state("Quick test")
        
        event_count = 0
        async for event in graph.astream(test_state, stream_mode="updates"):
            event_count += 1
            if event_count <= 3:  # Show first few events
                print(f"   Event {event_count}: {list(event.keys()) if event else 'Empty'}")
            elif event_count == 4:
                print("   ... (additional events)")
            
            # Prevent infinite streaming in test
            if event_count >= 10:
                break
        
        print(f"✅ Streaming test: SUCCESS ({event_count} events)")
        return True
        
    except Exception as e:
        print(f"❌ Streaming test: FAILED - {e}")
        return False


if __name__ == "__main__":
    async def main():
        success = await test_graph_functionality()
        if success:
            await test_streaming()
        
        return success
    
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 
#!/usr/bin/env python3
"""
Test script to verify frontend-backend automation integration.
This script simulates what happens when a user asks "ping the print server" in the frontend.
"""

import asyncio
import json
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.ai_assistant.services.chat_service import ChatService
from app.ai_assistant.services.model_service import ModelService
from app.config import get_settings

async def test_automation_integration():
    """Test the complete automation workflow."""
    print("🧪 Testing Frontend-Backend Automation Integration")
    print("=" * 60)
    
    try:
        # Initialize services
        print("1️⃣ Initializing services...")
        model_service = ModelService()
        await model_service.initialize_llm()
        await model_service.preload_and_warm_model()
        chat_service = ChatService(model_service)
        
        # Test query that should trigger automation
        test_queries = [
            "ping the print server",
            "check if the print server is working",
            "test connectivity to the print server",
            "backup network configurations",
            "check device health"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}️⃣ Testing query: '{query}'")
            print("-" * 40)
            
            # Simulate the automation request
            response_count = 0
            async for response_chunk in chat_service.handle_automation_request(query):
                response_count += 1
                try:
                    data = json.loads(response_chunk)
                    print(f"📤 Response {response_count}:")
                    print(f"   Type: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'start':
                        print(f"   Content: {data.get('content', '')}")
                    elif data.get('type') == 'tool_result':
                        print(f"   Tool: {data.get('tool', '')}")
                        print(f"   Success: {data.get('success', False)}")
                        print(f"   Output: {data.get('output', '')[:100]}...")
                    elif data.get('type') == 'final_response':
                        print(f"   Content: {data.get('content', '')[:200]}...")
                    elif data.get('type') == 'error':
                        print(f"   Error: {data.get('error', '')}")
                    else:
                        print(f"   Data: {data}")
                        
                except json.JSONDecodeError:
                    print(f"   Raw response: {response_chunk[:100]}...")
                
                print()
            
            if response_count == 0:
                print("❌ No responses received")
            else:
                print(f"✅ Received {response_count} response chunks")
        
        print("\n🎉 Automation integration test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_automation_integration()) 
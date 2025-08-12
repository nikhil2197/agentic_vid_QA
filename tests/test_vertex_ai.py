#!/usr/bin/env python3
"""
Test script for Vertex AI integration
"""

import os
import asyncio
import sys
# Add project root to path so 'src' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.adapters.llm_adapter import LLMAdapter

async def test_vertex_ai():
    """Test Vertex AI integration"""
    try:
        # Check environment variables
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        print(f"Project ID: {project_id}")
        
        if not project_id:
            print("❌ GOOGLE_CLOUD_PROJECT not set")
            print("Please set your Google Cloud project ID:")
            print("export GOOGLE_CLOUD_PROJECT='your-project-id'")
            return
        
        # Test text generation
        print("\n🧪 Testing text generation...")
        llm = LLMAdapter()
        
        response = llm.call_text("Hello, how are you?", temperature=0.7)
        print(f"✅ Text response: {response[:100]}...")
        
        # Test JSON generation
        print("\n🧪 Testing JSON generation...")
        json_response = llm.call_json("Return a JSON object with a greeting", temperature=0.0)
        print(f"✅ JSON response: {json_response}")
        
        print("\n🎉 All tests passed! Vertex AI integration is working.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure GOOGLE_CLOUD_PROJECT is set")
        print("2. Make sure you're authenticated with Google Cloud:")
        print("   gcloud auth application-default login")
        print("3. Make sure Vertex AI API is enabled in your project")

if __name__ == "__main__":
    asyncio.run(test_vertex_ai())

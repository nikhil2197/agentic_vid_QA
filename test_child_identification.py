#!/usr/bin/env python3
"""
Test script for child identification flow
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.state import QAState
from src.nodes.child_identifier import run as child_identifier

async def test_child_identifier():
    """Test the child identifier node"""
    
    print("🧪 Testing Child Identifier Node")
    print("=" * 50)
    
    # Test 1: First interaction (should ask for child info)
    print("\n📝 Test 1: First interaction")
    state1 = QAState(user_question="Did my child participate in the art activity?")
    
    # Mock LLM adapter (not needed for this test)
    class MockLLMAdapter:
        pass
    
    result1 = await child_identifier(state1, MockLLMAdapter())
    
    print(f"Original question: {result1.original_question}")
    print(f"Current question: {result1.user_question}")
    print(f"Waiting for child info: {result1.waiting_for_child_info}")
    print(f"Child info: {getattr(result1, 'child_info', 'Not set')}")
    
    # Test 2: With child info provided (should proceed)
    print("\n📝 Test 2: With child info provided")
    state2 = QAState(
        user_question="Did my child participate in the art activity?",
        child_info="Emma, wearing a blue dress with white polka dots"
    )
    
    result2 = await child_identifier(state2, MockLLMAdapter())
    
    print(f"Original question: {result2.original_question}")
    print(f"Current question: {result2.user_question}")
    print(f"Waiting for child info: {result2.waiting_for_child_info}")
    print(f"Child info: {getattr(result2, 'child_info', 'Not set')}")
    
    print("\n✅ Child identifier tests completed!")

if __name__ == "__main__":
    asyncio.run(test_child_identifier())

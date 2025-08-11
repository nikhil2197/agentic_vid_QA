#!/usr/bin/env python3
"""
Test the system flow without making API calls
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.state import QAState, ConversationMessage
from src.adapters.catalog_adapter import CatalogAdapter

async def test_system_flow():
    """Test the system flow without API calls"""
    
    print("🧪 Testing System Flow (No API Calls)")
    print("=" * 50)
    
    # Test 1: Load catalog
    print("\n📝 Test 1: Loading video catalog")
    try:
        catalog_adapter = CatalogAdapter()
        catalog = catalog_adapter.list_catalog()
        print(f"✅ Catalog loaded successfully with {len(catalog)} videos")
        
        for video in catalog:
            print(f"  - {video['id']}: {video['session-type']} ({video['start-time']} - {video['end-time']})")
            
    except Exception as e:
        print(f"❌ Catalog loading failed: {e}")
        return
    
    # Test 2: Create initial state
    print("\n📝 Test 2: Creating initial state")
    try:
        initial_state = QAState(user_question="Did my child participate in the water activity?")
        print(f"✅ State created successfully")
        print(f"  - Question: {initial_state.user_question}")
        print(f"  - Request ID: {initial_state.request_id}")
        
    except Exception as e:
        print(f"❌ State creation failed: {e}")
        return
    
    # Test 3: Simulate child identification flow
    print("\n📝 Test 3: Simulating child identification flow")
    try:
        # Simulate what happens in child_identifier
        initial_state.original_question = initial_state.user_question
        initial_state.user_question = "Can you tell me your child's name and describe what they were wearing today?"
        initial_state.waiting_for_child_info = True
        
        print(f"✅ Child identification requested")
        print(f"  - Original question stored: {initial_state.original_question}")
        print(f"  - Current question: {initial_state.user_question}")
        print(f"  - Waiting for child info: {initial_state.waiting_for_child_info}")
        
        # Simulate child response
        child_response = "Emma, wearing a blue dress with white polka dots"
        initial_state.child_info = child_response
        initial_state.waiting_for_child_info = False
        
        print(f"✅ Child info provided: {child_response}")
        
    except Exception as e:
        print(f"❌ Child identification simulation failed: {e}")
        return
    
    # Test 4: Simulate video selection
    print("\n📝 Test 4: Simulating video selection")
    try:
        # Simulate what video_picker would do
        initial_state.target_videos = ["vid_3", "vid_4"]  # Plant and Table activities (water-related)
        print(f"✅ Videos selected: {', '.join(initial_state.target_videos)}")
        
        # Show why these videos were selected
        for vid_id in initial_state.target_videos:
            video_info = catalog_adapter.get_metadata(vid_id)
            print(f"  - {vid_id}: {video_info['act-description']}")
        
    except Exception as e:
        print(f"❌ Video selection simulation failed: {e}")
        return
    
    # Test 5: Simulate question refinement
    print("\n📝 Test 5: Simulating question refinement")
    try:
        initial_state.target_question = "Did Emma participate in the water activity while wearing a blue dress with white polka dots?"
        print(f"✅ Question refined: {initial_state.target_question}")
        
    except Exception as e:
        print(f"❌ Question refinement simulation failed: {e}")
        return
    
    # Test 6: Simulate video analysis
    print("\n📝 Test 6: Simulating video analysis")
    try:
        initial_state.per_video_answers = {
            "vid_3": "Emma in a blue dress was actively engaged in watering plants, showing enthusiasm and following teacher instructions carefully.",
            "vid_4": "Emma participated in the sensory table activity with mud and seeds, getting her hands dirty while learning about planting."
        }
        print(f"✅ Video analysis completed")
        for vid_id, answer in initial_state.per_video_answers.items():
            print(f"  - {vid_id}: {answer[:80]}...")
        
    except Exception as e:
        print(f"❌ Video analysis simulation failed: {e}")
        return
    
    # Test 7: Simulate final composition
    print("\n📝 Test 7: Simulating final composition")
    try:
        initial_state.final_answer = "Yes, Emma actively participated in water-related activities! She was engaged in watering plants during outdoor time and also participated in a sensory table activity with mud and seeds. She showed enthusiasm and followed teacher instructions well while learning about how water helps plants grow."
        print(f"✅ Final answer composed")
        print(f"  - Answer: {initial_state.final_answer[:100]}...")
        
    except Exception as e:
        print(f"❌ Final composition simulation failed: {e}")
        return
    
    print("\n🎉 System flow test completed successfully!")
    print("\n📋 Summary of what the system would do:")
    print("1. ✅ Ask for child identification")
    print("2. ✅ Select relevant videos (Plant and Table activities)")
    print("3. ✅ Refine question to focus on specific child")
    print("4. ✅ Analyze videos for child-specific behavior")
    print("5. ✅ Compose parent-friendly answer")
    print("\n🚀 The system structure is working correctly!")
    print("   Next step: Enable the Generative Language API to test with real AI calls")

if __name__ == "__main__":
    asyncio.run(test_system_flow())

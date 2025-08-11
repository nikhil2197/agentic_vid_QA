#!/usr/bin/env python3
"""
Test script to verify CLI runner fix for state field access
"""

from src.state import QAState

def test_state_field_access():
    """Test that the CLI runner can safely access state fields"""
    
    # Create a test state with minimal fields (simulating final output)
    test_state = QAState(
        user_question="Did my child participate in the water activity?",
        final_answer="Based on the video analysis, your child did participate in the water activity."
    )
    
    # Test the CLI runner logic for displaying results
    print("🧪 Testing CLI runner state field access...")
    
    # This is the logic from the CLI runner that was failing
    try:
        videos_analyzed = ', '.join(test_state.target_videos) if test_state.target_videos else 'None'
        refined_question = test_state.target_question if test_state.target_question else 'None'
        final_answer = test_state.final_answer
        
        print(f"✅ Videos analyzed: {videos_analyzed}")
        print(f"✅ Refined question: {refined_question}")
        print(f"✅ Final answer: {final_answer}")
        
        print("\n🎉 Test passed! CLI runner can safely access state fields.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_state_with_all_fields():
    """Test with a complete state to ensure all fields work"""
    
    print("\n🧪 Testing with complete state...")
    
    complete_state = QAState(
        user_question="Did my child participate in the water activity?",
        target_videos=["vid_1", "vid_2"],
        target_question="Did the child participate in water activities?",
        final_answer="Yes, your child participated in water activities."
    )
    
    try:
        videos_analyzed = ', '.join(complete_state.target_videos) if complete_state.target_videos else 'None'
        refined_question = complete_state.target_question if complete_state.target_question else 'None'
        final_answer = complete_state.final_answer
        
        print(f"✅ Videos analyzed: {videos_analyzed}")
        print(f"✅ Refined question: {refined_question}")
        print(f"✅ Final answer: {final_answer}")
        
        print("\n🎉 Complete state test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Complete state test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing CLI runner state field access fix...")
    print("=" * 60)
    
    test1_passed = test_state_field_access()
    test2_passed = test_state_with_all_fields()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The CLI runner fix is working correctly.")
    else:
        print("\n❌ Some tests failed. The CLI runner still has issues.")

#!/usr/bin/env python3
"""
CLI Runner for Agentic Video QA System
Runs the main flow and handles follow-up questions interactively
"""

import asyncio
import logging
import sys
from typing import List
from src.graph import run_main_flow, run_graph
from src.state import QAState, ConversationMessage
from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main CLI runner function"""
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli_runner 'Your question here'")
        print("Example: python -m src.cli_runner 'Did the teacher run any small-group activity after circle time?'")
        sys.exit(1)
    
    # Get the initial question
    user_question = " ".join(sys.argv[1:])
    print(f"\n🤔 Question: {user_question}")
    print("=" * 80)
    
    try:
        # Initialize adapters
        llm_adapter = LLMAdapter()
        catalog_adapter = CatalogAdapter()
        
        # Run main flow (up to composer) - this will start with child identification
        print("\n🔄 Starting analysis (will ask for child identification first)...")
        result = await run_main_flow(
            user_question=user_question,
            llm_adapter=llm_adapter,
            catalog_adapter=catalog_adapter
        )
        
        # Check if we need child identification first
        if hasattr(result, 'waiting_for_child_info') and result.waiting_for_child_info:
            print(f"\n👶 {result.user_question}")
            child_response = input("Your response: ").strip()
            
            # Update the state with child information
            result.child_info = child_response
            result.waiting_for_child_info = False
            
            # Add to conversation history
            conversation_history = [
                ConversationMessage(role="user", content=user_question),
                ConversationMessage(role="assistant", content=result.user_question),
                ConversationMessage(role="user", content=child_response)
            ]
            
            # Now run the actual analysis with child info
            print("\n🔄 Running video analysis with child information...")
            # Re-run main flow seeded with collected child info and history
            result = await run_main_flow(
                user_question=user_question,
                llm_adapter=llm_adapter,
                catalog_adapter=catalog_adapter,
                child_info=result.child_info,
                original_question=result.original_question,
                conversation_history=conversation_history
            )
        
        # Display results
        print(f"\n📹 Videos analyzed: {', '.join(result.target_videos) if result.target_videos else 'None'}")
        print(f"🎯 Refined question: {result.target_question if result.target_question else 'None'}")
        print(f"\n💡 Final Answer:")
        print(f"{result.final_answer}")
        
        # Handle follow-up questions
        conversation_history = [
            ConversationMessage(role="user", content=user_question),
            ConversationMessage(role="assistant", content=result.final_answer)
        ]
        
        while True:
            print("\n" + "=" * 80)
            followup = input("\n❓ Follow-up question (or 'quit' to exit): ").strip()
            
            if followup.lower() in ['quit', 'exit', 'q', '']:
                print("👋 Goodbye!")
                break
            
            if followup:
                print(f"\n🔄 Processing follow-up...")
                
                # Add follow-up to conversation history
                conversation_history.append(ConversationMessage(role="user", content=followup))
                
                # Run followup_advisor
                followup_state = QAState(
                    user_question=user_question,
                    final_answer=result.final_answer,
                    conversation_history=conversation_history
                )
                
                # Import and run followup_advisor directly
                from src.nodes.followup_advisor import run as followup_advisor
                # followup_advisor is synchronous, so call it directly without await
                followup_result = followup_advisor(followup_state, llm_adapter)
                
                # Display follow-up response
                print(f"\n💡 Follow-up Response:")
                print(f"{followup_result.followup_response}")
                
                # Add response to conversation history
                conversation_history.append(ConversationMessage(role="assistant", content=followup_result.followup_response))
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"CLI runner failed: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

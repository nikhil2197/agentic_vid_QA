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
    
    # Demo mode support
    demo_mode = (len(sys.argv) >= 2 and sys.argv[1] == "--demo")
    transcripts_only = any(arg == "--transcripts-only" for arg in sys.argv[1:])
    if demo_mode:
        # Force transcripts-only in demo for a non-multimodal path
        transcripts_only = True
        greeting = (
            "Hi Sounak, what do you want to learn about Ayaan's day? "
            "You can ask about what he did, whether he participated, what skills we worked on and much more."
        )
        print(f"\n👋 {greeting}")
        user_question = input("Your question: ").strip()
        if not user_question:
            print("No question entered. Exiting.")
            sys.exit(0)
    else:
        if len(sys.argv) < 2:
            print("Usage: python -m src.cli_runner 'Your question here'")
            print("Example: python -m src.cli_runner 'Did the teacher run any small-group activity after circle time?'")
            sys.exit(1)
        user_question = " ".join(sys.argv[1:])
        print(f"\n🤔 Question: {user_question}")
        print("=" * 80)
    
    try:
        # Initialize adapters
        llm_adapter = LLMAdapter()
        catalog_adapter = CatalogAdapter()
        
        # Run main flow (up to composer) - this will start with child identification
        if demo_mode:
            # Preselect Ayaan and proceed directly
            conversation_history = [
                ConversationMessage(role="assistant", content=greeting),
                ConversationMessage(role="user", content=user_question)
            ]
            print("\n🔄 Running analysis with child=Ayaan...")
            result = await run_main_flow(
                user_question=user_question,
                llm_adapter=llm_adapter,
                catalog_adapter=catalog_adapter,
                child_info="Ayaan",
                original_question=user_question,
                conversation_history=conversation_history,
                demo_mode=True,
                transcripts_only=transcripts_only
            )
        else:
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
                    conversation_history=conversation_history,
                    transcripts_only=transcripts_only
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
                from src.nodes.followup_advisor import run as followup_advisor_node
                followup_result = followup_advisor_node(followup_state, llm_adapter)

                # Decide route
                route = getattr(followup_result, 'followup_route', None)
                if route in ("transcript_child", "transcript_day"):
                    # Rerun main flow with the follow-up as a new question
                    next_q = followup_result.conversation_history[-1].content if followup_result.conversation_history else followup
                    print("\n🔄 Rerouting follow-up through transcripts...")
                    result = await run_main_flow(
                        user_question=next_q,
                        llm_adapter=llm_adapter,
                        catalog_adapter=catalog_adapter,
                        child_info="Ayaan" if demo_mode else None,
                        original_question=next_q,
                        conversation_history=conversation_history,
                    )
                    # Show new final answer
                    print(f"\n💡 Answer:")
                    print(f"{result.final_answer}")
                    # Update conversation history with this turn
                    conversation_history.append(ConversationMessage(role="assistant", content=result.final_answer))
                elif route == "evidence":
                    # Run evidence snipper node directly and show outputs
                    print("\n🔄 Preparing evidence clips (vid_2)...")
                    from src.nodes.evidence_snipper import run as evidence_snipper_node
                    # Reuse the result state so child_transcript_data and transcript_path are available
                    ev_state = result
                    # Ensure the latest conversation history is present
                    ev_state.conversation_history = conversation_history
                    ev_state = evidence_snipper_node(ev_state, catalog_adapter)
                    msg = getattr(ev_state, 'evidence_message', None) or ""
                    clips = (getattr(ev_state, 'evidence_clips', {}) or {}).get('vid_2', [])
                    print(f"\n💡 Evidence: {msg}")
                    if clips:
                        print("Saved clips:")
                        for p in clips:
                            print(f" - {p}")
                    else:
                        print("No clips available.")
                    # Keep conversation turn with a short acknowledgment
                    conversation_history.append(ConversationMessage(role="assistant", content=(msg or "Evidence processed.")))
                else:
                    # Display follow-up response from advisor (parenting help)
                    print(f"\n💡 Follow-up Response:")
                    print(f"{followup_result.followup_response}")
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

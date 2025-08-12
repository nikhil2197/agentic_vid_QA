import logging
import asyncio
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.state import QAState
from src.adapters.llm_adapter import LLMAdapter
from src.adapters.catalog_adapter import CatalogAdapter
from src.nodes.child_identifier import run as child_identifier
from src.nodes.video_picker import run as video_picker
from src.nodes.question_refiner import run as question_refiner
from src.nodes.video_analyzers import run as video_analyzers
from src.nodes.transcript_builder import run as transcript_builder
from src.nodes.transcript_answerer import run as transcript_answerer
from src.nodes.composer import run as composer
from src.nodes.followup_advisor import run as followup_advisor

logger = logging.getLogger(__name__)

def create_graph(llm_adapter: LLMAdapter = None, catalog_adapter: CatalogAdapter = None) -> StateGraph:
    """Create the LangGraph workflow for the agentic video QA system"""
    
    # Initialize adapters if not provided
    if llm_adapter is None:
        llm_adapter = LLMAdapter()
    if catalog_adapter is None:
        catalog_adapter = CatalogAdapter()
    
    # Create the graph
    workflow = StateGraph(QAState)
    
    # Create wrapper functions that bind the adapters
    async def child_identifier_wrapper(state: QAState) -> QAState:
        # Await the async child_identifier node
        return await child_identifier(state, llm_adapter)
    
    def video_picker_wrapper(state: QAState) -> QAState:
        return video_picker(state, llm_adapter, catalog_adapter)
    
    def question_refiner_wrapper(state: QAState) -> QAState:
        return question_refiner(state, llm_adapter)
    
    def video_analyzers_wrapper(state: QAState) -> QAState:
        return video_analyzers(state, llm_adapter, catalog_adapter)
    
    def composer_wrapper(state: QAState) -> QAState:
        return composer(state, llm_adapter)
    
    def followup_advisor_wrapper(state: QAState) -> QAState:
        return followup_advisor(state, llm_adapter)
    
    def transcript_builder_wrapper(state: QAState) -> QAState:
        return transcript_builder(state, llm_adapter, catalog_adapter)
    
    def transcript_answerer_wrapper(state: QAState) -> QAState:
        return transcript_answerer(state, llm_adapter)
    
    # Add nodes
    workflow.add_node("child_identifier", child_identifier_wrapper)
    workflow.add_node("video_picker", video_picker_wrapper)
    workflow.add_node("question_refiner", question_refiner_wrapper)
    workflow.add_node("video_analyzers", video_analyzers_wrapper)
    workflow.add_node("composer", composer_wrapper)
    workflow.add_node("followup_advisor", followup_advisor_wrapper)
    workflow.add_node("transcript_builder", transcript_builder_wrapper)
    workflow.add_node("transcript_answerer", transcript_answerer_wrapper)
    
    # Set entry point
    workflow.set_entry_point("child_identifier")
    
    # Add edges (sequential flow) with conditional branch after child identification
    def _after_child(state: QAState) -> str:
        """If still waiting for child info, end; otherwise proceed to video_picker"""
        if getattr(state, 'waiting_for_child_info', False):
            return END
        return "video_picker"
    workflow.add_conditional_edges("child_identifier", _after_child)
    workflow.add_edge("video_picker", "question_refiner")
    # Transcript-first branch after question refinement
    workflow.add_edge("question_refiner", "transcript_builder")
    workflow.add_edge("transcript_builder", "transcript_answerer")
    
    # Conditional: if transcript can answer, go straight to composer; else go to video analyzers
    def _after_transcript(state: QAState) -> str:
        if getattr(state, 'transcript_can_answer', False):
            # per_video_answers is pre-seeded by transcript_answerer
            return "composer"
        return "video_analyzers"
    workflow.add_conditional_edges("transcript_answerer", _after_transcript)
    workflow.add_edge("video_analyzers", "composer")
    
    # Conditional edge for followup_advisor
    def should_continue(state: QAState) -> str:
        """Check if we should continue to followup_advisor"""
        if state.conversation_history:
            return "followup_advisor"
        return END
    
    workflow.add_conditional_edges("composer", should_continue)
    workflow.add_edge("followup_advisor", END)
    
    return workflow

async def run_graph(
    user_question: str,
    conversation_history: list = None,
    llm_adapter: LLMAdapter = None,
    catalog_adapter: CatalogAdapter = None
) -> QAState:
    """Run the complete graph workflow"""
    
    # Initialize adapters if not provided
    if llm_adapter is None:
        llm_adapter = LLMAdapter()
    if catalog_adapter is None:
        catalog_adapter = CatalogAdapter()
    
    # Create initial state
    initial_state = QAState(
        user_question=user_question,
        conversation_history=conversation_history or []
    )
    
    # Create and compile graph
    graph = create_graph(llm_adapter, catalog_adapter)
    compiled_graph = graph.compile()
    
    # Run the graph
    try:
        logger.info(f"Starting graph execution for question: {user_question[:50]}...")
        result = await compiled_graph.ainvoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id": initial_state.request_id
                }
            }
        )
        logger.info("Graph execution completed successfully")
        # Ensure we return a QAState instance (compiled_graph may yield a dict)
        if isinstance(result, dict):
            result = QAState.parse_obj(result)
        return result
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise

async def run_main_flow(
    user_question: str,
    llm_adapter: LLMAdapter = None,
    catalog_adapter: CatalogAdapter = None,
    child_info: str = None,
    original_question: str = None,
    conversation_history: list = None,
) -> QAState:
    """Run the main flow (up to composer) without followup"""
    
    # Initialize adapters if not provided
    if llm_adapter is None:
        llm_adapter = LLMAdapter()
    if catalog_adapter is None:
        catalog_adapter = CatalogAdapter()
    
    # Create initial state with optional pre-set fields
    initial_state = QAState(user_question=user_question)
    # Seed child information and original question if provided
    if child_info is not None:
        initial_state.child_info = child_info
    if original_question is not None:
        initial_state.original_question = original_question
    if conversation_history is not None:
        initial_state.conversation_history = conversation_history
    
    # Create graph for main flow only
    workflow = StateGraph(QAState)
    
    # Create wrapper functions that bind the adapters
    async def child_identifier_wrapper(state: QAState) -> QAState:
        # Await the async child_identifier node
        return await child_identifier(state, llm_adapter)
    
    def video_picker_wrapper(state: QAState) -> QAState:
        return video_picker(state, llm_adapter, catalog_adapter)
    
    def question_refiner_wrapper(state: QAState) -> QAState:
        return question_refiner(state, llm_adapter)
    
    def video_analyzers_wrapper(state: QAState) -> QAState:
        return video_analyzers(state, llm_adapter, catalog_adapter)

    def transcript_builder_wrapper(state: QAState) -> QAState:
        return transcript_builder(state, llm_adapter, catalog_adapter)

    def transcript_answerer_wrapper(state: QAState) -> QAState:
        return transcript_answerer(state, llm_adapter)
    
    def composer_wrapper(state: QAState) -> QAState:
        return composer(state, llm_adapter)
    
    workflow.add_node("child_identifier", child_identifier_wrapper)
    workflow.add_node("video_picker", video_picker_wrapper)
    workflow.add_node("question_refiner", question_refiner_wrapper)
    workflow.add_node("video_analyzers", video_analyzers_wrapper)
    workflow.add_node("composer", composer_wrapper)
    workflow.add_node("transcript_builder", transcript_builder_wrapper)
    workflow.add_node("transcript_answerer", transcript_answerer_wrapper)
    
    workflow.set_entry_point("child_identifier")
    # Conditional branch: if waiting for child info, stop; otherwise proceed
    def _after_child_main(state: QAState) -> str:
        if getattr(state, 'waiting_for_child_info', False):
            return END
        return "video_picker"
    workflow.add_conditional_edges("child_identifier", _after_child_main)
    workflow.add_edge("video_picker", "question_refiner")
    # Transcript-first branch after question refinement
    workflow.add_edge("question_refiner", "transcript_builder")
    workflow.add_edge("transcript_builder", "transcript_answerer")
    def _after_transcript_main(state: QAState) -> str:
        if getattr(state, 'transcript_can_answer', False):
            return "composer"
        return "video_analyzers"
    workflow.add_conditional_edges("transcript_answerer", _after_transcript_main)
    workflow.add_edge("video_analyzers", "composer")
    
    # Compile and run
    compiled_graph = workflow.compile()
    
    try:
        logger.info(f"Starting main flow execution for question: {user_question[:50]}...")
        result = await compiled_graph.ainvoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id": initial_state.request_id
                }
            }
        )
        logger.info("Main flow execution completed successfully")
        # Ensure we return a QAState instance (compiled_graph may yield a dict)
        if isinstance(result, dict):
            result = QAState.parse_obj(result)
        return result
    except Exception as e:
        logger.error(f"Main flow execution failed: {e}")
        raise

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
    def child_identifier_wrapper(state: QAState) -> QAState:
        return child_identifier(state, llm_adapter)
    
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
    
    # Add nodes
    workflow.add_node("child_identifier", child_identifier_wrapper)
    workflow.add_node("video_picker", video_picker_wrapper)
    workflow.add_node("question_refiner", question_refiner_wrapper)
    workflow.add_node("video_analyzers", video_analyzers_wrapper)
    workflow.add_node("composer", composer_wrapper)
    workflow.add_node("followup_advisor", followup_advisor_wrapper)
    
    # Set entry point
    workflow.set_entry_point("child_identifier")
    
    # Add edges (sequential flow)
    workflow.add_edge("child_identifier", "video_picker")
    workflow.add_edge("video_picker", "question_refiner")
    workflow.add_edge("question_refiner", "video_analyzers")
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
    catalog_adapter: CatalogAdapter = None
) -> QAState:
    """Run the main flow (up to composer) without followup"""
    
    # Initialize adapters if not provided
    if llm_adapter is None:
        llm_adapter = LLMAdapter()
    if catalog_adapter is None:
        catalog_adapter = CatalogAdapter()
    
    # Create initial state
    initial_state = QAState(user_question=user_question)
    
    # Create graph for main flow only
    workflow = StateGraph(QAState)
    
    # Create wrapper functions that bind the adapters
    def child_identifier_wrapper(state: QAState) -> QAState:
        return child_identifier(state, llm_adapter)
    
    def video_picker_wrapper(state: QAState) -> QAState:
        return video_picker(state, llm_adapter, catalog_adapter)
    
    def question_refiner_wrapper(state: QAState) -> QAState:
        return question_refiner(state, llm_adapter)
    
    def video_analyzers_wrapper(state: QAState) -> QAState:
        return video_analyzers(state, llm_adapter, catalog_adapter)
    
    def composer_wrapper(state: QAState) -> QAState:
        return composer(state, llm_adapter)
    
    workflow.add_node("child_identifier", child_identifier_wrapper)
    workflow.add_node("video_picker", video_picker_wrapper)
    workflow.add_node("question_refiner", question_refiner_wrapper)
    workflow.add_node("video_analyzers", video_analyzers_wrapper)
    workflow.add_node("composer", composer_wrapper)
    
    workflow.set_entry_point("child_identifier")
    workflow.add_edge("child_identifier", "video_picker")
    workflow.add_edge("video_picker", "question_refiner")
    workflow.add_edge("question_refiner", "video_analyzers")
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

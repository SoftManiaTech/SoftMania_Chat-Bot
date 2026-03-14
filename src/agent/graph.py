from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import router_node, decomposer_node, compressor_node, synthesizer_node
from src.agent.retrievers import hybrid_retriever_node
from src.config import Config
from src.logger import setup_logger

logger = setup_logger(__name__)

# ── Conditional Edge: After Router (3-Tier) ──
def route_after_router(state: AgentState):
    """Routes based on the 3-tier classification from the smart router."""
    route = state.get("route_type", "simple")
    
    if route == "off_topic":
        logger.info("--- GRAPH EDGE --- Off-topic detected. Skipping to END.")
        return "end"
    elif route == "complex":
        logger.info("--- GRAPH EDGE --- Complex query. Routing to Decomposer.")
        return "decomposer"
    else:
        logger.info("--- GRAPH EDGE --- Simple query. Routing directly to Retriever.")
        return "retriever"

# ── Conditional Edge: After Retriever ──
def route_after_retriever(state: AgentState):
    """Simple queries skip the compressor to save time."""
    if state.get("route_type") == "simple":
        logger.info("--- GRAPH EDGE --- Simple query: skipping compressor → Synthesizer.")
        return "synthesizer"
    else:
        logger.info("--- GRAPH EDGE --- Complex query: compressing context first.")
        return "compressor"

# ── Conditional Edge: After Synthesizer (Hop Check) ──
def check_after_synthesis(state: AgentState):
    """
    After synthesis, check if the answer is sufficient or if we need another hop.
    This replaces the old dedicated evaluator_node.
    """
    is_sufficient = state.get("is_sufficient", True)
    hop_count = state.get("hop_count", 0)
    
    if is_sufficient:
        logger.info("--- GRAPH EDGE --- Answer is sufficient. Done!")
        return "end"
    
    if hop_count >= Config.MAX_HOP_COUNT:
        logger.warning(f"--- GRAPH EDGE --- Max hops ({Config.MAX_HOP_COUNT}) reached. Forcing end.")
        return "end"
    
    logger.info(f"--- GRAPH EDGE --- Insufficient context (hop {hop_count}). Looping back to Decomposer.")
    return "decomposer"

# ── Build the Graph ──
workflow = StateGraph(AgentState)

# Add Nodes (no evaluator_node — its logic is merged into synthesizer)
workflow.add_node("router", router_node)
workflow.add_node("decomposer", decomposer_node)
workflow.add_node("retriever", hybrid_retriever_node)
workflow.add_node("compressor", compressor_node)
workflow.add_node("synthesizer", synthesizer_node)

# ── Edges ──
workflow.set_entry_point("router")

# After Router: 3-tier split
workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "end": END,                 # Off-topic → instant response, done
        "retriever": "retriever",   # Simple → go straight to retriever
        "decomposer": "decomposer"  # Complex → decompose first
    }
)

# Decomposer always goes to Retriever
workflow.add_edge("decomposer", "retriever")

# After Retriever: simple skips compressor, complex compresses first
workflow.add_conditional_edges(
    "retriever",
    route_after_retriever,
    {
        "synthesizer": "synthesizer",
        "compressor": "compressor"
    }
)

# Compressor always goes to Synthesizer
workflow.add_edge("compressor", "synthesizer")

# After Synthesizer: check if done or need another hop
workflow.add_conditional_edges(
    "synthesizer",
    check_after_synthesis,
    {
        "end": END,
        "decomposer": "decomposer"
    }
)

# Compile the LangGraph engine
graph_app = workflow.compile()

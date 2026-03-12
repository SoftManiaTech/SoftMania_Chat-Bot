from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import router_node, decomposer_node, evaluator_node, synthesizer_node
from src.agent.retrievers import hybrid_retriever_node
from src.config import Config

def check_sufficiency_or_hop(state: AgentState):
    """
    Conditional Edge router enforcing strict max hop boundaries.
    """
    hop_count = state.get("hop_count", 0)
    
    # We enforce a strict max hop limit from config to prevent explosive latency
    if hop_count >= Config.MAX_HOP_COUNT:
        return "synthesize"
    else:
        return "evaluator"

# Build the Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router", router_node)
workflow.add_node("decomposer", decomposer_node)
workflow.add_node("retriever", hybrid_retriever_node)
workflow.add_node("evaluator", evaluator_node)
workflow.add_node("synthesizer", synthesizer_node)

# Add Edges
workflow.set_entry_point("router")

workflow.add_edge("router", "decomposer")

workflow.add_edge("decomposer", "retriever")

# After retrieving context, we evaluate if we need to synthesize or jump context
workflow.add_conditional_edges(
    "retriever",
    check_sufficiency_or_hop,
    {
        "synthesize": "synthesizer",
        "evaluator": "evaluator" 
    }
)

# After evaluating, we synthesize if possible, else decompose new questions based on missing gaps
workflow.add_conditional_edges(
    "evaluator",
    lambda state: "synthesize" if state.get("is_sufficient", False) else "decomposer",
    {
        "synthesize": "synthesizer",
        "decomposer": "decomposer" 
    }
)

workflow.add_edge("synthesizer", END)

# Compile the LangGraph engine
graph_app = workflow.compile()

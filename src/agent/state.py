import operator
from typing import Annotated, TypedDict, List

class AgentState(TypedDict):
    """
    Represents the state of our multi-hop reasoning LangGraph.
    """
    question: str
    route_type: str           # "off_topic", "simple", or "complex"
    is_complex: bool
    sub_queries: List[str]
    # We use Annotated with operator.add so that parallel sub-query results get appended
    retrieved_context: Annotated[List[str], operator.add]
    compressed_context: str
    hop_count: int
    is_sufficient: bool       # Merged evaluator flag (set by synthesizer)
    final_answer: str

import os
from typing import Dict, Any
from pydantic import BaseModel, Field
from src.agent.state import AgentState
from src.config import Config
from src.prompts import ROUTER_PROMPT, DECOMPOSER_PROMPT, EVALUATOR_PROMPT, SYNTHESIZER_PROMPT

class RouteDecision(BaseModel):
    is_complex: bool = Field(description="True if the question requires synthesizing multiple pieces of information or multi-hop reasoning. False if simple.")

class SubQueries(BaseModel):
    queries: list[str] = Field(description="List of isolated, semantic sub-queries.")

class EvaluationDecision(BaseModel):
    is_sufficient: bool = Field(description="True if the context fully answers the question, False otherwise.")

class FinalAnswer(BaseModel):
    answer: str = Field(description="The complete, helpful, and safe answer to the user's query.")
    citations: list[str] = Field(description="List of document citations used, empty if none.")

def get_llm():
    return Config.get_llm(temperature=0.0)

async def router_node(state: AgentState) -> Dict[str, Any]:
    """Classifies if the query needs multi-hop decomposition."""
    llm = get_llm()
    chain = ROUTER_PROMPT | llm.with_structured_output(RouteDecision)
    decision = await chain.ainvoke({"question": state["question"]})
    return {"is_complex": decision.is_complex, "hop_count": 0}

async def decomposer_node(state: AgentState) -> Dict[str, Any]:
    """Breaks down a complex query into simpler parallel sub-queries."""
    if not state.get("is_complex"):
        return {"sub_queries": [state["question"]]}
        
    llm = get_llm()
    chain = DECOMPOSER_PROMPT | llm.with_structured_output(SubQueries)
    result = await chain.ainvoke({"question": state["question"]})
    return {"sub_queries": result.queries}

async def evaluator_node(state: AgentState) -> Dict[str, Any]:
    """Evaluates if the currently retrieved context is enough to answer the original question."""
    llm = get_llm()
    context_str = "\n".join(state.get("retrieved_context", []))
    chain = EVALUATOR_PROMPT | llm.with_structured_output(EvaluationDecision)
    result = await chain.ainvoke({"question": state["question"], "context": context_str})
    
    # We update hop_count here as it represents one full retrieval cycle evaluation
    new_hop_count = state.get("hop_count", 0) + 1
    # We return the flag just to be used by the conditional edge routing, we don't strictly need to save it to state
    # but returning it updates the state if we added it, but let's just use it in the edge
    return {"hop_count": new_hop_count, "is_sufficient": result.is_sufficient}

async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes the final answer using all retrieved contexts."""
    llm = get_llm()
    
    # GUARDRAIL: Strict output parsing with automated fallback to a zero-temperature strict model
    safe_llm = Config.get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(FinalAnswer).with_fallbacks([
        safe_llm.with_structured_output(FinalAnswer)
    ])
    
    context_str = "\n\n".join(state.get("retrieved_context", []))
    chain = SYNTHESIZER_PROMPT | structured_llm
    
    try:
        result = await chain.ainvoke({"question": state["question"], "context": context_str})
        if not result:
            raise ValueError("LLM returned empty structured output.")
    except Exception as e:
        # Fallback if both the primary and fallback LLMs fail parsing (e.g. complete injection failure)
        return {"final_answer": "I apologize, but I am unable to safely process or retrieve an answer for that request. (Safety Guardrail Triggered)"}
    
    final_output = result.answer
    if result.citations:
        final_output += f"\n\nSources: {', '.join(result.citations)}"
        
    return {"final_answer": final_output}

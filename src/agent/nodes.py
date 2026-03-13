import os
from typing import Dict, Any
from pydantic import BaseModel, Field
from src.agent.state import AgentState
from src.config import Config
from src.prompts import ROUTER_PROMPT, DECOMPOSER_PROMPT, EVALUATOR_PROMPT, SYNTHESIZER_PROMPT, COMPRESSOR_PROMPT
from src.logger import setup_logger

logger = setup_logger(__name__)

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
    logger.info(f"--- ROUTER NODE --- Analyzing question: '{state['question']}'")
    llm = get_llm()
    chain = ROUTER_PROMPT | llm.with_structured_output(RouteDecision)
    decision = await chain.ainvoke({"question": state["question"]})
    logger.info(f"   -> Router Decision: is_complex={decision.is_complex}")
    return {"is_complex": decision.is_complex, "hop_count": 0}

async def decomposer_node(state: AgentState) -> Dict[str, Any]:
    """Breaks down a complex query into simpler parallel sub-queries."""
    logger.info("--- DECOMPOSER NODE ---")
    if not state.get("is_complex"):
        logger.info("   -> Simple query detected. Skipping decomposition.")
        return {"sub_queries": [state["question"]]}
        
    llm = get_llm()
    chain = DECOMPOSER_PROMPT | llm.with_structured_output(SubQueries)
    result = await chain.ainvoke({"question": state["question"]})
    logger.info(f"   -> Sub-queries generated: {result.queries}")
    return {"sub_queries": result.queries}

async def evaluator_node(state: AgentState) -> Dict[str, Any]:
    """Evaluates if the currently retrieved context is enough to answer the original question."""
    new_hop_count = state.get("hop_count", 0) + 1
    logger.info(f"--- EVALUATOR NODE (Hop {new_hop_count}) ---")
    llm = get_llm()
    
    context_str = state.get("compressed_context", "")
    if not context_str:
        context_str = "\n".join(state.get("retrieved_context", []))
    if not context_str:
        logger.info("   -> No context available yet. Deferring evaluation.")
        return {"hop_count": new_hop_count, "is_sufficient": False}
        
    chain = EVALUATOR_PROMPT | llm.with_structured_output(EvaluationDecision)
    result = await chain.ainvoke({"question": state["question"], "context": context_str})
    
    logger.info(f"   -> Evaluation Decision: is_sufficient={result.is_sufficient}")
    
    return {"hop_count": new_hop_count, "is_sufficient": result.is_sufficient}

async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes the final answer using all retrieved contexts."""
    logger.info("--- SYNTHESIZER NODE --- Generating final answer...")
    llm = get_llm()
    
    # GUARDRAIL: Strict output parsing with automated fallback to a zero-temperature strict model
    safe_llm = Config.get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(FinalAnswer).with_fallbacks([
        safe_llm.with_structured_output(FinalAnswer)
    ])
    
    context_str = state.get("compressed_context", "")
    if not context_str:
        context_str = "\n\n".join(state.get("retrieved_context", []))
    chain = SYNTHESIZER_PROMPT | structured_llm
    
    try:
        result = await chain.ainvoke({"question": state["question"], "context": context_str})
        if not result:
            raise ValueError("LLM returned empty structured output.")
    except Exception as e:
        logger.error(f"   -> Synthesizer Error/Guardrail Triggered: {e}")
        # Fallback if both the primary and fallback LLMs fail parsing (e.g. complete injection failure)
        return {"final_answer": "I apologize, but I am unable to safely process or retrieve an answer for that request. (Safety Guardrail Triggered)"}
    
    final_output = result.answer
    if result.citations:
        cf_str = ', '.join(result.citations)
        final_output += f"\n\nSources: {cf_str}"
        logger.info(f"   -> Synthesis Complete with Citations: {cf_str}")
    else:
        logger.info("   -> Synthesis Complete (No citations).")
        
    return {"final_answer": final_output}

class CompressedContext(BaseModel):
    compressed_text: str = Field(description="The salient facts relevant to the sub-queries, compressed to save tokens.")

async def compressor_node(state: AgentState) -> Dict[str, Any]:
    """Compresses the heavily inflated retrieved context into a dense summary of facts."""
    logger.info("--- COMPRESSOR NODE ---")
    
    raw_context = "\n".join(state.get("retrieved_context", []))
    if not raw_context:
        return {"compressed_context": ""}
        
    llm = get_llm()
    chain = COMPRESSOR_PROMPT | llm.with_structured_output(CompressedContext)
    
    try:
        result = await chain.ainvoke({
            "question": state["question"], 
            "sub_queries": ", ".join(state.get("sub_queries", [])),
            "context": raw_context
        })
        compressed = result.compressed_text
        logger.info(f"   -> Context compressed from {len(raw_context)} to {len(compressed)} characters.")
    except Exception as e:
        logger.error(f"   -> Compression Failed, falling back to raw context: {e}")
        compressed = raw_context
        
    return {"compressed_context": compressed}

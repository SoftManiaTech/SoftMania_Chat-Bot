import os
from typing import Dict, Any
from pydantic import BaseModel, Field
from src.agent.state import AgentState
from src.config import Config
from src.prompts import ROUTER_PROMPT, DECOMPOSER_PROMPT, SYNTHESIZER_PROMPT, COMPRESSOR_PROMPT
from src.logger import setup_logger

logger = setup_logger(__name__)

# ── Pydantic Schemas ──

class RouteDecision(BaseModel):
    route_type: str = Field(description="One of: 'off_topic', 'simple', 'complex'")

class SubQueries(BaseModel):
    queries: list[str] = Field(description="List of isolated, semantic sub-queries.")

class SynthesisResult(BaseModel):
    answer: str = Field(description="The complete, helpful, and well-formatted answer to the user's query.")
    is_sufficient: bool = Field(description="True if the context fully answers the question, False if more information is needed.")

class CompressedContext(BaseModel):
    compressed_text: str = Field(description="The salient facts relevant to the sub-queries, compressed to save tokens.")

# ── Off-Topic Response ──
OFF_TOPIC_RESPONSE = (
    "I'm the **SoftMania Assistant** — I can only answer questions about "
    "SoftMania's Splunk training, labs, courses, pricing, and policies.\n\n"
    "Please ask me something related to SoftMania! 😊"
)

# ── Node Functions ──

async def router_node(state: AgentState) -> Dict[str, Any]:
    """
    3-Tier Smart Router (1 fast LLM call) — acts as the FIRST guardrail:
    - off_topic → instant reject (sets final_answer, skips everything)
    - simple → single retrieval iteration (no decomposition)
    - complex → full multi-hop pipeline
    """
    logger.info(f"--- ROUTER NODE --- Classifying: '{state['question']}'")
    llm = Config.get_fast_llm()
    chain = ROUTER_PROMPT | llm.with_structured_output(RouteDecision)
    
    try:
        decision = await chain.ainvoke({"question": state["question"]})
        route = decision.route_type.lower().strip()
    except Exception as e:
        logger.warning(f"   -> Router failed ({e}), defaulting to 'simple'")
        route = "simple"
    
    # Validate route_type
    if route not in ("off_topic", "simple", "complex"):
        route = "simple"
    
    logger.info(f"   -> Route Decision: {route}")
    
    if route == "off_topic":
        return {"route_type": route, "final_answer": OFF_TOPIC_RESPONSE, "is_complex": False}
    
    return {"route_type": route, "is_complex": route == "complex", "hop_count": 0}

async def decomposer_node(state: AgentState) -> Dict[str, Any]:
    """Breaks down a complex query into simpler parallel sub-queries using the fast model."""
    logger.info("--- DECOMPOSER NODE ---")
    llm = Config.get_fast_llm()
    chain = DECOMPOSER_PROMPT | llm.with_structured_output(SubQueries)
    result = await chain.ainvoke({"question": state["question"]})
    logger.info(f"   -> Sub-queries generated: {result.queries}")
    return {"sub_queries": result.queries}

async def compressor_node(state: AgentState) -> Dict[str, Any]:
    """Compresses retrieved context into dense facts using the fast model."""
    logger.info("--- COMPRESSOR NODE ---")
    
    raw_context = "\n".join(state.get("retrieved_context", []))
    if not raw_context:
        return {"compressed_context": ""}
        
    llm = Config.get_fast_llm()
    chain = COMPRESSOR_PROMPT | llm.with_structured_output(CompressedContext)
    
    try:
        result = await chain.ainvoke({
            "question": state["question"], 
            "sub_queries": ", ".join(state.get("sub_queries", [])),
            "context": raw_context
        })
        compressed = result.compressed_text
        logger.info(f"   -> Context compressed from {len(raw_context)} to {len(compressed)} chars.")
    except Exception as e:
        logger.error(f"   -> Compression failed, falling back to raw context: {e}")
        compressed = raw_context
        
    return {"compressed_context": compressed}

async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Synthesizes the final answer AND evaluates context sufficiency in one call.
    Uses the fast mini model for speed.
    """
    logger.info("--- SYNTHESIZER NODE --- Generating final answer...")
    llm = Config.get_fast_llm(temperature=0.1)
    
    # GUARDRAIL: Strict output parsing with fallback
    safe_llm = Config.get_fast_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(SynthesisResult).with_fallbacks([
        safe_llm.with_structured_output(SynthesisResult)
    ])
    
    # Use compressed context if available, else raw context
    context_str = state.get("compressed_context", "")
    if not context_str:
        context_str = "\n\n".join(state.get("retrieved_context", []))
    
    chain = SYNTHESIZER_PROMPT | structured_llm
    
    try:
        result = await chain.ainvoke({"question": state["question"], "context": context_str})
        if not result:
            raise ValueError("LLM returned empty structured output.")
        
        logger.info(f"   -> Synthesis Complete. is_sufficient={result.is_sufficient}")
        return {
            "final_answer": result.answer,
            "is_sufficient": result.is_sufficient
        }
    except Exception as e:
        logger.error(f"   -> Synthesizer Error/Guardrail Triggered: {e}")
        return {
            "final_answer": "I apologize, but I am unable to safely process that request. (Safety Guardrail Triggered)",
            "is_sufficient": True  # Don't loop on errors
        }

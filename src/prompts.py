import yaml
import os
from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------
# Dynamic Prompt Loader
# ---------------------------------------------------------

def load_prompts():
    """Loads all prompt templates and guardrails from prompts.yaml."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(current_dir, "prompts.yaml")
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

_DATA = load_prompts()
_G = _DATA["guardrails"]
_P = _DATA["prompts"]

# ---------------------------------------------------------
# Agent Reasoning Prompts (Dynamic)
# ---------------------------------------------------------

ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _P["router"]["system"].format(guardrail=_G["router"])),
    ("placeholder", "{chat_history}"),
    ("human", "{question}")
])

DECOMPOSER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _P["decomposer"]["system"].format(guardrail=_G["decomposer"])),
    ("human", "{question}")
])

EVALUATOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _P["evaluator"]["system"].format(guardrail=_G["evaluator"])),
    ("human", "Question: {question}\n\nContext: {context}")
])

SYNTHESIZER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _P["synthesizer"]["system"].format(guardrail=_G["synthesizer"], portal_links="{portal_links}")),
    ("placeholder", "{chat_history}"),
    ("human", "Question: {question}\n\nContext: {context}")
])

COMPRESSOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _P["compressor"]["system"].format(guardrail=_G["synthesizer"])),
    ("human", "Question: {question}\nSub-Queries: {sub_queries}\n\nRaw Context:\n{context}")
])

# ---------------------------------------------------------
# Ingestion & Extraction Prompts (Dynamic)
# ---------------------------------------------------------

KNOWLEDGE_GRAPH_EXTRACTION_PROMPT = _P["knowledge_graph"]["system"].format(
    guardrail=_G["extraction"],
    text="{text}"
)

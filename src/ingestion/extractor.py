import os
from typing import List, Tuple
from langchain_core.documents import Document
from src.schema import KnowledgeGraphExtraction
from src.config import Config
from src.prompts import KNOWLEDGE_GRAPH_EXTRACTION_PROMPT

def parse_with_llm(documents: List[Document]) -> List[Tuple[str, str, KnowledgeGraphExtraction]]:
    """
    Takes text chunks and extracts a Knowledge Graph matching the base Pydantic ontology.
    It guarantees type safety for nodes while allowing LLM creativity for relationship edges.
    """
    llm = Config.get_llm(temperature=0.0)
    
    # We use OpenAI's native structured outputs (via with_structured_output in Langchain) 
    # to enforce the Pydantic schema returned.
    extractor_chain = llm.with_structured_output(KnowledgeGraphExtraction)
    
    extractions = []
    
    for doc in documents:
        text = doc.page_content
        # Use the centralized context prompt
        prompt = KNOWLEDGE_GRAPH_EXTRACTION_PROMPT.format(text=text)
        try:
            # We assume it's synchronous for now during ingestion batching
            result = extractor_chain.invoke(prompt)
            extractions.append((doc.metadata["doc_id"], doc.metadata["chunk_id"], result))
        except Exception as e:
            print(f"Failed extraction on chunk {doc.metadata.get('chunk_id')}: {e}")
            # Real implementation would have a retry loop or fallback chain
            
    return extractions

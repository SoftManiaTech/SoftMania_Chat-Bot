import os
import json
import asyncio
from functools import lru_cache
from typing import Dict, Any, List
from src.agent.state import AgentState
from src.ingestion.vector_db import semantic_search
from src.config import Config

@lru_cache(maxsize=512)
def fetch_graph_traversals(chunk_ids: tuple) -> List[Dict[str, Any]]:
    if not chunk_ids:
        return []
        
    graph = Config.get_neo4j_graph()
    cypher_query = """
    MATCH (n)-[r]-(m)
    WHERE r.chunk_id IN $chunk_ids OR n.chunk_id IN $chunk_ids
    RETURN n.id AS source, type(r) AS relation, m.id AS target
    LIMIT 10
    """
    results = graph.query(cypher_query, params={"chunk_ids": list(chunk_ids)})
    return results

async def process_sub_query(query: str, embeddings) -> List[str]:
    local_context = []
    
    # 1. Semantic Vector Search against PGVector using AsyncPG
    query_embedding = await embeddings.aembed_query(query)
    vector_results = await semantic_search(query_embedding, top_k=3)
    
    chunk_ids_found = []
    for res in vector_results:
        text = res["text"]
        chunk_id = res["chunk_id"]
        chunk_ids_found.append(chunk_id)
        local_context.append(f"[Vector Result source={chunk_id}]: {text}")
        
    # 2. Graph Traversal Link with Caching 
    # Run synchronous Neo4j query in a thread pool to avoid blocking async event loop
    if chunk_ids_found:
        graph_records = await asyncio.to_thread(fetch_graph_traversals, tuple(chunk_ids_found))
        for record in graph_records:
            if record.get("relation"):
                local_context.append(f"[Graph Result]: {record['source']} -> {record['relation']} -> {record['target']}")
                
    return local_context

async def hybrid_retriever_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes parallel sub-queries hitting both Neon PGVector and Neo4j.
    It performs semantic search, uses the returned doc_ids and chunk_ids to 
    traverse the Knowledge Graph, pulling linked entities 1-hop away.
    It now uses parallel query execution and traversal caching.
    """
    embeddings = Config.get_embeddings()
    
    sub_queries = state.get("sub_queries", [])
    if not sub_queries:
        sub_queries = [state.get("question", "")]
        
    # Execute all sub-queries concurrently!
    tasks = [process_sub_query(query, embeddings) for query in sub_queries]
    results = await asyncio.gather(*tasks)
    
    # Flatten the results
    all_context = []
    for ctx_list in results:
        all_context.extend(ctx_list)
                        
    # state["retrieved_context"] uses Annotated[operator.add], so returning a list appends it automatically
    # We explicitly bump the hop count 
    new_hop_count = state.get("hop_count", 0) + 1
    return {"retrieved_context": all_context, "hop_count": new_hop_count}

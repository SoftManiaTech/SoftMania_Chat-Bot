import os
import json
from typing import Dict, Any
from src.agent.state import AgentState
from src.ingestion.vector_db import semantic_search
from src.config import Config

async def hybrid_retriever_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes parallel sub-queries hitting both Neon PGVector and Neo4j.
    It performs semantic search, uses the returned doc_ids and chunk_ids to 
    traverse the Knowledge Graph, pulling linked entities 1-hop away.
    """
    embeddings = Config.get_embeddings()
    
    sub_queries = state.get("sub_queries", [])
    if not sub_queries:
        sub_queries = [state.get("question", "")]
        
    all_context = []
    
    for query in sub_queries:
        # 1. Semantic Vector Search against PGVector using AsyncPG
        query_embedding = await embeddings.aembed_query(query)
        # Assuming semantic_search returns a list of dictionaries with text and chunk_id
        vector_results = await semantic_search(query_embedding, top_k=3)
        
        chunk_ids_found = []
        for res in vector_results:
            text = res["text"]
            chunk_id = res["chunk_id"]
            chunk_ids_found.append(chunk_id)
            all_context.append(f"[Vector Result source={chunk_id}]: {text}")
            
        # 2. Graph Traversal Link
        # Given the top-k chunk_ids we just found semantically, let's find 1-hop 
        # entity relationships in Neo4j (Retrieval Fusion)
        
        if chunk_ids_found:
            graph = Config.get_neo4j_graph()
            cypher_query = """
            MATCH (n)-[r]-(m)
            WHERE r.chunk_id IN $chunk_ids OR n.chunk_id IN $chunk_ids
            RETURN n.id AS source, type(r) AS relation, m.id AS target
            LIMIT 10
            """
            graph_records = graph.query(cypher_query, params={"chunk_ids": chunk_ids_found})
            
            for record in graph_records:
                if record.get("relation"):
                    all_context.append(f"[Graph Result]: {record['source']} -> {record['relation']} -> {record['target']}")
                        
    # state["retrieved_context"] uses Annotated[operator.add], so returning a list appends it automatically
    # We explicitly bump the hop count 
    new_hop_count = state.get("hop_count", 0) + 1
    return {"retrieved_context": all_context, "hop_count": new_hop_count}

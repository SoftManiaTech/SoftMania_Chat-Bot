import json
from src.schema import KnowledgeGraphExtraction
from src.config import Config

async def batch_insert_graph(doc_id: str, chunk_id: str, extraction: KnowledgeGraphExtraction):
    """
    Takes the structured Pydantic extraction from the LLM, and writes it to Neo4j.
    Every node and edge is linked to the root doc_id and chunk_id for hybrid retrieval fusion.
    """
    graph = Config.get_neo4j_graph()
    
    # Insert Nodes matching strict Pydantic ontology
    for node in extraction.nodes:
        label = node.type
        query = f"""
            MERGE (n:`{label}` {{id: $id}})
            SET n.doc_id = $doc_id, n.chunk_id = $chunk_id, n.properties = $properties
        """
        graph.query(
            query, 
            params={
                "id": node.id, 
                "doc_id": doc_id, 
                "chunk_id": chunk_id, 
                "properties": json.dumps(node.properties)
            }
        )
        
    # Insert Relationships dynamically
    for rel in extraction.relationships:
        # Cypher requires relationship types to be statically defined in the syntax, 
        # so we use string formatting securely only for the type label.
        sanitized_type = "".join(c if c.isalnum() else "_" for c in rel.type).upper()
        
        query = f"""
            MATCH (s {{id: $source_id}})
            MATCH (t {{id: $target_id}})
            MERGE (s)-[r:`{sanitized_type}`]->(t)
            SET r.doc_id = $doc_id, r.chunk_id = $chunk_id, r.properties = $properties
        """
        graph.query(
            query, 
            params={
                "source_id": rel.source_id, 
                "target_id": rel.target_id, 
                "doc_id": doc_id, 
                "chunk_id": chunk_id,
                "properties": json.dumps(rel.properties)
            }
        )

async def clear_all_graph_data():
    """Wipes all nodes and relationships from the Neo4j Graph database."""
    graph = Config.get_neo4j_graph()
    graph.query("MATCH (n) DETACH DELETE n")


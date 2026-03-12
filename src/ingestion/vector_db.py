import json
from typing import List, Dict, Any
from src.config import Config

async def setup_pgvector_tables():
    """Initializes the PGVector extension and creates the necessary tables."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create chunks table
        # We store doc_id and chunk_id heavily indexed for hybrid retrieval
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding vector(1024), -- Assuming Mistral 1024 dim
                metadata JSONB DEFAULT '{}'::jsonb
            );
        """)
        
        # Create HNSW index for fast approximate nearest neighbor search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
            ON document_chunks 
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)
        
        # Create indexes on IDs for fast entity-linking hybrid lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS document_chunks_doc_id_idx ON document_chunks (doc_id);
            CREATE INDEX IF NOT EXISTS document_chunks_chunk_id_idx ON document_chunks (chunk_id);
        """)

async def batch_insert_chunks(doc_id: str, chunks: List[Dict[str, Any]]):
    """
    Batched asynchronous insert into PGVector using asyncpg.
    Chunks is expected to be a list of dicts:
    [{"chunk_id": "c1", "text": "...", "embedding": [0.1, ...], "metadata": {...}}]
    """
    pool = await Config.get_pg_pool()
    
    # Prepare data for executemany
    records = []
    for chunk in chunks:
        records.append((
            doc_id,
            chunk["chunk_id"],
            chunk["text"],
            json.dumps(chunk["embedding"]), # pgvector accepts string representation of array
            json.dumps(chunk.get("metadata", {}))
        ))
        
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany("""
                INSERT INTO document_chunks (doc_id, chunk_id, text, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, records)
            
async def semantic_search(query_embedding: List[float], top_k: int = None) -> List[Dict[str, Any]]:
    """Performs a vector search and returns the top_k matching chunks."""
    limit = top_k if top_k is not None else Config.TOP_K_RESULTS
    pool = await Config.get_pg_pool()
    embedding_str = json.dumps(query_embedding)
    
    async with pool.acquire() as conn:
        # Use <=> for cosine distance in pgvector
        rows = await conn.fetch("""
            SELECT doc_id, chunk_id, text, metadata, 1 - (embedding <=> $1) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> $1
            LIMIT $2;
        """, embedding_str, limit)
        
        return [dict(row) for row in rows]

async def clear_all_vectors():
    """Wipes all data from the document_chunks table."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE document_chunks;")


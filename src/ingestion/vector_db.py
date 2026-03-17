import json
from typing import List, Dict, Any
from src.config import Config

async def setup_pgvector_tables():
    """Initializes the PGVector extension and creates the necessary tables."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create chunks table (original safe flow — no data loss)
        # We store doc_id and chunk_id heavily indexed for hybrid retrieval
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding vector(1024), -- Mistral 1024 dims
                metadata JSONB DEFAULT '{}'::jsonb
            );
        """)
        
        # Safe migration: if the table already exists with wrong vector dimensions,
        # ALTER the column to match our current embedding model (1024 dims).
        # This handles upgrades from older 384-dim models gracefully.
        try:
            dim_row = await conn.fetchrow("""
                SELECT atttypmod FROM pg_attribute 
                WHERE attrelid = 'document_chunks'::regclass 
                AND attname = 'embedding';
            """)
            if dim_row and dim_row['atttypmod'] != 1024:
                await conn.execute("TRUNCATE TABLE document_chunks;")
                await conn.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024);")
        except Exception:
            pass  # Table is fresh, no migration needed
        
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
        
        # Create Query Logs table (Persistent)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                hop_count INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create Portal Links table for CRUD API
        await setup_portal_links_table(conn)
        
        # Create Chat Sessions table for memory
        await setup_chat_sessions_table(conn)

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

async def insert_query_log(question: str, answer: str, hop_count: int):
    """Inserts a persistent log of a user query and the intelligence engine response."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO query_logs (question, answer, hop_count)
            VALUES ($1, $2, $3)
        """, question, answer, hop_count)

# ---------------------------------------------------------
# Portal Links CRUD Operations
# ---------------------------------------------------------

async def setup_portal_links_table(conn):
    """Creates the portal_links table (called internally by setup_pgvector_tables)."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS portal_links (
            id SERIAL PRIMARY KEY,
            page_url TEXT UNIQUE NOT NULL,
            domain TEXT NOT NULL,
            page_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

async def create_portal_link(page_url: str, domain: str, page_type: str, summary: str):
    """Inserts a new portal link."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO portal_links (page_url, domain, page_type, summary)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (page_url) DO UPDATE 
            SET domain=$2, page_type=$3, summary=$4 
            RETURNING id, page_url, domain, page_type, summary
        """, page_url, domain, page_type, summary)
        return dict(row) if row else None

async def get_all_portal_links() -> List[Dict[str, Any]]:
    """Retrieves all portal links."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, page_url, domain, page_type, summary FROM portal_links ORDER BY id ASC")
        return [dict(row) for row in rows]
    return []

async def update_portal_link(link_id: int, page_url: str, domain: str, page_type: str, summary: str):
    """Updates an existing portal link by ID."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE portal_links 
            SET page_url=$2, domain=$3, page_type=$4, summary=$5
            WHERE id=$1
            RETURNING id, page_url, domain, page_type, summary
        """, link_id, page_url, domain, page_type, summary)
        return dict(row) if row else None

async def delete_portal_link(link_id: int):
    """Deletes a portal link by ID."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM portal_links WHERE id=$1", link_id)
        # result typically looks like "DELETE 1" or "DELETE 0"
        return result.endswith("1")


async def setup_chat_sessions_table(conn):
    """Creates the chat_sessions table for conversational memory."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            ip_address TEXT,
            device_signature TEXT,
            history JSONB DEFAULT '[]'::jsonb,
            last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

async def upsert_session_history(session_id: str, history_json: List[Dict[str, Any]], ip_address: str = None, device_signature: str = None):
    """Updates or creates a chat session history."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_sessions (session_id, ip_address, device_signature, history, last_active)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            ON CONFLICT (session_id) DO UPDATE 
            SET history = $4, last_active = CURRENT_TIMESTAMP, ip_address = COALESCE($2, chat_sessions.ip_address);
        """, session_id, ip_address, device_signature, json.dumps(history_json))

async def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves the history for a given session."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT history FROM chat_sessions WHERE session_id = $1", session_id)
        if row and row['history']:
            return json.loads(row['history'])
        return []
    return []

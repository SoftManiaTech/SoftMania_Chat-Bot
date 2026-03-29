import json
from typing import List, Dict, Any, Optional
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
        
        # Create Portal Links table for CRUD API
        await setup_portal_links_table(conn)
        
        # Create Chat Sessions table (session metadata)
        await setup_chat_sessions_table(conn)
        
        # Create Query Logs table (normalized conversation turns, FK → chat_sessions)
        await setup_query_logs_table(conn)

        # Create WhatsApp Template tracking tables
        await setup_whatsapp_template_tables(conn)


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
            
async def semantic_search(query_embedding: List[float], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
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

async def get_all_portal_links() -> List[Dict[str, Any]]:  # noqa
    """Retrieves all portal links."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, page_url, domain, page_type, summary FROM portal_links ORDER BY id ASC")
        return [dict(row) for row in rows]

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


# ---------------------------------------------------------
# Chat Sessions — session metadata
# ---------------------------------------------------------

async def setup_chat_sessions_table(conn):
    """
    Creates the chat_sessions table.
    Stores ONE row per unique browser/device session.
    """
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id       TEXT PRIMARY KEY,
            hmac_token       TEXT NOT NULL,
            ip_address       TEXT,
            device_signature TEXT,
            created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_active      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_turn_index  INTEGER DEFAULT -1
        );
    """)
    # Migration: gracefully add the column to existing tables
    await conn.execute("""
        ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS last_turn_index INTEGER DEFAULT -1;
    """)
    await conn.execute("""
        ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS current_menu_node TEXT;
    """)


# ---------------------------------------------------------
# Query Logs — normalized conversation turns (FK → chat_sessions)
# ---------------------------------------------------------

async def setup_query_logs_table(conn):
    """
    Creates the query_logs table.
    Each row = one message (either 'human' or 'assistant').
    turn_index keeps them in chronological order within the session.
    """
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id           SERIAL PRIMARY KEY,
            session_id   TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            turn_index   INTEGER NOT NULL,
            role         TEXT NOT NULL CHECK (role IN ('human', 'assistant')),
            content      TEXT NOT NULL,
            hop_count    INTEGER DEFAULT 0,
            feedback     TEXT DEFAULT NULL CHECK (feedback IS NULL OR feedback IN ('like', 'dislike')),
            created_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Index for fast history lookups by session
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_logs_session
        ON query_logs (session_id, turn_index ASC);
    """)


# ---------------------------------------------------------
# Session + History helper functions
# ---------------------------------------------------------

async def ensure_session(session_id: str, hmac_token: str, ip_address: Optional[str] = None, device_signature: Optional[str] = None):
    """
    Creates a session row if it does not exist, otherwise
    touches last_active timestamp.  Always safe to call.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_sessions (session_id, hmac_token, ip_address, device_signature)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (session_id) DO UPDATE
            SET last_active       = CURRENT_TIMESTAMP,
                ip_address        = COALESCE($3, chat_sessions.ip_address),
                device_signature  = COALESCE($4, chat_sessions.device_signature);
        """, session_id, hmac_token, ip_address, device_signature)


async def append_turn(session_id: str, human_msg: str, ai_msg: str, hop_count: Optional[int] = 0):
    """
    Appends a full conversation turn (human + assistant) as TWO rows
    in query_logs using an atomic UPDATE on chat_sessions, avoiding SELECT MAX concurrency hotspots.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Atomically increment last_turn_index by 2 and update last_active timestamp
            row = await conn.fetchrow("""
                UPDATE chat_sessions
                SET last_turn_index = last_turn_index + 2,
                    last_active = CURRENT_TIMESTAMP
                WHERE session_id = $1
                RETURNING last_turn_index;
            """, session_id)
            
            if not row:
                # Fallback if session somehow doesn't exist 
                raise ValueError(f"Session {session_id} not found when appending turn.")

            current_max = row["last_turn_index"]
            next_idx = current_max - 1  # Human message is the first of the newly reserved indices

            # Human message
            await conn.execute("""
                INSERT INTO query_logs (session_id, turn_index, role, content, hop_count)
                VALUES ($1, $2, 'human', $3, 0)
            """, session_id, next_idx, human_msg)

            # Assistant response
            await conn.execute("""
                INSERT INTO query_logs (session_id, turn_index, role, content, hop_count)
                VALUES ($1, $2, 'assistant', $3, $4)
            """, session_id, current_max, ai_msg, hop_count)

        return current_max


async def get_session_history(session_id: str, max_turns: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves conversation history for a session as a list of
    {"role", "content", "created_at", "turn_index", "feedback"} dicts,
    ordered by turn_index ASC.

    If max_turns is provided, returns only the last N *pairs*
    (i.e. last max_turns human+assistant exchanges = max_turns*2 rows).
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        if max_turns is not None:
            rows = await conn.fetch("""
                SELECT role, content, created_at, turn_index, feedback
                FROM query_logs
                WHERE session_id = $1
                ORDER BY turn_index DESC
                LIMIT $2;
            """, session_id, max_turns * 2)
            rows = list(reversed(rows))
        else:
            rows = await conn.fetch("""
                SELECT role, content, created_at, turn_index, feedback
                FROM query_logs
                WHERE session_id = $1
                ORDER BY turn_index ASC;
            """, session_id)

        return [
            {
                "role": r["role"],
                "content": r["content"],
                "created_at": str(r["created_at"]),
                "turn_index": r["turn_index"],
                "feedback": r["feedback"]
            }
            for r in rows
        ]


async def get_session_record(session_id: str) -> Optional[Dict[str, Any]]:
    """Fetches full session row including hmac_token, ip, device, last_active."""
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT session_id, hmac_token, ip_address, device_signature, created_at, last_active
            FROM chat_sessions WHERE session_id = $1;
        """, session_id)
        return dict(row) if row else None


async def save_feedback(session_id: str, turn_index: int, feedback: str):
    """
    Saves a like/dislike rating for a specific message in query_logs.
    Updates the feedback column on the existing row (upsert-style).
    Only 'assistant' role messages should be rated.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE query_logs
            SET feedback = $3
            WHERE session_id = $1
              AND turn_index = $2
              AND role = 'assistant';
        """, session_id, turn_index, feedback)
        return result  # e.g. "UPDATE 1" or "UPDATE 0"


async def cleanup_expired_sessions(expiry_hours: int):
    """
    Deletes sessions inactive longer than expiry_hours.
    CASCADE will automatically delete their query_logs rows.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(f"""
            DELETE FROM chat_sessions
            WHERE last_active < CURRENT_TIMESTAMP - INTERVAL '{expiry_hours} hours';
        """)
        return result

# ---------------------------------------------------------
# WhatsApp Menu State & Tracking (Template Mode)
# ---------------------------------------------------------

async def setup_whatsapp_template_tables(conn):
    """
    Creates lightweight tracking tables strictly for the menu state machine.
    This runs completely isolated from the RAG query_logs.
    """
    # Drop the old standalone table if it exists
    await conn.execute("DROP TABLE IF EXISTS whatsapp_template_sessions CASCADE;")

    # Menu Logs: Linear tracking of messages sent in Template Mode
    # Now references chat_sessions instead of the old standalone table
    # We must explicitly drop the old version so the 'session_id' column change takes effect
    await conn.execute("DROP TABLE IF EXISTS whatsapp_template_logs CASCADE;")

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_template_logs (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
            content TEXT NOT NULL,
            node TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

async def get_menu_session(session_id: str, timeout_sec: int) -> Optional[str]:
    """
    Returns the current_menu_node for a session_id if it exists and hasn't expired.
    Otherwise returns None, prompting a reset to root_menu.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT current_menu_node, last_active 
            FROM chat_sessions 
            WHERE session_id = $1
        """, session_id)

        if not row or row['current_menu_node'] is None:
            return None

        # Check expiration logic
        from datetime import datetime, timezone
        time_diff = (datetime.now(timezone.utc) - row['last_active']).total_seconds()
        
        if time_diff > timeout_sec:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Menu session for {session_id} expired ({time_diff}s > {timeout_sec}s).")
            # Nullify the template state without deleting the whole RAG session
            await conn.execute("UPDATE chat_sessions SET current_menu_node = NULL WHERE session_id = $1", session_id)
            return None
            
        return row['current_menu_node']

async def set_menu_session(session_id: str, current_node: str):
    """
    Updates the user's current menu node and last_active.
    We assume the session was already created via ensure_session in the router.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE chat_sessions
            SET current_menu_node = $2,
                last_active = CURRENT_TIMESTAMP
            WHERE session_id = $1
        """, session_id, current_node)

async def log_menu_interaction(session_id: str, role: str, content: str, node: Optional[str] = None):
    """
    Inserts a fast lightweight tracking log for template mode interactions.
    """
    pool = await Config.get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO whatsapp_template_logs (session_id, role, content, node)
            VALUES ($1, $2, $3, $4)
        """, session_id, role, content, node)


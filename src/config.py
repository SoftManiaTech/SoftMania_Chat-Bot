import os
import asyncpg
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()

# Neon PGVector Settings
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")

# Neo4j Settings
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", NEO4J_USERNAME)

# Mistral Settings
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

class Config:
    _neo4j_graph = None
    _pg_pool = None
    
    # Central LLM Configurations
    PRIMARY_LLM_MODEL = "mistral-large-latest"
    EMBEDDING_MODEL = "mistral-embed"
    DEFAULT_TEMPERATURE = 0.2
    
    # Ingestion Parameters
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Retrieval & Reasoning Parameters
    TOP_K_RESULTS = 5
    MAX_HOP_COUNT = 3

    @classmethod
    def get_neo4j_graph(cls):
        """Returns the LangChain Neo4jGraph integration instance."""
        if cls._neo4j_graph is None and NEO4J_URI:
            cls._neo4j_graph = Neo4jGraph(
                url=NEO4J_URI,
                username=NEO4J_USERNAME,
                password=NEO4J_PASSWORD,
                database=NEO4J_DATABASE
            )
        return cls._neo4j_graph

    @classmethod
    async def get_pg_pool(cls):
        """Returns an asyncpg connection pool for Neon PGVector."""
        neon_url = os.getenv("NEON_DATABASE_URL")
        if not neon_url:
            raise ValueError("NEON_DATABASE_URL environment variable is missing. Please set it in your .env file or Hugging Face Space Secrets.")
            
        if cls._pg_pool is None:
            cls._pg_pool = await asyncpg.create_pool(
                dsn=neon_url,
                min_size=1,
                max_size=20 # PgBouncer on Neon can handle this
            )
        return cls._pg_pool

    @classmethod
    async def close_all(cls):
        """Closes all active database connection pools."""
        # Neo4jGraph handles its own connection lifecycle, so we only close PG
        if cls._pg_pool:
            await cls._pg_pool.close()

    @classmethod
    def get_llm(cls, temperature: float = None):
        """Returns the configured LLM instance for extraction and reasoning."""
        from langchain_mistralai import ChatMistralAI
        temp = temperature if temperature is not None else cls.DEFAULT_TEMPERATURE
        return ChatMistralAI(
            model=cls.PRIMARY_LLM_MODEL, 
            temperature=temp, 
            api_key=MISTRAL_API_KEY
        )

    @classmethod
    def get_embeddings(cls):
        """Returns the configured Embeddings instance."""
        from langchain_mistralai import MistralAIEmbeddings
        return MistralAIEmbeddings(
            model=cls.EMBEDDING_MODEL, 
            api_key=MISTRAL_API_KEY
        )

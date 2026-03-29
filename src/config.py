import os
import asyncpg
from dotenv import load_dotenv
from typing import Optional
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
    
    # ---------------------------------------------------------
    # Server & Networking
    # ---------------------------------------------------------
    PORT = int(os.getenv("PORT", 7860))
    HOST = os.getenv("HOST", "0.0.0.0")
    SPACE_HOST = os.getenv("SPACE_HOST", "")
    
    # ---------------------------------------------------------
    # Hugging Face Settings
    # ---------------------------------------------------------
    HF_HOME = os.getenv("HF_HOME", os.path.abspath("./.cache/huggingface"))
    LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "false").lower() != "false"
    
    # ---------------------------------------------------------
    # Cookie & Security
    # ---------------------------------------------------------
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"
    
    # ---------------------------------------------------------
    # WhatsApp Settings
    # ---------------------------------------------------------
    WA_PHONE_ID = os.getenv("WA_PHONE_ID", "YOUR_PHONE_ID")
    WA_TOKEN = os.getenv("WA_TOKEN", "YOUR_PERMANENT_TOKEN")
    WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "c7396c9a2023d3c8e135f4d502ae9598")
    META_APP_SECRET = os.getenv("META_APP_SECRET", "")  # For webhook signature verification
    
    # Central LLM Configurations
    PRIMARY_LLM_MODEL = "mistral-large-latest"         # Used by ingestion (extraction)
    FAST_LLM_MODEL = "open-mistral-nemo"               # Used by agent (router, decomposer, compressor, synthesizer)
    EMBEDDING_MODEL = "mistral-embed"
    DEFAULT_TEMPERATURE = 0.2
    
    # Ingestion Parameters
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    
    # Retrieval & Reasoning Parameters
    TOP_K_RESULTS = 5
    MAX_HOP_COUNT = 3
    HISTORY_MAX_TURNS = int(os.getenv("HISTORY_MAX_TURNS", "0"))  # Number of previous Q&A turns to remember
    # Session Management
    SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "72"))  # Sessions expire after N hours of inactivity
    SESSION_HMAC_SECRET = os.getenv("SESSION_HMAC_SECRET", "softmania-default-secret-change-in-production")
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")  # Protect admin endpoints
    MAX_QUERY_LENGTH = 2000       # Max characters per user query
    # Rate & Concurrency Limits for Production
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "300"))    # Max queries per session per minute
    WA_RATE_LIMIT = int(os.getenv("WA_RATE_LIMIT", "10"))        # Max WhatsApp messages per phone per window
    WA_RATE_WINDOW = int(os.getenv("WA_RATE_WINDOW", "60"))      # Rate limit window in seconds
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))     # Stop retrying after N times to prevent Thundering Herd
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "15"))            # Hard timeout in seconds for LLM APIs
    LLM_CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY_LIMIT", "10")) # Global semaphore for LLM endpoints

    # WhatsApp Behavior Toggle
    WA_USE_AGENT = os.getenv("WA_USE_AGENT", "false").lower() == "true"
    WA_STATIC_RESPONSE = os.getenv("WA_STATIC_RESPONSE", "Hello! We've received your message. SoftMania AI Agent is currently in 'Maintenance Mode'. We will get back to you soon!")
    # WhatsApp Bot Status false = maintenance mode, true = online
    WA_STATUS = os.getenv("WA_STATUS", "false").lower() == "true"
    # Path to the WhatsApp menu state-machine config (JSON)
    WA_MENU_CONFIG_PATH = os.getenv("WA_MENU_CONFIG_PATH", "src/whatsapp/menu_config.json")
    # Menu session timeout in seconds (default 30 minutes)
    WA_MENU_SESSION_TIMEOUT = int(os.getenv("WA_MENU_SESSION_TIMEOUT", "1800"))

    # Application Environment
    APP_ENV = os.getenv("APP_ENV", "production")

    @classmethod
    def is_dev(cls) -> bool:
        """Returns True if running in local development mode, False for production."""
        return cls.APP_ENV == "development"


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
    def get_llm(cls, temperature: Optional[float] = None):
        """Returns the configured LLM instance for extraction and reasoning."""
        from langchain_mistralai import ChatMistralAI
        temp = temperature if temperature is not None else cls.DEFAULT_TEMPERATURE
        return ChatMistralAI(
            model=cls.PRIMARY_LLM_MODEL, 
            temperature=temp, 
            api_key=MISTRAL_API_KEY,
            max_retries=cls.LLM_MAX_RETRIES,
            timeout=cls.LLM_TIMEOUT
        )

    @classmethod
    def get_fast_llm(cls, temperature: float = 0.0):
        """Returns a fast, lightweight LLM for routing, decomposition, and compression."""
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model=cls.FAST_LLM_MODEL,
            temperature=temperature,
            api_key=MISTRAL_API_KEY,
            max_retries=cls.LLM_MAX_RETRIES,
            timeout=cls.LLM_TIMEOUT
        )

    @classmethod
    def get_embeddings(cls):
        """Returns the configured Embeddings instance."""
        from langchain_mistralai import MistralAIEmbeddings
        return MistralAIEmbeddings(
            model=cls.EMBEDDING_MODEL, 
            api_key=MISTRAL_API_KEY
        )

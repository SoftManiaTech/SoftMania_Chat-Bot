import asyncio
from pathlib import Path
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader,
    BSHTMLLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredMarkdownLoader
)
from src.ingestion.chunker import create_chunks
from src.ingestion.extractor import parse_with_llm
from src.ingestion.vector_db import setup_pgvector_tables, batch_insert_chunks
from src.ingestion.graph_db import batch_insert_graph
from src.config import Config
from typing import Dict, Any
from src.logger import setup_logger

logger = setup_logger(__name__)

async def ingest_document(file_path: str) -> Dict[str, Any]:
    """
    Main orchestration function for Local Data Ingestion.
    Loads a file, semantic chunks it, extracts a knowledge graph,
    and saves both vector embeddings (Neon) and graph edges (Neo4j).
    """
    logger.info(f"--- Starting Ingestion Process for: {file_path} ---")
    
    # 1. Load the document locally
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
        
    logger.info("Loading document content...")
    suffix = path.suffix.lower()
    
    loader_mapping = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".html": BSHTMLLoader,
        ".htm": BSHTMLLoader,
        ".docx": Docx2txtLoader,
        ".csv": CSVLoader,
        ".md": UnstructuredMarkdownLoader
    }
    
    if suffix not in loader_mapping:
        raise ValueError(f"Unsupported file extension: {suffix}")
        
    loader_class = loader_mapping[suffix]
    if loader_class == TextLoader:
        loader = loader_class(str(path), autodetect_encoding=True)
    else:
        loader = loader_class(str(path))
    
    docs = loader.load()
    
    # If a loader generates multiple docs (e.g. per page), we consolidate them
    # to ensure our chunker gets the full text.
    full_text = "\n\n".join([doc.page_content for doc in docs])
    
    doc_id = path.stem # Use filename as the root document ID
    logger.info(f"Loaded document. Assigned root doc_id: '{doc_id}'")

    # 2. Setup Vector DB Tables
    logger.info("Verifying Neon PGVector Schema...")
    await setup_pgvector_tables()

    # 3. Chunk Document
    # We chunk locally so we don't overwhelm the Mistral extraction context window
    logger.info("Applying Semantic Chunking...")
    text_chunks = create_chunks(full_text)
    logger.info(f"Split document into {len(text_chunks)} distinct chunks.")
    
    # 4. Process each chunk
    total_nodes = 0
    total_rels = 0
    
    for i, doc in enumerate(text_chunks):
        chunk_id = f"{doc_id}_chunk_{i}"
        text = doc.page_content
        logger.info(f"\n[{i+1}/{len(text_chunks)}] Processing Chunk ID: {chunk_id}")
        
        # 4a. Vector Embedding Pipeline
        # Get Mistral embeddings (1024 dims)
        logger.info("   -> Generating Vectors (Mistral Embeddings)...")
        embeddings = Config.get_embeddings()
        vector = await embeddings.aembed_query(text)
        
        chunk_data = [{
            "chunk_id": chunk_id,
            "text": text,
            "embedding": vector,
            "metadata": {"source": path.name, "chunk_index": i}
        }]
        
        # Save to Neon PGVector
        logger.info("   -> Saving Vector to Neon Database...")
        await batch_insert_chunks(doc_id, chunk_data)
        
        # 4b. Graph Extraction Pipeline
        logger.info("   -> Extracting Entities & Relationships (Mistral LLM)...")
        extractions = parse_with_llm([doc])
        if not extractions:
            logger.warning("   -> No extraction results returned.")
            continue
        
        extraction = extractions[0][2]
        
        num_nodes = len(extraction.nodes)
        num_rels = len(extraction.relationships)
        total_nodes += num_nodes
        total_rels += num_rels
        
        logger.info(f"   -> Found {num_nodes} nodes and {num_rels} relationships.")

        # Save to Neo4j
        logger.info("   -> Saving Sub-Graph to Neo4j Database...")
        await batch_insert_graph(doc_id, chunk_id, extraction)
        
        logger.info(f"   ✓ Chunk {i+1} successfully stored in both databases linked by doc_id='{doc_id}'.")
        
    logger.info("\n--- Ingestion Complete! ---")
    
    return {
        "status": "completed",
        "doc_id": doc_id,
        "chunks_processed": len(text_chunks),
        "nodes_extracted": total_nodes,
        "relationships_extracted": total_rels
    }

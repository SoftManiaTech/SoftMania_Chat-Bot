import uuid
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config import Config

def create_chunks(text: str, doc_id: str = None) -> List[Document]:
    """
    Splits raw text into semantic chunks for ingestion.
    Each chunk gets a unique chunk_id and inherits the doc_id for linking.
    """
    if not doc_id:
        doc_id = str(uuid.uuid4())
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    
    documents = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_chunk_{i}"
        doc = Document(
            page_content=chunk,
            metadata={
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_index": i
            }
        )
        documents.append(doc)
        
    return documents

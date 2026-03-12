import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from src.agent.graph import graph_app
from src.ingestion.orchestrator import ingest_document
from src.ingestion.vector_db import clear_all_vectors
from src.ingestion.graph_db import clear_all_graph_data

app = FastAPI(title="Advanced Multi-Hop RAG API")

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    hop_count: int

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/html",
    "text/csv",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # .docx
    "application/xml",
    "text/xml"
}

@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """
    API endpoint to upload a document, chunk it, extract Knowledge Graph entities,
    and save them into PGVector and Neo4j.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415, 
            detail=f"Unsupported Media Type: {file.content_type}. Please upload text, pdf, html, csv, or docx."
        )
        
    try:
        # Create a temp directory for uploads if it doesn't exist
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        # Save the uploaded file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run the ingestion orchestrator
        result = await ingest_document(file_path)
        
        # Clean up the file after processing
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # result returns {"status": "completed", ...} as requested
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    try:
        # We start the LangGraph with just the question.
        initial_state = {"question": request.question, "hop_count": 0, "retrieved_context": []}
        
        # We use ainvoke for asynchronous execution of the graph
        # This will trace automatically via LangSmith if LANGCHAIN_TRACING_V2 is set
        result = await graph_app.ainvoke(initial_state)
        
        return QueryResponse(
            answer=result.get("final_answer", "No answer generated."),
            hop_count=result.get("hop_count", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear")
async def clear_database():
    """
    Completely purges all data from the Vector Database and the 
    Knowledge Graph, acting as a full reset.
    """
    try:
        await clear_all_vectors()
        await clear_all_graph_data()
        return {"status": "success", "message": "All database records have been purged."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

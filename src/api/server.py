import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.agent.graph import graph_app
from src.ingestion.orchestrator import ingest_document
from src.ingestion.vector_db import clear_all_vectors, insert_query_log
from src.ingestion.graph_db import clear_all_graph_data
from src.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="SoftMania Chat-Bot API")

# CORS — allow iframe embedding and cross-origin requests from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (widget.html lives here)
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# ── Landing Page with Usage Guide & Embed Code ──
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SoftMania Chat-Bot API</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0a0f;color:#e2e2f0;min-height:100vh}
  .container{max-width:780px;margin:0 auto;padding:48px 24px}
  h1{font-size:28px;background:linear-gradient(135deg,#6366f1,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}
  .sub{color:#888;font-size:14px;margin-bottom:36px}
  h2{font-size:18px;color:#a5b4fc;margin:32px 0 12px;display:flex;align-items:center;gap:8px}
  p,li{font-size:14px;line-height:1.7;color:#bbb}
  table{width:100%;border-collapse:collapse;margin:12px 0 24px}
  th,td{text-align:left;padding:10px 14px;font-size:13px;border-bottom:1px solid rgba(255,255,255,.06)}
  th{color:#a5b4fc;font-weight:600;background:#12121a}
  td{color:#ccc}
  td code{background:#1e1e2e;padding:2px 6px;border-radius:4px;font-size:12px;color:#c4b5fd}
  .code-block{background:#12121a;border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:16px;margin:10px 0 24px;overflow-x:auto;position:relative}
  .code-block code{font-family:'Cascadia Code','Fira Code',monospace;font-size:12.5px;color:#c4b5fd;white-space:pre;display:block}
  .copy-btn{position:absolute;top:8px;right:10px;background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:6px;font-size:11px;cursor:pointer;opacity:.8;transition:opacity .15s}
  .copy-btn:hover{opacity:1}
  .badge{display:inline-block;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600}
  .get{background:rgba(34,197,94,.15);color:#4ade80}
  .post{background:rgba(59,130,246,.15);color:#60a5fa}
  .del{background:rgba(239,68,68,.15);color:#f87171}
  .preview{margin-top:20px;border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,.06)}
  .preview iframe{width:100%;height:540px;border:none}
  .footer{text-align:center;color:#555;font-size:12px;margin-top:48px;padding-top:24px;border-top:1px solid rgba(255,255,255,.06)}
</style>
</head>
<body>
<div class="container">
  <h1>🚀 SoftMania Chat-Bot API</h1>
  <p class="sub">Hybrid LangGraph Agent · Neon PGVector · Neo4j Knowledge Graph</p>

  <h2>📡 API Endpoints</h2>
  <table>
    <tr><th>Method</th><th>Endpoint</th><th>Description</th></tr>
    <tr><td><span class="badge get">GET</span></td><td><code>/health</code></td><td>Health check</td></tr>
    <tr><td><span class="badge post">POST</span></td><td><code>/query</code></td><td>Interact with the intelligence engine</td></tr>
    <tr><td><span class="badge post">POST</span></td><td><code>/ingest</code></td><td>Upload a document for ingestion</td></tr>
    <tr><td><span class="badge del">DELETE</span></td><td><code>/clear</code></td><td>Purge all database records</td></tr>
  </table>

  <h2>💬 Embeddable Chat Widget</h2>
  <p>Copy the snippet below to embed the chatbot on any website:</p>
  <div class="code-block">
    <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('embed-code').textContent)">Copy</button>
    <code id="embed-code">&lt;iframe
  src="{BASE_URL}/static/widget.html"
  width="420" height="580"
  style="border:none;position:fixed;bottom:0;right:0;z-index:9999;"
  allow="clipboard-read; clipboard-write"&gt;
&lt;/iframe&gt;</code>
  </div>

  <h2>🔍 Live Preview</h2>
  <div class="preview">
    <iframe src="/static/widget.html" title="Chat Widget Preview"></iframe>
  </div>

  <div class="footer">SoftMania Technologies · Intelligence Engine · Powered by LangGraph</div>
</div>

<!-- Render the actual Chatbot Widget on this Landing Page -->
<iframe src="{BASE_URL}/static/widget.html"
        width="420" height="580"
        style="border:none;position:fixed;bottom:0;right:0;z-index:9999;"
        allow="clipboard-read; clipboard-write">
</iframe>

</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Landing page with usage guide and embeddable widget preview."""
    from starlette.requests import Request
    # Inject the actual base URL for the embed snippet
    base_url = os.getenv("SPACE_HOST", "")
    if base_url and not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    if not base_url:
        base_url = "https://rsnarsna-advanced-multi-hop-rag.hf.space"
    return HTMLResponse(content=LANDING_HTML.replace("{BASE_URL}", base_url))

@app.get("/health")
async def health_check():
    """Health check endpoint for container probes."""
    return {"status": "healthy", "service": "SoftMania Chat-Bot API"}

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
        
    logger.info(f"--- API REQUEST: /ingest --- Received file: {file.filename}")
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
        logger.info(f"--- API RESPONSE: /ingest --- Successfully ingested: {file.filename}")
        return result
        
    except Exception as e:
        logger.error(f"--- API ERROR: /ingest --- {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_softmania(request: QueryRequest):
    logger.info(f"--- API REQUEST: /query --- Question: '{request.question}'")
    try:
        # We start the LangGraph with just the question.
        initial_state = {"question": request.question, "hop_count": 0, "retrieved_context": []}
        
        # We use ainvoke for asynchronous execution of the graph
        # This will trace automatically via LangSmith if LANGCHAIN_TRACING_V2 is set
        result = await graph_app.ainvoke(initial_state)
        
        answer = result.get("final_answer", "No answer generated.")
        hop_count = result.get("hop_count", 0)
        
        # Log the request/response pair into the un-deletable table
        await insert_query_log(request.question, answer, hop_count)
        
        logger.info(f"--- API RESPONSE: /query --- Generated answer in {hop_count} hops.")
        return QueryResponse(
            answer=answer,
            hop_count=hop_count
        )
    except Exception as e:
        logger.error(f"--- API ERROR: /query --- {e}")
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

import os
import re
import hmac
import hashlib
import shutil
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from src.agent.graph import graph_app
from src.ingestion.orchestrator import ingest_document
from src.ingestion.vector_db import (
    clear_all_vectors,
    get_all_portal_links,
    get_session_history,
    ensure_session,
    append_turn,
    get_session_record,
    save_feedback,
    cleanup_expired_sessions,
    setup_pgvector_tables
)
from src.ingestion.graph_db import clear_all_graph_data
from src.api.active_links import router as links_router
from src.config import Config
from src.logger import setup_logger
import uuid
from fastapi import Request, Response
from langchain_core.messages import HumanMessage, AIMessage

logger = setup_logger(__name__)

# UUID v4 format validation regex
UUID4_REGEX = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# ---------------------------------------------------------
# HMAC Session Security
# ---------------------------------------------------------

def generate_hmac_token(session_id: str, ip: str, user_agent: str) -> str:
    """Generates an HMAC-SHA256 token binding a session to its origin."""
    secret = Config.SESSION_HMAC_SECRET.encode()
    message = f"{session_id}:{ip}:{user_agent}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

def verify_hmac_token(token: str, session_id: str, ip: str, user_agent: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    expected = generate_hmac_token(session_id, ip, user_agent)
    return hmac.compare_digest(token, expected)

async def validate_or_create_session(
    session_id: Optional[str],
    token: Optional[str],
    request: Request
) -> tuple:
    """
    Validates an existing session or creates a new one.
    Returns: (valid_session_id, valid_token, is_new_session)
    """
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("User-Agent", "unknown")

    # Case 1: No session provided → create new
    if not session_id or not token:
        new_id = str(uuid.uuid4())
        new_token = generate_hmac_token(new_id, ip, ua)
        await ensure_session(new_id, new_token, ip, ua)
        logger.info(f"New session created: {new_id}")
        return (new_id, new_token, True)

    # Case 2: Session provided — validate format
    if not UUID4_REGEX.match(session_id):
        logger.warning(f"Invalid session_id format rejected: {session_id[:50]}")
        new_id = str(uuid.uuid4())
        new_token = generate_hmac_token(new_id, ip, ua)
        await ensure_session(new_id, new_token, ip, ua)
        return (new_id, new_token, True)

    # Case 3: Check if session exists in DB
    record = await get_session_record(session_id)
    if not record:
        logger.warning(f"Session not found in DB: {session_id}")
        new_id = str(uuid.uuid4())
        new_token = generate_hmac_token(new_id, ip, ua)
        await ensure_session(new_id, new_token, ip, ua)
        return (new_id, new_token, True)

    # Case 4: Verify HMAC token
    if not hmac.compare_digest(record["hmac_token"], token):
        logger.warning(f"HMAC mismatch for session: {session_id}")
        new_id = str(uuid.uuid4())
        new_token = generate_hmac_token(new_id, ip, ua)
        await ensure_session(new_id, new_token, ip, ua)
        return (new_id, new_token, True)

    # Case 5: Check expiry
    last_active = record["last_active"]
    expiry_delta = timedelta(hours=Config.SESSION_EXPIRY_HOURS)
    if datetime.now(timezone.utc) - last_active > expiry_delta:
        logger.info(f"Session expired: {session_id}")
        new_id = str(uuid.uuid4())
        new_token = generate_hmac_token(new_id, ip, ua)
        await ensure_session(new_id, new_token, ip, ua)
        return (new_id, new_token, True)

    # Case 6: Valid session — touch last_active
    await ensure_session(session_id, record["hmac_token"], ip, ua)
    return (session_id, record["hmac_token"], False)


app = FastAPI(title="SoftMania Chat-Bot API")

# Include the new Link Management router
app.include_router(links_router)

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

@app.on_event("startup")
async def startup_event():
    """Create DB tables on server boot if they don't exist."""
    logger.info("Running DB table setup on startup...")
    await setup_pgvector_tables()
    logger.info("DB tables ready.")

# ---------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    token: Optional[str] = None  # HMAC token for session validation

class QueryResponse(BaseModel):
    answer: str
    hop_count: int
    session_id: str
    token: str  # Return HMAC token to the client

class HistoryRequest(BaseModel):
    session_id: Optional[str] = None
    token: Optional[str] = None

class HistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    session_id: str
    token: str
    expired: bool

class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    token: Optional[str] = None
    turn_index: int
    feedback: str  # "like" or "dislike"

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
LANDING_HTML = """\
<!DOCTYPE html>
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
    <tr><td><span class="badge post">POST</span></td><td><code>/history</code></td><td>Fetch session conversation history</td></tr>
    <tr><td><span class="badge post">POST</span></td><td><code>/feedback</code></td><td>Submit like/dislike for a message</td></tr>
    <tr><td><span class="badge post">POST</span></td><td><code>/ingest</code></td><td>Upload a document for ingestion</td></tr>
    <tr><td><span class="badge del">DELETE</span></td><td><code>/clear</code></td><td>Purge all database records</td></tr>
  </table>

  <h2>💬 Embeddable Chat Widget</h2>
  <p>Copy the snippet below to embed the chatbot seamlessly on any website:</p>
  <div class="code-block">
    <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('embed-code').textContent)">Copy</button>
    <code id="embed-code">&lt;script&gt;
  (function(){
    var i=document.createElement('iframe');
    i.id="softmania-chat-widget";
    i.src="{BASE_URL}/static/widget.html";
    i.style.cssText="border:none;position:fixed;bottom:0;right:0;width:100px;height:100px;z-index:99999;transition:all 0.3s ease;color-scheme:light dark;background:transparent;";
    i.allow="clipboard-read; clipboard-write";
    document.body.appendChild(i);
    window.addEventListener("message", function(e){
      if(e.data === 'softmania-open') { i.style.width="420px"; i.style.height="580px"; }
      if(e.data === 'softmania-close') { i.style.width="100px"; i.style.height="100px"; }
      if(e.data === 'softmania-fullscreen') { i.style.width="100vw"; i.style.height="100vh"; }
      if(e.data === 'softmania-fullscreen-exit') { i.style.width="420px"; i.style.height="580px"; }
    });
  })();
&lt;/script&gt;</code>
  </div>

  <h2>🔍 Live Preview</h2>
  <div class="preview">
    <!-- Notice we don't resize the generic preview widget, as that simulates a mobile screen embed locally -->
    <iframe src="/static/widget.html" title="Chat Widget Preview"></iframe>
  </div>

  <div class="footer">SoftMania Technologies · Intelligence Engine · Powered by LangGraph</div>
</div>

<!-- Render the actual Chatbot Widget on this Landing Page using the above snippet -->
<script>
  (function(){
    var i=document.createElement('iframe');
    i.id="softmania-chat-widget";
    i.src="{BASE_URL}/static/widget.html";
    i.style.cssText="border:none;position:fixed;bottom:0;right:0;width:100px;height:100px;z-index:99999;transition:all 0.3s ease;color-scheme:light dark;background:transparent;";
    i.allow="clipboard-read; clipboard-write";
    document.body.appendChild(i);
    window.addEventListener("message", function(e){
      if(e.data === 'softmania-open') { i.style.width="420px"; i.style.height="580px"; }
      if(e.data === 'softmania-close') { i.style.width="100px"; i.style.height="100px"; }
      if(e.data === 'softmania-fullscreen') { i.style.width="100vw"; i.style.height="100vh"; }
      if(e.data === 'softmania-fullscreen-exit') { i.style.width="420px"; i.style.height="580px"; }
    });
  })();
</script>

</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page with usage guide and embeddable widget preview."""
    # Try getting SPACE_HOST first (for Hugging Face Spaces)
    base_url = Config.SPACE_HOST
    if base_url:
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"
    else:
        # Default to the current request URL (for local testing/other hosting)
        base_url = str(request.base_url).rstrip("/")
        
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
        
    if not Config.LOCAL_EMBEDDING_MODEL:
        raise HTTPException(
            status_code=503, 
            detail="Ingestion disabled: LOCAL_EMBEDDING_MODEL is false. Ingestion exclusively requires local embedding models."
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
async def query_softmania(request_body: QueryRequest, request: Request, response: Response):
    """
    Main entry point for queries. Uses HMAC session validation,
    normalized DB tables, and sliding-window conversation memory.
    """
    # Input sanitization — cap query length
    question = request_body.question.strip()
    if len(question) > Config.MAX_QUERY_LENGTH:
        question = question[:Config.MAX_QUERY_LENGTH]
    else:
        raise HTTPException(status_code=400, detail=f"Question exceeds maximum length of {Config.MAX_QUERY_LENGTH} characters.")   
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # 1. Validate or create session (HMAC + expiry check)
        session_id_in = request_body.session_id or request.cookies.get("session_id")
        token_in = request_body.token or request.cookies.get("session_token")
        session_id, token, is_new = await validate_or_create_session(
            session_id_in, token_in, request
        )
        
        if is_new:
            response.set_cookie(key="session_id", value=session_id, httponly=True, secure=Config.SESSION_COOKIE_SECURE, samesite="lax")
            response.set_cookie(key="session_token", value=token, httponly=True, secure=Config.SESSION_COOKIE_SECURE, samesite="lax")
            
        logger.info(f"--- API REQUEST: /query --- Session: {session_id} (new={is_new}) | Q: '{question[:80]}'")

        # 2. Fetch chat history (normalized rows from query_logs)
        # If HISTORY_MAX_TURNS is 0 or less, skip history retrieval to avoid
        # unnecessary DB calls and keep the chat context empty.
        chat_history = []
        try:
            if int(Config.HISTORY_MAX_TURNS) > 0:
                max_turns = int(Config.HISTORY_MAX_TURNS)
                raw_history = await get_session_history(session_id, max_turns=max_turns)

                # Convert normalized rows to LangChain Message objects
                for entry in raw_history:
                    if entry["role"] == "human":
                        chat_history.append(HumanMessage(content=entry["content"]))
                    elif entry["role"] == "assistant":
                        chat_history.append(AIMessage(content=entry["content"]))
            else:
                # No history retention configured; leave chat_history empty
                pass
        except Exception as e:
            logger.warning(f"Failed to fetch/parse session history: {e}")
            chat_history = []

        # 3. Fetch active links from the database to inject into the prompt
        try:
            links_data = await get_all_portal_links()
            formatted_links = "\n".join(
                f"- **{link['page_type'].title()}** ({link['domain']}): [{link['summary']}]({link['page_url']})"
                for link in links_data
            )
            if not formatted_links:
                formatted_links = "No active portal links currently available."
        except Exception as e:
            logger.warning(f"Failed to fetch portal links for injection: {e}")
            formatted_links = "Error fetching links."

        # 4. Invoke LangGraph with full context
        initial_state = {
            "question": question,
            "hop_count": 0,
            "retrieved_context": [],
            "portal_links": formatted_links,
            "chat_history": chat_history
        }

        result = await graph_app.ainvoke(initial_state)

        answer = result.get("final_answer", "No answer generated.")
        hop_count = result.get("hop_count", 0)

        # 5. Append this turn to query_logs (two rows: human + assistant)
        await append_turn(session_id, question, answer, hop_count)

        logger.info(f"--- API RESPONSE: /query --- Session: {session_id} | Answer complete.")
        return QueryResponse(
            answer=answer,
            hop_count=hop_count,
            session_id=session_id,
            token=token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"--- API ERROR: /query --- {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/history", response_model=HistoryResponse)
async def get_chat_history(request_body: HistoryRequest, request: Request, response: Response):
    """
    Fetches conversation history for a validated session.
    Returns the full history (all turns) for UI rendering.
    If session is expired/invalid, returns empty history with new credentials.
    """
    try:
        session_id_in = request_body.session_id or request.cookies.get("session_id")
        token_in = request_body.token or request.cookies.get("session_token")
        session_id, token, is_new = await validate_or_create_session(
            session_id_in, token_in, request
        )

        if is_new:
            response.set_cookie(key="session_id", value=session_id, httponly=True, secure=Config.SESSION_COOKIE_SECURE, samesite="lax")
            response.set_cookie(key="session_token", value=token, httponly=True, secure=Config.SESSION_COOKIE_SECURE, samesite="lax")
            # Old session was invalid or expired — return empty history
            return HistoryResponse(
                history=[],
                session_id=session_id,
                token=token,
                expired=True
            )

        # Fetch full history for UI rendering (not just the LLM window)
        history = await get_session_history(session_id)

        return HistoryResponse(
            history=history,
            session_id=session_id,
            token=token,
            expired=False
        )
    except Exception as e:
        logger.error(f"--- API ERROR: /history --- {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
async def submit_feedback(request_body: FeedbackRequest, request: Request, response: Response):
    """
    Saves a like/dislike rating for a specific bot message.
    Validates session HMAC before accepting.
    """
    # Validate feedback value
    if request_body.feedback not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="Feedback must be 'like' or 'dislike'.")

    try:
        session_id_in = request_body.session_id or request.cookies.get("session_id")
        token_in = request_body.token or request.cookies.get("session_token")
        session_id, token, is_new = await validate_or_create_session(
            session_id_in, token_in, request
        )

        if is_new:
            response.set_cookie(key="session_id", value=session_id, httponly=True, secure=Config.SESSION_COOKIE_SECURE, samesite="lax")
            response.set_cookie(key="session_token", value=token, httponly=True, secure=Config.SESSION_COOKIE_SECURE, samesite="lax")
            raise HTTPException(status_code=403, detail="Session invalid or expired.")

        # Save feedback to query_logs.feedback column
        result = await save_feedback(session_id, request_body.turn_index, request_body.feedback)

        if result and result.endswith("0"):
            raise HTTPException(status_code=404, detail="Message not found or not an assistant message.")

        return {"status": "ok", "session_id": session_id, "token": token}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"--- API ERROR: /feedback --- {e}")
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


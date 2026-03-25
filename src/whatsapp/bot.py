import hmac
import hashlib
import threading
import logging
from pywa import WhatsApp
from pywa.types import Button
from src.config import Config
from src.api.chat_engine import generate_agent_response

logger = logging.getLogger(__name__)

wa_client = None
_client_lock = threading.Lock()

def init_whatsapp_client():
    """
    Initializes the WhatsApp client for sending messages.
    Thread-safe singleton (Fix #16).
    """
    global wa_client
    if not wa_client:
        with _client_lock:
            if not wa_client:
                wa_client = WhatsApp(
                    phone_id=Config.WA_PHONE_ID,
                    token=Config.WA_TOKEN
                )
    return wa_client

def send_whatsapp_message(to_phone_number: str, text_content: str, preview_url: bool = False, turn_index: int = None, is_complex: bool = False):
    """
    Sends a basic text message to WhatsApp.
    If turn_index is provided AND is_complex is True, it appends an interactive feedback button payload.
    """
    client = init_whatsapp_client()
         
    logger.info(f"Sending WhatsApp message to {to_phone_number}...")
    
    # Send the main text message
    res = client.send_message(
        to=to_phone_number,
        text=text_content,
        preview_url=preview_url
    )
    
    # Send a separate interactive message with dynamic ID mapped buttons to avoid the 1024-char limit
    if turn_index is not None and is_complex:
        client.send_message(
            to=to_phone_number,
            text="Was this helpful?",
            buttons=[
                Button(title="👍 Yes", callback_data=f"like_{turn_index}"),
                Button(title="👎 No", callback_data=f"dislike_{turn_index}")
            ]
        )
        
    return res

async def process_whatsapp_message(from_number: str, text: str):
    """
    Business logic for handling a received WhatsApp message by passing it to the SoftMania LangGraph Agent.
    """
    text = text.strip() if text else ""
    logger.info(f"WhatsApp incoming message: '{text}' from {from_number}")
    
    if not text:
        send_whatsapp_message(from_number, "Please send a valid text message.")
        return
    
    # We use the WhatsApp Phone Number as the session ID for memory!
    try:
        from src.api.chat_engine import generate_agent_response
        from src.ingestion.vector_db import ensure_session

        # Fix #10: Generate proper HMAC token for WhatsApp sessions
        wa_hmac = hmac.new(Config.SESSION_HMAC_SECRET.encode(), from_number.encode(), hashlib.sha256).hexdigest()
        await ensure_session(from_number, wa_hmac, "whatsapp_api", "whatsapp_client")

        answer, hop_count, turn_index, is_complex = await generate_agent_response(session_id=from_number, question=text)
        send_whatsapp_message(from_number, answer, turn_index=turn_index, is_complex=is_complex)
    except Exception as e:
        logger.error(f"Error generating WhatsApp response: {e}")
        send_whatsapp_message(from_number, "Sorry, I encountered an internal error processing your request.")

async def process_whatsapp_interactive(from_number: str, button_id: str):
    """
    Handles interactive button clicks (like Feedback).
    """
    logger.info(f"WhatsApp interactive click: '{button_id}' from {from_number}")
    from src.ingestion.vector_db import save_feedback
    
    # Expected button_id format: e.g., "like_12" or "dislike_12"
    if button_id and (button_id.startswith("like_") or button_id.startswith("dislike_")):
        parts = button_id.split("_", 1)  # Split only once
        if len(parts) != 2:
            logger.warning(f"Malformed button_id: {button_id}")
            return
        
        # Fix #7: Validate turn_index is a non-negative integer
        try:
            turn_index = int(parts[1])
            if turn_index < 0:
                raise ValueError
        except (ValueError, IndexError):
            logger.warning(f"Invalid turn_index in button_id: {button_id}")
            return
        
        feedback_value = parts[0]
        await save_feedback(from_number, turn_index, feedback_value)
        # Send friendly conversational confirmation back to the user!
        send_whatsapp_message(from_number, "Thanks for your support or feedback!", turn_index=None)

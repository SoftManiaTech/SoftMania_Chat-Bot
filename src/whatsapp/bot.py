import hmac
import hashlib
import time
import threading
import logging
from pywa import WhatsApp
from pywa.types import Button
from src.config import Config
from src.whatsapp.menu_engine import (
    get_root_triggers,
    get_root_menu_message,
    process_menu_input,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WhatsApp Client — Thread-safe singleton
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Menu Session Store — In-memory, per phone number
# ---------------------------------------------------------------------------
# Maps phone_number -> { "current_node": str, "last_updated": float }
# Transient by design: resets on server restart (menu navigation is not persistent state).
_menu_sessions: dict[str, dict] = {}


def _get_menu_session(phone: str) -> dict | None:
    """Returns the active menu session for a phone, or None if expired/missing."""
    session = _menu_sessions.get(phone)
    if not session:
        return None
    timeout_sec = Config.WA_MENU_SESSION_TIMEOUT
    if time.time() - session["last_updated"] > timeout_sec:
        logger.info(f"Menu session for {phone} has expired. Clearing.")
        _menu_sessions.pop(phone, None)
        return None
    return session


def _set_menu_session(phone: str, node: str):
    """Creates or updates the menu session for a phone number."""
    _menu_sessions[phone] = {
        "current_node": node,
        "last_updated": time.time(),
    }


# ---------------------------------------------------------------------------
# Core Message Processor — 4-Priority Router
# ---------------------------------------------------------------------------

async def process_whatsapp_message(from_number: str, text: str):
    """
    4-Priority Router for all incoming WhatsApp messages.

    Priority 1 — Maintenance Gate:
        WA_STATUS=false → Always sends the static maintenance message.

    Priority 2 — Menu (State Machine) Mode:
        WA_STATUS=true, WA_USE_AGENT=false → Runs the config-driven state machine menu.

    Priority 3 — RAG Agent Mode:
        WA_STATUS=true, WA_USE_AGENT=true → Full LangGraph multi-hop AI response.
    """
    text = text.strip() if text else ""
    logger.info(f"WhatsApp incoming message: '{text}' from {from_number}")

    if not text:
        send_whatsapp_message(from_number, "Please send a valid text message.")
        return

    try:
        # ---------------------------------------------------------------
        # PRIORITY 1: Maintenance Mode
        # ---------------------------------------------------------------
        if not Config.WA_STATUS:
            logger.info(f"[MAINTENANCE] WhatsApp is OFFLINE. Sending static template to {from_number}.")
            send_whatsapp_message(from_number, Config.WA_STATIC_RESPONSE)
            return

        # ---------------------------------------------------------------
        # PRIORITY 2: Menu (State Machine) Mode
        # ---------------------------------------------------------------
        if not Config.WA_USE_AGENT:
            _handle_menu_mode(from_number, text)
            return

        # ---------------------------------------------------------------
        # PRIORITY 3: RAG Agent Mode
        # ---------------------------------------------------------------
        from src.api.chat_engine import generate_agent_response
        from src.ingestion.vector_db import ensure_session

        logger.info(f"[AGENT] Routing to RAG Agent for {from_number}.")
        # Generate HMAC session token for WhatsApp sessions
        wa_hmac = hmac.new(Config.SESSION_HMAC_SECRET.encode(), from_number.encode(), hashlib.sha256).hexdigest()
        await ensure_session(from_number, wa_hmac, "whatsapp_api", "whatsapp_client")

        answer, hop_count, turn_index, is_complex = await generate_agent_response(session_id=from_number, question=text)
        send_whatsapp_message(from_number, answer, turn_index=turn_index, is_complex=is_complex)

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
        send_whatsapp_message(from_number, "Sorry, I encountered an internal error processing your request.")


def _handle_menu_mode(from_number: str, text: str):
    """
    Handles all logic for Menu (State Machine) Mode.
    Called when WA_STATUS=true and WA_USE_AGENT=false.

    Sub-routing inside menu mode:
      Step A — Root Trigger: text is "menu", "hi", etc. → reset session to root_menu.
      Step B — Active Session: user is mid-menu → process transition.
      Step C — No Session, No Trigger → prompt to type 'menu'.
    """
    normalized = text.lower().strip()
    root_triggers = get_root_triggers()

    # Step A: Root trigger detected → reset to root menu
    if normalized in root_triggers:
        logger.info(f"[MENU] Root trigger '{text}' from {from_number}. Starting root_menu.")
        _set_menu_session(from_number, "root_menu")
        send_whatsapp_message(from_number, get_root_menu_message())
        return

    # Step B: Active session exists → process state transition
    session = _get_menu_session(from_number)
    if session:
        current_node = session["current_node"]
        logger.info(f"[MENU] {from_number} on node '{current_node}', input='{text}'")
        response, next_node = process_menu_input(current_node, text)
        _set_menu_session(from_number, next_node)
        send_whatsapp_message(from_number, response)
        return

    # Step C: No session, no trigger → guide the user to start
    logger.info(f"[MENU] No active session for {from_number}. Sending prompt.")
    send_whatsapp_message(from_number, "👋 Hi! Type *menu* to get started.")


# ---------------------------------------------------------------------------
# Interactive Button Handler (Feedback)
# ---------------------------------------------------------------------------

async def process_whatsapp_interactive(from_number: str, button_id: str):
    """
    Handles interactive button clicks (like/dislike Feedback from RAG mode).
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
        # Send friendly conversational confirmation back to the user
        send_whatsapp_message(from_number, "Thanks for your feedback! 🙏", turn_index=None)

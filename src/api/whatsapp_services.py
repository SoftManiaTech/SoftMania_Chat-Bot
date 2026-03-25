import hmac
import hashlib
import time
import logging
from collections import defaultdict
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
from src.config import Config
from src.whatsapp.bot import process_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WhatsApp"])

# Fix #9: Simple in-memory rate limiter per phone number
_rate_limit: dict = defaultdict(list)  # phone -> list of timestamps

def _is_rate_limited(phone: str) -> bool:
    now = time.time()
    _rate_limit[phone] = [t for t in _rate_limit[phone] if now - t < Config.WA_RATE_WINDOW]
    if len(_rate_limit[phone]) >= Config.WA_RATE_LIMIT:
        return True
    _rate_limit[phone].append(now)
    return False

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    WhatsApp webhook verification endpoint.
    """
    # print("--- GET /webhook ---")
    # print(f"hub.mode: {hub_mode}")
    # print(f"hub.challenge: {hub_challenge}")
    # print(f"hub.verify_token: {hub_verify_token}")
    # print(f"SERVER TOKEN: {Config.WA_VERIFY_TOKEN}")
    # print("--------------------")
    if hub_mode == "subscribe" and hub_verify_token == Config.WA_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    
    logger.warning("WhatsApp webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    WhatsApp webhook endpoint for receiving messages.
    """
    try:
        body_bytes = await request.body()

        # Fix #5: Verify Meta's X-Hub-Signature-256
        if Config.META_APP_SECRET:
            signature = request.headers.get("X-Hub-Signature-256", "")
            expected = "sha256=" + hmac.new(
                Config.META_APP_SECRET.encode(), body_bytes, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                logger.warning("WhatsApp webhook signature mismatch! Rejecting.")
                raise HTTPException(status_code=403, detail="Invalid signature")

        import json
        body = json.loads(body_bytes)
        logger.debug(f"Received WhatsApp webhook body")
        
        # WhatsApp returns JSON payload where message list is buried deep
        if "entry" in body and body["entry"]:
            for entry in body["entry"]:
                if "changes" in entry and entry["changes"]:
                    for change in entry["changes"]:
                        value = change.get("value", {})
                        if "messages" in value and value["messages"]:
                            for message in value["messages"]:
                                from_number = message.get("from")
                                message_type = message.get("type")
                                
                                # Fix #9: Per-phone rate limiting
                                if _is_rate_limited(from_number):
                                    logger.warning(f"Rate limited phone: {from_number}")
                                    continue
                                
                                if message_type == "text":
                                    text = message.get("text", {}).get("body", "")
                                    # Process the message logic
                                    await process_whatsapp_message(from_number, text)
                                elif message_type == "interactive":
                                    interactive = message.get("interactive", {})
                                    if interactive.get("type") == "button_reply":
                                        button_id = interactive.get("button_reply", {}).get("id")
                                        from src.whatsapp.bot import process_whatsapp_interactive
                                        await process_whatsapp_interactive(from_number, button_id)
                                else:
                                    logger.info(f"Received non-text message type: {message_type}")
                                    
        # Always return OK to acknowledge receipt
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return {"status": "ok"}

import logging
from src.agent.graph import graph_app
from src.ingestion.vector_db import get_session_history, get_all_portal_links, append_turn
from src.config import Config
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# Fix #12: Deterministic prompt injection filter
BLOCKED_PATTERNS = [
    "ignore previous", "ignore all instructions", "ignore above",
    "you are now", "act as", "pretend to be",
    "reveal your prompt", "show your system prompt", "system prompt",
    "disregard all", "forget your instructions",
]

def _is_prompt_injection(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in BLOCKED_PATTERNS)

async def generate_agent_response(session_id: str, question: str) -> tuple[str, int, int, bool]:
    """
    Core reusable logic to fetch chat history, fetch active links, invoke the
    LangGraph agent, and save the turn to the database.
    """
    # Fix #12: Block prompt injection before expensive LLM calls
    if _is_prompt_injection(question):
        logger.warning(f"Prompt injection blocked for session {session_id}: '{question[:80]}'")
        rejection = "I can only answer questions about SoftMania's services. Please ask a relevant question! \U0001f60a"
        turn_index = await append_turn(session_id, question, rejection, 0)
        return rejection, 0, turn_index, False

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
    except Exception as e:
        logger.warning(f"Failed to fetch/parse session history: {e}")

    # Fetch active links from the database to inject into the prompt
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

    # Invoke LangGraph with full context
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
    is_complex = result.get("is_complex", False)

    # Append this turn to query_logs (two rows: human + assistant)
    turn_index = await append_turn(session_id, question, answer, hop_count)

    return answer, hop_count, turn_index, is_complex
    
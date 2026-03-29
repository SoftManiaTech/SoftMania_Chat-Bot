"""
Menu Engine for SoftMania WhatsApp Bot.

A pure, stateless module responsible for all state-machine menu transitions.
It takes the current session node and user input, and returns the next
node key and the response message to send. No side effects.
"""
import json
import logging
import os
from functools import lru_cache
from src.config import Config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_menu_config() -> dict:
    """
    Load and cache the menu configuration from JSON file.
    Uses lru_cache so it's only read from disk once per process lifetime (O(n) once).
    """
    config_path = os.path.abspath(Config.WA_MENU_CONFIG_PATH)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"WhatsApp menu config loaded from: {config_path} (v{config.get('version', '?')})")
        return config
    except FileNotFoundError:
        logger.error(f"Menu config file not found at: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Menu config JSON is invalid: {e}")
        raise


def get_root_triggers() -> list[str]:
    """Returns the list of trigger words that reset the session to root_menu."""
    config = load_menu_config()
    return [t.lower() for t in config.get("settings", {}).get("root_trigger", ["menu"])]


def get_root_menu_message() -> str:
    """Returns the message text for the root_menu node."""
    config = load_menu_config()
    return config["nodes"]["root_menu"]["message"]


def process_menu_input(current_node: str, text: str) -> tuple[str, str]:
    """
    Core state-machine transition function.

    Given the user's current_node and their text input, computes:
      - response_message: The string to send back to the user.
      - next_node: The key of the next node the session should move to.

    This function is PURE (no I/O, no side effects). All state is passed in and returned.

    Args:
        current_node: The key of the node the user is currently on (e.g. "root_menu").
        text: The raw user text input (will be stripped internally).

    Returns:
        A tuple of (response_message: str, next_node: str).
    """
    config = load_menu_config()
    nodes = config["nodes"]
    fallback_message = config.get("settings", {}).get("fallback_message", "Invalid option.")

    # Safety: if the node doesn't exist in config, reset to root
    node = nodes.get(current_node)
    if not node:
        logger.warning(f"Unknown menu node: '{current_node}'. Resetting to root_menu.")
        return nodes["root_menu"]["message"], "root_menu"

    # Terminal nodes: they have no transitions. Just replay their message.
    if node.get("terminal", False):
        return node["message"], current_node

    # Normalize the user's input for matching
    user_choice = text.strip()

    # Check if choice matches a valid option
    next_node_key = node.get("options", {}).get(user_choice)

    if next_node_key:
        next_node = nodes.get(next_node_key)
        if next_node:
            return next_node["message"], next_node_key
        else:
            # Config integrity issue: option points to a non-existent node
            logger.error(f"Config error: node '{current_node}' option '{user_choice}' points to non-existent node '{next_node_key}'.")
            return nodes["root_menu"]["message"], "root_menu"

    # Invalid input: show fallback message + repeat the current node's menu
    fallback_node_key = node.get("fallback", current_node)
    fallback_node = nodes.get(fallback_node_key, node)
    combined_response = f"{fallback_message}\n\n{fallback_node['message']}"
    return combined_response, fallback_node_key

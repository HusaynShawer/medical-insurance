"""
tools.py — Builds Gemini FunctionDeclaration / Tool objects from the
single source of truth in shared.py.

OpenRouter and Claude agents use TOOLS_SCHEMA directly (plain dicts).
Gemini agent imports `booking_tools` from here.
"""

from google.generativeai.types import FunctionDeclaration, Tool
from app.agent.shared import TOOLS_SCHEMA


def _schema_to_gemini(tool: dict) -> FunctionDeclaration:
    """Convert a plain TOOLS_SCHEMA entry to a Gemini FunctionDeclaration."""
    return FunctionDeclaration(
        name=tool["name"],
        description=tool["description"],
        parameters=tool["parameters"],
    )


booking_tools = Tool(
    function_declarations=[_schema_to_gemini(t) for t in TOOLS_SCHEMA]
)
"""
state_manager.py — Explicit conversation state tracker.

Tracks everything collected so far so the agent NEVER has to re-ask.
State is passed alongside history on every turn and injected into the
system prompt so the model always sees it — even if history grows long.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import re


@dataclass
class ConversationState:
    # Core identity
    national_id: Optional[str] = None

    # Doctor booking
    symptom: Optional[str] = None
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    slot_id: Optional[int] = None
    slot_date: Optional[str] = None
    slot_time: Optional[str] = None

    # Services (lab/radiology)
    service_type: Optional[str] = None   # "lab_test" | "radiology"
    city: Optional[str] = None
    service_id: Optional[int] = None
    branch_id: Optional[int] = None
    service_slot_id: Optional[int] = None

    # Flow control
    current_flow: Optional[str] = None   # "doctor" | "service"
    step: Optional[str] = None           # e.g. "awaiting_slot", "awaiting_confirm"

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_prompt_block(self) -> str:
        """Render state as a clear block injected at the end of the system prompt."""
        d = self.to_dict()
        if not d:
            return ""
        lines = ["", "════════════════════════════════",
                 "CURRENT CONVERSATION STATE (already collected — do NOT ask again)",
                 "════════════════════════════════"]
        label_map = {
            "national_id":     "✅ national_id",
            "symptom":         "✅ symptom",
            "doctor_id":       "✅ doctor_id",
            "doctor_name":     "✅ doctor_name",
            "slot_id":         "✅ slot_id",
            "slot_date":       "✅ slot_date",
            "slot_time":       "✅ slot_time",
            "service_type":    "✅ service_type",
            "city":            "✅ city",
            "service_id":      "✅ service_id",
            "branch_id":       "✅ branch_id",
            "service_slot_id": "✅ service_slot_id",
            "current_flow":    "📍 current_flow",
            "step":            "📍 step",
        }
        for k, v in d.items():
            label = label_map.get(k, k)
            lines.append(f"  {label} = {v}")
        lines.append("════════════════════════════════")
        lines.append("Use the values above directly. Never ask for them again.")
        return "\n".join(lines)


def extract_state_from_tool_result(
    state: ConversationState,
    fn_name: str,
    fn_args: dict,
    result: dict,
) -> ConversationState:
    """
    After each tool call, update the state with anything new we learned.
    This is the single place where state is updated — no magic.
    """
    # Always capture national_id from args
    if fn_args.get("national_id"):
        state.national_id = fn_args["national_id"]

    if fn_name == "search_doctors":
        state.current_flow = "doctor"
        if fn_args.get("symptom"):
            state.symptom = fn_args["symptom"]

    elif fn_name == "get_slots":
        if fn_args.get("doctor_id"):
            state.doctor_id = fn_args["doctor_id"]
        if isinstance(result, dict) and result.get("doctor_name"):
            state.doctor_name = result["doctor_name"]

    elif fn_name == "confirm_booking":
        if fn_args.get("slot_id"):
            state.slot_id = fn_args["slot_id"]
        state.step = "booked"

    elif fn_name == "get_available_services":
        state.current_flow = "service"
        if fn_args.get("service_type"):
            state.service_type = fn_args["service_type"]
        if fn_args.get("city"):
            state.city = fn_args["city"]

    elif fn_name == "check_service_availability":
        if fn_args.get("service_id"):
            state.service_id = fn_args["service_id"]
        if fn_args.get("branch_id"):
            state.branch_id = fn_args["branch_id"]
        if isinstance(result, dict) and result.get("available"):
            state.step = "service_available"
            if result.get("slot_id"):
                state.service_slot_id = result["slot_id"]

    elif fn_name == "request_service":
        state.step = "service_booked"

    return state


def update_state_from_message(state: ConversationState, message: str) -> ConversationState:
    """
    Extract obvious info from user messages (national_id, city, service_type).
    This is a lightweight pre-pass — the LLM still does the real work.
    """
    # National ID: 14 digits
    match = re.search(r'\b\d{14}\b', message)
    if match and not state.national_id:
        state.national_id = match.group(0)

    # Service type keywords
    msg_lower = message.lower()
    if not state.service_type:
        radiology_keywords = ["أشعة", "اشعة", "radiology", "ray", "x-ray"]
        lab_keywords = ["تحاليل", "lab", "lab test", "تحليل"]
        if any(k in msg_lower for k in radiology_keywords):
            state.service_type = "radiology"
        elif any(k in msg_lower for k in lab_keywords):
            state.service_type = "lab_test"

    return state
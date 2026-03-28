import os
import inspect
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.functions import TOOL_EXECUTORS

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """
You are a medical booking assistant. Your only task is to execute tools and show results.

Mandatory sequence for doctor booking:
1. Ask for national_id if not provided.
2. Ask for symptoms.
3. Call search_doctors and display results exactly as returned.
4. Ask user: "Which doctor do you prefer?"
5. Call get_slots for the chosen doctor.
6. Show available slots as returned.
7. Ask user: "Which slot do you prefer?"
8. Request explicit confirmation: "Do you confirm booking with [doctor] on [slot]?"
9. After explicit confirmation, call confirm_booking.

After successful doctor booking (confirmed):
10. Ask: "Do you need any additional services? (lab tests / radiology / medicines)"
11. If yes, ask: "Do you want lab tests or radiology?"
12. Based on answer, call get_available_services with service_type="lab_test" or "radiology".
13. Display available services as returned.
14. Ask user to choose service, branch, date, and time.
15. Call check_service_availability.
16. If available, ask for explicit confirmation.
17. After confirmation, call request_service.
18. Inform user that the request is being processed.

Strict rules:
- Never invent doctor names; only use search_doctors results.
- Never use confirm_booking without doctor_id and slot_id from tools.
- Never book without explicit user confirmation.
- Always respond in the same language the user is using (Arabic or English).
- If a tool returns an error, explain the reason clearly.
"""

TOOLS = [
    {
        "name": "search_doctors",
        "description": "Search for available doctors based on national_id and symptoms. Returns list of doctors in user's network sorted by specialization and city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "14-digit national ID"},
                "symptom": {"type": "string", "description": "Symptoms or reason for visit"}
            },
            "required": ["national_id", "symptom"]
        }
    },
    {
        "name": "get_slots",
        "description": "Get available slots for a specific doctor. Use only after user selects a doctor from search_doctors results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "integer", "description": "Doctor ID from search_doctors"}
            },
            "required": ["doctor_id"]
        }
    },
    {
        "name": "confirm_booking",
        "description": "Confirm booking after explicit user confirmation. Only use after user confirms doctor and slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "National ID"},
                "doctor_id": {"type": "integer", "description": "Selected doctor ID"},
                "slot_id": {"type": "integer", "description": "Selected slot ID"}
            },
            "required": ["national_id", "doctor_id", "slot_id"]
        }
    },
    {
        "name": "get_available_services",
        "description": "Search for available services (lab tests / radiology) based on symptoms, city, and service type. Use after user chooses service type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "National ID"},
                "city": {"type": "string", "description": "User's city"},
                "symptom": {"type": "string", "description": "Symptoms (optional)"},
                "service_type": {"type": "string", "description": "Service type: lab_test or radiology"}
            },
            "required": ["national_id", "city"]
        }
    },
    {
        "name": "check_service_availability",
        "description": "Check if a specific service is available at a branch on a given date and time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "integer", "description": "Service ID from get_available_services"},
                "branch_id": {"type": "integer", "description": "Branch ID"},
                "requested_date": {"type": "string", "description": "Date in YYYY-MM-DD"},
                "requested_time": {"type": "string", "description": "Time in HH:MM:SS"}
            },
            "required": ["service_id", "branch_id", "requested_date", "requested_time"]
        }
    },
    {
        "name": "request_service",
        "description": "Request an additional service after explicit user confirmation. Only use after check_service_availability returns available=True.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "National ID"},
                "service_id": {"type": "integer", "description": "Service ID"},
                "branch_id": {"type": "integer", "description": "Branch ID"},
                "slot_id": {"type": "integer", "description": "Slot ID from check_service_availability"},
                "appointment_id": {"type": "integer", "description": "Optional: doctor appointment ID"}
            },
            "required": ["national_id", "service_id", "branch_id", "slot_id"]
        }
    }
]

async def run_claude_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:
    history = history + [{"role": "user", "content": message}]

    while True:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        history = history + [{"role": "assistant", "content": response.content}]

        if response.stop_reason != "tool_use":
            reply = next((b.text for b in response.content if hasattr(b, "text")), "")
            return reply, history

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            executor = TOOL_EXECUTORS.get(block.name)
            if not executor:
                result = {"error": f"Tool {block.name} not found"}
            elif "session" in inspect.signature(executor).parameters:
                result = await executor(**block.input, session=session)
            else:
                result = await executor(**block.input)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })

        history = history + [{"role": "user", "content": tool_results}]
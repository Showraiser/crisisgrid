"""
Manager Agent — ADK orchestrator that sequences the Ingestion, Reasoning,
and Dispatch sub-agents. Also exposes the ADK agent object for Vertex AI Agent Engine.
"""
from google.adk.agents import LlmAgent
from config import GEMINI_MODEL_FLASH
from agents.ingestion_agent import IngestionAgent, ingestion_agent
from agents.reasoning_agent import ReasoningAgent, reasoning_agent
from agents.dispatch_agent  import DispatchAgent,  dispatch_agent


# ── ADK multi-agent definition (for Vertex AI Agent Engine hosting) ───────────
#
#  The manager delegates to the three sub-agents as ADK sub-agents.
#  Vertex AI Agent Engine picks this up via the `agent` export at the
#  bottom of this file.
#
manager_agent = LlmAgent(
    name        = "manager_agent",
    model       = GEMINI_MODEL_FLASH,
    description = "Orchestrates the full CrisisGrid pipeline: ingest → reason → dispatch.",
    instruction = (
        "You are the CrisisGrid Manager Agent. "
        "Based on the trigger type in your context, delegate to the appropriate sub-agents:\n"
        "• trigger='new_report'        → run ingestion_agent only.\n"
        "• trigger='scheduled_dispatch' → run reasoning_agent to get the target zone, "
        "  then run dispatch_agent with that zone.\n"
        "Always return a summary of what was done."
    ),
    sub_agents = [ingestion_agent, reasoning_agent, dispatch_agent],
)

# This export is what Vertex AI Agent Engine looks for when you deploy with ADK
agent = manager_agent


# ── Synchronous convenience wrapper (used by FastAPI endpoints) ──────────────
class ManagerAgent:

    def __init__(self):
        self._ingestion  = IngestionAgent()
        self._reasoning  = ReasoningAgent()
        self._dispatch   = DispatchAgent()

    def run(self, context: dict) -> dict:
        trigger = context.get("trigger")
        results = {}
        print(f"Manager Agent: trigger='{trigger}'")

        if trigger == "new_report":
            results["ingestion"] = self._ingestion.run({})

        elif trigger in ("scheduled_dispatch", "manual_dispatch"):
            reasoning_result = self._reasoning.run({})
            results["reasoning"] = reasoning_result

            if reasoning_result and reasoning_result.get("targetZoneId"):
                results["dispatch"] = self._dispatch.run(reasoning_result)
            else:
                print("Manager Agent: reasoning returned no target — no dispatch needed.")

        else:
            print(f"Manager Agent: unknown trigger '{trigger}'")

        return results

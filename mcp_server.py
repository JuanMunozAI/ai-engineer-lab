"""mcp_server.py - offer the claim tools to any MCP app (Cline, Claude Desktop, ...).

The app starts this file itself; you don't run it by hand.
Same 5 tools as agent.py, written once, now with a standard plug.
"""
import os
from pathlib import Path

os.chdir(Path(__file__).parent)     # apps may start us from another folder; data/ and chroma_db/ live here

from mcp.server.mcpserver import MCPServer      # the "standard plug" kit (mcp 2.x)

import agent

mcp = MCPServer("lakeside-claims")


@mcp.tool()
def get_claim(claim_id: str) -> dict:
    """Get one insurance claim by its ID, e.g. C04: plan, procedures, fees, attachments, pre-auth."""
    return agent.get_claim(claim_id)


@mcp.tool()
def get_patient(patient_id: str) -> dict:
    """Get a fake patient by ID, e.g. P004: birth date, plan, member-since date, HMO assignment, past visits."""
    return agent.get_patient(patient_id)


@mcp.tool()
def search_office_manual(query: str) -> list[dict]:
    """Search the Lakeside office manual (plan rules, claim procedures, CDT code notes, policies)."""
    return agent.search_office_manual(query)


@mcp.tool()
def date_math(start: str, end: str) -> dict:
    """Exact time between two dates (YYYY-MM-DD): days, whole months, whole years."""
    return agent.date_math(start, end)


@mcp.tool()
def check_required_fields(claim_id: str) -> dict:
    """Rule check for required claim fields: tooth numbers, filling surfaces, quadrants, provider NPI."""
    return agent.check_required_fields(claim_id)


@mcp.tool()
def list_claims() -> list[dict]:
    """List all pending claims with their ID, patient, plan and date of service."""
    return [{k: c[k] for k in ("claim_id", "patient_id", "plan", "date_of_service")} for c in agent.CLAIMS.values()]


if __name__ == "__main__":
    mcp.run()                         # talks to the app over stdin/stdout

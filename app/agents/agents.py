"""Agent catalogue and tool-ownership validation for the banking assistant.

The banking agents are bounded tool groups, not autonomous LLMs. The supervisor
selects tools; the service validates ownership before calling the banking layer.
Policy and FAQ questions use the separate RAG pipeline represented by the
knowledge agent entry below.
"""
from dataclasses import dataclass
from typing import Any

from app.tools.registry import REGISTRY


@dataclass(frozen=True)
class AgentDefinition:
    """Human-readable role and tools assigned to one assistant agent."""

    name: str
    description: str
    tools: tuple[str, ...]
    implementation: str


@dataclass(frozen=True)
class BankingAgent:
    """Guard that prevents an agent from invoking another agent's tool."""

    name: str

    def validate(self, call: Any) -> Any:
        owner = REGISTRY.get(call.name, (None,))[0]
        if owner != self.name:
            raise ValueError("Tool does not belong to this agent")
        return call


_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    name: tuple(sorted(tool for tool, (owner, _writes) in REGISTRY.items() if owner == name))
    for name in {owner for owner, _writes in REGISTRY.values()}
}

AGENT_CATALOG: dict[str, AgentDefinition] = {
    "account": AgentDefinition(
        "account", "Account details, balances, transactions, and spending summaries.",
        _TOOL_NAMES["account"], "Banking tools / relational database",
    ),
    "payments": AgentDefinition(
        "payments", "Payment status and upcoming payment information.",
        _TOOL_NAMES["payments"], "Banking tools / relational database",
    ),
    "cards": AgentDefinition(
        "cards", "Card details and card blocking requests.",
        _TOOL_NAMES["cards"], "Banking tools / relational database",
    ),
    "loans": AgentDefinition(
        "loans", "Loan details and offer eligibility.",
        _TOOL_NAMES["loans"], "Banking tools / relational database",
    ),
    "fraud": AgentDefinition(
        "fraud", "Fraud verification and transaction dispute requests.",
        _TOOL_NAMES["fraud"], "Banking tools / relational database",
    ),
    "knowledge": AgentDefinition(
        "knowledge", "Approved policy and FAQ answers with document citations.",
        (), "RAG retrieval pipeline / FAISS vector store",
    ),
}

# Operational handlers are indexed by tool owner. Knowledge retrieval is invoked
# by the service's RAG path and therefore has no banking-tool validator.
AGENTS: dict[str, BankingAgent] = {
    name: BankingAgent(name) for name in _TOOL_NAMES
}


def describe_agents() -> list[dict[str, object]]:
    """Return a serializable catalogue suitable for diagnostics or UI display."""
    return [
        {
            "name": agent.name,
            "description": agent.description,
            "tools": list(agent.tools),
            "implementation": agent.implementation,
        }
        for agent in AGENT_CATALOG.values()
    ]

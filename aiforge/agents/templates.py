"""Agent templates and profiles — ready-made :class:`AgentConfig` factories.

These map directly onto the catalog's example projects so an application can
spin up a capable agent in one call.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from .agent import AgentConfig


def _cfg(**kwargs) -> AgentConfig:
    return AgentConfig(**kwargs)


TEMPLATES: Dict[str, Callable[[], AgentConfig]] = {
    "research_assistant": lambda: _cfg(
        name="research_assistant",
        role="researcher",
        description="Gathers and synthesises information using search and web tools.",
        system_prompt="Research thoroughly, cite tool outputs, and summarise findings clearly.",
        tools=["web_search", "http_request", "summarize_text"],
        permissions=["network"],
        max_steps=8,
    ),
    "browser_agent": lambda: _cfg(
        name="browser_agent",
        role="executor",
        description="Fetches and reads web pages to accomplish tasks.",
        system_prompt="Use HTTP tools to retrieve pages and extract the requested information.",
        tools=["http_request", "web_search", "summarize_text"],
        permissions=["network"],
    ),
    "coding_agent": lambda: _cfg(
        name="coding_agent",
        role="coder",
        description="Reads, writes, and reasons about code within a sandbox.",
        system_prompt="Write clean code, run calculations, and persist files in the sandbox.",
        tools=["read_file", "write_file", "list_dir", "calculator"],
        permissions=["fs"],
        max_steps=10,
    ),
    "file_assistant": lambda: _cfg(
        name="file_assistant",
        role="assistant",
        description="Organises and manipulates files in the sandbox.",
        tools=["read_file", "write_file", "list_dir"],
        permissions=["fs"],
    ),
    "document_analyst": lambda: _cfg(
        name="document_analyst",
        role="analyst",
        description="Reads documents and answers questions about them.",
        tools=["read_file", "summarize_text", "word_count"],
        permissions=["fs"],
    ),
    "customer_support_agent": lambda: _cfg(
        name="customer_support_agent",
        role="assistant",
        description="Answers customer questions from a knowledge base in memory.",
        system_prompt="Be empathetic, accurate, and escalate when unsure.",
        tools=["web_search"],
        use_memory=True,
    ),
    "meeting_assistant": lambda: _cfg(
        name="meeting_assistant",
        role="assistant",
        description="Summarises transcripts and extracts action items.",
        tools=["summarize_text", "word_count", "write_file"],
        permissions=["fs"],
    ),
    "cybersecurity_agent": lambda: _cfg(
        name="cybersecurity_agent",
        role="analyst",
        description="Analyses artifacts and reasons about security findings.",
        system_prompt="Assist only with authorised, defensive security analysis.",
        tools=["read_file", "calculator", "json_parse", "json_query"],
        permissions=["fs"],
    ),
    "data_analysis_agent": lambda: _cfg(
        name="data_analysis_agent",
        role="analyst",
        description="Computes metrics and reasons over structured data.",
        tools=["calculator", "json_parse", "json_query", "read_file"],
        permissions=["fs"],
    ),
    "automation_agent": lambda: _cfg(
        name="automation_agent",
        role="executor",
        description="Chains tools to automate multi-step tasks.",
        tools=["http_request", "read_file", "write_file", "calculator", "current_datetime"],
        permissions=["fs", "network"],
        max_steps=12,
    ),
}


def get_template(name: str) -> AgentConfig:
    if name not in TEMPLATES:
        raise KeyError(f"Unknown template '{name}'. Available: {list(TEMPLATES)}")
    return TEMPLATES[name]()


def list_templates() -> List[str]:
    return list(TEMPLATES)

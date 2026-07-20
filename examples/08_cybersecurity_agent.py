"""Cybersecurity Agent — defensive analysis of structured artifacts.

This example is strictly defensive: it parses a JSON finding and reasons about
severity. It never performs offensive actions.
Run: python examples/08_cybersecurity_agent.py
"""
import json

from aiforge.sdk import AIForge

FINDING = json.dumps(
    {
        "id": "CVE-DEMO-1",
        "component": "example-lib",
        "severity": "high",
        "description": "Improper input validation in the parser.",
    }
)


def main() -> None:
    forge = AIForge()
    agent = forge.agent("cybersecurity_agent", template="cybersecurity_agent")

    severity = forge.call_tool("json_query", text=FINDING, path="severity")
    print("Parsed severity:", severity.output)

    result = agent.run(
        "Given this finding, recommend a defensive remediation and a test to verify it: "
        + FINDING
    )
    print("ANALYSIS:", result.output)


if __name__ == "__main__":
    main()

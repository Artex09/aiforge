"""Browser Agent — fetches web pages via the HTTP tool and extracts information.

The http_request tool honours the config network allowlist. Offline, the mock
provider drives the loop deterministically.

Run: python examples/02_browser_agent.py
"""
from aiforge.sdk import AIForge


def main() -> None:
    forge = AIForge(overrides={"security": {"network_allowlist": ["example.com"]}})
    agent = forge.agent("browser_agent", template="browser_agent")

    task = "Search for 'AIForge multi-agent framework' and summarise the top result."
    result = agent.run(task)
    print("TASK:", task)
    print("RESULT:", result.output)


if __name__ == "__main__":
    main()

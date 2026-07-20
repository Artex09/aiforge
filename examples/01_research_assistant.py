"""Research Assistant — gathers information with search tools and synthesises it.

Run: python examples/01_research_assistant.py
Works offline with the built-in mock provider. Set OPENAI_API_KEY or
ANTHROPIC_API_KEY (and provider.default in config) to use a real model.
"""
from aiforge.sdk import AIForge


def main() -> None:
    forge = AIForge()
    agent = forge.agent("research_assistant", template="research_assistant")

    question = "What are the core principles behind the AIForge framework?"
    result = agent.run(question)

    print("QUESTION:", question)
    print("ANSWER:", result.output)
    print(f"(steps={result.steps}, tokens={result.usage.total_tokens})")


if __name__ == "__main__":
    main()

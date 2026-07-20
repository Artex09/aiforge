"""Customer Support Agent — answers from a knowledge base held in memory.

Run: python examples/06_customer_support_agent.py
"""
from aiforge.sdk import AIForge

KB = [
    "Refunds are processed within 5 business days.",
    "Free shipping applies to orders over $50.",
    "Support hours are 9am-6pm Monday to Friday.",
]


def main() -> None:
    forge = AIForge()
    for fact in KB:
        forge.remember(fact, semantic=True)

    agent = forge.agent("customer_support_agent", template="customer_support_agent")
    for question in ["How long do refunds take?", "When can I reach support?"]:
        result = agent.run(question)
        print(f"Q: {question}\nA: {result.output}\n")


if __name__ == "__main__":
    main()

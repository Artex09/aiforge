"""Document Analyst — reads a document and answers questions about it.

Run: python examples/05_document_analyst.py
"""
from aiforge.sdk import AIForge

DOC = (
    "AIForge is a modular framework for autonomous multi-agent AI systems. "
    "It is provider agnostic, tool-first, memory-first and event-driven. "
    "The workflow engine supports sequential, conditional, parallel and nested flows."
)


def main() -> None:
    forge = AIForge()
    forge.call_tool("write_file", path="doc.txt", content=DOC)
    agent = forge.agent("document_analyst", template="document_analyst")

    # Seed memory with the document so recall can inform the answer.
    forge.remember(DOC, semantic=True)
    summary = forge.call_tool("summarize_text", text=DOC, sentences=2)
    print("SUMMARY:", summary.output)

    result = agent.run("What kind of workflows does AIForge support?")
    print("Q&A:", result.output)


if __name__ == "__main__":
    main()

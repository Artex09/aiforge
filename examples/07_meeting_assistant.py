"""Meeting Assistant — summarises a transcript and extracts action items.

Demonstrates a small workflow: summarise -> count -> persist.
Run: python examples/07_meeting_assistant.py
"""
from aiforge.sdk import AIForge

TRANSCRIPT = (
    "Alice: We should ship the beta by Friday. "
    "Bob: I'll finish the API. Alice: I'll write the docs. "
    "Bob: Let's review metrics next week."
)


def main() -> None:
    forge = AIForge()
    forge.agent("meeting_assistant", template="meeting_assistant")

    workflow = (
        forge.workflow("meeting_notes", "Summarise a transcript and store notes")
        .set({"transcript": TRANSCRIPT})
        .tool("summarize_text", {"text": "$transcript", "sentences": 2}, output_var="summary")
        .tool("word_count", {"text": "$transcript"}, output_var="stats")
        .tool("write_file", {"path": "meeting_notes.txt", "content": "$summary"})
        .build()
    )
    result = forge.run_workflow(workflow, {"input": TRANSCRIPT})
    print("Workflow success:", result.success)
    print("Saved notes:", forge.call_tool("read_file", path="meeting_notes.txt").output)


if __name__ == "__main__":
    main()

"""File Assistant — organises files in the sandbox.

Run: python examples/04_file_assistant.py
"""
from aiforge.sdk import AIForge


def main() -> None:
    forge = AIForge()
    forge.agent("file_assistant", template="file_assistant")

    forge.call_tool("write_file", path="notes/todo.txt", content="- ship AIForge\n- write docs\n")
    forge.call_tool("write_file", path="notes/ideas.txt", content="agent marketplace\n")

    listing = forge.call_tool("list_dir", path="notes")
    print("FILES in notes/:")
    for entry in listing.output:
        print("  ", entry["name"], "(dir)" if entry["is_dir"] else "")


if __name__ == "__main__":
    main()

"""Coding Agent — writes and reads files inside the sandbox, does calculations.

Run: python examples/03_coding_agent.py
"""
from aiforge.sdk import AIForge


def main() -> None:
    forge = AIForge()
    agent = forge.agent("coding_agent", template="coding_agent")

    # Directly exercise the sandboxed file tools the agent can call.
    write = forge.call_tool("write_file", path="snippet.py", content="print('hello from AIForge')\n")
    print("WROTE:", write.output)

    read = forge.call_tool("read_file", path="snippet.py")
    print("READ BACK:", read.output.strip())

    result = agent.run("Compute 2 ** 10 and explain what it represents.")
    print("AGENT:", result.output)


if __name__ == "__main__":
    main()

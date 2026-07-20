"""AIForge command-line interface (argparse-based, stdlib only).

Examples::

    python -m aiforge.cli version
    python -m aiforge.cli list tools
    python -m aiforge.cli run-template research_assistant "Summarize AIForge"
    python -m aiforge.cli serve --port 8787
    python -m aiforge.cli init ./my-project
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .. import __version__
from ..config.settings import Config
from ..core.engine import Engine


def _engine(args: argparse.Namespace) -> Engine:
    overrides = {}
    if getattr(args, "provider", None):
        overrides.setdefault("provider", {})["default"] = args.provider
    config = Config.load(path=getattr(args, "config", None), overrides=overrides)
    return Engine(config)


def cmd_version(args: argparse.Namespace) -> int:
    print(f"AIForge {__version__}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    engine = _engine(args)
    print(json.dumps(engine.status(), indent=2, default=str))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    engine = _engine(args)
    if args.what == "tools":
        for tool in engine.tools.list():
            print(f"  {tool.name:20} {tool.description}")
    elif args.what == "providers":
        for name in engine.providers.names():
            print(f"  {name}")
    elif args.what == "templates":
        from ..agents.templates import list_templates

        for name in list_templates():
            print(f"  {name}")
    elif args.what == "agents":
        for name in engine.agents.names():
            print(f"  {name}")
    return 0


def cmd_run_template(args: argparse.Namespace) -> int:
    engine = _engine(args)
    agent = engine.agent_from_template(args.template)
    result = agent.run(args.input)
    print(result.output)
    if args.verbose:
        print("\n--- run info ---", file=sys.stderr)
        print(json.dumps(result.to_dict(), indent=2, default=str), file=sys.stderr)
    return 0 if result.success else 1


def cmd_run_agent(args: argparse.Namespace) -> int:
    engine = _engine(args)
    # Build an ad-hoc agent from flags.
    from ..agents.agent import AgentConfig

    config = AgentConfig(
        name=args.name or "cli_agent",
        role=args.role,
        system_prompt=args.system or "",
        allow_all_tools=args.all_tools,
        tools=args.tools.split(",") if args.tools else [],
    )
    agent = engine.create_agent(config)
    result = agent.run(args.input)
    print(result.output)
    return 0 if result.success else 1


def cmd_run_workflow(args: argparse.Namespace) -> int:
    engine = _engine(args)
    from ..workflows.serialization import workflow_from_json

    with open(args.file, "r", encoding="utf-8") as fh:
        workflow = workflow_from_json(fh.read())
    inputs = json.loads(args.inputs) if args.inputs else None
    result = engine.run_workflow(workflow, inputs)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.success else 1


def cmd_serve(args: argparse.Namespace) -> int:
    engine = _engine(args)
    from ..api.server import serve

    serve(engine, host=args.host, port=args.port)
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    engine = _engine(args)
    agent = engine.agent_from_template("research_assistant") if args.template == "research_assistant" \
        else engine.create_agent(__import__("aiforge.agents.agent", fromlist=["AgentConfig"]).AgentConfig(name="chat", allow_all_tools=True))
    print("AIForge chat — type 'exit' to quit.")
    history: List = []
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in {"exit", "quit"}:
            break
        if not line:
            continue
        result = agent.run(line, history=history)
        print(f"{agent.config.name}> {result.output}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    target = os.path.abspath(args.path)
    os.makedirs(target, exist_ok=True)
    config_path = os.path.join(target, "aiforge.config.json")
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "provider": {"default": "mock", "model": "aiforge-mock-1"},
                    "storage": {"backend": "local", "path": ".aiforge"},
                    "security": {"allow_shell": False},
                },
                fh,
                indent=2,
            )
    example_path = os.path.join(target, "main.py")
    if not os.path.exists(example_path):
        with open(example_path, "w", encoding="utf-8") as fh:
            fh.write(
                "from aiforge.sdk import AIForge\n\n"
                "forge = AIForge(config_path='aiforge.config.json')\n"
                "agent = forge.agent('assistant', system_prompt='You are helpful.')\n"
                "print(forge.run(agent, 'Hello from AIForge!').output)\n"
            )
    print(f"Initialized AIForge project at {target}")
    print("  - aiforge.config.json")
    print("  - main.py")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aiforge", description="AIForge multi-agent framework CLI")
    parser.add_argument("--config", help="Path to a config file (JSON/YAML)")
    parser.add_argument("--provider", help="Override the default provider")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Show version").set_defaults(func=cmd_version)
    sub.add_parser("status", help="Show engine status").set_defaults(func=cmd_status)

    p_list = sub.add_parser("list", help="List resources")
    p_list.add_argument("what", choices=["tools", "providers", "templates", "agents"])
    p_list.set_defaults(func=cmd_list)

    p_tmpl = sub.add_parser("run-template", help="Run an agent template")
    p_tmpl.add_argument("template")
    p_tmpl.add_argument("input")
    p_tmpl.add_argument("-v", "--verbose", action="store_true")
    p_tmpl.set_defaults(func=cmd_run_template)

    p_agent = sub.add_parser("run-agent", help="Run an ad-hoc agent")
    p_agent.add_argument("input")
    p_agent.add_argument("--name")
    p_agent.add_argument("--role", default="assistant")
    p_agent.add_argument("--system")
    p_agent.add_argument("--tools", help="Comma-separated tool names")
    p_agent.add_argument("--all-tools", action="store_true")
    p_agent.set_defaults(func=cmd_run_agent)

    p_wf = sub.add_parser("run-workflow", help="Run a workflow from a JSON file")
    p_wf.add_argument("file")
    p_wf.add_argument("--inputs", help="JSON object of inputs")
    p_wf.set_defaults(func=cmd_run_workflow)

    for name in ("serve", "studio", "dashboard"):
        p_serve = sub.add_parser(name, help="Start the REST API + Studio (visual workflow builder)")
        p_serve.add_argument("--host", default="127.0.0.1")
        p_serve.add_argument("--port", type=int, default=8787)
        p_serve.set_defaults(func=cmd_serve)

    p_chat = sub.add_parser("chat", help="Interactive chat with an agent")
    p_chat.add_argument("--template", default="assistant")
    p_chat.set_defaults(func=cmd_chat)

    p_init = sub.add_parser("init", help="Scaffold a new AIForge project")
    p_init.add_argument("path", nargs="?", default=".")
    p_init.set_defaults(func=cmd_init)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

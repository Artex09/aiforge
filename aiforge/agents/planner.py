"""Turn a natural-language brief into a *specialised* multi-agent crew.

The Studio Chat used to answer every brief with the same two agents — a
"Research Specialist" and a "Report Writer" — which made a software request like
"build a backend in Rust" come out as *research a backend*. That is not what a
real agent framework does: it should architect, build, and test.

``plan_crew`` reads the intent of the brief and assembles a domain-appropriate
crew with **action-oriented** tasks:

* software / build  -> Lead Software Architect + language-specific Developer(s)
                       + QA / Test Engineer  (+ DevOps when deployment is asked)
* data / analysis   -> Data Engineer + Data Analyst + Insights Specialist
* content / writing -> Content Strategist + Writer + Editor
* research (default) -> Research Specialist + Analyst + Synthesis Lead

Every agent gets a real role, a scoped tool set, and a specific system prompt;
every task is a concrete step toward the deliverable rather than "write a
report on X".  The result is a graph the canvas can render and the engine can
run directly (see :meth:`aiforge.core.engine.Engine.run_graph`).
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

MODEL = "aiforge-mock-1"


# --------------------------------------------------------------------------- #
# Intent signals
# --------------------------------------------------------------------------- #
_LANG_PATTERNS: List[Tuple[str, str]] = [
    (r"\brust\b", "Rust"),
    (r"\bpython\b", "Python"),
    (r"\bgolang\b", "Go"),
    (r"\btypescript\b", "TypeScript"),
    (r"\bjavascript\b", "JavaScript"),
    (r"\bnode(?:\.?js)?\b", "Node.js"),
    (r"\bkotlin\b", "Kotlin"),
    (r"\bswift\b", "Swift"),
    (r"\bjava\b", "Java"),
    (r"\b(?:c#|c\-sharp|csharp|\.net|dotnet)\b", "C#"),
    (r"\b(?:c\+\+|cpp)\b", "C++"),
    (r"\bruby\b", "Ruby"),
    (r"\bphp\b", "PHP"),
    (r"\belixir\b", "Elixir"),
    (r"\bscala\b", "Scala"),
]

_LANG_FRAMEWORKS: Dict[str, str] = {
    "Rust": "Axum or Actix-web, SQLx or Diesel, and Tokio for async",
    "Python": "FastAPI or Django, SQLAlchemy, and Pydantic for validation",
    "Go": "Gin or Echo, database/sql with a pool, and goroutines",
    "TypeScript": "NestJS or Express with Prisma",
    "JavaScript": "Express or Fastify with Prisma or Knex",
    "Node.js": "Express or Fastify with Prisma",
    "Java": "Spring Boot with JPA/Hibernate",
    "Kotlin": "Ktor or Spring Boot with Exposed",
    "Swift": "Vapor with Fluent",
    "C#": "ASP.NET Core with Entity Framework Core",
    "C++": "Crow or Drogon",
    "Ruby": "Ruby on Rails with ActiveRecord",
    "PHP": "Laravel with Eloquent",
    "Elixir": "Phoenix with Ecto",
    "Scala": "Play or http4s with Doobie",
}

# Words that, alone, signal a software build.
_SW_STRONG = (
    "backend", "back-end", "frontend", "front-end", "full stack", "fullstack",
    "full-stack", "api", "rest api", "graphql", "microservice", "micro-service",
    "endpoint", "sdk", "cli", "web app", "webapp", "web-app", "database schema",
    "smart contract", "compiler", "kernel", "driver",
)
# Words that signal software only alongside a build verb.
_SW_WEAK = (
    "app", "application", "website", "web site", "program", "script", "service",
    "server", "game", "bot", "platform", "system", "dashboard", "mobile",
    "android", "ios", "extension", "plugin", "library", "package", "module",
    "feature", "integration", "pipeline", "tool",
)
_BUILD_VERBS = (
    "build", "develop", "implement", "code", "coding", "program", "refactor",
    "debug", "architect", "create", "make", "write", "design", "set up", "setup",
    "ship", "engineer", "prototype",
)

_DATA_WORDS = (
    "dataset", "data set", "csv", "spreadsheet", "dataframe", "etl", "sql query",
    "analytics", "metric", "kpi", "visualis", "visualiz", "chart", "forecast",
    "regression", "statistic", "clean the data", "data pipeline", "data analysis",
    "analyze data", "analyse data", "data cleaning", "correlation",
)
_CONTENT_WORDS = (
    "blog", "article", "essay", "copywriting", "copy for", "marketing", "newsletter",
    "seo", "landing page", "social media", "tweet", "caption", "story", "screenplay",
    "email campaign", "press release", "ad copy", "product description", "content for",
)


def _has(text: str, *words: str) -> bool:
    return any(w in text for w in words)


def _word(text: str, *words: str) -> bool:
    """Whole-word match — avoids 'build' matching 'ui' or 'go' matching 'ago'."""
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def _detect_language(text: str) -> Optional[str]:
    for pattern, label in _LANG_PATTERNS:
        if re.search(pattern, text):
            return label
    # Bare "go" is only a language when it sits in a software context, so it
    # isn't confused with the verb ("go build …").
    if re.search(r"\bgo\b", text) and _has(
        text, "backend", "api", "service", "server", "microservice", "module"
    ):
        return "Go"
    return None


def _domain(text: str, language: Optional[str]) -> str:
    # Strong, unambiguous signals win first.
    if language is not None:
        return "software"
    if _word(text, *_SW_STRONG):
        return "software"
    if _word(text, *_DATA_WORDS):
        return "data"
    if _word(text, *_CONTENT_WORDS):
        return "content"
    # Weak software nouns only count alongside an explicit build verb.
    if _word(text, *_SW_WEAK) and _word(text, *_BUILD_VERBS):
        return "software"
    return "research"


def _subject(message: str) -> str:
    """A clean noun phrase for the brief, e.g. 'backend with Rust language'."""
    text = message.strip().rstrip(" .!?")
    low = text.lower()
    lead = (
        "please ", "can you ", "could you ", "i want you to ", "i want to ",
        "i'd like to ", "i would like to ", "help me ", "let's ", "lets ",
        "a crew that ", "a crew to ", "build ", "create ", "make ", "develop ",
        "implement ", "design ", "write ", "code ", "set up ", "setup ",
        "architect ", "engineer ", "prototype ",
    )
    changed = True
    while changed:
        changed = False
        for p in lead:
            if low.startswith(p):
                text = text[len(p):].strip(" :,-")
                low = text.lower()
                changed = True
                break
    for p in ("a ", "an ", "the ", "me ", "us "):
        if low.startswith(p):
            text = text[len(p):]
            low = text.lower()
    return (text.strip() or "the project")[:90]


# --------------------------------------------------------------------------- #
# Crew blueprints (one builder per domain)
# --------------------------------------------------------------------------- #
def _software_crew(text: str, subject: str, language: Optional[str]) -> Tuple[list, list]:
    lang = language or "the chosen language"
    frameworks = _LANG_FRAMEWORKS.get(language or "", "an idiomatic web framework and ORM")

    wants_frontend = _word(
        text, "frontend", "front-end", "ui", "web app", "webapp", "website",
        "react", "vue", "svelte", "page", "css", "html", "interface", "mobile",
        "android", "ios", "full stack", "fullstack", "full-stack",
    )
    wants_backend = _word(
        text, "backend", "back-end", "api", "server", "endpoint", "database",
        "service", "microservice", "auth", "crud", "graphql", "full stack",
        "fullstack", "full-stack",
    ) or not wants_frontend  # default a build to having a backend
    wants_devops = _word(
        text, "deploy", "docker", "kubernetes", "k8s", "ci/cd", "cicd",
        "pipeline", "infrastructure", "terraform", "container", "production",
    )

    agents: List[dict] = [
        {
            "key": "architect",
            "name": "Lead Software Architect",
            "role": "architect",
            "system_prompt": (
                f"You are a lead software architect. For '{subject}', design the "
                "system architecture: define the data model/database schema, the "
                "API surface and routing, module boundaries, and the project/file "
                "structure. Choose libraries and justify the trade-offs. Output "
                "concrete specs and directory layouts, not vague advice."
            ),
            "tools": ["write_file", "read_file", "json_parse", "current_datetime"],
        }
    ]
    tasks: List[dict] = [
        {
            "label": f"Design the architecture for {subject}",
            "agent": "Lead Software Architect",
            "description": (
                f"Define the architecture for {subject}: components, data model and "
                "database schema, API contract (routes, methods, payloads), module "
                "boundaries, and the concrete project/file structure. Recommend the "
                "core libraries and explain the trade-offs."
            ),
            "expected_output": (
                "An architecture spec: component diagram in text, data model/schema, "
                "API contract, and a project directory layout."
            ),
        }
    ]

    if wants_backend:
        agents.append({
            "key": "backend",
            "name": f"{language} Backend Developer" if language else "Backend Developer",
            "role": "backend-engineer",
            "system_prompt": (
                f"You are a senior backend engineer specialised in {lang}. Write "
                f"idiomatic {lang} using {frameworks}. Implement routing/endpoints, "
                "database access with connection pooling, CRUD and business logic, "
                "input validation, structured error handling, and safe concurrency. "
                "Always output complete, compilable code in fenced code blocks with "
                "the correct dependency/manifest files."
            ),
            "tools": ["write_file", "read_file", "list_dir", "shell", "calculator"],
        })
        tasks.append({
            "label": f"Implement the {language} backend" if language else "Implement the backend",
            "agent": agents[-1]["name"],
            "description": (
                f"Implement the backend for {subject} in {lang} following the "
                f"architecture. Build the {frameworks} endpoints, database "
                "connection pooling, CRUD and core business logic, request "
                "validation, and error handling. Include the dependency manifest "
                "and provide complete, idiomatic code."
            ),
            "expected_output": (
                f"Working, idiomatic {lang} backend code organised into modules, plus "
                "the dependency/manifest file."
            ),
        })

    if wants_frontend:
        agents.append({
            "key": "frontend",
            "name": "Frontend Developer",
            "role": "frontend-engineer",
            "system_prompt": (
                "You are a senior frontend engineer. Build the user interface for "
                "the project: componentised views, state management, API "
                "integration, form validation, responsive layout, and basic "
                "accessibility. Output complete component code in fenced blocks."
            ),
            "tools": ["write_file", "read_file", "list_dir", "shell"],
        })
        tasks.append({
            "label": "Build the frontend UI",
            "agent": "Frontend Developer",
            "description": (
                f"Build the frontend for {subject}: the screens/components, state, "
                "wiring to the backend API, form validation, and a responsive, "
                "accessible layout. Provide complete component code."
            ),
            "expected_output": "A working frontend with components wired to the API.",
        })

    # QA is always part of a real build.
    agents.append({
        "key": "qa",
        "name": "QA / Test Engineer",
        "role": "qa",
        "system_prompt": (
            "You are a QA / test engineer. Write unit and integration tests that "
            "cover the endpoints and core logic, then compile and run them and "
            "report pass/fail. When something breaks, propose the exact fix. Prefer "
            "concrete test code over prose."
        ),
        "tools": ["write_file", "read_file", "list_dir", "shell", "calculator"],
    })
    tasks.append({
        "label": "Write and run the test suite",
        "agent": "QA / Test Engineer",
        "description": (
            f"Write unit and integration tests for {subject} covering the endpoints "
            "and core logic, compile/run them, and report results. Perform a "
            "compilation/error check and list any fixes required to make it green."
        ),
        "expected_output": (
            "A test suite plus a short QA report: what was validated, results, and "
            "any fixes."
        ),
    })

    if wants_devops:
        agents.append({
            "key": "devops",
            "name": "DevOps Engineer",
            "role": "devops",
            "system_prompt": (
                "You are a DevOps engineer. Produce the Dockerfile, a CI pipeline, "
                "environment/config handling, and deployment manifests. Keep secrets "
                "out of the image and make the build reproducible."
            ),
            "tools": ["write_file", "read_file", "shell", "current_datetime"],
        })
        tasks.append({
            "label": "Containerise and set up CI/CD",
            "agent": "DevOps Engineer",
            "description": (
                f"Containerise {subject} with a Dockerfile, add a CI pipeline that "
                "builds and runs the tests, and provide deployment configuration and "
                "environment/secret handling."
            ),
            "expected_output": "Dockerfile, CI pipeline config, and deploy manifests.",
        })

    return agents, tasks


def _data_crew(text: str, subject: str, language: Optional[str]) -> Tuple[list, list]:
    agents = [
        {
            "key": "engineer",
            "name": "Data Engineer",
            "role": "data-engineer",
            "system_prompt": (
                "You are a data engineer. Ingest, clean, and transform the data: "
                "handle missing values, types, and outliers, and prepare a tidy "
                "dataset for analysis."
            ),
            "tools": ["read_file", "write_file", "json_parse", "json_query", "calculator"],
        },
        {
            "key": "analyst",
            "name": "Data Analyst",
            "role": "analyst",
            "system_prompt": (
                "You are a data analyst. Compute the relevant metrics and summary "
                "statistics, test hypotheses, and surface the patterns and anomalies "
                "that matter."
            ),
            "tools": ["calculator", "json_parse", "json_query", "read_file"],
        },
        {
            "key": "insights",
            "name": "Insights Specialist",
            "role": "analyst",
            "system_prompt": (
                "You are an insights specialist. Turn the analysis into a clear, "
                "decision-ready summary with concrete, prioritised recommendations "
                "and the charts worth building."
            ),
            "tools": ["write_file", "summarize_text", "word_count"],
        },
    ]
    tasks = [
        {
            "label": f"Ingest and clean the data for {subject}",
            "agent": "Data Engineer",
            "description": (
                f"Load the data for {subject}, clean it (types, missing values, "
                "duplicates, outliers), and output a tidy dataset ready to analyse."
            ),
            "expected_output": "A cleaned dataset and a note on what was changed.",
        },
        {
            "label": "Analyse the data and compute metrics",
            "agent": "Data Analyst",
            "description": (
                f"Analyse the cleaned data for {subject}: compute the key metrics and "
                "summary statistics, examine relationships, and identify the most "
                "important patterns and anomalies."
            ),
            "expected_output": "Metrics, statistics, and the key findings.",
        },
        {
            "label": "Produce insights and recommendations",
            "agent": "Insights Specialist",
            "description": (
                f"Translate the analysis of {subject} into a decision-ready brief: "
                "the headline insights, prioritised recommendations, and the "
                "visualisations worth building."
            ),
            "expected_output": "A concise insights brief with recommendations.",
        },
    ]
    return agents, tasks


def _content_crew(text: str, subject: str, language: Optional[str]) -> Tuple[list, list]:
    agents = [
        {
            "key": "strategist",
            "name": "Content Strategist",
            "role": "strategist",
            "system_prompt": (
                "You are a content strategist. Define the audience, the goal, the key "
                "messages, and an outline; note the SEO keywords and the voice to use."
            ),
            "tools": ["web_search", "summarize_text"],
        },
        {
            "key": "writer",
            "name": "Content Writer",
            "role": "writer",
            "system_prompt": (
                "You are a professional writer. Draft the piece to the outline in the "
                "requested voice — clear, specific, and engaging, with strong "
                "structure and no filler."
            ),
            "tools": ["write_file", "summarize_text", "word_count"],
        },
        {
            "key": "editor",
            "name": "Editor",
            "role": "editor",
            "system_prompt": (
                "You are a sharp editor. Tighten the draft, fix flow and tone, check "
                "the facts and claims, and deliver the final, polished version."
            ),
            "tools": ["read_file", "summarize_text", "word_count", "write_file"],
        },
    ]
    tasks = [
        {
            "label": f"Plan and outline: {subject}",
            "agent": "Content Strategist",
            "description": (
                f"Plan the content for {subject}: audience, goal, key messages, SEO "
                "keywords, and a section-by-section outline in the target voice."
            ),
            "expected_output": "An audience-aware outline with key messages and keywords.",
        },
        {
            "label": "Write the draft",
            "agent": "Content Writer",
            "description": (
                f"Write a complete first draft of {subject} following the outline and "
                "voice — structured, specific, and engaging."
            ),
            "expected_output": "A complete first draft.",
        },
        {
            "label": "Edit and finalise",
            "agent": "Editor",
            "description": (
                f"Edit the draft of {subject} for clarity, flow, tone, and accuracy, "
                "and deliver the final polished version."
            ),
            "expected_output": "The final, publication-ready piece.",
        },
    ]
    return agents, tasks


def _research_crew(text: str, subject: str, language: Optional[str]) -> Tuple[list, list]:
    agents = [
        {
            "key": "researcher",
            "name": "Research Specialist",
            "role": "researcher",
            "system_prompt": (
                "You are a meticulous researcher. Gather reliable, up-to-date "
                "information using the available tools and cite every source."
            ),
            "tools": ["web_search", "http_request", "summarize_text"],
        },
        {
            "key": "analyst",
            "name": "Insights Analyst",
            "role": "analyst",
            "system_prompt": (
                "You are an analyst. Evaluate the sources for credibility, reconcile "
                "conflicts, and extract the findings that actually answer the "
                "question."
            ),
            "tools": ["summarize_text", "json_parse", "word_count"],
        },
        {
            "key": "synthesis",
            "name": "Synthesis Lead",
            "role": "synthesis",
            "system_prompt": (
                "You are a synthesis lead. Turn the findings into a decision brief: a "
                "clear answer, the supporting evidence, the trade-offs, and a "
                "recommendation."
            ),
            "tools": ["write_file", "summarize_text"],
        },
    ]
    tasks = [
        {
            "label": f"Gather sources on {subject}",
            "agent": "Research Specialist",
            "description": (
                f"Research {subject} using the available tools; collect reliable, "
                "current sources and record what each one supports."
            ),
            "expected_output": "A set of cited findings with sources.",
        },
        {
            "label": "Analyse and extract key findings",
            "agent": "Insights Analyst",
            "description": (
                f"Evaluate the sources on {subject}, reconcile any conflicts, and "
                "extract the findings that directly answer the brief."
            ),
            "expected_output": "The vetted key findings, with confidence noted.",
        },
        {
            "label": "Synthesise a decision brief",
            "agent": "Synthesis Lead",
            "description": (
                f"Synthesise the findings on {subject} into a decision brief: the "
                "answer, the evidence, trade-offs, and a clear recommendation."
            ),
            "expected_output": "A concise decision brief with a recommendation.",
        },
    ]
    return agents, tasks


_DOMAIN_BUILDERS: Dict[str, Callable[[str, str, Optional[str]], Tuple[list, list]]] = {
    "software": _software_crew,
    "data": _data_crew,
    "content": _content_crew,
    "research": _research_crew,
}

_DOMAIN_LABEL = {
    "software": "software build",
    "data": "data analysis",
    "content": "content",
    "research": "research",
}


# --------------------------------------------------------------------------- #
# Graph assembly
# --------------------------------------------------------------------------- #
def _build_graph(agents: list, tasks: list, process: str = "sequential") -> Dict[str, Any]:
    rows = max(len(agents), len(tasks), 1)
    top = 70
    step = 165
    mid_y = top + (rows - 1) * step / 2

    nodes: List[dict] = [{
        "id": "trigger-1",
        "type": "trigger",
        "position": {"x": 40, "y": int(mid_y)},
        "data": {"label": "Trigger", "subtitle": "Manual run"},
    }]

    for i, a in enumerate(agents):
        nodes.append({
            "id": f"agent-{a['key']}",
            "type": "agent",
            "position": {"x": 340, "y": top + i * step},
            "data": {
                "name": a["name"],
                "role": a["role"],
                "model": MODEL,
                "system_prompt": a["system_prompt"],
                "tools": a["tools"],
            },
        })

    task_ids: List[str] = []
    for i, t in enumerate(tasks):
        tid = f"task-{i + 1}"
        task_ids.append(tid)
        nodes.append({
            "id": tid,
            "type": "task",
            "position": {"x": 720, "y": top + i * step},
            "data": {
                "label": t["label"],
                "description": t["description"],
                "agent": t["agent"],
                "expected_output": t["expected_output"],
            },
        })

    edges: List[dict] = []
    if task_ids:
        edges.append({"id": "e-trigger", "source": "trigger-1", "target": task_ids[0]})
    for i in range(len(task_ids) - 1):
        edges.append({"id": f"e{i + 1}", "source": task_ids[i], "target": task_ids[i + 1]})

    return {"process": process, "nodes": nodes, "edges": edges}


def plan_crew(message: str, process: str = "sequential") -> Dict[str, Any]:
    """Plan a specialised crew for *message*.

    Returns ``{reply, steps, graph, process, domain}`` ready for the Studio.
    """
    text = " " + (message or "").lower() + " "
    language = _detect_language(text)
    domain = _domain(text, language)
    subject = _subject(message or "")

    agents, tasks = _DOMAIN_BUILDERS[domain](text, subject, language)
    graph = _build_graph(agents, tasks, process)

    steps = [f"Creating {a['name']} ({a['role']})" for a in agents]
    steps += [f"Adding task: {t['label']}" for t in tasks]
    steps.append(f"Wiring {len(tasks)} tasks in sequential order")

    names = ", ".join(a["name"] for a in agents[:-1])
    names = f"{names}, and {agents[-1]['name']}" if len(agents) > 1 else agents[0]["name"]
    reply = (
        f"I've assembled a **{_DOMAIN_LABEL[domain]}** crew for **{subject}** — "
        f"{len(agents)} specialised agents ({names}) running {len(tasks)} sequential "
        "tasks. They're on the canvas; press **Run** to execute, or tweak any node "
        "first."
    )

    return {
        "reply": reply,
        "steps": steps,
        "graph": graph,
        "process": process,
        "domain": domain,
    }

# Examples

Ten runnable projects in [`examples/`](../examples), one per catalog use case.
All run **offline** with the mock provider.

| File | Project | Demonstrates |
|------|---------|--------------|
| `01_research_assistant.py` | Research Assistant | Search tools + synthesis |
| `02_browser_agent.py` | Browser Agent | HTTP tool + allowlist |
| `03_coding_agent.py` | Coding Agent | Sandboxed file read/write |
| `04_file_assistant.py` | File Assistant | Directory operations |
| `05_document_analyst.py` | Document Analyst | Summarise + Q&A over a doc |
| `06_customer_support_agent.py` | Customer Support | Knowledge base in memory |
| `07_meeting_assistant.py` | Meeting Assistant | A summarise→count→persist workflow |
| `08_cybersecurity_agent.py` | Cybersecurity (defensive) | Parse + reason about a finding |
| `09_data_analysis_agent.py` | Data Analysis | Metrics via calculator |
| `10_automation_agent.py` | Automation | Coordinator routing + tool chaining |

Run any example:

```bash
python examples/01_research_assistant.py
```

Also included:

- `examples/aiforge.config.json` — a sample configuration file.
- `examples/workflow_example.json` — a declarative workflow you can run with
  `python -m aiforge.cli run-workflow examples/workflow_example.json`.

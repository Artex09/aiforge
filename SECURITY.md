# Security Policy

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.
Include a description, reproduction steps, and impact. We aim to acknowledge
reports promptly and to ship a fix or mitigation.

## Security model

AIForge is designed to run untrusted-*input* through trusted code. Key controls:

- **No `eval` on user input.** Workflow conditions are parsed and interpreted by
  an AST allow-list (`aiforge/core/safe_eval.py`) — no calls, attribute access,
  or name resolution outside supplied variables.
- **Filesystem sandbox.** File tools resolve paths with `realpath` and reject
  anything outside the configured sandbox root, including via symlinks.
- **SSRF protection.** `http_request` permits only `http(s)` URLs and, unless a
  host is explicitly allow-listed, blocks private/loopback/link-local/reserved/
  multicast addresses (including cloud metadata endpoints).
- **Permissions.** Agents are deny-by-default: capabilities (`fs`, `network`,
  `shell`, …) must be granted via role defaults or explicit `permissions`.
  `["*"]` is the explicit "allow all" escape hatch.
- **Execution limits.** Steps, tokens, and tool calls are bounded per run.
- **API surface.** The REST server binds to `127.0.0.1` by default, sends **no**
  wildcard CORS header (cross-origin requires an explicit `api.cors_origins`
  entry), and supports an optional bearer token (`api.auth_token`).
- **Secrets.** Managed via `SecretsManager` with redaction helpers; never logged.

## Hardening for production

- Set `api.auth_token` and run behind TLS if exposing beyond localhost.
- Keep `security.allow_shell = false` unless you fully trust inputs.
- Populate `security.network_allowlist` for any tools that must reach internal
  hosts, rather than disabling SSRF protection.
- Run agents under the narrowest `permissions` that work.

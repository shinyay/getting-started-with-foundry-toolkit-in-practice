# Agentic Knowledge Gateway coding instructions

This project is a Microsoft Foundry Hosted Agent built with Python, Microsoft
Agent Framework, Responses 2.0, Foundry Memory, and incoming A2A v1.0.

## Architecture invariants

- `ResponsesHostServer` remains the Hosted Agent entry point.
- `FoundryChatClient` and `FoundryMemoryProvider` reuse one
  `AIProjectClient`.
- Exact opaque tutorial associations are written through the strict
  `remember_synthetic_association` Agent tool, not semantic extraction alone.
- `MEMORY_SCOPE` is a required fixed tutorial scope. Do not describe it as
  per-user isolation.
- The Memory Store is mandatory. Startup must fail with an actionable error
  when configuration or access is invalid.
- Local F5 validates Responses only. Incoming A2A is configured and tested
  after cloud deployment.
- A2A uses Agent Card v1.0, non-streaming JSON-RPC, and authenticated
  discovery from `agentCard/v1.0`.

## Development workflow

```bash
uv venv --python 3.12 .venv
uv pip install --prerelease=allow --python .venv/bin/python \
  -r src/agent-framework-agent-foundry-memory-responses/requirements-dev.txt
cd src/agent-framework-agent-foundry-memory-responses
../../.venv/bin/python -m unittest discover -s tests -v
cd ../..
azd ai agent run
azd deploy
```

Use only synthetic tutorial facts. Never commit `.env`, `.azure/`, `.venv/`,
tokens, keys, or credentials.

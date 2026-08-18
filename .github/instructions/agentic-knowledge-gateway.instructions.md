---
applyTo: "agentic-knowledge-gateway/**"
---

# Agentic Knowledge Gateway instructions

- Preserve the Python, Microsoft Agent Framework, Responses 2.0, and Foundry
  source-deployment architecture.
- Keep `main.py` as a thin entry point. Put configuration, memory, and A2A
  contracts in focused modules under `gateway/`.
- Load local `.env` values with `load_dotenv(override=False)` so Foundry
  runtime variables always win.
- Use Microsoft Entra ID through `DefaultAzureCredential`. Never add API keys,
  access tokens, credentials, or connection strings to source or examples.
- Treat Agent Service Memory and incoming A2A as preview capabilities.
- The tutorial uses one fixed `MEMORY_SCOPE`. It is shared test state, not
  per-user isolation or an authorization boundary.
- Store only synthetic, non-sensitive tutorial facts. Never use production
  personal, medical, legal, financial, credential, or confidential data.
- Configure incoming A2A with Agent Card version 1.0 and
  `agent_endpoint.protocol_configuration`; do not copy the legacy `protocols`
  array or default to A2A v0.3.
- Surface configuration and Memory access failures. Do not silently continue
  without the requested capability.
- Memory verification uses independently random opaque key/value values. Keep
  the value out of recall queries and require the exact pair in one Memory item.
- Use the validation-gated Agent tool and Memory item API for exact opaque
  writes. Keep `FoundryMemoryProvider` for semantic retrieval and ordinary
  interaction updates, but skip its after-run update for strict pair-write
  turns so asynchronous extraction cannot rewrite the direct item. Semantic
  extraction alone is not verbatim proof.
- Retry only explicitly classified transient Memory service failures within a
  bounded deadline, then surface the final cause.
- Do not automatically retry A2A writes. A read-only recall may retry one
  `InternalError` only if no output was received.
- Keep generated `.foundry/agent-metadata.yaml` local and ignored. Track only
  the environment-neutral metadata example.
- Use Python 3.12 for the local virtual environment and Python 3.13 for Hosted
  Code and the optional Dockerfile.
- Make destructive resource and Memory deletion explicit and confirmation
  gated.
- Add or update focused `unittest` coverage with each behavior change.

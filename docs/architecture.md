# Architecture and trust boundaries

Streamlit native chat -> loopback FastAPI -> opaque development session -> supervisor plan -> specialized handlers -> centralized PIN/confirmation gateway -> repository or approved FAISS retrieval -> deterministic response verification/composition -> audit.

The supplied diagram and use-case PDF guide six domains: accounts, payments, cards, loans, fraud and knowledge. Handlers share a supervisor, with no independent model processes. Domain tool membership is validated in `handlers.py`; public knowledge requests use the retriever.

The optional OpenRouter planner makes one OpenAI-compatible Chat Completions function-calling request to propose a plan. The selected Nemotron free model does not guarantee structured JSON output, so the API response is parsed into the Pydantic plan and rejected if invalid. The model never receives a PIN, repository result, bearer token or PIN hash. The gateway recomputes protection requirements from its registry. Planning has a 30-second timeout and no agent loop. Provider failure returns unavailable. Use only fictional data with the free endpoint; do not send confidential information or personal data. References: [OpenRouter Chat Completions API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request), [Nemotron 3.5 Lightning (free)](https://openrouter.ai/nvidia/nemotron-3.5-lightning%3Afree).

Offline routing is a keyword baseline, not an LLM. Responses use deterministic templates over validated financial results and exact policy excerpts. This constrains unsupported financial claims but limits conversational fluency.

Protected requests pause before financial reads. PIN verification creates a server-side grant bound to the customer, session and SHA-256 digest of the exact validated plan. Grants last 60 seconds; pending requests last 5 minutes. Successful execution consumes the grant. Write confirmation binds the same digest. Expired, replayed, foreign-session or changed-resource requests fail. Mutations are serialized in this single-worker prototype and repository queries independently enforce ownership.

The loopback session issuer simulates bank login. It rejects browser Origin requests and non-loopback peers. FastAPI validates Host and binds to loopback. Streamlit calls from its Python server, not browser JavaScript. Production mode refuses startup until verified upstream identity and shared persistent authorization storage are integrated.

PINs use Argon2id. The mock repository uses a development hash in ignored `.env`; the supplied SQLite dataset stores a separately salted hash per account in `account_security`. Its setup script prompts locally and never persists plaintext PINs. Tests generate ephemeral credentials. Five failed attempts lock a customer for five minutes across sessions. Lockouts reset on process restart; this is a prototype limitation.

Histories are process-local under bearer-session ownership. Clear Chat invalidates pending operations. PIN values never enter history or audit. Secret-like chat input is rejected before routing and omitted from history. Audit includes trace, identity, decisions, tools, source IDs, outcome and latency, never raw private prompts or responses.

Nine fictional policy documents use section-aware chunks, approval digests, version/current markers and role/classification filters before indexing. Default local TF-IDF word/bigram vectors use FAISS; they are not semantic transformer embeddings. Hosted embeddings are configurable. Known malicious instructions are quarantined, but this heuristic does not establish general injection resistance. Approval and extractive composition remain trust boundaries.

SQLite integration is tested only against the documented contract. Live payments, replacement fulfillment, limit changes, scheduled notifications and regulated advice are unsupported. High-risk matters are directed to authorized staff; no external message is sent automatically.

<p align="center">
  <pre align="center">
██╗   ██       ███████╗       ██╗   ██╗     ██╗         ████████╗       ██████╗   ██████╗  ████████╗
██║   ██║      ██╔══██╗       ██║   ██║     ██║         ╚══██╔══╝       ██╔══██╗ ██╔═══██╗ ╚══██╔══╝
██║   ██║      ███████║       ██║   ██║     ██║            ██║          ██████╔╝ ██║   ██║    ██║
╚██╗ ██╔╝      ██╔══██║       ██║   ██║     ██║            ██║          ██╔══██╗ ██║   ██║    ██║
 ╚████╔╝  ██╗  ██║  ██║  ██╗  ╚██████╔╝ ██╗ ███████╗  ██╗  ██║  ██╗     ██████╔╝ ╚██████╔╝    ██║
  ╚═══╝   ╚═╝  ╚═╝  ╚═╝  ╚═╝   ╚═════╝  ╚═╝ ╚══════╝  ╚═╝  ╚═╝  ╚═╝     ╚═════╝   ╚═════╝     ╚═╝
 </pre>
</p>

<p align="center">
  <strong>Security-first, Your Own Personal Autonomous AI assistant.</strong>
  <br>
  <em>V.A.U.L.T. — Verified Autonomous Utility & Logical Taskrunner</em>
</p>

<p align="center">
  <a href="https://github.com/encryptedtouhid/VaultBot/actions"><img src="https://img.shields.io/github/actions/workflow/status/encryptedtouhid/VaultBot/ci.yml?branch=main&label=CI&style=flat-square" alt="CI"></a>
  <a href="https://github.com/encryptedtouhid/VaultBot/releases"><img src="https://img.shields.io/github/v/release/encryptedtouhid/VaultBot?style=flat-square&label=version" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-BSL--1.1-blue?style=flat-square" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square" alt="Python"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#platform-support">Platforms</a> &middot;
  <a href="#llm-providers">LLM Providers</a> &middot;
  <a href="#security-architecture">Security</a> &middot;
  <a href="#media--ai-tools">Media & AI</a> &middot;
  <a href="#plugin-system">Plugins</a> &middot;
  <a href="#deployment">Deployment</a> &middot;
  <a href="#cli-reference">CLI</a> &middot;
  <a href="#configuration">Configuration</a> &middot;
  <a href="#testing">Testing</a> &middot;
  <a href="#roadmap">Roadmap</a> &middot;
  <a href="#contributing">Contributing</a>
</p>

---

## Overview

VaultBot is a **security-first, autonomous AI agent platform** that connects 14+ messaging platforms to 16+ LLM providers through a hardened, auditable pipeline. Every credential is encrypted, every plugin is cryptographically signed, every action is logged, and every security mechanism is on by default and cannot be turned off.

Built for teams and individuals who need an AI assistant they can trust with production systems.

### Key Principles

- **Secure by default** — Zero-trust authentication, immutable security policies, encrypted credential storage
- **Multi-platform** — Single bot instance serving Telegram, Discord, Slack, WhatsApp, Signal, Teams, and 8 more
- **Provider-agnostic** — Claude, GPT, Gemini, 12+ compatible providers, and local models via Ollama/vLLM
- **Auditable** — Structured JSON audit logging, append-only, covering every action and decision
- **Extensible** — Ed25519-signed plugins running in sandboxed subprocesses with declarative permissions

---

## Quick Start

### From Source

```bash
# Clone and install
git clone https://github.com/encryptedtouhid/VaultBot.git
cd VaultBot
pip install -e .

# Verify environment
vaultbot doctor

# Interactive setup — credentials stored in OS keychain
vaultbot init

# Start the bot
vaultbot run
```

### With Docker

```bash
cp .env.example .env       # Configure your tokens and API keys
docker compose up -d        # Start VaultBot
```

### With Docker + Redis (multi-instance)

```bash
docker compose up -d vaultbot redis
```

### With Local LLM

```bash
docker compose --profile local-llm up -d
```

---

## Platform Support

VaultBot supports **14 messaging platforms** with a unified adapter interface. Each platform is fully async with healthcheck monitoring and graceful reconnection.

| Platform | Library | Connection Mode | Features |
|---|---|---|---|
| **Telegram** | `python-telegram-bot` | Polling + Webhook | Inline keyboards, file handling, topic threads |
| **Discord** | `nextcord` | Gateway + Intents | Guild support, embeds, mentions, threads |
| **WhatsApp** | `httpx` (Cloud API) | Webhook | Meta Business integration, media messages |
| **Signal** | `signal-cli` JSON-RPC | TCP polling | End-to-end encryption via Signal protocol |
| **Slack** | `slack-bolt` | Socket Mode + Events API | App tokens, channels, threads |
| **Microsoft Teams** | `botbuilder-core` | Bot Framework | Enterprise SSO, channel routing |
| **iMessage** | AppleScript + SQLite | Local polling | macOS native, read/unread tracking |
| **IRC** | `asyncio` raw | TLS + plaintext | RFC 1459, SASL auth, multi-channel |
| **Matrix** | `httpx` (CS API) | Long-poll `/sync` | Federated rooms, E2EE-ready |
| **Mattermost** | `httpx` + WebSocket | REST v4 + WS | Self-hosted, slash commands |
| **LINE** | `httpx` (Messaging API) | Webhook | Rich menus, reply tokens |
| **Google Chat** | `httpx` (Chat API) | Webhook + SA | Workspace integration, threads |
| **Twitch** | `asyncio` IRC gateway | TLS + OAuth | Chat commands, moderation |
| **Nostr** | WebSocket (NIP-01) | Multi-relay | Decentralized, relay management |

### Platform Features

- **Unified message model** — `InboundMessage` / `OutboundMessage` abstractions across all platforms
- **Async-first** — All adapters are fully asynchronous with non-blocking I/O
- **Auto-reconnect** — Graceful disconnect and reconnection handling
- **Health monitoring** — Per-platform `healthcheck()` for orchestration readiness
- **Multi-platform routing** — Single bot instance responds on all enabled platforms

---

## LLM Providers

VaultBot integrates with **16 LLM providers** — 3 native SDKs and 12+ OpenAI-compatible endpoints. Any OpenAI-compatible API works out of the box.

### Native SDK Providers

| Provider | Default Model | Features |
|---|---|---|
| **Anthropic Claude** | claude-sonnet-4-20250514 | Vision, tool use, extended thinking |
| **OpenAI GPT** | gpt-4o | Vision, function calling, streaming |
| **Google Gemini** | gemini-2.0-flash | Multimodal, long context |

### Compatible Providers

| Provider | Default Model | Notes |
|---|---|---|
| **OpenRouter** | anthropic/claude-sonnet-4 | Gateway to 200+ models |
| **Together AI** | Llama-3-70b | Open-source model hosting |
| **Groq** | llama-3.1-70b-versatile | Ultra-fast inference |
| **Mistral** | mistral-large-latest | European AI provider |
| **Perplexity** | llama-3.1-sonar-large | Built-in web search |
| **DeepSeek** | deepseek-chat | Cost-effective reasoning |
| **Fireworks AI** | llama-v3p1-70b-instruct | Fast open-source hosting |
| **xAI (Grok)** | grok-2-latest | Real-time knowledge |
| **Amazon Bedrock** | anthropic.claude-sonnet-4 | AWS-managed inference |

### Local Providers

| Provider | Notes |
|---|---|
| **Ollama** | One-command local model deployment |
| **vLLM** | High-throughput local inference |
| **LM Studio** | Desktop-friendly local models |
| **Custom** | Any OpenAI-compatible endpoint URL |

### LLM Security & Reliability

- **Prompt injection guard** — 13 input attack patterns + 3 output leak patterns scanned on every request
- **Model fallback** — Automatic provider failover with exponential backoff on rate limits, timeouts, and 5xx errors
- **Health tracking** — Per-provider cooldown management and health state
- **Streaming** — Both `complete()` and `stream()` methods with consistent error handling

---

## Security Architecture

VaultBot implements **10+ defense-in-depth security layers**. All security mechanisms are enabled by default and cannot be disabled.

> Full policy and responsible disclosure: [SECURITY.md](SECURITY.md)

### Security Layers

| Layer | Implementation |
|---|---|
| **Credential Storage** | OS keychain via `keyring`, Fernet + Argon2id encrypted fallback, `VAULTBOT_*` env vars for containers |
| **Zero-Trust Auth** | Explicit allowlist required — unknown senders are rejected and audit-logged |
| **Immutable Policies** | `auth.require_allowlist`, `plugins.require_signature`, `actions.require_approval`, `audit.enabled` — hardcoded `true`, override attempts are logged |
| **Prompt Guard** | 13 injection patterns (ignore instructions, jailbreak, DAN mode, role override) + 3 output leak patterns |
| **Input Sanitizer** | Strips zero-width chars, control chars, bidi overrides; Unicode NFC normalization; 4096-char limit |
| **Rate Limiting** | Token bucket per-user and global, always enabled, configurable burst/sustain rates |
| **Plugin Signing** | Ed25519 signatures verified against local trust store — unsigned plugins refuse to load |
| **Plugin Sandbox** | Subprocess isolation with restricted PATH/env, network allowlists, hard timeout + OOM kill |
| **Action Approval** | 5-level severity engine: INFO (auto) through CRITICAL (2FA required) |
| **Audit Logging** | Structured JSON, append-only — covers auth, messages, actions, plugins, config changes, errors |
| **SSRF Protection** | Blocks private IPs, cloud metadata endpoints, non-HTTP schemes in fetch and browser tools |
| **Secret Scanning** | Pre-commit hooks + runtime scanner detect API keys, passwords, and tokens |
| **2FA Enforcement** | TOTP verification for CRITICAL actions (key rotation, data deletion, admin operations) |

### Approval Engine

| Severity | Behavior | Example Actions |
|---|---|---|
| **INFO** | Auto-approved | Read-only queries, search |
| **LOW** | Auto-approved + audit log | LLM requests, memory reads |
| **MEDIUM** | Requires user confirmation | Config changes, plugin enable/disable |
| **HIGH** | Confirmation + cooldown period | Plugin install/remove, credential changes |
| **CRITICAL** | Confirmation + TOTP 2FA | Data deletion, key rotation, admin operations |

---

## Media & AI Tools

| Capability | Providers | Description |
|---|---|---|
| **Image Generation** | DALL-E 3, Stability AI | Text-to-image with size, quality, and style controls |
| **Video Generation** | Provider registry | Extensible text-to-video with async job tracking |
| **Music Generation** | Provider registry | Text-to-music with genre and duration controls |
| **Text-to-Speech** | OpenAI TTS, ElevenLabs | 14+ voices, MP3/OPUS/AAC/FLAC/WAV output |
| **Web Search** | Brave Search, DuckDuckGo, Tavily | Multi-provider with fallback and structured results |
| **Web Fetch** | httpx | SSRF-protected page fetching with HTML-to-text |
| **Browser Automation** | Playwright | Headless browsing, screenshots, form filling, JS execution |
| **Link Understanding** | Built-in | URL content extraction, HTML parsing, metadata |

---

## Agent Capabilities

| Feature | Description |
|---|---|
| **Sub-Agent Spawning** | Parallel task execution with depth limits (max 3), token budgets (50k default), and timeout protection |
| **Cron Scheduler** | Standard cron expressions + simple intervals, persistent storage, run logging, success/failure tracking |
| **Hooks System** | 8 event types (before/after tool, LLM, message, startup, shutdown, error) with priority ordering |
| **MCP Client** | Model Context Protocol via stdio/HTTP transport — automatic tool and resource discovery |
| **Auto-Reply** | Pattern-based triggers with regex matching, case sensitivity control, instant responses |
| **Smart Routing** | Content-based LLM selection — route coding questions to one model, creative tasks to another |
| **Polls** | Single/multi-choice voting with results aggregation and platform-native rendering |
| **Canvas** | Collaborative document workspace (text, code, markdown, table) with revision history |
| **Context Compaction** | LLM-powered conversation summarization with token budget management |
| **Vector Memory** | Semantic search via cosine similarity with importance weighting and metadata |

---

## Plugin System

VaultBot's plugin system enforces security at every layer — from cryptographic signing to subprocess isolation.

### Plugin Security Model

| Feature | Details |
|---|---|
| **Ed25519 Signing** | Plugins must be signed with a trusted key — unsigned plugins refuse to load |
| **Subprocess Sandbox** | Each plugin runs in an isolated process via JSON-RPC with restricted environment |
| **Manifest Permissions** | Plugins declare required network domains, filesystem access level, and secrets |
| **Resource Limits** | Configurable timeout (default 30s) and memory cap (default 256MB) per plugin |
| **Approval Integration** | Plugin actions route through the 5-level severity approval engine |

### Plugin Lifecycle

```bash
# Scaffold a new plugin
vaultbot sdk new weather-lookup --desc "Weather by location" --author "you"

# Implement logic in weather-lookup/plugin.py

# Run automated validation (5 checks)
vaultbot sdk test ./weather-lookup

# Validate manifest
vaultbot sdk validate ./weather-lookup

# Generate signing keypair (one time)
vaultbot plugin keygen ./my-keys

# Sign the plugin
vaultbot plugin sign ./weather-lookup ./my-keys/vaultbot_signing_key.pem

# Trust the key and install
cp ./my-keys/vaultbot_signing_key.pub ~/.vaultbot/trust_store/
vaultbot plugin install ./weather-lookup
```

### Marketplace

```bash
vaultbot marketplace search <query>      # Search reviewed plugins
vaultbot marketplace info <name>         # Plugin details and compatibility
vaultbot plugin install <name>           # Install with version pinning
```

---

## Memory System

VaultBot provides three pluggable memory backends:

| Backend | Use Case | Features |
|---|---|---|
| **SQLite** | Single-instance deployments | Async I/O, indexed queries, zero config |
| **Redis** | Multi-instance with shared state | Distributed cache, optional TTL, hiredis support |
| **Vector Store** | Semantic search | Cosine similarity, importance weighting, metadata |

### Memory Features

- Per-user and per-chat conversation history
- Automatic context compaction via LLM summarization
- Semantic memory search with relevance scoring
- Thread-safe atomic operations
- Configurable TTL (Redis backend)

---

## Deployment

### Docker

```bash
# Bot only
docker compose up -d vaultbot

# Bot + Redis (multi-instance shared state)
docker compose up -d vaultbot redis

# Bot + local LLM (Ollama)
docker compose --profile local-llm up -d
```

### Container Security

| Measure | Details |
|---|---|
| **Non-root user** | Runs as `vaultbot:vaultbot` (dedicated UID/GID) |
| **Read-only filesystem** | Root FS is read-only; `/tmp` is tmpfs (noexec, nosuid, 64MB) |
| **Capability dropping** | All Linux capabilities dropped via `cap_drop: ALL` |
| **No privilege escalation** | Enforced via `no-new-privileges: true` |
| **Network isolation** | Bridge network between services |
| **Log rotation** | json-file driver, 10MB max, 3 files |
| **Health checks** | HTTP `/health` every 30s; Redis `ping` every 10s |
| **Persistent volumes** | `vaultbot-data`, `redis-data`, `ollama-data` |

### Daemon Mode

```bash
vaultbot run --daemon                    # Start in background
vaultbot run --daemon --status           # Check daemon status
```

- PID file management with stale PID detection
- Signal handling (SIGTERM for graceful shutdown, SIGHUP for reload)
- Health endpoints (`/health`, `/ready`) for Kubernetes probes

---

## Configuration

VaultBot reads configuration from three sources (highest priority first):

| Priority | Source | Best For |
|---|---|---|
| 1 | `VAULTBOT_*` environment variables | Docker, CI/CD, Kubernetes |
| 2 | `.env` file | Local development |
| 3 | `~/.vaultbot/config.yaml` | Desktop, persistent config |

### Credential Storage

| Priority | Source | Best For |
|---|---|---|
| 1 | `VAULTBOT_*` env vars | Containers and CI/CD |
| 2 | OS keychain (`keyring`) | Desktop (macOS, Windows, Linux) |
| 3 | Fernet + Argon2id encrypted file | Headless servers |

### Platform Credentials

| Platform | Requirement |
|---|---|
| Telegram | Bot token from [@BotFather](https://t.me/BotFather) |
| Discord | Bot token from [Developer Portal](https://discord.com/developers) |
| WhatsApp | Access token + Phone Number ID from Meta Business |
| Signal | Phone number + `signal-cli` daemon |
| Slack | Bot token (`xoxb-`) + App token (`xapp-`) |
| Teams | App ID + Password from Azure Bot registration |
| iMessage | None — uses local Messages.app (macOS only) |
| IRC | Server, port, nick, channels |
| Matrix | Homeserver URL + access token |
| Mattermost | Server URL + personal access token |
| LINE | Channel access token + channel secret |
| Google Chat | Service account key or webhook URL |
| Twitch | OAuth token + bot username |
| Nostr | Private key hex + relay URLs |

All 30+ configuration variables are documented in [`.env.example`](.env.example).

---

## CLI Reference

### Core Commands

```bash
vaultbot init                            # Interactive setup wizard
vaultbot run                             # Start the bot
vaultbot run -c ./config.yaml            # Start with custom config
vaultbot run --daemon                    # Start in background
vaultbot doctor                          # Run diagnostic checks
```

### Credential Management

```bash
vaultbot credentials set <key>           # Store in OS keychain (hidden input)
vaultbot credentials check <key>         # Verify existence without revealing value
vaultbot credentials delete <key>        # Remove from keychain
```

### Plugin Management

```bash
vaultbot plugin install <dir>            # Install a signed plugin
vaultbot plugin list                     # List installed plugins
vaultbot plugin enable <name>            # Enable a plugin
vaultbot plugin disable <name>           # Disable without uninstalling
vaultbot plugin uninstall <name>         # Remove from registry
vaultbot plugin sign <dir> <key-file>    # Sign with Ed25519 key
vaultbot plugin keygen <output-dir>      # Generate signing keypair
```

### Plugin SDK

```bash
vaultbot sdk new <name>                  # Scaffold plugin boilerplate
vaultbot sdk test <dir>                  # Run validation harness
vaultbot sdk validate <dir>              # Check manifest
```

### Marketplace & Teams

```bash
vaultbot marketplace search <query>      # Search plugin marketplace
vaultbot marketplace info <name>         # Get plugin details
vaultbot team create <name>              # Create a new team
vaultbot team list                       # List all teams
```

---

## Architecture

```
src/vaultbot/
├── core/               Bot orchestrator, message router, context management,
│                       compaction, summarizer, task engine, healthcheck, auto-reply
├── platforms/          14 messaging adapters with unified PlatformAdapter protocol
├── llm/                Claude, OpenAI, Gemini, compatible providers, local adapters,
│                       prompt guard, factory, fallback engine
├── security/           Credentials, auth, rate limiter, audit logger, policy enforcer,
│                       sanitizer, teams, audit scanner, two-factor auth
├── plugins/            Loader, sandbox, signer, registry, SDK, marketplace, versioning
├── memory/             SQLite, Redis, and vector store backends
├── media/              Image/video/music generation, TTS, link understanding
├── tools/              Web search, web fetch, browser automation, canvas, polls
├── mcp/                Model Context Protocol client (stdio + HTTP transport)
├── agents/             Sub-agent spawning and orchestration
├── cron/               Scheduled task system with persistent storage
├── hooks/              Event system with 8 hook types
├── i18n/               Internationalization with YAML locale files
├── dashboard/          SSE web dashboard with real-time metrics
├── config.py           Pydantic config with multi-source resolution
├── cli.py              Typer CLI with 7 command groups
├── daemon.py           Background daemon with PID and signal management
├── setup.py            Setup wizard and doctor diagnostics
├── tui.py              Terminal UI with ANSI rendering
├── pairing.py          Device pairing for companion apps
└── observability.py    OpenTelemetry-compatible metrics and tracing
```

---

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run full test suite
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Linting
ruff check src/ tests/

# Format check
ruff format --check src/ tests/

# Type checking
mypy src/

# Security audit
pip-audit
```

### Test Coverage

| Category | Tests | Scope |
|---|---|---|
| **Security** | 56+ | Auth, rate limiting, policy, sanitizer, prompt guard, teams, credentials, audit, 2FA |
| **Core** | 50+ | Message routing, context, compaction, summarizer, healthcheck, task engine, auto-reply |
| **Platforms** | 180+ | All 14 adapters — init, send, receive, healthcheck, connect, disconnect |
| **LLM Providers** | 40+ | Gemini, compatible presets, factory, fallback, protocol compliance |
| **Media & Tools** | 100+ | Image/video/music/TTS generation, web search, fetch, browser, canvas, polls |
| **Plugins** | 60+ | Signing, sandbox, registry, SDK, marketplace, version manager |
| **Infrastructure** | 80+ | MCP, cron, hooks, sub-agents, daemon, pairing, i18n, TUI, observability |
| **E2E Integration** | 80+ | Full pipeline per platform, multi-user isolation, injection blocking, failover |
| **Total** | **840+** | |

---

## Roadmap

VaultBot is under active development. Key areas on the roadmap:

- **Voice I/O** — Speech-to-text, wake word detection, push-to-talk, talk mode
- **Native Apps** — macOS, iOS, Android, and Apple Watch companion apps
- **Gateway** — WebSocket control plane for remote management and multi-client access
- **Expanded Providers** — 35+ LLM providers including Asian market coverage
- **Video & Music** — Concrete generation providers (FAL, Runway, Comfy, Suno)
- **Advanced Memory** — Wiki-based knowledge, active memory, dreaming, LanceDB vectors
- **Workflow Engine** — Multi-step typed pipelines with approval gates and branching
- **Coding Agent** — Sandboxed code execution with multi-language support
- **More Platforms** — 9+ additional messaging platforms including WeChat, QQ, Feishu
- **Enterprise Cron** — Delivery plans, stagger, heartbeat, session reaping
- **Plugin Ecosystem** — Published SDK, hosted marketplace, bundled and managed skills
- **Prompt Caching** — Provider-native caching for cost optimization
- **Block Streaming** — Paragraph-aware chunked delivery with backpressure

See the [full issue tracker](https://github.com/encryptedtouhid/VaultBot/issues) for detailed implementation plans.

---

## Project Stats

| Metric | Value |
|---|---|
| **Version** | 0.1.0 (alpha) |
| **Language** | Python 3.11+ |
| **Source Files** | 106 |
| **Test Files** | 64 |
| **Total Tests** | 840+ |
| **Messaging Platforms** | 14 |
| **LLM Providers** | 16 (3 native + 12 compatible + custom) |
| **Memory Backends** | 3 (SQLite, Redis, Vector) |
| **Security Layers** | 10+ |
| **CLI Commands** | 20+ across 7 groups |
| **CI/CD** | GitHub Actions (lint, format, type check, tests, security audit, Docker) |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and pull request process.

For security vulnerabilities, see [SECURITY.md](SECURITY.md) for responsible disclosure.

For incident response procedures, see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md).

---

## License

VaultBot is licensed under the [Business Source License 1.1](LICENSE).

**Free to use** for personal, development, testing, educational, and internal purposes. A [commercial license](mailto:your-email@example.com) is required for production services offered to third parties.

On **2030-04-11**, all code released under this license automatically converts to **Apache License 2.0**.

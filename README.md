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
  <strong>Security-first, source-available autonomous AI agent</strong>
  <br>
  <em>V.A.U.L.T. — Verified Autonomous Utility & Logical Taskrunner</em>
  <br>
  <em>14 platforms &bull; 16 LLM providers &bull; 10 security layers &bull; 840+ tests</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#supported-platforms">Platforms</a> &bull;
  <a href="#security-architecture">Security</a> &bull;
  <a href="#media--ai-tools">Media & AI</a> &bull;
  <a href="#docker-deployment">Docker</a> &bull;
  <a href="#plugin-development">Plugins</a> &bull;
  <a href="#cli-reference">CLI</a> &bull;
  <a href="#testing">Testing</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

## Why VaultBot?

AI agent bots like OpenClaw ship with authentication disabled by default, store credentials in plain text, and let anyone upload executable plugins with zero code review. The result: [138+ CVEs](https://blink.new/blog/openclaw-security-best-practices-2026), [42,000+ exposed instances](https://www.sangfor.com/blog/cybersecurity/openclaw-ai-agent-security-risks-2026), and [824+ malicious plugins](https://www.immersivelabs.com/resources/c7-blog/openclaw-what-you-need-to-know-before-it-claws-its-way-into-your-organization) in the wild.

VaultBot takes the opposite approach. Every security mechanism is **on by default and cannot be turned off**. Credentials are never stored in plain text. Plugins are cryptographically signed and run in sandboxed subprocesses. Every action is audited.

| | OpenClaw | VaultBot |
|---|---|---|
| **CVEs** | 138+ (41% High/Critical) | 0 (secure by design) |
| **Auth default** | Disabled | Always on, immutable |
| **Credentials** | Plain text in `~/.clawdbot` | OS keychain + encrypted fallback |
| **Plugin vetting** | Zero review | Ed25519 signed + subprocess sandboxed |
| **Prompt injection** | No protection | 13 input patterns + 3 output leak patterns |
| **Autonomy control** | Over-autonomous ($400+ token burns) | 5-level approval engine with user confirmation |

## Quick Start

```bash
# Install from source
pip install -e .

# Run diagnostics to verify setup
vaultbot doctor

# Interactive setup wizard — credentials stored in OS keychain
vaultbot init

# Start the bot
vaultbot run
```

Or with Docker:

```bash
cp .env.example .env    # Fill in your tokens and API keys
docker compose up -d
```

## Features

### Supported Platforms

VaultBot supports **14 messaging platforms** out of the box:

| Platform | Library | Connection Mode |
|---|---|---|
| **Telegram** | `python-telegram-bot` | Polling + Webhook |
| **Discord** | `nextcord` | Message events + intents |
| **WhatsApp** | `httpx` (Cloud API) | Webhook |
| **Signal** | `signal-cli` JSON-RPC | TCP polling |
| **Slack** | `slack-bolt` | Socket Mode + Events API |
| **Microsoft Teams** | `botbuilder-core` | Bot Framework webhook |
| **iMessage** | AppleScript + SQLite | Local polling (macOS only) |
| **IRC** | `asyncio` raw protocol | TLS + plaintext |
| **Matrix** | `httpx` (Client-Server API) | Long-poll `/sync` |
| **Mattermost** | `httpx` + WebSocket | REST API v4 + WS events |
| **LINE** | `httpx` (Messaging API) | Webhook + reply tokens |
| **Google Chat** | `httpx` (Chat API) | Webhook + service account |
| **Twitch** | `asyncio` IRC gateway | TLS + OAuth |
| **Nostr** | WebSocket (NIP-01) | Multi-relay subscription |

### 16 LLM Providers

Any OpenAI-compatible API works out of the box. Native SDKs for Claude, OpenAI, and Google Gemini.

| Provider | Type | Default Model |
|---|---|---|
| **Claude** (recommended) | Native SDK | claude-sonnet-4-20250514 |
| **OpenAI GPT** | Native SDK | gpt-4o |
| **Google Gemini** | Native REST | gemini-2.0-flash |
| **OpenRouter** | Compatible | anthropic/claude-sonnet-4 (200+ models) |
| **Together AI** | Compatible | Llama-3-70b |
| **Groq** | Compatible | llama-3.1-70b-versatile |
| **Mistral** | Compatible | mistral-large-latest |
| **Perplexity** | Compatible | llama-3.1-sonar-large (with web search) |
| **DeepSeek** | Compatible | deepseek-chat |
| **Fireworks AI** | Compatible | llama-v3p1-70b-instruct |
| **xAI (Grok)** | Compatible | grok-2-latest |
| **Amazon Bedrock** | Compatible | anthropic.claude-sonnet-4 |
| **Ollama** | Local | llama3.2 |
| **vLLM** | Local | Any loaded model |
| **LM Studio** | Local | Any loaded model |
| **Custom** | Any URL | Any OpenAI-compatible endpoint |

All LLM calls pass through a **prompt injection guard** that scans for 13 known attack patterns and 3 output leak indicators before responses reach users.

#### Model Fallback & Failover

VaultBot includes automatic **provider failover** with exponential backoff:

- Ordered fallback chain (primary -> secondary -> tertiary)
- Automatic failover on rate limits, timeouts, or 5xx errors
- Per-provider health tracking and cooldown management
- Works with both `complete()` and `stream()` methods

### Media & AI Tools

| Capability | Providers | Description |
|---|---|---|
| **Image Generation** | DALL-E 3, Stability AI | Text-to-image with size, quality, style controls |
| **Video Generation** | Provider registry | Text-to-video with async job tracking |
| **Music Generation** | Provider registry | Text-to-music with genre/duration controls |
| **TTS (Text-to-Speech)** | OpenAI TTS, ElevenLabs | 14+ voices, MP3/OPUS/AAC/FLAC/WAV formats |
| **Media Understanding** | Link extractor | URL content extraction, HTML parsing, title extraction |
| **Web Search** | Brave Search, Tavily | Structured search results with multi-provider support |
| **Web Fetch** | httpx | SSRF-protected page fetching with HTML-to-text conversion |
| **Browser Automation** | Playwright | Headless browsing with SSRF protection and sandbox mode |

### Agent Capabilities

| Feature | Description |
|---|---|
| **Sub-Agent Spawning** | Spawn child agents for parallel tasks with depth limits and token budgets |
| **Cron Scheduler** | Cron expressions + simple intervals, persistent jobs, run logging |
| **Hooks System** | Before/after tool execution, priority ordering, blocking support |
| **MCP Client** | Model Context Protocol via stdio transport, tool discovery and execution |
| **Auto-Reply** | Pattern-based automatic responses, smart model routing by content type |
| **Polls** | Single/multi-choice voting, results aggregation, platform-native rendering |
| **Canvas** | Collaborative document workspace with revisions and undo |
| **Context Compaction** | Smart message summarization when conversations exceed token budgets |
| **Vector Memory** | Semantic search via cosine similarity with importance weighting |

### Plugin System

| Feature | Description |
|---|---|
| **Ed25519 signing** | Unsigned or untrusted plugins refuse to load |
| **Subprocess sandbox** | Plugins run in isolated processes via JSON-RPC with restricted env |
| **Manifest permissions** | Plugins declare network domains, filesystem access, and required secrets |
| **Time & memory limits** | Configurable timeout (default 30s) and memory cap (default 256MB) |
| **Approval engine** | 5 severity levels: INFO (auto) / LOW (audit) / MEDIUM (confirm) / HIGH (confirm + cooldown) / CRITICAL (confirm + 2FA) |
| **SDK** | Scaffold, test, validate, sign, and install plugins from the CLI |
| **Marketplace** | Browse, install, and update reviewed plugins with version pinning |
| **Version Manager** | Track versions, check for updates, auto-update with rollback |

### Production Hardening

| Feature | Details |
|---|---|
| **Docker** | Multi-stage build, non-root user, read-only FS, all capabilities dropped |
| **CI/CD** | GitHub Actions: ruff lint, format check, mypy, pytest, pip-audit, Docker build |
| **Daemon Mode** | Background operation with PID file, signal handling (SIGTERM/SIGHUP), status monitoring |
| **Healthcheck** | `/health` and `/ready` endpoints for Kubernetes/Docker orchestration |
| **Redis** | Optional shared memory backend for multi-instance deployments |
| **Summarization** | LLM-powered conversation compression to manage token costs |
| **Dashboard** | SSE-based real-time monitoring with metrics (messages/sec, token usage, error rates) |
| **Teams** | Multi-user roles (Admin/User), per-team daily budgets, shared plugin configs |
| **Device Pairing** | Secure 6-digit codes with expiry for mobile companion app connections |
| **i18n** | YAML locale files with variable substitution (English, Spanish included) |
| **TUI** | Rich terminal interface with colorized output, status panels, help display |
| **Observability** | OpenTelemetry-compatible metrics, counters, gauges, histograms, and spans |
| **Security Scanner** | Deep audit scanning for leaked secrets, risky configs, dangerous code patterns |
| **2FA** | TOTP-based two-factor authentication for CRITICAL severity actions |

## Security Architecture

> Full policy and responsible disclosure: [SECURITY.md](SECURITY.md)

| Layer | Implementation |
|---|---|
| **Credential storage** | OS keychain via `keyring`, Fernet + Argon2id fallback, `VAULTBOT_*` env vars for Docker |
| **Zero-trust auth** | Every user must be explicitly allowlisted; unknown senders are rejected and logged |
| **Immutable defaults** | `auth.require_allowlist`, `plugins.require_signature`, `actions.require_approval`, `audit.enabled` cannot be set to false |
| **Prompt guard** | 13 injection patterns (ignore instructions, jailbreak, DAN mode, role override, etc.) + 3 output leak patterns |
| **Input sanitizer** | Strips zero-width chars, control chars, bidi overrides; normalizes Unicode (NFC); 4096-char limit |
| **Rate limiting** | Token bucket per user and globally, always enabled, configurable burst/sustain rates |
| **Plugin signing** | Ed25519 signatures verified against a local trust store of approved public keys |
| **Plugin sandbox** | Subprocess isolation, restricted PATH/env, network allowlists from manifest, hard timeout + kill |
| **Action approval** | Severity-based gates — MEDIUM+ actions require explicit user confirmation via messaging platform |
| **Audit logging** | Structured JSON, append-only, covers auth, messages, actions, plugins, config changes, errors |
| **SSRF protection** | Blocks internal IPs, cloud metadata endpoints, non-HTTP schemes in web fetch and browser tools |
| **Secret scanning** | Pre-commit hooks + audit scanner detect leaked API keys, passwords, and tokens |
| **2FA enforcement** | TOTP-based verification for CRITICAL actions (key rotation, data deletion) |

## Architecture

```
src/vaultbot/                          106 source files across 14 modules
├── core/                            Bot orchestrator, router, context, compaction,
│                                    summarizer, task engine, healthcheck, auto-reply
├── platforms/                       Telegram, Discord, WhatsApp, Signal, Slack, Teams,
│                                    iMessage, IRC, Matrix, Mattermost, LINE, Google Chat,
│                                    Twitch, Nostr, webhook server
├── llm/                             Claude, OpenAI, Gemini, compatible providers, local
│                                    adapters, prompt guard, factory, fallback
├── plugins/                         Base, loader, sandbox, signer, registry, SDK,
│                                    marketplace, version manager
├── security/                        Credentials, auth, rate limiter, audit, policy,
│                                    sanitizer, teams, audit scanner, two-factor
├── memory/                          SQLite, Redis, vector store (semantic search)
├── media/                           Image generation (DALL-E, Stability AI), TTS (OpenAI,
│                                    ElevenLabs), video generation, music generation,
│                                    media understanding (link extraction)
├── tools/                           Web search (Brave, Tavily), web fetch (SSRF protected),
│                                    browser automation (Playwright), canvas, polls
├── mcp/                             Model Context Protocol client (stdio transport)
├── agents/                          Sub-agent spawning and orchestration
├── cron/                            Scheduled task system with cron expressions
├── hooks/                           Before/after tool execution event system
├── i18n/                            Internationalization with YAML locales
├── dashboard/                       SSE web dashboard, REST API, real-time metrics
├── config.py                        Pydantic config with .env + YAML + env vars
├── cli.py                           7 command groups, 20+ subcommands
├── daemon.py                        Background daemon with PID management
├── setup.py                         Setup wizard and doctor diagnostics
├── tui.py                           Terminal UI with ANSI colors
├── pairing.py                       Device pairing for companion apps
└── observability.py                 OpenTelemetry-compatible metrics and tracing
```

## Configuration

VaultBot reads configuration from three sources (highest priority first):

1. **Environment variables** — `VAULTBOT_*` prefix, best for Docker
2. **`.env` file** — auto-loaded by pydantic-settings
3. **YAML config** — `~/.vaultbot/config.yaml`, created by `vaultbot init`

### Environment Variables

```bash
cp .env.example .env
# Edit .env with your tokens, API keys, and preferences
```

All 30+ variables are documented in [`.env.example`](.env.example), organized by section: general, LLM, platforms, rate limiting, infrastructure.

### Credential Lookup Order

| Priority | Source | Best for |
|---|---|---|
| 1 | `VAULTBOT_*` env var | Docker, CI/CD |
| 2 | OS keychain (`keyring`) | Desktop (macOS, Windows, Linux) |
| 3 | Encrypted file store | Headless servers |

### Platform Credentials

| Platform | What you need |
|---|---|
| Telegram | Bot token from [@BotFather](https://t.me/BotFather) |
| Discord | Bot token from Discord Developer Portal |
| WhatsApp | Access token + Phone Number ID from Meta Business |
| Signal | Phone number + `signal-cli` daemon running |
| Slack | Bot token (`xoxb-`) + App token (`xapp-`) from Slack API |
| Teams | App ID + App Password from Azure Bot registration |
| iMessage | None — uses local Messages.app (macOS only) |
| IRC | Server, port, nick, channels (TLS by default) |
| Matrix | Homeserver URL + access token or user/password |
| Mattermost | Server URL + personal access token |
| LINE | Channel access token + channel secret |
| Google Chat | Service account key or webhook URL |
| Twitch | OAuth token + bot username |
| Nostr | Private key hex + relay URLs |

## Docker Deployment

```bash
# Standard: bot + Claude API
docker compose up -d vaultbot

# With Redis for multi-instance shared state
docker compose up -d vaultbot redis

# With local LLM (Ollama)
docker compose --profile local-llm up -d
```

### Container Security

| Measure | Details |
|---|---|
| Non-root user | Runs as `vaultbot:vaultbot` (UID/GID created at build) |
| Read-only filesystem | Root FS is read-only; `/tmp` is tmpfs (noexec, nosuid, 64MB) |
| Capability dropping | All Linux capabilities dropped via `cap_drop: ALL` |
| Privilege escalation | Blocked via `no-new-privileges: true` |
| Network isolation | Bridge network (`vaultbot-net`) between services |
| Log rotation | Docker json-file driver, 10MB max, 3 files |
| Health checks | Bot: HTTP `/health` every 30s; Redis: `redis-cli ping` every 10s |
| Persistent volumes | `vaultbot-data` (config/memory/logs), `redis-data`, `ollama-data` |

## CLI Reference

### Core

```bash
vaultbot init                            # Interactive setup wizard
vaultbot run                             # Start the bot
vaultbot doctor                          # Run diagnostic checks
vaultbot run -c ./config.yaml            # Start with custom config
```

### Credentials

```bash
vaultbot credentials set <key>           # Store in OS keychain (hidden input)
vaultbot credentials check <key>         # Check existence without revealing value
vaultbot credentials delete <key>        # Remove from keychain
```

### Plugins

```bash
vaultbot plugin install <dir>            # Install a signed plugin
vaultbot plugin list                     # List installed plugins with status
vaultbot plugin enable <name>            # Enable a disabled plugin
vaultbot plugin disable <name>           # Disable without uninstalling
vaultbot plugin uninstall <name>         # Remove from registry
vaultbot plugin sign <dir> <key-file>    # Sign with Ed25519 private key
vaultbot plugin keygen <output-dir>      # Generate Ed25519 signing keypair
```

### Plugin SDK

```bash
vaultbot sdk new <name>                  # Scaffold plugin with boilerplate
vaultbot sdk test <dir>                  # Run 5-test validation harness
vaultbot sdk validate <dir>              # Check manifest for errors
```

### Marketplace & Teams

```bash
vaultbot marketplace search <query>      # Search plugin marketplace
vaultbot marketplace info <name>         # Get plugin details
vaultbot team create <name>              # Create a new team
vaultbot team list                       # List all teams
```

## Plugin Development

### Full Workflow

```bash
# 1. Scaffold
vaultbot sdk new weather-lookup --desc "Weather by location" --author "you"

# 2. Implement logic in weather-lookup/plugin.py
#    (see examples/plugins/ for reference)

# 3. Test locally (runs 5 automated checks)
vaultbot sdk test ./weather-lookup

# 4. Validate manifest
vaultbot sdk validate ./weather-lookup

# 5. Generate signing key (one time)
vaultbot plugin keygen ./my-keys

# 6. Sign the plugin
vaultbot plugin sign ./weather-lookup ./my-keys/vaultbot_signing_key.pem

# 7. Trust the key and install
cp ./my-keys/vaultbot_signing_key.pub ~/.vaultbot/trust_store/
vaultbot plugin install ./weather-lookup
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration / e2e tests only
pytest tests/integration/ -v

# Lint
ruff check src/ tests/

# Format check
ruff format --check src/ tests/
```

### Test Breakdown

| Category | Tests | Coverage |
|---|---|---|
| **Security** | 56+ | Auth, rate limiting, policy, sanitizer, prompt guard, teams, credentials, logging, audit scanner, 2FA |
| **Core** | 50+ | Message routing, context, compaction, summarizer, healthcheck, task engine, auto-reply |
| **Platforms** | 180+ | All 14 adapters: init, send, receive, healthcheck, connect/disconnect, line handling |
| **LLM Providers** | 40+ | Gemini, compatible presets, factory, fallback/failover, protocol compliance |
| **Media & Tools** | 100+ | Image/video/music/TTS generation, web search/fetch, browser, canvas, polls |
| **Plugins** | 60+ | Signing, sandbox, registry, SDK, marketplace, version manager |
| **Infrastructure** | 80+ | MCP, cron, hooks, sub-agents, daemon, pairing, i18n, TUI, metrics, observability |
| **E2E Integration** | 80+ | Full pipeline per platform, multi-user isolation, injection blocking, failover |
| **Total** | **840+** | |

## Project Overview

| Metric | Value |
|---|---|
| **Version** | 0.1.0 (alpha) |
| **Language** | Python 3.11+ |
| **Source files** | 106 |
| **Test files** | 60 |
| **Total tests** | 840+ |
| **Platforms** | 14 |
| **LLM providers** | 16 (3 native + 12 compatible + custom) |
| **Memory backends** | 3 (SQLite, Redis, Vector) |
| **Security layers** | 10+ |
| **CLI commands** | 20+ across 7 groups |
| **Config variables** | 30+ |
| **CI/CD** | GitHub Actions (lint, format, type check, tests, security audit, Docker) |
| **License** | BSL 1.1 (converts to Apache 2.0 on 2030-04-11) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR process.

For security vulnerabilities, see [SECURITY.md](SECURITY.md) for the responsible disclosure process.

For incident response procedures, see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md).

## License

VaultBot is licensed under the [Business Source License 1.1](LICENSE).

**Free to use** for personal, development, testing, educational, and internal purposes. A [commercial license](mailto:your-email@example.com) is required for production services offered to third parties.

On **2030-04-11**, all code released under this license automatically converts to **Apache License 2.0**.

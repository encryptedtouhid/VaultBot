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
  <em>7 platforms &bull; 13 LLM providers &bull; 10 security layers &bull; 235 tests</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#supported-platforms">Platforms</a> &bull;
  <a href="#security-architecture">Security</a> &bull;
  <a href="#docker-deployment">Docker</a> &bull;
  <a href="#plugin-development">Plugins</a> &bull;
  <a href="#cli-reference">CLI</a> &bull;
  <a href="#testing">Testing</a>
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

| Platform | Library | Connection Mode |
|---|---|---|
| **Telegram** | `python-telegram-bot` | Polling + Webhook |
| **Discord** | `nextcord` | Message events + intents |
| **WhatsApp** | `httpx` (Cloud API) | Webhook |
| **Signal** | `signal-cli` JSON-RPC | TCP polling |
| **Slack** | `slack-bolt` | Socket Mode + Events API |
| **Microsoft Teams** | `botbuilder-core` | Bot Framework webhook |
| **iMessage** | AppleScript + SQLite | Local polling (macOS only) |

### 13 LLM Providers

Any OpenAI-compatible API works out of the box. Native SDKs for Claude and OpenAI.

| Provider | Type | Default Model |
|---|---|---|
| **Claude** (recommended) | Native SDK | claude-sonnet-4-20250514 |
| **OpenAI GPT** | Native SDK | gpt-4o |
| **OpenRouter** | Compatible | anthropic/claude-sonnet-4 (200+ models) |
| **Together AI** | Compatible | Llama-3-70b |
| **Groq** | Compatible | llama-3.1-70b-versatile |
| **Mistral** | Compatible | mistral-large-latest |
| **Perplexity** | Compatible | llama-3.1-sonar-large (with web search) |
| **DeepSeek** | Compatible | deepseek-chat |
| **Fireworks AI** | Compatible | llama-v3p1-70b-instruct |
| **Ollama** | Local | llama3.2 |
| **vLLM** | Local | Any loaded model |
| **LM Studio** | Local | Any loaded model |
| **Custom** | Any URL | Any OpenAI-compatible endpoint |

All LLM calls pass through a **prompt injection guard** that scans for 13 known attack patterns and 3 output leak indicators before responses reach users.

### Plugin System

| Feature | Description |
|---|---|
| **Ed25519 signing** | Unsigned or untrusted plugins refuse to load |
| **Subprocess sandbox** | Plugins run in isolated processes via JSON-RPC with restricted env |
| **Manifest permissions** | Plugins declare network domains, filesystem access, and required secrets |
| **Time & memory limits** | Configurable timeout (default 30s) and memory cap (default 256MB) |
| **Approval engine** | 5 severity levels: INFO (auto) / LOW (audit) / MEDIUM (confirm) / HIGH (confirm + cooldown) / CRITICAL (confirm + 2FA) |
| **SDK** | Scaffold, test, validate, sign, and install plugins from the CLI |
| **Marketplace** | Client for browsing and installing reviewed plugins |

### Production Hardening

| Feature | Details |
|---|---|
| **Docker** | Multi-stage build, non-root user, read-only FS, all capabilities dropped |
| **Healthcheck** | `/health` and `/ready` endpoints for Kubernetes/Docker orchestration |
| **Redis** | Optional shared memory backend for multi-instance deployments |
| **Summarization** | LLM-powered conversation compression to manage token costs |
| **File logging** | Rotating JSON logs: `vaultbot.log`, `vaultbot.error.log`, `audit.log` (10MB, 5 backups) |
| **Dashboard** | SSE-based real-time monitoring, token-authenticated, localhost by default |
| **Teams** | Multi-user roles (Admin/User), per-team daily budgets, shared plugin configs |

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

## Architecture

```
src/vaultbot/                          54 source files across 8 modules
├── core/                            Bot orchestrator, router, context, summarizer,
│                                    task engine, healthcheck
├── platforms/                       Telegram, Discord, WhatsApp, Signal, Slack,
│                                    Teams, iMessage, webhook server
├── llm/                             Claude, OpenAI, local adapters, prompt guard
├── plugins/                         Base, loader, sandbox, signer, registry,
│                                    SDK, marketplace
├── security/                        Credentials, auth, rate limiter, audit,
│                                    policy, sanitizer, teams
├── memory/                          SQLite and Redis persistent storage
├── dashboard/                       SSE web dashboard with token auth
├── utils/                           Structured logging, crypto, CLI styling
├── config.py                        Pydantic config with .env + YAML + env vars
└── cli.py                           7 command groups, 20+ subcommands
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

### Exposed Ports

| Port | Service |
|---|---|
| 8080 | Webhook server (WhatsApp, Telegram, Teams) |
| 8081 | Healthcheck (`/health`, `/ready`) |
| 8082 | Dashboard (SSE, token-authenticated) |

## CLI Reference

### Core

```bash
vaultbot init                            # Interactive setup wizard with colorful output
vaultbot run                             # Start the bot with all enabled platforms
vaultbot run -c ./config.yaml            # Start with custom config file
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

### Plugin Manifest (`vaultbot_plugin.json`)

```json
{
    "name": "weather-lookup",
    "version": "1.0.0",
    "description": "Look up weather by location",
    "author": "you@example.com",
    "min_vaultbot_version": "0.1.0",
    "network_domains": ["api.openweathermap.org"],
    "filesystem": "none",
    "secrets": ["OPENWEATHER_API_KEY"],
    "timeout_seconds": 10.0,
    "max_memory_mb": 64
}
```

### Example Plugins

| Plugin | Location | What it does |
|---|---|---|
| **Calculator** | `examples/plugins/calculator/` | Safe math via AST parsing (not eval), blocks DoS via exponent limits |
| **Weather** | `examples/plugins/weather/` | OpenWeatherMap API with declared network permissions and secret handling |

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
ruff check src/ tests/ examples/

# Type check
mypy src/
```

### Test Breakdown

| Category | Files | Tests | Coverage |
|---|---|---|---|
| **Security** | 8 | 56 | Auth, rate limiting, policy, sanitizer, prompt guard, teams, credentials, logging |
| **Core** | 4 | 19 | Message routing, context, summarizer, healthcheck, task engine |
| **Plugins** | 5 | 41 | Signing, verification, sandbox, registry, SDK, calculator plugin |
| **Platforms** | 1 | 9 | Import guards, platform names, macOS checks |
| **Memory** | 1 | 8 | SQLite CRUD, persistence across restarts, chat isolation |
| **Dashboard** | 1 | 9 | SSE broadcasting, events, config, marketplace entries |
| **E2E Integration** | 3 | 59 | Full pipeline, multi-user isolation, injection blocking, plugin lifecycle, memory persistence, team workflows, SSE streaming |
| **Webhook** | 1 | 4 | Query parsing, WhatsApp verification |
| **Total** | **24** | **235** | |

## Logging

VaultBot writes structured JSON logs to `~/.vaultbot/logs/`:

| File | Content | Level | Rotation |
|---|---|---|---|
| `vaultbot.log` | All application events | Configured (default INFO) | 10MB, 5 backups |
| `vaultbot.error.log` | Warnings and errors only | WARNING+ | 10MB, 5 backups |
| `audit.log` | Security audit events | All | 10MB, 5 backups |

Every log entry includes: ISO timestamp, log level, event name, source filename, function name, and line number. File permissions are `0600` (owner read/write only).

## Project Overview

| Metric | Value |
|---|---|
| **Version** | 0.1.0 (alpha) |
| **Language** | Python 3.11+ |
| **Source files** | 54 |
| **Test files** | 28 |
| **Total tests** | 235 |
| **Platforms** | 7 |
| **LLM providers** | 13 (2 native + 10 compatible + custom) |
| **Memory backends** | 2 (SQLite, Redis) |
| **Security layers** | 10 |
| **CLI commands** | 20+ across 7 groups |
| **Config variables** | 30+ |
| **License** | BSL 1.1 (converts to Apache 2.0 on 2030-04-11) |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Write tests for your changes
4. Ensure all tests pass: `pytest tests/ -v`
5. Ensure lint passes: `ruff check src/ tests/`
6. Commit your changes with a descriptive message
7. Push to the branch and open a Pull Request

For security vulnerabilities, see [SECURITY.md](SECURITY.md) for the responsible disclosure process.

## License

VaultBot is licensed under the [Business Source License 1.1](LICENSE).

**Free to use** for personal, development, testing, educational, and internal purposes. A [commercial license](mailto:your-email@example.com) is required for production services offered to third parties.

On **2030-04-11**, all code released under this license automatically converts to **Apache License 2.0**.

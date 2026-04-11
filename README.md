<p align="center">
  <pre align="center">
  ███████╗███████╗███╗   ██╗██████╗  ██████╗ ████████╗
  ╚══███╔╝██╔════╝████╗  ██║██╔══██╗██╔═══██╗╚══██╔══╝
    ███╔╝ █████╗  ██╔██╗ ██║██████╔╝██║   ██║   ██║
   ███╔╝  ██╔══╝  ██║╚██╗██║██╔══██╗██║   ██║   ██║
  ███████╗███████╗██║ ╚████║██████╔╝╚██████╔╝   ██║
  ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝    ╚═╝
  </pre>
</p>

<p align="center">
  <strong>Security-first, open-source AI agent bot for messaging platforms</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#supported-platforms">Platforms</a> &bull;
  <a href="#security">Security</a> &bull;
  <a href="#docker">Docker</a> &bull;
  <a href="#plugin-development">Plugins</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

## Why ZenBot?

Existing AI agent bots like OpenClaw ship with authentication disabled, store credentials in plain text, and run unvetted plugins with full host access — resulting in [138+ CVEs](https://blink.new/blog/openclaw-security-best-practices-2026), 42,000+ exposed instances, and 824+ malicious plugins in the wild.

ZenBot is built differently. Every security mechanism is **on by default and cannot be turned off**. Credentials are encrypted, plugins are signed and sandboxed, and every action is audited.

## Quick Start

```bash
# Install from source
pip install -e .

# Interactive setup wizard (credentials stored in OS keychain)
zenbot init

# Start the bot
zenbot run
```

Or with Docker:

```bash
cp .env.example .env    # Edit with your tokens/keys
docker compose up -d
```

## Features

### 7 Messaging Platforms

| Platform | Library | Mode |
|---|---|---|
| **Telegram** | python-telegram-bot | Polling + Webhook |
| **Discord** | nextcord | Message events |
| **WhatsApp** | httpx (Cloud API) | Webhook |
| **Signal** | signal-cli JSON-RPC | Polling |
| **Slack** | slack-bolt | Socket Mode + Events API |
| **Microsoft Teams** | botbuilder-core | Bot Framework webhook |
| **iMessage** | AppleScript bridge | Local polling (macOS only) |

### 3 LLM Backends

| Provider | Library | Notes |
|---|---|---|
| **Claude** (default) | anthropic SDK | Best reasoning, safety-focused |
| **OpenAI GPT** | openai SDK | GPT-4o and newer |
| **Local Models** | httpx | Ollama, vLLM, llama.cpp (OpenAI-compatible) |

All LLM calls are wrapped with a **prompt injection guard** (17 attack patterns detected) and output leak scanning.

### Plugin System

Extend ZenBot with signed, sandboxed plugins:

- **Ed25519 signing** — unsigned or untrusted plugins refuse to load
- **Subprocess sandbox** — plugins run in isolated processes via JSON-RPC, never in the main bot process
- **Manifest permissions** — plugins declare what they need (network domains, filesystem, secrets)
- **Approval engine** — 5-level severity system; destructive actions require user confirmation
- **Marketplace** — browse, download, and submit plugins with mandatory review

### Production Hardening

- **Docker** — multi-stage build, non-root user, read-only filesystem, dropped capabilities
- **Healthcheck** — `/health` and `/ready` endpoints for Kubernetes / Docker orchestration
- **Redis** — optional backend for multi-instance deployments with shared state
- **Conversation summarization** — LLM-powered compression keeps token costs manageable
- **File logging** — rotating JSON logs: `zenbot.log`, `zenbot.error.log`, `audit.log` with caller info
- **Web dashboard** — SSE-based real-time monitoring (no websockets), token-authenticated

### Teams & Multi-User

- Role-based access control (Admin / User)
- Team-based grouping with shared plugin configs
- Per-team daily message budgets
- Cross-platform user isolation

## Security

> See [SECURITY.md](SECURITY.md) for the full security policy and responsible disclosure process.

### Security Architecture

| Layer | What It Does |
|---|---|
| **Encrypted credentials** | OS keychain via `keyring`, Fernet+Argon2 fallback, env var support for Docker |
| **Zero-trust auth** | Every user must be allowlisted. Unknown senders get rejected and logged |
| **Immutable defaults** | `auth`, `plugin signing`, `approval flows`, and `audit logging` cannot be disabled |
| **Prompt injection guard** | 17 input patterns + 3 output leak patterns block jailbreaks and prompt extraction |
| **Input sanitization** | Strips zero-width chars, control chars, bidi overrides; enforces length limits |
| **Rate limiting** | Per-user and global token bucket rate limiting, always enabled |
| **Plugin sandbox** | Subprocess isolation, restricted env, network allowlist, memory/time limits |
| **Plugin signing** | Ed25519 signatures verified against a local trust store |
| **Action approval** | INFO/LOW auto-approved; MEDIUM needs confirmation; HIGH adds cooldown; CRITICAL needs 2FA |
| **Audit logging** | Structured JSON, append-only, every auth/action/plugin/error event |

### vs OpenClaw

| Issue | OpenClaw | ZenBot |
|---|---|---|
| CVEs tracked | 138+ | 0 (secure by design) |
| Auth default | Disabled | Always on, immutable |
| Credentials | Plain text files | OS keychain + encrypted fallback |
| Plugin vetting | Zero review | Ed25519 signed + sandboxed |
| Prompt injection | No protection | 17-pattern guard + output scanning |
| Autonomy control | Over-autonomous | 5-level approval engine |

## Architecture

```
src/zenbot/
├── core/           Bot orchestrator, message routing, context, summarizer, healthcheck
├── platforms/      Telegram, Discord, WhatsApp, Signal, Slack, Teams, iMessage
├── llm/            Claude, OpenAI, local adapters + prompt injection guard
├── plugins/        Base, loader, sandbox, signer, registry, SDK, marketplace
├── security/       Credentials, auth, rate limiter, audit, policy, sanitizer, teams
├── memory/         SQLite (encrypted) and Redis persistent storage
├── dashboard/      Web dashboard with SSE real-time events
└── utils/          Structured logging, crypto, CLI styling
```

## Configuration

ZenBot supports three configuration methods (in priority order):

1. **Environment variables** — `ZENBOT_*` prefix (best for Docker)
2. **`.env` file** — loaded automatically by pydantic-settings
3. **YAML config** — `~/.zenbot/config.yaml` (created by `zenbot init`)

### Environment Variables

```bash
cp .env.example .env
# Edit .env with your values
```

See [`.env.example`](.env.example) for all available variables.

### Credential Storage

| Environment | Storage Method |
|---|---|
| **Desktop (macOS)** | macOS Keychain via `keyring` |
| **Desktop (Windows)** | Windows Credential Locker |
| **Desktop (Linux)** | GNOME Keyring / KDE Wallet |
| **Headless / Server** | Fernet-encrypted file with Argon2 key derivation |
| **Docker** | `ZENBOT_*` environment variables |

### Platform Setup

| Platform | Credentials Needed |
|---|---|
| Telegram | Bot token from [@BotFather](https://t.me/BotFather) |
| Discord | Bot token from Discord Developer Portal |
| WhatsApp | Access token + Phone ID from Meta Business |
| Signal | Phone number + `signal-cli` daemon running |
| Slack | Bot token (xoxb-) + App token (xapp-) from Slack API |
| Teams | App ID + App Password from Azure Bot registration |
| iMessage | None (uses local Messages.app, macOS only) |

## Docker

```bash
# Standard deployment (Telegram/Discord/WhatsApp + Claude)
cp .env.example .env
# Edit .env with your credentials
docker compose up -d

# With Redis for multi-instance
docker compose up -d zenbot redis

# With local LLM (Ollama)
docker compose --profile local-llm up -d
```

### Docker Security

- Non-root user (`zenbot:zenbot`)
- Read-only root filesystem
- All Linux capabilities dropped
- `no-new-privileges` enforced
- tmpfs for `/tmp` (noexec, nosuid)
- JSON log rotation (10MB, 3 files)
- Bridge network isolation between services
- Redis healthcheck enabled

## CLI Reference

```bash
# ---- Core ----
zenbot init                          # Interactive setup wizard
zenbot run                           # Start the bot
zenbot run -c ./config.yaml          # Start with custom config

# ---- Credentials ----
zenbot credentials set <key>         # Store securely in OS keychain
zenbot credentials check <key>       # Check if credential exists
zenbot credentials delete <key>      # Remove a credential

# ---- Plugins ----
zenbot plugin install <dir>          # Install a signed plugin
zenbot plugin list                   # List installed plugins
zenbot plugin enable <name>          # Enable a plugin
zenbot plugin disable <name>         # Disable a plugin
zenbot plugin uninstall <name>       # Remove a plugin
zenbot plugin sign <dir> <key>       # Sign a plugin with Ed25519 key
zenbot plugin keygen <dir>           # Generate signing keypair

# ---- Plugin SDK ----
zenbot sdk new <name>                # Scaffold a new plugin project
zenbot sdk test <dir>                # Run the 5-test harness
zenbot sdk validate <dir>            # Validate manifest file

# ---- Marketplace ----
zenbot marketplace search <query>    # Search for plugins
zenbot marketplace info <name>       # Get plugin details

# ---- Teams ----
zenbot team create <name>            # Create a team
zenbot team list                     # List all teams
```

## Plugin Development

```bash
# 1. Scaffold a new plugin
zenbot sdk new weather-lookup --desc "Look up weather" --author "you"

# 2. Implement your logic in weather-lookup/plugin.py

# 3. Test locally
zenbot sdk test ./weather-lookup

# 4. Validate the manifest
zenbot sdk validate ./weather-lookup

# 5. Generate a signing key (one time)
zenbot plugin keygen ./my-keys

# 6. Sign the plugin
zenbot plugin sign ./weather-lookup ./my-keys/zenbot_signing_key.pem

# 7. Install locally
cp ./my-keys/zenbot_signing_key.pub ~/.zenbot/trust_store/
zenbot plugin install ./weather-lookup
```

### Plugin Manifest (`zenbot_plugin.json`)

```json
{
    "name": "weather-lookup",
    "version": "1.0.0",
    "description": "Look up weather by location",
    "author": "you@example.com",
    "network_domains": ["api.openweathermap.org"],
    "filesystem": "none",
    "secrets": ["OPENWEATHER_API_KEY"],
    "timeout_seconds": 10.0,
    "max_memory_mb": 64
}
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all 235 tests
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

### Test Coverage

| Area | Tests | What's Covered |
|---|---|---|
| Security | 56 | Auth, rate limiting, policy, sanitizer, prompt guard, teams, credentials |
| Core | 19 | Message routing, context, summarizer, healthcheck, task engine |
| Plugins | 41 | Signing, verification, sandbox, registry, SDK, calculator plugin |
| Platforms | 9 | Import guards, platform names, iMessage macOS check |
| Memory | 8 | SQLite persistence, history, summaries, preferences |
| Dashboard | 9 | SSE broadcasting, events, config, marketplace entries |
| Logging | 7 | File creation, JSON format, error filtering, permissions, audit separation |
| E2E | 59 | Full pipeline, multi-user isolation, injection blocking, persistence |
| **Total** | **235** | |

## Logging

ZenBot writes structured JSON logs to `~/.zenbot/logs/`:

| File | Content | Level |
|---|---|---|
| `zenbot.log` | All application events | Configured (default: INFO) |
| `zenbot.error.log` | Errors and warnings only | WARNING+ |
| `audit.log` | Security audit events | All auth, actions, plugins |

Every log entry includes timestamp, level, event name, filename, function, and line number.

Logs rotate at 10MB with 5 backups retained. File permissions are `0600` (owner-only).

## Project Stats

- **Language**: Python 3.11+
- **Source files**: 54
- **Test files**: 28
- **Total tests**: 235
- **Platforms**: 7
- **LLM backends**: 3
- **Security layers**: 10
- **License**: MIT

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/ -v`)
5. Ensure lint passes (`ruff check src/ tests/`)
6. Commit your changes
7. Push to the branch
8. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

# ZenBot

A security-first, open-source AI agent bot for messaging platforms. Built as a safer alternative to OpenClaw, with encrypted credentials, mandatory authentication, plugin sandboxing, and prompt injection protection baked in from day one.

## Quick Start

```bash
# Install
pip install -e .

# Run the setup wizard
zenbot init

# Start the bot
zenbot run
```

## Features

### Multi-Platform Messaging
Connect to users wherever they are:
- **Telegram** — polling and webhook modes
- **Discord** — message events via nextcord
- **WhatsApp** — Cloud API with webhook support
- **Signal** — via signal-cli JSON-RPC

### Pluggable LLM Backend
Bring your own AI:
- **Claude** (Anthropic) — default, recommended
- **OpenAI GPT** — GPT-4o and newer
- **Local models** — Ollama, vLLM, llama.cpp via OpenAI-compatible API

### Security-First Architecture

| Feature | Description |
|---|---|
| **Encrypted credentials** | OS keychain via `keyring`, Fernet-encrypted fallback — never plain text |
| **Zero-trust auth** | Every user must be explicitly allowlisted before the bot responds |
| **Immutable security defaults** | Auth, plugin signing, approval flows, and audit logging cannot be disabled |
| **Prompt injection guard** | 17 input patterns + output leak detection, blocks jailbreak attempts |
| **Input sanitization** | Strips zero-width chars, control chars, bidi overrides, enforces length limits |
| **Rate limiting** | Per-user and global token bucket rate limiting |
| **Audit logging** | Structured, append-only logs for all security events |

### Plugin System
Extend ZenBot safely:
- **Ed25519 signing** — unsigned plugins refuse to load
- **Subprocess sandbox** — plugins run in isolated processes via JSON-RPC
- **Manifest permissions** — declared network domains, filesystem access, and secrets
- **Approval engine** — 5-level severity system (INFO → CRITICAL) with user confirmation for destructive actions

### Plugin SDK
Build plugins easily:
```bash
# Scaffold a new plugin
zenbot sdk new my-plugin --desc "My awesome plugin" --author "me"

# Test it locally
zenbot sdk test ./my-plugin

# Validate the manifest
zenbot sdk validate ./my-plugin

# Sign it for distribution
zenbot plugin keygen ./keys
zenbot plugin sign ./my-plugin ./keys/zenbot_signing_key.pem
```

### Production Ready
- **Docker** — multi-stage build, non-root user, read-only filesystem, dropped capabilities
- **Healthcheck** — `/health` and `/ready` endpoints for Kubernetes/Docker orchestration
- **Redis backend** — optional Redis memory store for multi-instance deployments
- **Conversation summarization** — LLM-powered compression of long conversations
- **Web dashboard** — authenticated SSE-based real-time monitoring (no websockets)
- **Teams** — multi-user access with roles, per-team budgets, and shared plugin configs

## Architecture

```
src/zenbot/
├── core/           # Bot orchestrator, message routing, context, summarizer
├── platforms/      # Telegram, Discord, WhatsApp, Signal adapters
├── llm/            # Claude, OpenAI, local model adapters + prompt guard
├── plugins/        # Plugin system: base, loader, sandbox, signer, registry, SDK, marketplace
├── security/       # Credentials, auth, rate limiter, audit, policy, sanitizer, teams
├── memory/         # SQLite and Redis persistent storage
├── dashboard/      # Web dashboard with SSE
└── utils/          # Logging, crypto, CLI styling
```

## CLI Reference

```bash
# Core
zenbot init                          # Setup wizard
zenbot run                           # Start the bot
zenbot run --config ./config.yaml    # Start with custom config

# Credentials (stored in OS keychain, never plain text)
zenbot credentials set <key>         # Store a credential
zenbot credentials check <key>       # Check if a credential exists
zenbot credentials delete <key>      # Remove a credential

# Plugins
zenbot plugin install <dir>          # Install a signed plugin
zenbot plugin list                   # List installed plugins
zenbot plugin enable <name>          # Enable a plugin
zenbot plugin disable <name>         # Disable a plugin
zenbot plugin uninstall <name>       # Remove a plugin
zenbot plugin sign <dir> <key>       # Sign a plugin
zenbot plugin keygen <output-dir>    # Generate signing keypair

# Plugin SDK
zenbot sdk new <name>                # Scaffold a new plugin
zenbot sdk test <dir>                # Run test harness
zenbot sdk validate <dir>            # Validate manifest

# Marketplace
zenbot marketplace search <query>    # Search for plugins
zenbot marketplace info <name>       # Get plugin details

# Teams
zenbot team create <name>            # Create a team
zenbot team list                     # List teams
```

## Docker

```bash
# Build and run
docker-compose up -d

# With Redis for multi-instance
docker-compose up -d zenbot redis
```

The Docker setup includes:
- Non-root user
- Read-only root filesystem
- All capabilities dropped
- No new privileges
- Health checks configured

## Configuration

ZenBot stores config in `~/.zenbot/config.yaml`. Credentials are stored separately in the OS keychain (macOS Keychain, Windows Credential Locker, GNOME Keyring) or an encrypted fallback file.

### Required Setup

| Platform | What you need |
|---|---|
| Telegram | Bot token from [@BotFather](https://t.me/BotFather) |
| Discord | Bot token from Discord Developer Portal |
| WhatsApp | Access token + phone ID from Meta Business |
| Signal | Phone number + `signal-cli` running |

| LLM Provider | What you need |
|---|---|
| Claude | API key from console.anthropic.com |
| OpenAI | API key from platform.openai.com |
| Local | Ollama running (`ollama serve`) |

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all 219 tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only e2e/integration tests
pytest tests/integration/ -v

# Lint
ruff check src/ tests/ examples/
```

## Security

See [SECURITY.md](SECURITY.md) for the security policy and responsible disclosure process.

### Security Design Principles

1. **Zero-trust by default** — all users must be explicitly allowlisted
2. **Encrypted credential storage** — OS keychain or encrypted fallback, never plain text
3. **Immutable security defaults** — core security settings cannot be disabled
4. **Plugin sandboxing** — Ed25519 signing + subprocess isolation + manifest permissions
5. **Action approval flows** — destructive actions require explicit user confirmation
6. **Prompt injection protection** — input scanning + output leak detection
7. **Audit logging** — all security events logged, append-only

## License

MIT

# Getting Started with VaultBot

## Prerequisites

- Python 3.11+
- pip or pipx

## Installation

```bash
pip install vaultbot
```

## Quick Start

1. Run the setup wizard:
```bash
vaultbot setup
```

2. Configure your first channel (e.g., Telegram):
```bash
vaultbot channel add telegram
```

3. Set your LLM provider:
```bash
vaultbot config set llm.provider claude
```

4. Start the bot:
```bash
vaultbot run
```

## Configuration

VaultBot uses YAML configuration stored in `~/.vaultbot/config.yaml`. You can also use environment variables with the `VAULTBOT_` prefix.

## Next Steps

- [Architecture](architecture.md) — How VaultBot works
- [Channels](channels.md) — Platform integrations
- [Plugins](plugins.md) — Extend functionality
- [Security](security.md) — Security model

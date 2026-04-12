# Architecture

## Overview

VaultBot is a security-first, multi-channel AI agent built in Python. It connects messaging platforms to LLM providers through a modular, pluggable architecture.

## Core Components

### Platforms (`src/vaultbot/platforms/`)
Adapters for 25+ messaging platforms: Telegram, Discord, Slack, WhatsApp, Signal, Teams, Matrix, IRC, and more.

### LLM Providers (`src/vaultbot/llm/`)
Multi-provider LLM support: Claude, OpenAI, Gemini, DeepSeek, Qwen, Zhipu, Moonshot, LiteLLM proxy, local models.

### Gateway (`src/vaultbot/gateway/`)
WebSocket gateway with multi-node orchestration, authentication, event bus, and RPC protocol.

### ACP (`src/vaultbot/acp/`)
Approval Control Plane for session lifecycle, policy enforcement, and provenance tracking.

### Context Engine (`src/vaultbot/core/context_engine.py`)
Pluggable context management with token budgeting, compaction, and transcript DAG.

### Media (`src/vaultbot/media/`)
Image/video/music generation, TTS/STT, realtime voice, media understanding, and MIME handling.

### Security (`src/vaultbot/security/`)
Auth, rate limiting, audit logging, code scanning, secrets management, key rotation, 2FA.

### Plugins (`src/vaultbot/plugins/`)
Plugin SDK with command registry, manifest management, lifecycle, and bundled skills.

## Data Flow

```
User Message → Platform Adapter → Router → Context Engine → LLM Provider → Reply Pipeline → Platform
```

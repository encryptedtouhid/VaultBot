# Plugin System

## Overview

VaultBot's plugin system allows extending functionality through:
- **Bundled skills** — Built-in reminder, notes, todo
- **Custom plugins** — User-created extensions
- **Slash commands** — Commands that bypass the LLM
- **MCP tools** — Model Context Protocol integration

## Creating a Plugin

1. Create a plugin manifest (`zenbot_plugin.json`):
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "entry_point": "plugin.py",
  "commands": ["mycommand"]
}
```

2. Implement the plugin:
```python
class MyPlugin:
    async def handle_command(self, command, args):
        return "Plugin response"
```

3. Install:
```bash
vaultbot plugin install ./my-plugin
```

## Plugin Lifecycle

Plugins go through: Installed -> Activating -> Active -> Deactivating -> Inactive

## Bundled Skills

- **Reminder** — Set and manage reminders
- **Notes** — Create and search notes
- **Todo** — Task list management

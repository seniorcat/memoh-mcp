# memoh-mcp

MCP server for managing [Memoh](https://github.com/memohai/Memoh) AI agents from Claude Code, Cursor, or any MCP-compatible client.

## 26 Tools

| Category | Tools |
|----------|-------|
| **Bots** | `list_bots`, `get_bot`, `create_bot`, `update_bot`, `delete_bot` |
| **Containers** | `get_container`, `create_container`, `delete_container`, `start_container`, `stop_container` |
| **Files** | `read_file`, `write_file`, `list_files` |
| **Skills** | `list_skills`, `write_skills`, `delete_skills` |
| **Memory** | `list_memories`, `add_memory`, `search_memory`, `delete_memory` |
| **Chat** | `send_message`, `get_messages` |
| **Settings** | `get_settings`, `update_settings` |
| **Heartbeat** | `heartbeat_logs` |
| **Health** | `health_check` |

## Quick Start

### 1. Install

```bash
pip install mcp python-dotenv
```

Or with uv:

```bash
uv pip install mcp python-dotenv
```

### 2. Configure

Set environment variables (or create a `.env` file next to the server script):

```bash
export MEMOH_API=http://localhost:8080
export MEMOH_USER=admin
export MEMOH_PASS=your-password
```

### 3. Add to Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "memoh": {
      "command": "python3",
      "args": ["/path/to/memoh_mcp_server.py"]
    }
  }
}
```

Or with a `.env` wrapper script:

```json
{
  "mcpServers": {
    "memoh": {
      "command": "/path/to/wrapper.sh"
    }
  }
}
```

Where `wrapper.sh`:

```bash
#!/bin/bash
exec python3 /path/to/memoh_mcp_server.py "$@"
```

### 4. Add to Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "memoh": {
      "command": "python3",
      "args": ["/path/to/memoh_mcp_server.py"],
      "env": {
        "MEMOH_API": "http://localhost:8080",
        "MEMOH_USER": "admin",
        "MEMOH_PASS": "your-password"
      }
    }
  }
}
```

## Usage

Once connected, your AI assistant can manage Memoh bots directly:

- **List bots**: See all bots with their IDs and status
- **Read/write files**: Edit bot identity, soul, memory, and other config files in containers
- **Manage skills**: Add procedural protocols that guide bot behavior
- **Vector memory**: Add, search, and delete bot memories
- **Chat**: Send messages to bots and read their responses
- **Settings**: Configure models, heartbeat intervals, and other bot settings

## Requirements

- Python 3.10+
- Running [Memoh](https://github.com/memohai/Memoh) server
- `mcp` Python package (MCP SDK)
- `python-dotenv` (optional, for `.env` file support)

## License

MIT

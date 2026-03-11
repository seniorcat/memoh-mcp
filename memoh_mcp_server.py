#!/usr/bin/env python3
"""Memoh MCP Server — manage bots, containers, files, memory, and chat."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP

# --- Config -----------------------------------------------------------------
# Load .env from the same directory if present (optional, for local dev).
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # python-dotenv is optional; env vars can be set externally

API = os.environ.get("MEMOH_API", "http://localhost:8080")
CREDS = {
    "username": os.environ.get("MEMOH_USER", "admin"),
    "password": os.environ.get("MEMOH_PASS", ""),
}
if not CREDS["password"]:
    raise SystemExit("MEMOH_PASS environment variable is required")

mcp = FastMCP(
    "memoh",
    instructions=(
        "Memoh MCP Server — manage the Noosphere multi-agent platform.\n\n"
        "Cogitators (bots) are identified by bot_id (UUID). Key container files:\n"
        "- /data/IDENTITY.md — role, function, protocols\n"
        "- /data/SOUL.md — character, principles, voice\n"
        "- /data/MEMORY.md — initial facts\n"
        "- /data/HEARTBEAT.md — heartbeat checklists\n"
        "- /data/TOOLS.md — available tools\n"
        "- /data/PROFILES.md — user profiles\n\n"
        "Use list_bots to discover bot IDs, then manage their containers, "
        "files, skills, and memory.\n"
        "Use send_message to chat with a bot programmatically "
        "(async — returns immediately, response via SSE)."
    ),
)

# --- Auth / HTTP helpers ----------------------------------------------------
_token_cache: dict[str, Any] = {"token": None, "expires": 0}


def _get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires"]:
        return _token_cache["token"]
    result = _api("POST", "/auth/login", CREDS, skip_auth=True)
    token = result.get("access_token", "")
    if not token:
        raise RuntimeError(f"Login failed: {result}")
    _token_cache["token"] = token
    _token_cache["expires"] = time.time() + 3500  # ~1 h
    return token


def _api(
    method: str,
    path: str,
    data: Any = None,
    *,
    skip_auth: bool = False,
    timeout: int = 60,
) -> Any:
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if not skip_auth:
        headers["Authorization"] = f"Bearer {_get_token()}"
    req = urllib.request.Request(
        f"{API}{path}", data=body, headers=headers, method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def _unwrap(result: Any, *keys: str) -> Any:
    """Extract a list from an API response dict by trying keys in order."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for k in keys:
            if k in result:
                return result[k]
    return result


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


# ===== Bot Management ======================================================

@mcp.tool()
def list_bots() -> str:
    """List all bots (cogitators) with IDs, names, and status."""
    result = _api("GET", "/bots")
    if isinstance(result, dict) and "error" in result:
        return _dump(result)
    bots = _unwrap(result, "items", "data")
    lines = []
    for b in bots:
        name = b.get("display_name", "unnamed")
        bid = b.get("id", "?")
        active = b.get("is_active", False)
        lines.append(f"{'✅' if active else '❌'} {name} — {bid}")
    return "\n".join(lines) if lines else "No bots found"


@mcp.tool()
def get_bot(bot_id: str) -> str:
    """Get detailed info about a specific bot."""
    return _dump(_api("GET", f"/bots/{bot_id}"))


@mcp.tool()
def create_bot(
    display_name: str, bot_type: str = "chatbot", metadata: str = "{}",
) -> str:
    """Create a new bot. metadata is a JSON string of key-value pairs."""
    meta = json.loads(metadata) if metadata else {}
    return _dump(_api("POST", "/bots", {
        "type": bot_type,
        "display_name": display_name,
        "is_active": True,
        "metadata": meta,
    }))


@mcp.tool()
def update_bot(bot_id: str, display_name: str = "", is_active: str = "") -> str:
    """Update bot properties. Only provided fields are changed."""
    data: dict[str, Any] = {}
    if display_name:
        data["display_name"] = display_name
    if is_active:
        data["is_active"] = is_active.lower() == "true"
    return _dump(_api("PUT", f"/bots/{bot_id}", data))


@mcp.tool()
def delete_bot(bot_id: str) -> str:
    """Delete a bot permanently."""
    return _dump(_api("DELETE", f"/bots/{bot_id}"))


# ===== Container Management =================================================

@mcp.tool()
def get_container(bot_id: str) -> str:
    """Get container status for a bot."""
    return _dump(_api("GET", f"/bots/{bot_id}/container"))


@mcp.tool()
def create_container(bot_id: str) -> str:
    """Create a container for a bot (starts it)."""
    return _dump(_api("POST", f"/bots/{bot_id}/container"))


@mcp.tool()
def delete_container(bot_id: str, preserve_data: bool = False) -> str:
    """Delete a bot's container. Set preserve_data=True to keep /data files for next container."""
    qs = "?preserve_data=true" if preserve_data else ""
    return _dump(_api("DELETE", f"/bots/{bot_id}/container{qs}"))


@mcp.tool()
def start_container(bot_id: str) -> str:
    """Start a bot's container."""
    return _dump(_api("POST", f"/bots/{bot_id}/container/start"))


@mcp.tool()
def stop_container(bot_id: str) -> str:
    """Stop a bot's container."""
    return _dump(_api("POST", f"/bots/{bot_id}/container/stop"))


# ===== Container Files ======================================================

@mcp.tool()
def read_file(bot_id: str, path: str = "/data/IDENTITY.md") -> str:
    """Read a file from bot's container. Common paths: /data/IDENTITY.md, /data/SOUL.md, /data/MEMORY.md, /data/HEARTBEAT.md, /data/TOOLS.md, /data/PROFILES.md"""
    encoded = urllib.request.quote(path, safe="")
    result = _api("GET", f"/bots/{bot_id}/container/fs/read?path={encoded}")
    if isinstance(result, dict):
        return result.get("content", _dump(result))
    return str(result)


@mcp.tool()
def write_file(bot_id: str, path: str, content: str) -> str:
    """Write content to a file in bot's container."""
    return _dump(_api("POST", f"/bots/{bot_id}/container/fs/write", {
        "path": path, "content": content,
    }))


@mcp.tool()
def list_files(bot_id: str, path: str = "/data") -> str:
    """List files in a directory in bot's container."""
    encoded = urllib.request.quote(path, safe="")
    result = _api("GET", f"/bots/{bot_id}/container/fs/list?path={encoded}")
    entries = _unwrap(result, "entries")
    if isinstance(entries, list):
        return "\n".join(f.get("name", str(f)) for f in entries)
    return _dump(result)


# ===== Skills ===============================================================

@mcp.tool()
def list_skills(bot_id: str) -> str:
    """List all skills for a bot."""
    result = _api("GET", f"/bots/{bot_id}/container/skills")
    if isinstance(result, dict) and "error" in result:
        return _dump(result)
    skills = _unwrap(result, "skills")
    if not skills:
        return "No skills"
    lines = []
    for s in skills:
        name = s.get("name", "unnamed")
        preview = s.get("content", "")[:100]
        lines.append(f"- {name}: {preview}...")
    return "\n".join(lines)


@mcp.tool()
def write_skills(bot_id: str, skills_json: str) -> str:
    """Write skills to a bot. skills_json is a JSON array: [{"name": "...", "content": "..."}]"""
    skills = json.loads(skills_json)
    return _dump(_api("POST", f"/bots/{bot_id}/container/skills", {"skills": skills}))


@mcp.tool()
def delete_skills(bot_id: str) -> str:
    """Delete all skills from a bot."""
    return _dump(_api("DELETE", f"/bots/{bot_id}/container/skills"))


# ===== Memory ===============================================================

@mcp.tool()
def list_memories(bot_id: str) -> str:
    """List all memories for a bot."""
    result = _api("GET", f"/bots/{bot_id}/memory")
    if isinstance(result, dict) and "error" in result:
        return _dump(result)
    memories = _unwrap(result, "results", "items", "data")
    if not memories:
        return "No memories"
    lines = []
    for m in memories:
        mid = m.get("id", "?")[-8:]
        text = m.get("memory", m.get("content", ""))[:120]
        lines.append(f"[{mid}] {text}")
    return "\n".join(lines)


@mcp.tool()
def add_memory(bot_id: str, content: str) -> str:
    """Add a memory to a bot."""
    return _dump(_api("POST", f"/bots/{bot_id}/memory", {"content": content}))


@mcp.tool()
def search_memory(bot_id: str, query: str) -> str:
    """Search bot's memory by query string."""
    return _dump(_api("POST", f"/bots/{bot_id}/memory/search", {"query": query}))


@mcp.tool()
def delete_memory(bot_id: str, memory_id: str) -> str:
    """Delete a specific memory by ID."""
    return _dump(_api("DELETE", f"/bots/{bot_id}/memory/{memory_id}"))


# ===== Chat =================================================================

@mcp.tool()
def send_message(bot_id: str, text: str) -> str:
    """Send a message to a bot. Returns immediately — bot processes async. Use get_messages to check for the response."""
    return _dump(_api("POST", f"/bots/{bot_id}/cli/messages", {
        "message": {"text": text},
    }))


@mcp.tool()
def get_messages(bot_id: str, limit: int = 10) -> str:
    """Get recent message history for a bot."""
    result = _api("GET", f"/bots/{bot_id}/messages?limit={limit}")
    if isinstance(result, dict) and "error" in result:
        return _dump(result)
    messages = _unwrap(result, "items", "data")
    if not messages:
        return "No messages"
    lines = []
    for m in messages:
        role = m.get("role", "?")
        # content can be a string or a nested object with content[].text
        raw_content = m.get("content", "")
        if isinstance(raw_content, dict):
            parts = raw_content.get("content", [])
            if isinstance(parts, list):
                text = " ".join(
                    p.get("text", "") for p in parts if isinstance(p, dict)
                )
            else:
                text = str(parts)
        elif isinstance(raw_content, list):
            text = " ".join(
                p.get("text", "") for p in raw_content if isinstance(p, dict)
            )
        else:
            text = str(raw_content)
        ts = m.get("created_at", "")[:19]
        lines.append(f"[{ts}] {role}: {text[:200]}")
    return "\n".join(lines)


# ===== Settings =============================================================

@mcp.tool()
def get_settings(bot_id: str) -> str:
    """Get bot settings (model, provider, heartbeat config, etc.)."""
    return _dump(_api("GET", f"/bots/{bot_id}/settings"))


@mcp.tool()
def update_settings(bot_id: str, settings_json: str) -> str:
    """Update bot settings. settings_json is a JSON object with fields to update."""
    return _dump(_api("PUT", f"/bots/{bot_id}/settings", json.loads(settings_json)))


# ===== Heartbeat ============================================================

@mcp.tool()
def heartbeat_logs(bot_id: str) -> str:
    """Get heartbeat execution logs for a bot."""
    return _dump(_api("GET", f"/bots/{bot_id}/heartbeat/logs"))


# ===== Health ===============================================================

@mcp.tool()
def health_check() -> str:
    """Check Memoh server health and capabilities."""
    return _dump(_api("GET", "/ping"))


if __name__ == "__main__":
    mcp.run(transport="stdio")

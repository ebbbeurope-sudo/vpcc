import asyncio
import json
from typing import Optional

from fastapi import WebSocket

from . import database

# token -> websocket
_agents: dict[str, WebSocket] = {}

# token -> (user_id, pc_id)
_agents_meta: dict[str, dict] = {}

# token -> pending future (ждёт answer команды)
_replies: dict[str, asyncio.Future] = {}


async def register_agent(token: str, ws: WebSocket, user_id: int, pc_id: int):
    _agents[token] = ws
    _agents_meta[token] = {"user_id": user_id, "pc_id": pc_id}


def unregister_agent(token: str):
    _agents.pop(token, None)
    _agents_meta.pop(token, None)
    fut = _replies.pop(token, None)
    if fut and not fut.done():
        fut.set_result({"ok": False, "error": "agent disconnected"})


def get_agent_token_for_user_pc(user_id: int, pc_id: int) -> Optional[str]:
    for token, meta in _agents_meta.items():
        if meta["user_id"] == user_id and meta["pc_id"] == pc_id:
            return token
    return None


def is_agent_online(token: str) -> bool:
    return token in _agents


async def send_command(token: str, command: dict) -> dict:
    ws = _agents.get(token)
    if not ws:
        return {"ok": False, "error": "agent offline"}
    fut = asyncio.get_event_loop().create_future()
    _replies[token] = fut
    try:
        await ws.send_text(json.dumps(command))
        return await asyncio.wait_for(fut, timeout=15)
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout"}
    finally:
        _replies.pop(token, None)


def resolve_reply(token: str, data: dict):
    fut = _replies.get(token)
    if fut and not fut.done():
        fut.set_result(data)
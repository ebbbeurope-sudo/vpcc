import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core import database, manager

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    token = None
    try:
        hello = json.loads(await ws.receive_text())
        if hello.get("type") != "hello":
            await ws.close(code=1008, reason="bad handshake")
            return
        token = hello.get("token", "")
        pc = database.get_pc_by_token(token)
        if not pc:
            await ws.send_text(json.dumps({"type": "error", "data": "invalid token"}))
            await ws.close(code=1008, reason="invalid token")
            return

        await manager.register_agent(token, ws, pc["user_id"], pc["id"])
        _set_online(pc["id"], True)
        await ws.send_text(json.dumps({"type": "hello_ok", "data": {"name": pc["name"]}}))

        while True:
            text = await ws.receive_text()
            data = json.loads(text)
            print(f"[WS] recv token={token[:6]} type={data.get('type')}", flush=True)
            if data.get("type") == "result":
                print(f"[WS] resolving reply for {token[:6]}", flush=True)
                manager.resolve_reply(token, data.get("data", {}))
    except WebSocketDisconnect:
        pass
    finally:
        if token:
            manager.unregister_agent(token)
            if database.get_pc_by_token(token):
                _set_online(database.get_pc_by_token(token)["id"], False)


def _set_online(pc_id: int, online: bool):
    with database.get_conn() as conn:
        conn.execute(
            "UPDATE pcs SET online = ? WHERE id = ?",
            (int(online), pc_id),
        )
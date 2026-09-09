import random
import string
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import database, manager

router = APIRouter(prefix="/api")


class BindRequest(BaseModel):
    code: str
    name: str = "PC"


class CommandRequest(BaseModel):
    user_id: int
    pc_id: int
    cmd: str
    params: dict = {}


@router.post("/bind")
async def bind_pc(req: BindRequest):
    row = database.get_code_user(req.code.strip())
    if not row:
        raise HTTPException(400, "invalid code")
    if time.time() - row["created_at"] > 300:
        database.delete_code(req.code)
        raise HTTPException(400, "code expired")
    if database.user_pc_count(row["user_id"]) >= 3:
        raise HTTPException(400, "pc limit reached")

    token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    pc_id = database.add_pc(row["user_id"], req.name, token)
    database.delete_code(req.code)
    return {"ok": True, "token": token, "pc_id": pc_id}


@router.get("/pcs/{user_id}")
async def list_pcs(user_id: int):
    pcs = database.get_user_pcs(user_id)
    return [{"id": p["id"], "name": p["name"], "online": p["online"]} for p in pcs]


@router.post("/command")
async def send_command(req: CommandRequest):
    token = manager.get_agent_token_for_user_pc(req.user_id, req.pc_id)
    if not token:
        raise HTTPException(400, "agent offline")
    result = await manager.send_command(token, {"cmd": req.cmd, "params": req.params})
    if result.get("error"):
        raise HTTPException(400, result["error"])
    return result

@router.get("/info/{pc_id}")
async def pc_info(pc_id: int):
    with database.get_conn() as conn:
        row = conn.execute("SELECT * FROM pcs WHERE id = ?", (pc_id,)).fetchone()
    return dict(row) if row else None
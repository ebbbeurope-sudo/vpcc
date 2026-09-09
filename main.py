from fastapi import FastAPI

from app.core.database import init_db
from app.routers import api, ws

app = FastAPI(title="VPCC Server")

init_db()

app.include_router(api.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"ok": True, "name": "VPCC Server"}
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
DB_PATH = os.getenv("DB_PATH", "app.db")
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8000"))
WS_PROXY = os.getenv("WS_PROXY", "").strip()
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
MAX_PCS_PER_USER = int(os.getenv("MAX_PCS_PER_USER", "3"))
CODE_TTL_SECONDS = int(os.getenv("CODE_TTL_SECONDS", "300"))
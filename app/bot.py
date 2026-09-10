import os
import random
import string
import time
import traceback

import pydantic
import aiogram
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

print(f"[VERSIONS] aiogram={aiogram.__version__} pydantic={pydantic.VERSION}", flush=True)

from app.core import database
from app.core.config import SERVER_URL

router = Router()
bot_ref: Bot | None = None


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Добавить ПК", callback_data="add_pc")],
        [InlineKeyboardButton(text="🖥 Мои ПК", callback_data="my_pcs")],
    ])


def gen_code() -> str:
    return "".join(random.choices(string.digits, k=6))


@router.message(CommandStart())
async def cmd_start(m: Message):
    print(f"[START] got /start from user={m.from_user.id}", flush=True)
    try:
        await m.answer(
            "🤖 VPCC — управляй своими ПК из Telegram.\n\n"
            "1. Нажми «Добавить ПК» — получишь код.\n"
            "2. Введи код в приложении на ПК.\n"
            "3. Управляй ПК отсюда.",
            reply_markup=main_menu(),
        )
        print("[START] answered ok", flush=True)
    except Exception as e:
        print(f"[START] error: {e}\n{traceback.format_exc()}", flush=True)


@router.callback_query(lambda c: c.data == "add_pc")
async def cb_add_pc(c: CallbackQuery):
    user_id = c.from_user.id
    if database.user_pc_count(user_id) >= 3:
        await c.answer("Лимит 3 ПК", show_alert=True)
        return
    code = gen_code()
    database.save_code(code, user_id, int(time.time()))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Новый код", callback_data="add_pc")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
    ])
    await c.message.edit_text(
        f"🔑 Твой код привязки:\n\n<code>{code}</code>\n\n"
        f"Введи его в приложении на ПК. Действует 5 минут.",
        reply_markup=kb,
    )
    await c.answer()


@router.callback_query(lambda c: c.data == "my_pcs")
async def cb_my_pcs(c: CallbackQuery):
    pcs = database.get_user_pcs(c.from_user.id)
    if not pcs:
        await c.message.edit_text("🖥 У тебя пока нет ПК.", reply_markup=main_menu())
        await c.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'🟢' if p['online'] else '⚫'} {p['name']}",
            callback_data=f"pc_{p['id']}",
        )] for p in pcs
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="main")]])
    await c.message.edit_text("🖥 Твои ПК:", reply_markup=kb)
    await c.answer()


@router.callback_query(lambda c: c.data == "main")
async def cb_main(c: CallbackQuery):
    await c.message.edit_text(
        "🤖 VPCC — управляй своими ПК из Telegram.", reply_markup=main_menu()
    )
    await c.answer()


@router.callback_query(lambda c: c.data.startswith("pc_"))
async def cb_pc(c: CallbackQuery):
    pc_id = int(c.data.split("_")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Инфо", callback_data=f"cmd_{pc_id}_sysinfo")],
        [InlineKeyboardButton(text="📸 Скриншот", callback_data=f"cmd_{pc_id}_screenshot")],
        [InlineKeyboardButton(text="🔊 +10", callback_data=f"cmd_{pc_id}_volup")],
        [InlineKeyboardButton(text="🔇 Mute", callback_data=f"cmd_{pc_id}_mute")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_pcs")],
    ])
    await c.message.edit_text(f"🖥 Управление ПК «{pcs_name(pc_id)}»:", reply_markup=kb)
    await c.answer()


def pcs_name(pc_id: int) -> str:
    with database.get_conn() as conn:
        row = conn.execute("SELECT name FROM pcs WHERE id = ?", (pc_id,)).fetchone()
    return row["name"] if row else f"#{pc_id}"


@router.callback_query(lambda c: c.data.startswith("cmd_"))
async def cb_cmd(c: CallbackQuery):
    _, pc_id_s, cmd = c.data.split("_", 2)
    pc_id = int(pc_id_s)
    url = f"{SERVER_URL}/api/command"
    print(f"[CMD] user={c.from_user.id} pc={pc_id} cmd={cmd} url={url}", flush=True)
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(
                url,
                json={"user_id": c.from_user.id, "pc_id": pc_id, "cmd": cmd, "params": {}},
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[CMD] error: {e}", flush=True)
            await c.answer("Агент не ответил", show_alert=True)
            return
    print(f"[CMD] resp ok={data.get('ok')}", flush=True)
    if cmd == "sysinfo":
        await c.message.answer(f"ℹ️ Инфо:\n{data.get('text', '')}")
    elif cmd == "screenshot":
        import base64
        img = data.get("image")
        if img:
            await c.message.answer_photo(
                BufferedInputFile(base64.b64decode(img), filename="shot.png"),
                caption="📸",
            )
        else:
            await c.answer("Нет изображения")
    else:
        await c.message.answer("✅ Выполнено")
    await c.answer()


def setup(bot: Bot):
    global bot_ref
    bot_ref = bot
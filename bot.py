import asyncio
import json
import os
import sqlite3
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "one_price_coffee.db"
SEED_PATH = BASE_DIR / "seed.json"

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}


def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        sizes TEXT DEFAULT '',
        ingredients TEXT DEFAULT '',
        technology TEXT DEFAULT '',
        description TEXT DEFAULT '',
        serve_time TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        UNIQUE(user_id, item_id)
    )
    """)

    # ÐÐ°Ð¶Ð´ÑÐ¹ Ð·Ð°Ð¿ÑÑÐº Ð¿ÐµÑÐµÑÐ¸ÑÑÐ²Ð°ÐµÐ¼ seed.json, ÑÑÐ¾Ð±Ñ Ð½Ð¾Ð²ÑÐµ Ð½Ð°Ð¿Ð¸ÑÐºÐ¸ Ð¸ ÑÑÐ¾ÐºÐ¸ ÑÐ¾ÑÐ½Ð¾ Ð¿Ð¾Ð¿Ð°Ð´Ð°Ð»Ð¸ Ð² Ð±Ð¾ÑÐ°.
    if SEED_PATH.exists():
        cur.execute("DELETE FROM items")
        cur.execute("DELETE FROM favorites")

        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        for item in data.get("items", []):
            cur.execute(
                """
                INSERT INTO items(category, name, sizes, ingredients, technology, description, serve_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("category", ""),
                    item.get("name", ""),
                    item.get("sizes", ""),
                    item.get("ingredients", ""),
                    item.get("technology", ""),
                    item.get("description", ""),
                    item.get("serve_time", ""),
                ),
            )

    conn.commit()
    conn.close()


def categories():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM items WHERE category != 'ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ' ORDER BY category")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def items_by_category(category):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM items WHERE category=? ORDER BY name", (category,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_item(item_id):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, category, name, sizes, ingredients, technology, description, serve_time FROM items WHERE id=?",
        (item_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def search_items(text):
    conn = db()
    cur = conn.cursor()
    q = f"%{text.lower()}%"
    cur.execute(
        """
        SELECT id, name, category FROM items
        WHERE category != 'ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ'
          AND (
              lower(name) LIKE ?
              OR lower(category) LIKE ?
              OR lower(description) LIKE ?
              OR lower(ingredients) LIKE ?
              OR lower(technology) LIKE ?
          )
        ORDER BY name
        LIMIT 20
        """,
        (q, q, q, q, q),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="â ÐÐµÐ½Ñ Ð½Ð°Ð¿Ð¸ÑÐºÐ¾Ð²", callback_data="categories")
    kb.button(text="ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ", callback_data="storage")
    kb.button(text="ð ÐÐ¾Ð¸ÑÐº", callback_data="search_help")
    kb.button(text="â­ ÐÐ·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ", callback_data="favorites")
    kb.adjust(1)
    return kb.as_markup()


def categories_kb():
    kb = InlineKeyboardBuilder()for cat in categories():
        kb.button(text=cat, callback_data=f"cat:{cat}")
    kb.button(text="â¬ï¸ ÐÐ°Ð·Ð°Ð´", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def item_list_kb(category):
    kb = InlineKeyboardBuilder()
    for item_id, name in items_by_category(category):
        kb.button(text=name, callback_data=f"item:{item_id}")

    if category == "ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ":
        kb.button(text="ð  Ð¡ÑÐ°ÑÑ", callback_data="home")
    else:
        kb.button(text="â¬ï¸ ÐÐ°ÑÐµÐ³Ð¾ÑÐ¸Ð¸", callback_data="categories")

    kb.adjust(1)
    return kb.as_markup()


def item_kb(item_id):
    row = get_item(item_id)
    category = row[1] if row else ""

    kb = InlineKeyboardBuilder()
    if category != "ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ":
        kb.button(text="â­ Ð Ð¸Ð·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ", callback_data=f"fav:{item_id}")
        kb.button(text="â¬ï¸ ÐÐ°ÑÐµÐ³Ð¾ÑÐ¸Ð¸", callback_data="categories")
    else:
        kb.button(text="â¬ï¸ Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ", callback_data="storage")

    kb.button(text="ð  Ð¡ÑÐ°ÑÑ", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def format_item(row):
    _, category, name, sizes, ingredients, technology, description, serve_time = row

    if category == "ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ":
        return (
            f"<b>{name}</b>\n"
            f"<i>{category}</i>\n\n"
            f"<b>Ð£ÑÐ»Ð¾Ð²Ð¸Ñ/ÑÐµÐ¼Ð¿ÐµÑÐ°ÑÑÑÐ°:</b>\n{sizes}\n\n"
            f"<b>Ð¢Ð°ÑÐ°/Ð¼Ð°ÑÐºÐ¸ÑÐ¾Ð²ÐºÐ°:</b>\n{ingredients}\n\n"
            f"<b>ÐÐ¾Ð¼Ð¼ÐµÐ½ÑÐ°ÑÐ¸Ð¹:</b>\n{technology}\n\n"
            f"<b>ÐÐ¾ÑÐ¼Ð°:</b>\n{description}\n\n"
            f"<b>Ð¡ÑÐ¾Ðº:</b> {serve_time}"
        )

    return (
        f"<b>{name}</b>\n"
        f"<i>{category}</i>\n\n"
        f"<b>ÐÐ±ÑÑÐ¼/ÑÑÐ»Ð¾Ð²Ð¸Ñ:</b>\n{sizes}\n\n"
        f"<b>Ð¡Ð¾ÑÑÐ°Ð²:</b>\n{ingredients}\n\n"
        f"<b>Ð¢ÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ñ:</b>\n{technology}\n\n"
        f"<b>ÐÐ¿Ð¸ÑÐ°Ð½Ð¸Ðµ:</b>\n{description}\n\n"
        f"<b>ÐÑÐµÐ¼Ñ/ÑÑÐ¾Ðº:</b> {serve_time}"
    )


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("ÐÐµÑ BOT_TOKEN. Ð¡Ð¾Ð·Ð´Ð°Ð¹ÑÐµ .env Ð¿Ð¾ Ð¿ÑÐ¸Ð¼ÐµÑÑ .env.example")

    init_db()

    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start(message: Message):
        await message.answer(
            "â One Price Coffee\n\nÐÐ°Ñ Ð³Ð¸Ð´ Ð¿Ð¾Ð´ ÑÑÐºÐ¾Ð¹.\n\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ°Ð·Ð´ÐµÐ» Ð¸Ð»Ð¸ Ð½Ð°Ð¿Ð¸ÑÐ¸ÑÐµ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð½Ð°Ð¿Ð¸ÑÐºÐ°.",
            reply_markup=main_menu_kb(),
        )

    @dp.message(Command("menu"))
    async def menu(message: Message):
        await message.answer("ÐÑÐ±ÐµÑÐ¸ÑÐµ ÐºÐ°ÑÐµÐ³Ð¾ÑÐ¸Ñ:", reply_markup=categories_kb())

    @dp.message(Command("search"))
    async def search_cmd(message: Message):
        await message.answer("ÐÐ°Ð¿Ð¸ÑÐ¸ÑÐµ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð½Ð°Ð¿Ð¸ÑÐºÐ° Ð¸Ð»Ð¸ Ð¸Ð½Ð³ÑÐµÐ´Ð¸ÐµÐ½ÑÐ°. ÐÐ°Ð¿ÑÐ¸Ð¼ÐµÑ: ÑÑÑÐ½ÑÐ¹ Ð»Ð°ÑÑÐµ")

    @dp.message(Command("admin"))
    async def admin(message: Message):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("ÐÐ´Ð¼Ð¸Ð½-Ð¿Ð°Ð½ÐµÐ»Ñ Ð´Ð¾ÑÑÑÐ¿Ð½Ð° ÑÐ¾Ð»ÑÐºÐ¾ Ð°Ð´Ð¼Ð¸Ð½Ð¸ÑÑÑÐ°ÑÐ¾ÑÐ°Ð¼.")
            return
        await message.answer(
            "âï¸ ÐÐ´Ð¼Ð¸Ð½-Ð¿Ð°Ð½ÐµÐ»Ñ\n\nÐÐ¾ÐºÐ° Ð´Ð¾ÑÑÑÐ¿Ð½Ð¾ Ð½Ð°Ð¿Ð¾Ð»Ð½ÐµÐ½Ð¸Ðµ ÑÐµÑÐµÐ· SQLite. "
            "ÐÐ¾Ð·Ð¶Ðµ Ð´Ð¾Ð±Ð°Ð²Ð¸Ð¼ ÐºÐ½Ð¾Ð¿ÐºÐ¸ Ð´Ð¾Ð±Ð°Ð²Ð»ÐµÐ½Ð¸Ñ/ÑÐµÐ´Ð°ÐºÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð¸Ñ Ð¿ÑÑÐ¼Ð¾ Ð² Telegram."
        )

    @dp.callback_query(F.data == "home")
    async def cb_home(call: CallbackQuery):
        await call.message.edit_text(
            "â One Price Coffee\n\nÐÐ°Ñ Ð³Ð¸Ð´ Ð¿Ð¾Ð´ ÑÑÐºÐ¾Ð¹.\n\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ°Ð·Ð´ÐµÐ» Ð¸Ð»Ð¸ Ð½Ð°Ð¿Ð¸ÑÐ¸ÑÐµ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð½Ð°Ð¿Ð¸ÑÐºÐ°.",
            reply_markup=main_menu_kb(),
        )
        await call.answer()

    @dp.callback_query(F.data == "categories")async def cb_categories(call: CallbackQuery):
        await call.message.edit_text("ÐÑÐ±ÐµÑÐ¸ÑÐµ ÐºÐ°ÑÐµÐ³Ð¾ÑÐ¸Ñ:", reply_markup=categories_kb())
        await call.answer()

    @dp.callback_query(F.data == "storage")
    async def cb_storage(call: CallbackQuery):
        await call.message.edit_text("ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ:", reply_markup=item_list_kb("ð Ð¡ÑÐ¾ÐºÐ¸ ÑÑÐ°Ð½ÐµÐ½Ð¸Ñ"))
        await call.answer()

    @dp.callback_query(F.data.startswith("cat:"))
    async def cb_cat(call: CallbackQuery):
        cat = call.data.split(":", 1)[1]
        await call.message.edit_text(f"<b>{cat}</b>\nÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¿Ð¾Ð·Ð¸ÑÐ¸Ñ:", reply_markup=item_list_kb(cat))
        await call.answer()

    @dp.callback_query(F.data.startswith("item:"))
    async def cb_item(call: CallbackQuery):
        item_id = int(call.data.split(":", 1)[1])
        row = get_item(item_id)
        if not row:
            await call.answer("ÐÐµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾", show_alert=True)
            return
        await call.message.edit_text(format_item(row), reply_markup=item_kb(item_id))
        await call.answer()

    @dp.callback_query(F.data.startswith("fav:"))
    async def cb_fav(call: CallbackQuery):
        item_id = int(call.data.split(":", 1)[1])
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO favorites(user_id,item_id) VALUES(?,?)",
            (call.from_user.id, item_id),
        )
        conn.commit()
        conn.close()
        await call.answer("ÐÐ¾Ð±Ð°Ð²Ð»ÐµÐ½Ð¾ Ð² Ð¸Ð·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ â­")

    @dp.callback_query(F.data == "favorites")
    async def cb_favorites(call: CallbackQuery):
        conn = db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT i.id, i.name
            FROM items i
            JOIN favorites f ON i.id=f.item_id
            WHERE f.user_id=?
            ORDER BY i.name
            """,
            (call.from_user.id,),
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            await call.message.edit_text("ÐÐ·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ Ð¿Ð¾ÐºÐ° Ð¿ÑÑÑÐ¾Ðµ.", reply_markup=main_menu_kb())
        else:
            kb = InlineKeyboardBuilder()
            for item_id, name in rows:
                kb.button(text=name, callback_data=f"item:{item_id}")
            kb.button(text="ð  Ð¡ÑÐ°ÑÑ", callback_data="home")
            kb.adjust(1)
            await call.message.edit_text("â­ ÐÐ·Ð±ÑÐ°Ð½Ð½Ð¾Ðµ:", reply_markup=kb.as_markup())

        await call.answer()

    @dp.callback_query(F.data == "search_help")
    async def cb_search_help(call: CallbackQuery):
        await call.message.edit_text(
            "ð ÐÐ°Ð¿Ð¸ÑÐ¸ÑÐµ Ð² ÑÐ°Ñ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð½Ð°Ð¿Ð¸ÑÐºÐ° Ð¸Ð»Ð¸ ÑÐ°ÑÑÑ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ñ.\n"
            "ÐÐ°Ð¿ÑÐ¸Ð¼ÐµÑ: <b>Ð¼Ð°ÑÑÐ°</b>, <b>ÑÑÑÐ½ÑÐ¹</b>, <b>Ð»Ð¸Ð¼Ð¾Ð½Ð°Ð´</b>.",
            reply_markup=main_menu_kb(),
        )
        await call.answer()

    @dp.message(F.text)
    async def text_search(message: Message):
        rows = search_items(message.text.strip())

        if not rows:
            await message.answer(
                "ÐÐ¸ÑÐµÐ³Ð¾ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾. ÐÐ¾Ð¿ÑÐ¾Ð±ÑÐ¹ÑÐµ Ð´ÑÑÐ³Ð¾Ðµ Ð½Ð°Ð·Ð²Ð°Ð½Ð¸Ðµ Ð¸Ð»Ð¸ Ð¾ÑÐºÑÐ¾Ð¹ÑÐµ Ð¼ÐµÐ½Ñ.",
                reply_markup=main_menu_kb(),
            )
            return

        kb = InlineKeyboardBuilder()
        for item_id, name, category in rows:
            kb.button(text=f"{name} â {category}", callback_data=f"item:{item_id}")
        kb.adjust(1)

        await message.answer("ÐÐ°ÑÐ»Ð° Ð²Ð°ÑÐ¸Ð°Ð½ÑÑ:", reply_markup=kb.as_markup())

    await dp.start_polling(bot)


if name == "__main__":
    asyncio.run(main())

import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ========= CONFIG =========
API_TOKEN = "8546774487:AAElNq0ld2Tji_eDHxRLDaPsWmctP5CX2DI"
ADMINS = [7750527012]
DB = "movies.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ========= DATABASE =========
def db(): return sqlite3.connect(DB)

def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                banned INTEGER DEFAULT 0
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS channels(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS movies(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                title TEXT,
                year TEXT,
                language TEXT,
                country TEXT,
                file_id TEXT
            )
        """)

# ========= HELPERS =========
def is_admin(uid): return uid in ADMINS

def add_user(m):
    with db() as con:
        con.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,0)",
                    (m.from_user.id, m.from_user.username, m.from_user.first_name))

def get_users():
    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users")
        return cur.fetchall()

def ban_user(uid):
    with db() as con:
        con.execute("UPDATE users SET banned=1 WHERE id=?", (uid,))

def add_movie(d):
    with db() as con:
        con.execute("INSERT INTO movies(code,title,year,language,country,file_id) VALUES(?,?,?,?,?,?)",
                    (d["code"], d["title"], d["year"], d["lang"], d["country"], d["file_id"]))

def get_movie(code):
    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM movies WHERE code=?", (code,))
        return cur.fetchone()

def del_movie(code):
    with db() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM movies WHERE code=?", (code,))
        return cur.rowcount

def add_channel(ch):
    with db() as con:
        con.execute("INSERT OR IGNORE INTO channels(username) VALUES(?)", (ch,))

def del_channel(ch):
    with db() as con:
        con.execute("DELETE FROM channels WHERE username=?", (ch,))

def get_channels():
    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT username FROM channels")
        return [i[0] for i in cur.fetchall()]

# ========= FSM =========
class AddMovie(StatesGroup):
    code = State()
    title = State()
    year = State()
    lang = State()
    country = State()
    file = State()

class AddChannel(StatesGroup):
    ch = State()

class DeleteMovie(StatesGroup):
    code = State()

class BanUser(StatesGroup):
    uid = State()

# ========= SUB CHECK =========
async def check_sub(uid):
    not_sub = []
    for ch in get_channels():
        try:
            member = await bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                not_sub.append(ch)
        except:
            not_sub.append(ch)
    return not_sub

# ========= START =========
@router.message(Command("start"))
async def start(m: types.Message):
    add_user(m)
    ns = await check_sub(m.from_user.id)
    if ns:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➕ Obuna: {ch}", url=f"https://t.me/{ch.replace('@','')}")]
            for ch in ns
        ] + [[InlineKeyboardButton(text="✅ Tekshirish", callback_data="check")]])
        await m.answer("Oldin kanallarga obuna bo‘ling:", reply_markup=kb)
    else:
        await m.answer("🎬 Kino kodini yuboring")

# ========= CHECK SUB =========
@router.callback_query(F.data == "check")
async def recheck(c: types.CallbackQuery):
    ns = await check_sub(c.from_user.id)
    if not ns:
        await c.message.edit_text("✅ Obuna tasdiqlandi! Endi kino kodini yuboring:")
    else:
        txt = "❌ Hali obuna emas:\n" + "\n".join(ns)
        await c.message.answer(txt)
    await c.answer()

# ========= ADMIN PANEL =========
@router.message(Command("admin"))
async def admin_panel(m: types.Message):
    if not is_admin(m.from_user.id):
        await m.answer("⛔ Siz admin emassiz")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton(text="❌ Kino o‘chirish", callback_data="del_movie")],
        [InlineKeyboardButton(text="📋 Kinolar", callback_data="list_movies")],
        [InlineKeyboardButton(text="👥 Userlar", callback_data="list_users")],
        [InlineKeyboardButton(text="🚫 Userni ban", callback_data="ban_user")],
        [
            InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="add_channel"),
            InlineKeyboardButton(text="➖ Kanal o‘chirish", callback_data="del_channel")
        ]
    ])
    await m.answer("✅ Admin panel:", reply_markup=kb)

# ========= ADMIN CALLBACKS =========
@router.callback_query(F.data == "list_users")
async def cb_list_users(c: types.CallbackQuery):
    us = get_users()
    txt = "\n".join([f"{u[0]} | @{u[1]}" for u in us]) or "Bo‘sh"
    await c.message.answer(txt)
    await c.answer()

@router.callback_query(F.data == "ban_user")
async def cb_ban_user(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(BanUser.uid)
    await c.message.answer("Ban qilinadigan user ID:")

@router.callback_query(F.data == "add_movie")
async def cb_add_movie(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddMovie.code)
    await c.message.answer("🎬 Kino kodi:")
    await c.answer()

@router.callback_query(F.data == "del_movie")
async def cb_del_movie(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(DeleteMovie.code)
    await c.message.answer("O‘chirish uchun kino kodi:")
    await c.answer()

@router.callback_query(F.data == "list_movies")
async def cb_list_movies(c: types.CallbackQuery):
    ms = get_movies()
    txt = "\n".join([f"{i[1]} | {i[2]} ({i[3]})" for i in ms]) or "Bo‘sh"
    await c.message.answer(txt)
    await c.answer()

@router.callback_query(F.data == "add_channel")
async def cb_add_channel(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddChannel.ch)
    await state.update_data(mode="add")
    await c.message.answer("➕ Kanal username (@kanal):")
    await c.answer()

@router.callback_query(F.data == "del_channel")
async def cb_del_channel(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddChannel.ch)
    await state.update_data(mode="del")
    await c.message.answer("➖ O‘chirish kanal username (@kanal):")
    await c.answer()

# ========= FSM HANDLERS =========
@router.message(AddMovie.code)
async def movie_code(m: types.Message, state: FSMContext):
    await state.update_data(code=m.text)
    await state.set_state(AddMovie.title)
    await m.answer("Nomi:")

@router.message(AddMovie.title)
async def movie_title(m: types.Message, state: FSMContext):
    await state.update_data(title=m.text)
    await state.set_state(AddMovie.year)
    await m.answer("Yili:")

@router.message(AddMovie.year)
async def movie_year(m: types.Message, state: FSMContext):
    await state.update_data(year=m.text)
    await state.set_state(AddMovie.lang)
    await m.answer("Tili:")

@router.message(AddMovie.lang)
async def movie_lang(m: types.Message, state: FSMContext):
    await state.update_data(lang=m.text)
    await state.set_state(AddMovie.country)
    await m.answer("Davlati:")

@router.message(AddMovie.country)
async def movie_country(m: types.Message, state: FSMContext):
    await state.update_data(country=m.text)
    await state.set_state(AddMovie.file)
    await m.answer("🎥 Video yuboring:")

@router.message(AddMovie.file, F.video)
async def movie_file(m: types.Message, state: FSMContext):
    data = await state.get_data()
    data["file_id"] = m.video.file_id
    add_movie(data)
    await m.answer("✅ Kino muvaffaqiyatli qo‘shildi")
    await state.clear()

@router.message(DeleteMovie.code)
async def movie_delete(m: types.Message, state: FSMContext):
    if del_movie(m.text):
        await m.answer("✅ O‘chirildi")
    else:
        await m.answer("❌ Topilmadi")
    await state.clear()

@router.message(AddChannel.ch)
async def channel_handler(m: types.Message, state: FSMContext):
    data = await state.get_data()
    mode = data.get("mode")
    ch = m.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    if mode == "del":
        del_channel(ch)
        await m.answer(f"✅ O‘chirildi: {ch}")
    else:
        add_channel(ch)
        await m.answer(f"✅ Qo‘shildi: {ch}")
    await state.clear()

@router.message(BanUser.uid)
async def ban_user_handler(m: types.Message, state: FSMContext):
    ban_user(int(m.text))
    await m.answer("✅ User ban qilindi")
    await state.clear()

# ========= USER MOVIE REQUEST =========
@router.message(F.text)
async def movie_request(m: types.Message):
    mv = get_movie(m.text)
    if not mv:
        await m.answer("❌ Kino topilmadi")
    else:
        await m.answer_video(mv[-1], caption=f"{mv[2]} ({mv[3]})")

# ========= BOT START =========
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

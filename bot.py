import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "7206068339:AAFQwp7LkYZVMHx1Pq_copkqHugGjmUnFOI"  # Bu yerga tokenni qo'y
ADMIN_ID = 8191601715

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DB INIT ---
def init_db():
    conn = sqlite3.connect("ttj_pro.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            room TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            status TEXT DEFAULT 'Kutilmoqda',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- STATE ---
class RegState(StatesGroup):
    name = State()
    room = State()

class ReportState(StatesGroup):
    text = State()

# --- BUTTONS ---
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛠 Ariza yuborish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👤 Profil")]
        ],
        resize_keyboard=True
    )

def admin_inline_kb(report_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"done_{report_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{report_id}")
        ]
    ])

# --- START / REGISTRATION ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    print(f"[DEBUG] /start keldi: {message.from_user.id}")
    conn = sqlite3.connect("ttj_pro.db")
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
    conn.close()

    if user:
        await message.answer(f"Xush kelibsiz, {user[1]}!", reply_markup=main_menu())
    else:
        await message.answer("Ro'yxatdan o'tish: Ism-familiyangizni yozing:")
        await state.set_state(RegState.name)

@dp.message(RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Xona raqamingizni kiriting:")
    await state.set_state(RegState.room)

@dp.message(RegState.room)
async def reg_room(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("ttj_pro.db")
    conn.execute(
        "INSERT INTO users VALUES (?, ?, ?)",
        (message.from_user.id, data['name'], message.text)
    )
    conn.commit()
    conn.close()
    await message.answer("Ro'yxatdan o'tdingiz!", reply_markup=main_menu())
    await state.clear()

# --- REPORT ---
@dp.message(F.text == "🛠 Ariza yuborish")
async def start_report(message: types.Message, state: FSMContext):
    await message.answer("Muammoni yozing:")
    await state.set_state(ReportState.text)

@dp.message(ReportState.text)
async def save_report(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("ttj_pro.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reports (user_id, text, created_at) VALUES (?, ?, ?)",
        (message.from_user.id, message.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    report_id = cursor.lastrowid
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
    conn.commit()
    conn.close()

    admin_text = f"🆕 ID: #{report_id}\n👤 {user[1]} (Xona: {user[2]})\n📝 {message.text}"
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_inline_kb(report_id))
    except Exception as e:
        print("Adminga xabar yuborishda xato:", e)

    await message.answer(f"✅ Ariza qabul qilindi! ID: #{report_id}", reply_markup=main_menu())
    await state.clear()

# --- ADMIN CALLBACKS ---
@dp.callback_query(F.data.startswith("done_"))
async def process_done(callback: CallbackQuery):
    report_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("ttj_pro.db")
    cursor = conn.cursor()
    res = cursor.execute("SELECT user_id FROM reports WHERE id=?", (report_id,)).fetchone()
    if not res:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return
    user_id = res[0]
    cursor.execute("UPDATE reports SET status='Bajarildi' WHERE id=?", (report_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(callback.message.text + "\n\n✅ HOLAT: BAJARILDI")
    await bot.send_message(user_id, f"🎉 Sizning #{report_id}-sonli arizangiz bajarildi!")

@dp.callback_query(F.data.startswith("reject_"))
async def process_reject(callback: CallbackQuery):
    report_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("ttj_pro.db")
    cursor = conn.cursor()
    res = cursor.execute("SELECT user_id FROM reports WHERE id=?", (report_id,)).fetchone()
    if not res:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return
    user_id = res[0]
    cursor.execute("UPDATE reports SET status='Rad etildi' WHERE id=?", (report_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text(callback.message.text + "\n\n❌ HOLAT: RAD ETILDI")
    await bot.send_message(user_id, f"⚠️ Sizning #{report_id}-sonli arizangiz rad etildi!")

# --- STATISTIKA / PROFIL ---
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    conn = sqlite3.connect("ttj_pro.db")
    total = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM reports WHERE status='Bajarildi'").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    text = f"📊 TTJ Statistikasi:\n\n👤 Talabalar: {users}\n📝 Jami arizalar: {total}\n✅ Bajarilgan: {done}"
    await message.answer(text)

@dp.message(F.text == "👤 Profil")
async def show_profile(message: types.Message):
    conn = sqlite3.connect("ttj_pro.db")
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
    conn.close()

    if user:
        await message.answer(f"👤 Ismingiz: {user[1]}\n🏠 Xona: {user[2]}")
    else:
        await message.answer("Profil topilmadi. Iltimos /start orqali ro'yxatdan o'ting.")

# --- RUN ---
async def main():
    print("[DEBUG] Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

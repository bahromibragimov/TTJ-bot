import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)


TOKEN = "7206068339:AAFQwp7LkYZVMHx1Pq_copkqHugGjmUnFOI"
ADMIN_ID = 8191601715

bot = Bot(token=TOKEN)
dp = Dispatcher()



class RegState(StatesGroup):
    name = State()
    kurs = State()
    room = State()


class ReportState(StatesGroup):
    text = State()



def db_query(sql, params=(), fetch=False):
    with sqlite3.connect("ttj_main.db") as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if fetch: return cursor.fetchall()
        conn.commit()



def main_menu():
    kb = [
        [KeyboardButton(text="🛠 Muammo yuborish"), KeyboardButton(text="📋 Arizalarim")],
        [KeyboardButton(text="👤 Profil"), KeyboardButton(text="💳 To'lov")],
        [KeyboardButton(text="📜 Shartnoma"), KeyboardButton(text="ℹ️ Qo'llanma")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)



@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = db_query("SELECT * FROM users WHERE user_id=?", (message.from_user.id,), fetch=True)
    if user:
        await message.answer(f"Xush kelibsiz, {user[0][1]}!", reply_markup=main_menu())
    else:
        await message.answer("Assalomu alaykum! TTJ tizimiga xush kelibsiz.\nIsm-familiyangizni kiriting:")
        await state.set_state(RegState.name)


@dp.message(RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    if len(message.text.split()) >= 2:
        await state.update_data(name=message.text)
        await message.answer("Kursigizni kiriting (1-4):")
        await state.set_state(RegState.kurs)
    else:
        await message.answer("⚠️ Iltimos, ism va familiyangizni to'liq yozing.")


@dp.message(RegState.kurs)
async def reg_kurs(message: types.Message, state: FSMContext):
    if message.text in ["1", "2", "3", "4"]:
        await state.update_data(kurs=message.text)
        await message.answer("Xona raqamingizni kiriting:")
        await state.set_state(RegState.room)
    else:
        await message.answer("⚠️ Faqat 1 dan 4 gacha raqam kiriting.")


@dp.message(RegState.room)
async def reg_room(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        data = await state.get_data()
        now = datetime.now().strftime("%d.%m.%Y")
        db_query("INSERT INTO users (user_id, full_name, kurs, room, reg_date) VALUES (?, ?, ?, ?, ?)",
                 (message.from_user.id, data['name'], data['kurs'], message.text, now))
        await message.answer("✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("⚠️ Xona raqami faqat raqamlardan iborat bo'lishi kerak.")


@dp.message(F.text == "👤 Profil")
async def show_profile(message: types.Message):

    user = db_query("SELECT full_name, kurs, room, reg_date FROM users WHERE user_id=?", (message.from_user.id,),
                    fetch=True)

    if user:
        u = user[0]
        text = (
            f"👤 **Foydalanuvchi profili:**\n\n"
            f"👤 **Ism:** {u[0]}\n"
            f"🎓 **Kurs:** {u[1]}-kurs\n"
            f"🚪 **Xona:** {u[2]}\n"
            f"📅 **Ro'yxatdan o'tgan sana:** {u[3]}"
        )
        await message.answer(text, parse_mode="Markdown")
    else:

        await message.answer("⚠️ Profilingiz topilmadi. Iltimos, /start buyrug'ini bosing va qayta ro'yxatdan o'ting.")

@dp.message(F.text == "📋 Arizalarim")
async def my_reports(message: types.Message):
    reports = db_query("SELECT id, text, status FROM reports WHERE user_id=? ORDER BY id DESC", (message.from_user.id,),
                       fetch=True)
    if not reports:
        return await message.answer("📭 Sizda hali arizalar yo'q.")

    res_text = "📋 **Sizning arizalaringiz:**\n\n"
    for r in reports:
        res_text += f"🆔 #{r[0]} | {r[2]}\n📝 {r[1][:30]}...\n\n"
    await message.answer(res_text, parse_mode="Markdown")


@dp.message(F.text == "💳 To'lov")
async def payment_info(message: types.Message):
    info = ("💳 **To'lov rekvizitlari:**\n\n🏦 Bank: Milliy Bank\n🔢 Karta: 8600 1234 5678 9012\n"
            "💰 Summa: 250,000 so'm\n\nTo'lovdan so'ng chekni adminga yuboring.")
    await message.answer(info, parse_mode="Markdown")


@dp.message(F.text == "ℹ️ Qo'llanma")
async def help_guide(message: types.Message):
    await message.answer(
        "📖 **Botdan foydalanish:**\n1. Muammo bo'lsa '🛠 Muammo yuborish'ni bosing.\n2. Profilingizni tekshirish uchun '👤 Profil'ni bosing.")


@dp.message(F.text == "📜 Shartnoma")
async def contract(message: types.Message):
    await message.answer("📜 **Yotoqxona tartib qoidalari:**\n\nTalaba intizomga rioya qilishi shart.")



@dp.message(F.text == "🛠 Muammo yuborish")
async def report_start(message: types.Message, state: FSMContext):
    await message.answer("🛠 Muammoingizni yozib yuboring:")
    await state.set_state(ReportState.text)


@dp.message(ReportState.text)
async def report_save(message: types.Message, state: FSMContext):
    now = datetime.now().strftime("%d.%m %H:%M")
    db_query("INSERT INTO reports (user_id, text, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
             (message.from_user.id, message.text, "⏳ Kutilmoqda", now, now))

    res = db_query("SELECT id FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1", (message.from_user.id,),
                   fetch=True)
    r_id = res[0][0]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Jarayonga olish", callback_query_data=f"proc_{r_id}")]
    ])

    try:
        await bot.send_message(ADMIN_ID,
                               f"🆕 Yangi ariza #{r_id}\n👤 Kimdan: {message.from_user.full_name}\n📝: {message.text}",
                               reply_markup=kb)
        await message.answer(f"✅ Arizangiz adminga yuborildi. ID: #{r_id}")
    except Exception as e:
        await message.answer("✅ Arizangiz saqlandi, lekin adminga yetkazilmadi.")

    await state.clear()


@dp.callback_query(F.data.startswith("proc_"))
async def to_process(call: CallbackQuery):
    r_id = call.data.split("_")[1]
    db_query("UPDATE reports SET status='🔧 Jarayonda' WHERE id=?", (r_id,))
    await call.message.edit_text(call.message.text + "\n\n✅ Holat: Jarayonga olindi")
    await call.answer("Status yangilandi")


async def main():

    await bot.delete_webhook(drop_pending_updates=True)


    await dp.start_polling(bot)
1

if __name__ == "__main__":
    asyncio.run(main())

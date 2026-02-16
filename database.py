import sqlite3
from datetime import datetime


def init_db():
    conn = sqlite3.connect("ttj_main.db")
    cursor = conn.cursor()


    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        kurs INTEGER,
        room TEXT,
        reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")


    cursor.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        status TEXT DEFAULT '⏳ Kutilmoqda',
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )""")


    cursor.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_id TEXT,
        status TEXT DEFAULT '⏳ Tekshirilyapti',
        amount REAL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )""")


    cursor.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    conn.commit()
    conn.close()

    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    def main_menu():
        kb = [
            [KeyboardButton(text="🛠 Muammo yuborish"), KeyboardButton(text="📋 Arizalarim")],
            [KeyboardButton(text="👤 Profil"), KeyboardButton(text="💳 To'lov")],
            [KeyboardButton(text="📜 Shartnoma"), KeyboardButton(text="ℹ️ Qo'llanma")]
        ]
        return ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True,
            input_field_placeholder="Kerakli bo'limni tanlang..."
        )

    @dp.message(RegState.room)
    async def validate_room(message: types.Message, state: FSMContext):
        if message.text.isdigit():
            data = await state.get_data()



            await message.answer(
                f"✅ Tabriklaymiz, {data['name']}! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.",
                reply_markup=main_menu()
            )
            await state.clear()
        else:
            await message.answer("⚠️ Xona raqami faqat raqamlardan iborat bo'lishi shart.")


            @dp.message(F.text == "👤 Profil")
            async def show_profile(message: types.Message):
                # Bu yerda bazadan ma'lumotlarni olish kerak, hozircha namunaviy:
                text = (
                    f"👤 **Foydalanuvchi profili:**\n\n"
                    f"🆔 ID: {message.from_user.id}\n"
                    f"📅 Ro'yxatdan o'tgan sana: 14.02.2026\n"
                    f"🏛 Kurs: 3-kurs\n"
                    f"🚪 Xona: 215"
                )
                await message.answer(text, parse_mode="Markdown")


            @dp.message(F.text == "💳 To'lov")
            async def payment_info(message: types.Message):
                info = (
                    "💳 **To'lov rekvizitlari:**\n\n"
                    "🏦 Bank: Milliy Bank\n"
                    "👤 Hisob egasi: TTJ Ma'muriyati\n"
                    "🔢 Hisob raqami: 8600 1234 5678 9012\n"
                    "💰 Oylik summa: 250,000 so'm\n\n"
                    "⚠️ To'lov qilgach, chekni rasm ko'rinishida yuboring."
                )
                await message.answer(info, parse_mode="Markdown")


            @dp.message(F.text == "ℹ️ Qo'llanma")
            async def help_guide(message: types.Message):
                await message.answer(
                    "Botdan foydalanish qoidalari:\n1. Arizani faqat o'z xonangiz uchun yuboring.\n2. To'lov chekini aniq rasmga oling.")

                import sqlite3
                from datetime import datetime
                from aiogram.fsm.state import State, StatesGroup


                def db_query(sql, params=(), fetch=False):
                    with sqlite3.connect("ttj_system.db") as conn:
                        cursor = conn.cursor()
                        cursor.execute(sql, params)
                        if fetch: return cursor.fetchall()
                        conn.commit()


                class ReportState(StatesGroup):
                    waiting_text = State()

                class PaymentState(StatesGroup):
                    waiting_file = State()

                class AdminState(StatesGroup):
                    broadcast = State()
                    personal_msg = State()


                    @dp.message(F.text == "🛠 Muammo yuborish")
                    async def report_start(message: types.Message, state: FSMContext):

                        last_report = db_query(
                            "SELECT created_at FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",
                            (message.from_user.id,), fetch=True)

                        await message.answer("Muammoni batafsil yozing (Bo'sh xabar yubormang):")
                        await state.set_state(ReportState.waiting_text)

                    @dp.message(ReportState.waiting_text)
                    async def report_save(message: types.Message, state: FSMContext):
                        if not message.text or len(message.text) < 5:
                            return await message.answer("⚠️ Muammo juda qisqa yoki bo'sh. Iltimos, aniqroq yozing.")

                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        db_query(
                            "INSERT INTO reports (user_id, text, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                            (message.from_user.id, message.text, "⏳ Kutilmoqda", now, now))

                        report_id = db_query("SELECT id FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",
                                             (message.from_user.id,), fetch=True)[0][0]

                        await message.answer(f"✅ Arizangiz qabul qilindi!\n🆔 ID: #{report_id}\n⏳ Holati: Kutilmoqda")


                        await bot.send_message(ADMIN_ID,
                                               f"🔔 Yangi ariza #{report_id}!\n👤 User: {message.from_user.full_name}\n📝: {message.text}")
                        await state.clear()


                    @dp.message(F.text == "📋 Arizalarim")
                    async def my_reports(message: types.Message):
                        reports = db_query(
                            "SELECT id, text, status, created_at FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 5",
                            (message.from_user.id,), fetch=True)

                        if not reports:
                            return await message.answer("Sizda hali arizalar yo'q.")

                        text = "📋 **Sizning oxirgi arizalaringiz:**\n\n"
                        for r in reports:
                            text += f"🆔 #{r[0]} | 📅 {r[3]}\n📝 {r[1][:30]}...\n🎭 Status: {r[2]}\n\n"
                        await message.answer(text, parse_mode="Markdown")

                        @dp.callback_query(F.data.startswith("st_"))
                        async def admin_status_change(call: types.CallbackQuery):

                            data = call.data.split("_")
                            action = data[1]
                            report_id = data[2]

                            status_map = {"process": "🔧 Jarayonda", "done": "✅ Bajarildi", "reject": "❌ Rad etildi"}
                            new_status = status_map[action]

                            db_query("UPDATE reports SET status=?, updated_at=? WHERE id=?",
                                     (new_status, datetime.now().strftime("%H:%M"), report_id))

                            user_id = db_query("SELECT user_id FROM reports WHERE id=?", (report_id,), fetch=True)[0][0]

                            await call.message.edit_text(f"Ariza #{report_id} statusi {new_status} ga o'zgartirildi.")
                            await bot.send_message(user_id,
                                                   f"🔔 Sizning #{report_id}-sonli arizangiz statusi o'zgardi: {new_status}")


                            @dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
                            async def admin_panel(message: types.Message):

                                users_count = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]


                                total_reports = db_query("SELECT COUNT(*) FROM reports", fetch=True)[0][0]
                                done_reports = \
                                db_query("SELECT COUNT(*) FROM reports WHERE status='✅ Bajarildi'", fetch=True)[0][0]


                                percent = (done_reports / total_reports * 100) if total_reports > 0 else 0


                                pending_payments = \
                                db_query("SELECT COUNT(*) FROM payments WHERE status='⏳ Tekshirilyapti'", fetch=True)[
                                    0][0]

                                stats_text = (
                                    "👮 **ADMIN PANEL - STATISTIKA**\n\n"
                                    f"👥 **Jami foydalanuvchilar:** {users_count} ta\n"
                                    f"📝 **Jami arizalar:** {total_reports} ta\n"
                                    f"✅ **Bajarilgan:** {done_reports} ta ({percent:.1f}%)\n"
                                    f"💰 **Kutilayotgan to'lovlar:** {pending_payments} ta\n\n"
                                    "Boshqarish uchun quyidagi buyruqlardan foydalaning:\n"
                                    "📢 /broadcast - Hammaga xabar yuborish\n"
                                    "📂 /all_reports - Barcha arizalarni ko'rish"
                                )

                                await message.answer(stats_text, parse_mode="Markdown")


                                @dp.message(ReportState.waiting_text)
                                async def report_save(message: types.Message,

                                    if not message.text or len(message.text.strip()) == 0:
                                        return await message.answer("⚠️ Bo'sh matn yuborish mumkin emas!")

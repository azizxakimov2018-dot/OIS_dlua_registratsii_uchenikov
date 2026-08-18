import asyncio
import sqlite3
import os
import pandas as pd
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

# --- НАСТРОЙКА БОТА И БАЗЫ ДАННЫХ ---
API_TOKEN = '5762798532:AAGxAutHouyZI6BDdlbDsf9HWyqFM6dQpVw'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Укажите ваш Telegram ID внутри скобок для доступа к команде /export (узнать в @userinfobot)
ADMIN_IDS = []  

# Относительный путь для сохранения документов (работает и на Windows, и на Render/Linux)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "school_documents")
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR, exist_ok=True)

# База данных (в папке с проектом)
db_path = os.path.join(BASE_DIR, "oxford_registration.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        fullname TEXT,
        language TEXT,
        grade INTEGER,
        phone TEXT,
        prev_school_type TEXT,
        abroad_details TEXT,
        docs_saved TEXT,
        reg_date TEXT
    )
''')
conn.commit()


# --- ТЕКСТЫ НА ДВУХ ЯЗЫКАХ ---
TEXTS = {
    "ru": {
        "ask_name": "Пожалуйста, введите **ФИО ученика** (полностью):",
        "ask_grade": "В какой **класс** поступает ученик? Напишите **только цифру** от 1 до 11:",
        "grade_error": "⚠️ Пожалуйста, введите только число от 1 до 11:",
        "ask_phone": "Поделитесь **номером телефона** родителя для связи:",
        "btn_phone": "📱 Отправить номер телефона",
        "ask_school_type": "Откуда переводится ученик?",
        "btn_local": "🏫 Из местной школы (Узбекистан)",
        "btn_abroad": "🌍 Учился за границей",
        "ask_abroad": "Укажите **страну и город**, где ребенок учился за границей:",
        "ask_local": "Укажите номер или название местной школы:",
        "btn_error": "⚠️ Выберите вариант кнопками.",
        "docs_head": "📋 **Требуемые документы для вашего класса:**\n\n",
        "doc_1": "• **Метрика (свидетельство о рождении) ребенка**",
        "doc_2_9_local": "• **Метрика ребенка**\n• **Табель оценок**",
        "doc_2_9_abroad": "• **Метрика ребенка**\n• **Оригинал табеля оценок**\n• **Официальный перевод табеля**",
        "doc_10_11_local": "• **Метрика ребенка**\n• **Аттестат за 9 класс / Табель**",
        "doc_10_11_abroad": (
            "• **Метрика или паспорт ученика**\n"
            "• **Оригиналы табелей за все классы (с 6 по 9-10 класс минимум)**\n"
            "• **Официальный перевод табелей от юридической фирмы / нотариуса**\n"
            "• **Нострификация аттестата из местного ГорОНО Узбекистана** (обязательно)"
        ),
        "docs_footer": "\n\nПожалуйста, **отправьте файлы или фотографии** этих документов одним или несколькими сообщениями. Как только закончите отправку, нажмите на кнопку **Готово**.",
        "doc_empty_error": "⚠️ Вы не отправили ни одного документа. Отправьте photo/файлы, а затем нажмите на кнопку 'Готово'.",
        "doc_accepted": "✅ Документ принят (загружено {}). Отправьте следующий или нажмите на кнопку **Готово**.",
        "success": "🎉 **Заявка в Oxford International School принята!**\n\n• **Ученик:** {}\n• **Класс обучения:** {}\n• **Загружено документов:** {} шт.\n\nПриемная комиссия проверит документы и свяжется с вами."
    },
    "uz": {
        "ask_name": "Iltimos, **o'quvchining F.I.Sh.** (to'liq) kiriting:",
        "ask_grade": "O'quvchi nechanchi **sinfga** kiradi? **Faqat raqamda** yozing (1 dan 11 gacha):",
        "grade_error": "⚠️ Iltimos, faqat 1 dan 11 gacha bo'lgan raqamni kiriting:",
        "ask_phone": "Bog'lanish uchun ota-onaning **telefon raqamini** yuboring:",
        "btn_phone": "📱 Telefon raqamini yuborish",
        "ask_school_type": "O'quvchi qayerdan ko'chirib o'tkazilmoqda?",
        "btn_local": "🏫 Mahalliy maktabdan (O'zbekiston)",
        "btn_abroad": "🌍 Chet elda o'qigan",
        "ask_abroad": "Bola chet elning **qaysi davlati va shahrida** o'qiganini ko'rsating:",
        "ask_local": "Mahalliy maktabning raqami yoki nomini kiriting:",
        "btn_error": "⚠️ Iltimos, tugmalardan birini tanlang.",
        "docs_head": "📋 **Sizning sinfingiz uchun talab qilinadigan hujjatlar:**\n\n",
        "doc_1": "• **Bolaning tug'ilganlik haqidagi guvohnomasi (metrika)**",
        "doc_2_9_local": "• **Bolaning metrikasi**\n• **Baholar tabeli**",
        "doc_2_9_abroad": "• **Bolaning metrikasi**\n• **Tabelning asli (originali)**\n• **Tabelning rasmiy tarjimasi**",
        "doc_10_11_local": "• **Bolaning metrikasi**\n• **9-sinf attestati / Tabel**",
        "doc_10_11_abroad": (
            "• **O'quvchining pasporti yoki tug'ilganlik haqidagi guvohnomasi**\n"
            "• **Barcha sinflar uchun tabel asllari (kamida 6-sinfdan 9-10-sinfgacha)**\n"
            "• **Yuridik firma yoki notarius tomonidan tabel tarjimasi**\n"
            "• **O'zbekiston hududiy xalq ta'limi (GorONO) tomonidan berilgan attestatni nostrifikatsiya qilish hujjati** (majburiy)"
        ),
        "docs_footer": "\n\nHujjatlarning **shaffof rasmini yoki faylini** bitta yoki bir nechta xabar qilib yuboring. Yuborib bo'lgach, **Tayyor** tugmasini bosing.",
        "doc_empty_error": "⚠️ Siz bitta ham hujjat yubormadingiz. Hujjatlarni yuboring va keyin 'Tayyor' tugmasini bosing.",
        "doc_accepted": "✅ Hujjat qabul qilindi ({} ta yuklandi). Keyingisini yuboring yoki **Tayyor** tugmasini bosing.",
        "success": "🎉 **Oxford International School-ga ariza qabul qilindi!**\n\n• **O'quvchi:** {}\n• **Sinf:** {}\n• **Yuklangan hujjatlar:** {} ta.\n\nQabul komissiyasi hujjatlarni tekshirib, siz bilan bog'lanadi."
    }
}


# --- ШАГИ РЕГИСТРАЦИИ (FSM) ---
class Registration(StatesGroup):
    waiting_for_language = State()       
    waiting_for_name = State()           
    waiting_for_grade = State()          
    waiting_for_phone = State()          
    waiting_for_school_type = State()    
    waiting_for_local_school = State()   
    waiting_for_abroad_details = State() 
    waiting_for_documents = State()      

# --- ЛОГИКА РЕГИСТРАЦИИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    kb = [
        [types.KeyboardButton(text="🇷🇺 Русский язык обучения")],
        [types.KeyboardButton(text="🇺🇿 O'zbek tili (Узбекский язык)")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(
        "🏫 **Добро пожаловать в систему регистрации Oxford International School!**\n"
        "🏫 **Oxford International School ro'yxatdan o'tish tizimiga xush kelibsiz!**\n\n"
        "Пожалуйста, выберите язык обучения / Iltimos, ta'lim tilini tanlang:", 
        reply_markup=keyboard
    )
    await state.set_state(Registration.waiting_for_language)


@dp.message(Registration.waiting_for_language)
async def process_language(message: types.Message, state: FSMContext):
    if "🇷🇺" in message.text:
        lang_code = "ru"
        lang_name = "Русский"
    elif "🇺🇿" in message.text:
        lang_code = "uz"
        lang_name = "Узбекский"
    else:
        await message.answer("⚠️ Пожалуйста, выберите язык кнопками / Iltimos, tilni tugmalar orqali tanlang.")
        return
        
    await state.update_data(lang_code=lang_code, language=lang_name)
    await message.answer(TEXTS[lang_code]["ask_name"], reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Registration.waiting_for_name)


@dp.message(Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    data = await state.get_data()
    await message.answer(TEXTS[data['lang_code']]["ask_grade"])
    await state.set_state(Registration.waiting_for_grade)


@dp.message(Registration.waiting_for_grade)
async def process_grade(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang_code']
    text = message.text.strip()
    
    if not text.isdigit() or not (1 <= int(text) <= 11):
        await message.answer(TEXTS[lang]["grade_error"])
        return
        
    grade = int(text)
    await state.update_data(grade=grade)
    
    kb = [[types.KeyboardButton(text=TEXTS[lang]["btn_phone"], request_contact=True)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(TEXTS[lang]["ask_phone"], reply_markup=keyboard)
    await state.set_state(Registration.waiting_for_phone)


@dp.message(Registration.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang_code']
    grade = int(data['grade'])
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    
    if grade == 1:
        if lang == "ru":
            kb = [
                [types.KeyboardButton(text="🇺🇿 Проживал в Узбекистане")],
                [types.KeyboardButton(text="🌍 Прибыл из-за границы")]
            ]
            msg_ask = "Укажите, пожалуйста, где ребенок проживал ранее:"
        else:
            kb = [
                [types.KeyboardButton(text="🇺🇿 O'zbekistonda yashagan")],
                [types.KeyboardButton(text="🌍 Chet eldan kelgan")]
            ]
            msg_ask = "Iltimos, bola gacha qayerda yashaganini ko'rsating:"
            
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
        await message.answer(msg_ask, reply_markup=keyboard)
        await state.set_state(Registration.waiting_for_school_type)

    else:
        kb = [
            [types.KeyboardButton(text=TEXTS[lang]["btn_local"])],
            [types.KeyboardButton(text=TEXTS[lang]["btn_abroad"])]
        ]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
        await message.answer(TEXTS[lang]["ask_school_type"], reply_markup=keyboard)
        await state.set_state(Registration.waiting_for_school_type)


@dp.message(Registration.waiting_for_school_type)
async def process_school_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang_code']
    grade = int(data['grade'])
    
    abroad_buttons = [TEXTS["ru"]["btn_abroad"], TEXTS["uz"]["btn_abroad"], "🌍 Прибыл из-за границы", "🌍 Chet eldan kelgan"]
    local_buttons = [TEXTS["ru"]["btn_local"], TEXTS["uz"]["btn_local"], "🇺🇿 Проживал в Узбекистане", "🇺🇿 O'zbekistonda yashagan"]
    
    if message.text in abroad_buttons:
        await state.update_data(prev_school_type="За границей")
        await message.answer(TEXTS[lang]["ask_abroad"], reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Registration.waiting_for_abroad_details)
        
    elif message.text in local_buttons:
        await state.update_data(prev_school_type="Местная школа")
        await state.update_data(abroad_details="Нет")
        
        if grade == 1:
            await state.update_data(prev_school_type="Первый класс (Местный)")
            await send_document_request(message, state)
        else:
            await message.answer(TEXTS[lang]["ask_local"], reply_markup=types.ReplyKeyboardRemove())
            await state.set_state(Registration.waiting_for_local_school)
    else:
        await message.answer(TEXTS[lang]["btn_error"])


@dp.message(Registration.waiting_for_local_school)
async def process_local_school(message: types.Message, state: FSMContext):
    await state.update_data(prev_school_type=f"Местная школа: {message.text}")
    await send_document_request(message, state)


@dp.message(Registration.waiting_for_abroad_details)
async def process_abroad_details(message: types.Message, state: FSMContext):
    await state.update_data(abroad_details=message.text)
    await send_document_request(message, state)


# --- УМНАЯ СИСТЕМА ЗАПРОСА ДОКУМЕНТОВ ---
async def send_document_request(message: types.Message, state: FSMContext):
    data = await state.get_data()
    grade = int(data['grade'])
    lang = data['lang_code']
    is_abroad = (data['prev_school_type'] == "За границей")

    msg_text = TEXTS[lang]["docs_head"]
    
    if grade == 1:
        msg_text += TEXTS[lang]["doc_1"]
    elif 2 <= grade <= 9:
        if is_abroad:
            msg_text += TEXTS[lang]["doc_2_9_abroad"]
        else:
            msg_text += TEXTS[lang]["doc_2_9_local"]
    elif grade == 10 or grade == 11:
        if is_abroad:
            msg_text += TEXTS[lang]["doc_10_11_abroad"]
        else:
            msg_text += TEXTS[lang]["doc_10_11_local"]

    msg_text += TEXTS[lang]["docs_footer"]
    
    btn_text = "✅ Готово" if lang == "ru" else "✅ Tayyor"
    kb = [[types.KeyboardButton(text=btn_text)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(msg_text, reply_markup=keyboard)
    await state.update_data(uploaded_files=[])  
    await state.set_state(Registration.waiting_for_documents)


@dp.message(Registration.waiting_for_documents)
async def process_documents(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang_code']
    
    if message.text and any(word in message.text.strip().lower() for word in ["готово", "tayyor"]):
        user_data = await state.get_data()
        files_list = user_data.get('uploaded_files', [])
        
        if not files_list:
            await message.answer(TEXTS[lang]["doc_empty_error"])
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        files_str = ", ".join(files_list)

        cursor.execute(
            "INSERT INTO applicants (telegram_id, fullname, language, grade, phone, prev_school_type, abroad_details, docs_saved, reg_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (message.from_user.id, user_data['fullname'], user_data['language'], user_data['grade'], 
             user_data['phone'], user_data['prev_school_type'], user_data['abroad_details'], files_str, current_time)
        )
        conn.commit()
        await state.clear()

        await message.answer(
            TEXTS[lang]["success"].format(user_data['fullname'], user_data['grade'], len(files_list)),
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    file_id = None
    orig_name = ""

    if message.photo:
        file_id = message.photo[-1].file_id
        orig_name = f"photo_{datetime.now().strftime('%H%M%S')}.jpg"
    elif message.document:
        file_id = message.document.file_id
        orig_name = message.document.file_name
    else:
        btn_text = "✅ Готово" if lang == "ru" else "✅ Tayyor"
        kb = [[types.KeyboardButton(text=btn_text)]]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer(TEXTS[lang]["docs_footer"], reply_markup=keyboard)
        return

    file = await bot.get_file(file_id)
    file_path = os.path.join(DOCS_DIR, f"{message.from_user.id}_{orig_name}")
    await bot.download_file(file.file_path, file_path)

    user_data = await state.get_data()
    uploaded_files = user_data.get('uploaded_files', [])
    uploaded_files.append(file_path)
    await state.update_data(uploaded_files=uploaded_files)

    btn_text = "✅ Готово" if lang == "ru" else "✅ Tayyor"
    kb = [[types.KeyboardButton(text=btn_text)]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(TEXTS[lang]["doc_accepted"].format(len(uploaded_files)), reply_markup=keyboard)


# --- НАДЁЖНЫЙ ЗАПУСК ---
async def main():
    print("Попытка запуска двуязычного бота Oxford School...")
    try:
        bot_user = await bot.get_me()
        print(f"✅ Успешное подключение к серверам Telegram!")
        print(f"Имя вашего бота в сети: @{bot_user.username}")
        print("--------------------------------------------------")
        print("Бот запущен и ожидает сообщений.")
        await dp.start_polling(bot)
    except Exception as e:
        print("\n❌ ПРОИЗОШЛА ОШИБКА ПРИ СВЯЗИ С TELEGRAM:")
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Описание: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Критическая ошибка asyncio: {e}")

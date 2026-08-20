import os, telebot, random, string, requests, sqlite3
from threading import Thread
from flask import Flask
from telebot import types

# === Flask Server (для UptimeRobot) ===
app = Flask('')

@app.route('/')
def home():
    return 'Bot is alive!'

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run).start()

# === Основная логика бота ===
BOT_TOKEN = "8604960714:AAEayr1c8DRCWCZj6543XPlJtFAfE1oVtS0"
PHOTO_ID = "AgACAgQAAxkBAAN_aoW03DqN0hasDXhWps2nkueKg-wAAoIVaxtX0TFQjmgrZO5yu5cBAAMCAAN4AAM9BA"
DB_NAME = "bot_database.db"

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# Только цифры для замен (без спецсимволов)
LEET_MAP = {
    'a': ['4'],
    'e': ['3'],
    'i': ['1'],
    'o': ['0'],
    't': ['7'],
    's': ['5'],
    'b': ['8'],
    'g': ['9'],
    'z': ['2']
}

def safe_send_message(chat_id, text, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return None

def safe_send_photo(chat_id, photo, caption=None, reply_markup=None):
    try:
        return bot.send_photo(chat_id, photo, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка отправки фото: {e}")
        return safe_send_message(chat_id, caption, reply_markup=reply_markup)

def db_exec(query, params=(), fetch=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(query, params)
        return c.fetchall() if fetch else conn.commit()

db_exec("CREATE TABLE IF NOT EXISTS collections (id INTEGER PRIMARY KEY, chat_id INTEGER, username TEXT, UNIQUE(chat_id, username))")

def calculate_score(u):
    l = len(u)
    s = 5 + (3 if l<=5 else 2 if l==6 else 1 if l==7 else 0) + (2 if u.isalpha() else 0) + (1 if len(set(u))<l else 0)
    return max(1, min(10, s))

def format_result(u):
    return f"🌐Юзернейм найден\n┌User: @{u}\n├Chars: {len(u)}\n└Score: {calculate_score(u)}/10"

def is_username_free(u):
    try:
        r = requests.get(f"https://t.me/{u}", timeout=5).text
        return "If you have Telegram, you can contact" not in r and "tgme_page_title" not in r
    except:
        return False

def gen_leet(w):
    w = w.lower()
    w = ''.join(c for c in w if c.isalnum())
    if not w:
        return ""
    
    res_list = []
    for c in w:
        if c in LEET_MAP and random.choice([True, False]):
            res_list.append(random.choice(LEET_MAP[c]))
        else:
            res_list.append(c)
    
    res = "".join(res_list)
    
    if res == w:
        for i, c in enumerate(w):
            if c in LEET_MAP:
                res = w[:i] + random.choice(LEET_MAP[c]) + w[i+1:]
                break

    # Запрет цифры в начале юзернейма
    if res and res[0].isdigit():
        res = random.choice(string.ascii_lowercase) + res[1:]
        
    return res

def gen_pattern(ptype, l=6):
    ch = string.ascii_lowercase
    if ptype == "repeat_end": 
        b = random.choice(ch)
        return b + ''.join(random.choices(ch, k=max(3, l-2))) + b
    if ptype == "triple_num": 
        return ''.join(random.choices(ch, k=max(2, l-3))) + random.choice(["777","666","999","000","111"])
    if ptype == "xx": 
        return random.choice(["xx","qq","vv","zz","oo"]) + ''.join(random.choices(ch, k=max(3, l-2)))
    if ptype == "bot": 
        return ''.join(random.choices(ch, k=max(3, l-3))) + "bot"
    return ''.join(random.choices(ch, k=l))

def gen_user(length, mode="letters", word="", word_pos="any"):
    word = word.lower()
    chars = string.ascii_lowercase + (string.digits if mode=="mix" else "")
    if word:
        rem = max(0, length - len(word))
        part = ''.join(random.choices(chars, k=rem))
        if mode=="mix" and not any(c.isdigit() for c in part+word) and part:
            part = part[:-1] + random.choice(string.digits)
        res = word + part if word_pos=="start" else part[:(p:=random.randint(0, len(part)))] + word + part[p:]
        return (random.choice(string.ascii_lowercase) + res[1:]) if res[0].isdigit() else res
    while True:
        res = random.choice(string.ascii_lowercase) + ''.join(random.choices(chars, k=length-1))
        if mode!="mix" or any(c.isdigit() for c in res): 
            return res

def get_free(length=5, count=1, mode="letters", word="", word_pos="any", pattern=""):
    free, att = [], 0
    while len(free) < count and att < 150:
        att += 1
        u = gen_pattern(pattern, length) if pattern else gen_leet(word) if mode=="leet" else gen_user(length, mode, word, word_pos)
        if u and is_username_free(u) and u not in free: 
            free.append(u)
    return free

def edit_msg(call, text, markup):
    try:
        if call.message.caption:
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=text, reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
    except Exception as e:
        safe_send_message(call.message.chat.id, text, reply_markup=markup)

def main_menu():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("🔘Поиск 5 значных юзов", callback_data="menu_5"),
          types.InlineKeyboardButton("🔘Поиск 6 значных юзов", callback_data="menu_6"),
          types.InlineKeyboardButton("🔘Поиск 7 значных юзов", callback_data="menu_7"),
          types.InlineKeyboardButton("🔘Поиск по слову", callback_data="menu_word"),
          types.InlineKeyboardButton("🔘Автозамены", callback_data="menu_leet"),
          types.InlineKeyboardButton("🔘Красивые повторы", callback_data="menu_pattern"),
          types.InlineKeyboardButton("🔘Проверка юзернейма", callback_data="menu_check"),
          types.InlineKeyboardButton("🔘Коллекция", callback_data="menu_collection"),
          types.InlineKeyboardButton("🔘Канал с новостями", url="https://t.me/ohota_user"))
    return m

def get_repeat_markup(data):
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔄Повторить", callback_data=data))

@bot.message_handler(commands=['start'])
def send_welcome(m):
    user_states.pop(m.chat.id, None)
    text = "👋🏻Здравствуйте\nРады вас видеть в проекте.\n└🔗Канал с новостями — @ohota_user\n\n\n📜Выберете действие:"
    safe_send_photo(m.chat.id, PHOTO_ID, caption=text, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    cid, data = call.message.chat.id, call.data
    
    if data in ["menu_5", "menu_6", "menu_7"]:
        l = data.split("_")[1]
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton(f"🔘Поиск {l} значных юзов (🔢)", callback_data=f"search_{l}_mix"),
              types.InlineKeyboardButton(f"🔘Поиск {l} значных юзов (🔡)", callback_data=f"search_{l}_letters"),
              types.InlineKeyboardButton("« Назад в меню", callback_data="main_menu"))
        edit_msg(call, f"Выберите тип символов для {l}-значных юзернеймов:", m)

    elif data == "menu_word":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton("🔘Поиск с начальным словом", callback_data="wordmode_start"),
              types.InlineKeyboardButton("🔘Поиск со словом (🔡)", callback_data="wordmode_any"),
              types.InlineKeyboardButton("🔘Поиск со словом (🔢)", callback_data="wordmode_mix"),
              types.InlineKeyboardButton("« Назад в меню", callback_data="main_menu"))
        edit_msg(call, "Выберите режим поиска по слову:", m)

    elif data.startswith("wordmode_"):
        mode = data.split("_")[1]
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(*[types.InlineKeyboardButton(f"🔘{i} символов", callback_data=f"wlen_{mode}_{i}") for i in [5,6,7,8]])
        m.add(types.InlineKeyboardButton("« Назад", callback_data="menu_word"))
        edit_msg(call, "Выберите длину итогового юзернейма:", m)

    elif data == "menu_leet":
        user_states[cid] = "input_leet_word"
        safe_send_message(cid, "Введите слово для генерации автозамен (например: alex):")

    elif data == "menu_pattern":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton("🔘Одинаковые буквы на концах (xalex)", callback_data="pat_repeat_end"),
              types.InlineKeyboardButton("🔘Тройная цифра (name777)", callback_data="pat_triple_num"),
              types.InlineKeyboardButton("🔘Красивые пары (xx, qq, vv)", callback_data="pat_xx"),
              types.InlineKeyboardButton("🔘С окончаниями bot (namebot)", callback_data="pat_bot"),
              types.InlineKeyboardButton("« Назад в меню", callback_data="main_menu"))
        edit_msg(call, "Выберите паттерн для поиска:", m)

    elif data.startswith("pat_"):
        safe_send_message(cid, "Идёт поиск свободного юзернейма по паттерну...")
        res = get_free(length=6, count=1, pattern=data.replace("pat_", ""))
        safe_send_message(cid, format_result(res[0]) if res else "Не удалось найти.", reply_markup=get_repeat_markup(data) if res else None)

    elif data.startswith("repeatword_"):
        parts = data.split(":")
        mode = parts[0].split("_")[1]
        l, w = parts[1], parts[2]
        res = get_free(length=int(l), count=1, mode="mix" if mode=="mix" else "letters", word=w, word_pos=mode)
        safe_send_message(cid, format_result(res[0]) if res else "Не удалось найти.", reply_markup=get_repeat_markup(data) if res else None)

    elif data.startswith("repeatleet_"):
        w = data.split("_")[1]
        res = get_free(word=w, mode="leet")
        safe_send_message(cid, format_result(res[0]) if res else "Не удалось найти.", reply_markup=get_repeat_markup(f"repeatleet_{txt}") if res else None)

    elif data == "menu_check":
        user_states[cid] = "input_check_username"
        safe_send_message(cid, "Введите юзернейм для проверки:")

    elif data.startswith("wlen_"):
        _, mode, l = data.split("_")
        user_states[cid] = {"type": f"word_{mode}", "length": int(l)}
        safe_send_message(cid, f"Введите ключевое слово (для юзернейма из {l} символов):")

    elif data == "menu_collection":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton("🔘Ваши экземпляры", callback_data="coll_view"),
              types.InlineKeyboardButton("🔘Добавить экземпляр", callback_data="coll_add"),
              types.InlineKeyboardButton("« Назад в меню", callback_data="main_menu"))
        edit_msg(call, "Раздел 'Коллекция'. Выберите действие:", m)

    elif data == "coll_view":
        rows = db_exec("SELECT username FROM collections WHERE chat_id = ?", (cid,), fetch=True)
        m = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("« Назад в коллекцию", callback_data="menu_collection"))
        edit_msg(call, "Ваши сохраненные экземпляры:\n\n" + "\n".join([r[0] for r in rows]) if rows else "Ваш список пуст.", m)

    elif data == "coll_add":
        user_states[cid] = "add_to_collection"
        safe_send_message(cid, "Введите юзернейм для добавления (начиная с @):")

    elif data == "main_menu":
        user_states.pop(cid, None)
        edit_msg(call, "👋🏻Здравствуйте\nРады вас видеть в проекте.\n└🔗Канал с новостями — @ohota_user\n\n\n📜Выберете действие:", main_menu())

    elif data.startswith("search_"):
        _, l, mode = data.split("_")
        res = get_free(length=int(l), count=1, mode=mode)
        safe_send_message(cid, format_result(res[0]) if res else "Не удалось найти.", reply_markup=get_repeat_markup(data) if res else None)

@bot.message_handler(func=lambda msg: msg.chat.id in user_states)
def handle_text_inputs(msg):
    cid, txt = msg.chat.id, msg.text.strip()
    st = user_states.pop(cid, None)

    if st == "add_to_collection":
        if not txt.startswith("@"): 
            return safe_send_message(cid, "Ошибка! Должно начинаться с @.")
        try:
            db_exec("INSERT INTO collections (chat_id, username) VALUES (?, ?)", (cid, txt))
            safe_send_message(cid, f"Экземпляр {txt} успешно сохранен!")
        except: 
            safe_send_message(cid, f"Экземпляр {txt} уже есть в коллекции.")

    elif st == "input_check_username":
        u = txt.replace("@", "").strip()
        safe_send_message(cid, format_result(u) if is_username_free(u) else f"❌ Юзернейм @{u} уже ЗАНЯТ.")

    elif st == "input_leet_word":
        res = get_free(word=txt, mode="leet")
        safe_send_message(cid, format_result(res[0]) if res else "Не удалось найти.", reply_markup=get_repeat_markup(f"repeatleet_{txt}") if res else None)

    elif isinstance(st, dict) and st.get("type","").startswith("word_"):
        mode, l = st["type"].split("_")[1], st["length"]
        res = get_free(length=l, count=1, mode="mix" if mode=="mix" else "letters", word=txt, word_pos=mode)
        safe_send_message(cid, format_result(res[0]) if res else "Не удалось найти.", reply_markup=get_repeat_markup(f"repeatword_{mode}:{l}:{txt}") if res else None)

if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"Ошибка в polling: {e}")

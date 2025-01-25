import telebot
import time
import random
import json
from telebot import types

# ضع هنا التوكن الخاص بك
API_TOKEN = '7622507883:AAFp5JpVWsHUr9YXSYaJoQjB1TSsGhJLMe0'

# إنشاء كائن البوت
bot = telebot.TeleBot(API_TOKEN)

# اسم الملف لتخزين البيانات
DATA_FILE = "data.json"

# الكلمة التي تكسب النقاط
reward_word = "daily"

# عدد الثواني بين كل مرة يحصل فيها المستخدم على النقاط
CLAIM_COOLDOWN = 24 * 60 * 60  # 24 ساعة بالثواني

# نسبة خصم تحويل النقاط (5%)
TRANSFER_FEE = 0.05

# نسبة الأشخاص الذين يحصلون على نقاط أكثر من 20
HIGH_POINT_PROBABILITY = 0.10  # 10%

# معرف المستخدم الخاص بالمالك (استبدل هذا بالـ user_id الخاص بك)
OWNER_ID = 5371702115  # استبدله بـ user_id الخاص بك

# تحميل البيانات من ملف JSON
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# حفظ البيانات في ملف JSON
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

# قاموس لتخزين البيانات
data = load_data()

# التعامل مع الأمر /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id

    # إذا لم يكن المستخدم قد اختار اللغة من قبل، نعرض له الأزرار
    if str(user_id) not in data:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        button1 = types.KeyboardButton("العربية")
        button2 = types.KeyboardButton("English")
        markup.add(button1, button2)
        bot.send_message(user_id, "Welcome! Please choose your language:\n\n1. العربية\n2. English", reply_markup=markup)
        return
    else:
        # إذا كان المستخدم قد اختار اللغة من قبل، تابع التفاعل
        language = data[str(user_id)]['language']
        send_help_message(user_id, language)

# التعامل مع اختيار اللغة
@bot.message_handler(func=lambda message: message.text in ['العربية', 'English'])
def handle_language_choice(message):
    user_id = message.from_user.id
    language = 'ar' if message.text == 'العربية' else 'en'
    
    # حفظ اللغة في البيانات
    data[str(user_id)] = {'language': language, 'points': 0, 'last_claim_time': 0}
    save_data(data)

    # التأكيد للمستخدم
    if language == 'ar':
        bot.reply_to(message, "تم اختيار اللغة العربية. الآن يمكنك التفاعل مع البوت.")
    else:
        bot.reply_to(message, "Language set to English. You can now interact with the bot.")
    
    # بعد اختيار اللغة، إرسال التعليمات الخاصة بها
    send_help_message(user_id, language)

# إرسال تعليمات الأوامر للمستخدم حسب اللغة المختارة
def send_help_message(user_id, language):
    if language == 'ar':
        bot.send_message(user_id, """
1. اكتب "daily" للحصول على النقاط.
2. اكتب "credit" لعرض عدد النقاط لديك.
3. اكتب "id" لعرض معرّف المستخدم الخاص بك.
4. اكتب "transfer [user_id] [amount]" لتحويل النقاط.
5. اكتب "help" لعرض الأوامر.
""")
    else:
        bot.send_message(user_id, """
1. Type "daily" to get points.
2. Type "credit" to check your points balance.
3. Type "id" to get your user ID.
4. Type "transfer [user_id] [amount]" to transfer points.
5. Type "help" to view available commands.
""")

# التعامل مع الأمر "credit" لعرض النقاط
@bot.message_handler(func=lambda message: message.text.lower() == "credit")
def handle_credit(message):
    user_id = message.from_user.id
    credit = data[str(user_id)]['points']
    language = data[str(user_id)]['language']
    
    # تحديد النقاط ليظهر بأقصى 3 أرقام بعد الفاصلة
    credit = round(credit, 2)
    
    if language == 'ar':
        bot.reply_to(message, f"لديك {credit} نقاط.")
    else:
        bot.reply_to(message, f"You have {credit} points.")

# التعامل مع الأمر "id" لعرض المعرف
@bot.message_handler(func=lambda message: message.text.lower() == "id")
def handle_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"Your user ID is: {user_id}" if data[str(user_id)]['language'] == 'en' else f"معرّف المستخدم الخاص بك هو: {user_id}")

# التعامل مع الأمر "transfer" لتحويل النقاط
@bot.message_handler(func=lambda message: message.text.lower().startswith("transfer"))
def handle_transfer(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Invalid usage. Use the command like this: transfer [user_id] [amount]" if data[str(message.from_user.id)]['language'] == 'en' else "استخدام غير صحيح. استخدم الأمر بهذا الشكل: transfer [user_id] [amount]")
            return

        target_user_id = int(parts[1])  # تحويل ID المستخدم المستهدف
        points_to_transfer = int(parts[2])  # عدد النقاط للتحويل

        sender_user_id = message.from_user.id
        sender_points = data[str(sender_user_id)]['points']

        if sender_points < points_to_transfer:
            bot.reply_to(message, "You don't have enough points to transfer." if data[str(sender_user_id)]['language'] == 'en' else "ليس لديك نقاط كافية لتحويلها.")
            return

        # خصم 5% من النقاط المحولة
        fee = points_to_transfer * TRANSFER_FEE
        final_transfer_points = points_to_transfer - fee

        # خصم النقاط من المرسل
        data[str(sender_user_id)]['points'] -= points_to_transfer
        # إضافة النقاط للمستقبل
        if str(target_user_id) not in data:
            data[str(target_user_id)] = {'language': 'en', 'points': 0, 'last_claim_time': 0}
        data[str(target_user_id)]['points'] += final_transfer_points

        # إرسال رسالة تأكيد للطرفين
        bot.reply_to(message, f"You have successfully transferred {final_transfer_points} points (after a 5% fee) to user {target_user_id}. You have now {data[str(sender_user_id)]['points']} points left." if data[str(sender_user_id)]['language'] == 'en' else f"لقد قمت بتحويل {final_transfer_points} نقطة (بعد خصم 5%) إلى المستخدم {target_user_id}. لديك الآن {data[str(sender_user_id)]['points']} نقطة متبقية.")
        bot.send_message(target_user_id, f"You have received {final_transfer_points} points from user {sender_user_id}. Your new balance is {data[str(target_user_id)]['points']} points." if data[str(target_user_id)]['language'] == 'en' else f"لقد استلمت {final_transfer_points} نقطة من المستخدم {sender_user_id}. رصيدك الجديد هو {data[str(target_user_id)]['points']} نقطة.")

        # حفظ البيانات بعد التحويل
        save_data(data)

    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid usage. Use the command like this: transfer [user_id] [amount]" if data[str(message.from_user.id)]['language'] == 'en' else "استخدام غير صحيح. استخدم الأمر بهذا الشكل: transfer [user_id] [amount]")

# التعامل مع الأمر "help"
@bot.message_handler(func=lambda message: message.text.lower() == "help")
def handle_help(message):
    user_id = message.from_user.id
    language = data[str(user_id)]['language']
    send_help_message(user_id, language)

# التعامل مع الرسائل النصية العامة (للكلمات التي تكسب النقاط)
@bot.message_handler(func=lambda message: message.text.lower() == reward_word.lower())
def handle_claim_points(message):
    user_id = message.from_user.id
    current_time = time.time()

    if current_time - data[str(user_id)]['last_claim_time'] < CLAIM_COOLDOWN:
        remaining_time = CLAIM_COOLDOWN - (current_time - data[str(user_id)]['last_claim_time'])
        hours = int(remaining_time // 3600)
        minutes = int((remaining_time % 3600) // 60)
        bot.reply_to(message, f"You can only claim points once every 24 hours. You can claim your points again in {hours} hours and {minutes} minutes." if data[str(user_id)]['language'] == 'en' else f"يمكنك الحصول على النقاط مرة واحدة فقط كل 24 ساعة. يمكنك المطالبة بنقاطك مرة أخرى خلال {hours} ساعة و{minutes} دقيقة.")
        return

    points_to_award = random.randint(1, 10)
    if points_to_award > 20 and random.random() > HIGH_POINT_PROBABILITY:
        points_to_award = random.randint(1, 5)  # تقليل النقاط إذا كانت أكثر من 20 وكان الاحتمال أقل من 10%

    data[str(user_id)]['points'] += points_to_award
    data[str(user_id)]['last_claim_time'] = current_time
    save_data(data)

    bot.reply_to(message, f"You have received {points_to_award} points! You now have {data[str(user_id)]['points']} points." if data[str(user_id)]['language'] == 'en' else f"لقد حصلت على {points_to_award} نقطة! لديك الآن {data[str(user_id)]['points']} نقطة.")

# التعامل مع الأوامر الخاصة بالمالك فقط (مثل إضافة أو حذف الأموال)
@bot.message_handler(func=lambda message: message.text.lower().startswith("add_credit") and message.from_user.id == OWNER_ID)
def handle_add_credit(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Invalid usage. Use the command like this: add_credit [user_id] [amount]")
            return

        target_user_id = int(parts[1])  # تحويل ID المستخدم المستهدف
        amount_to_add = float(parts[2])  # المبلغ الذي سيتم إضافته

        # التأكد من أن المستخدم المستهدف موجود في البيانات
        if str(target_user_id) not in data:
            data[str(target_user_id)] = {'language': 'en', 'points': 0, 'last_claim_time': 0}
        
        # إضافة المبلغ إلى حساب المستخدم
        data[str(target_user_id)]['points'] += amount_to_add
        save_data(data)

        # تأكيد الإضافة للمستخدم
        bot.reply_to(message, f"Successfully added {amount_to_add} points to user {target_user_id}.")

    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid usage. Use the command like this: add_credit [user_id] [amount]")

# التعامل مع الأوامر الخاصة بالمالك فقط (مثل إضافة أو حذف الأموال)
@bot.message_handler(func=lambda message: message.text.lower().startswith("subtract_credit") and message.from_user.id == OWNER_ID)
def handle_subtract_credit(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Invalid usage. Use the command like this: subtract_credit [user_id] [amount]")
            return

        target_user_id = int(parts[1])  # تحويل ID المستخدم المستهدف
        amount_to_subtract = float(parts[2])  # المبلغ الذي سيتم حذفه

        # التأكد من أن المستخدم المستهدف موجود في البيانات
        if str(target_user_id) not in data:
            data[str(target_user_id)] = {'language': 'en', 'points': 0, 'last_claim_time': 0}
        
        # التأكد من أن المستخدم لديه رصيد كافٍ
        if data[str(target_user_id)]['points'] < amount_to_subtract:
            bot.reply_to(message, "The user doesn't have enough points to subtract.")
            return

        # خصم المبلغ من حساب المستخدم
        data[str(target_user_id)]['points'] -= amount_to_subtract
        save_data(data)

        # تأكيد الخصم للمستخدم
        bot.reply_to(message, f"Successfully subtracted {amount_to_subtract} points from user {target_user_id}.")

    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid usage. Use the command like this: subtract_credit [user_id] [amount]")

# التعامل مع الرسائل التي لا تفهمها البوت
@bot.message_handler(func=lambda message: True)
def handle_unknown_message(message):
    user_id = message.from_user.id
    language = data[str(user_id)]['language']

    if language == 'ar':
        bot.reply_to(message, "لم أفهم ذلك. من فضلك اكتب 'help' لعرض الأوامر المتاحة.")
    else:
        bot.reply_to(message, "I didn't understand that. Please type 'help' to see the available commands.")

# بدء البوت
bot.polling(none_stop=True)

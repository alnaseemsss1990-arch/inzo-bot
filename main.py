import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import threading
import os

# ================= الإعدادات الأساسية =================
TELEGRAM_BOT_TOKEN = "8833837598:AAFlqM4XCkJsfr4Rg2EN-WSZzXkg8Mh7aAQ"
CHAT_ID = "7696437784"
TARGET_PRICE = 20000.000

# وضع التوكن مباشرة هنا كقيمة نصية صريحة
INZO_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ2NGE2QHlhaG9vLmNvbSIsImlhdCI6MTc4NzcyODE2MCwiZXhwIjoxNzg3NzcxMzYwfQ.JZhwohKpLru4WWOhMvFLJSClZ5oTgiL2fXQeitBngBn9w2dr98sZ8IlTdxodwYJn-SJrMjfTHlI_r7OSO77IBA"

# القائمة الخاصة بأكواد وأسماء طرق الدفع المراد مراقبتها
TARGET_PAYMENT_IDS = ["9", "103"]
# ======================================================

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

is_monitoring = False
notified_offers = {}

headers = {
    "Authorization": INZO_TOKEN,
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, /",
    "Origin": "https://p2p.inzo.co",
    "Referer": "https://p2p.inzo.co/"
}

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    btn_start = InlineKeyboardButton("▶️ تشغيل المراقبة", callback_data="start_mon")
    btn_stop = InlineKeyboardButton("⏹️ إيقاف", callback_data="stop_mon")
    btn_status = InlineKeyboardButton("ℹ️ حالة البوت", callback_data="status")
    btn_update = InlineKeyboardButton("🔄 تحديث التوكن", callback_data="update_token")
    
    markup.add(btn_start, btn_stop)
    markup.add(btn_status, btn_update)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if str(message.chat.id) == CHAT_ID:
        bot.send_message(message.chat.id, "👋 أهلاً بك في لوحة تحكم INZO P2P!\nاختر ما تريد من الأزرار أدناه:", reply_markup=main_menu())

def process_new_token(message):
    global INZO_TOKEN, headers
    new_token = message.text.strip()
    
    if not new_token.startswith("Bearer "):
        new_token = "Bearer " + new_token
        
    INZO_TOKEN = new_token
    headers["Authorization"] = INZO_TOKEN
    
    bot.send_message(message.chat.id, "✅ *تم تحديث التوكن في الكود بنجاح!*\nيمكنك الآن تشغيل المراقبة.", reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global is_monitoring
    try:
        if call.data == "start_mon":
            if not is_monitoring:
                is_monitoring = True
                bot.answer_callback_query(call.id, "✅ تم التشغيل!")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ *تم تشغيل المراقبة لطرق الدفع (9 و 103 والكلمات المفتاحية)!*\nسأقوم بإرسال الإشعارات فور توفر عروض.", reply_markup=main_menu(), parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "⚠️ المراقبة تعمل بالفعل!")
                
        elif call.data == "stop_mon":
            if is_monitoring:
                is_monitoring = False
                bot.answer_callback_query(call.id, "🛑 تم الإيقاف!")
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🛑 *تم إيقاف المراقبة!*\nالبوت في وضع الاستراحة حالياً.", reply_markup=main_menu(), parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "⚠️ المراقبة متوقفة بالفعل!")
                
        elif call.data == "status":
            state = "🟢 تعمل الآن" if is_monitoring else "🔴 متوقفة"
            bot.answer_callback_query(call.id, f"الحالة: {state}")
            bot.send_message(call.message.chat.id, f"ℹ️ *حالة النظام:*\n- المراقبة: {state}\n- الأكواد المدعومة: 9, 103\n- السعر المستهدف: {TARGET_PRICE}", reply_markup=main_menu(), parse_mode="Markdown")
            
        elif call.data == "update_token":
            bot.answer_callback_query(call.id, "يرجى إرسال التوكن")
            msg = bot.send_message(call.message.chat.id, "📝 *أرسل التوكن الجديد الآن:*\n(قم بنسخه من المتصفح وألصقه هنا في المحادثة كرسالة عادية)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_new_token)
    except Exception as e:
        pass

def monitor_inzo():
    global is_monitoring, notified_offers
    API_URL = "https://p2pbe.inzo.co/api/offers/BUY?pageSize=50&countryCode=IQ&sort=activeBuyer-desc,buyRate-asc"
    
    while True:
        if is_monitoring:
            try:
                response = requests.get(API_URL, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    offers = data.get("data", []) if isinstance(data, dict) else data
                    
                    for offer in offers:
                        if not isinstance(offer, dict): 
                            continue
                        
                        try:
                            price = float(offer.get("rate", offer.get("price", 0)))
                            available_qty = float(offer.get("available", offer.get("availableQuantity", 0)))
                        except:
                            continue
                            
                        merchant_name = offer.get("fullName", offer.get("merchantName", "غير معروف"))
                        payment_methods = offer.get("paymentMethods", offer.get("payMethods", []))
                        
                        is_valid_method = False
                        methods_text = ""
                        
                        if isinstance(payment_methods, list):
                            for m in payment_methods:
                                method_id = None
                                if isinstance(m, (int, float)):
                                    method_id = int(m)
                                elif isinstance(m, dict):
                                    method_id = m.get("id") or m.get("paymentMethodId")
                                    m_name = str(m.get("name", m.get("title", m.get("paymentMethodName", "")))).lower()
                                    methods_text += " " + m_name
                                elif isinstance(m, str):
                                    methods_text += " " + m.lower()
                                    
                                if method_id in TARGET_PAYMENT_IDS or str(method_id) in [str(x) for x in TARGET_PAYMENT_IDS]:
                                    is_valid_method = True
                                    break
                        
                        if not is_valid_method:
                            for keyword in TARGET_KEYWORDS:
                                if keyword in methods_text:
                                    is_valid_method = True
                                    break
                        

                            if notified_offers.get(merchant_name) != price:
                                current_time = time.strftime('%I:%M %p') 
                                alert_msg = (
                                    f"🚨 تنبيه توفر USDT (طرق الدفع المطابقة)! 🚨\n\n"
                                    f"👤 التاجر: {merchant_name}\n"
                                    f"💰 السعر: {price} IQD\n"
                                    f"📦 المتوفر: {available_qty} USDT\n"
                                    f"⏱️ الوقت: {current_time}\n"
                                    f"------------------------------"
                                )
                                bot.send_message(CHAT_ID, alert_msg, parse_mode="Markdown")
                                notified_offers[merchant_name] = price
                                
                elif response.status_code == 401:
                    is_monitoring = False
                    bot.send_message(CHAT_ID, "❌ ⚠️ تنبيه أمني:\nتوكن INZO منتهي الصلاحية!\n\nتم إيقاف المراقبة تلقائياً. يرجى تحديث التوكن.", parse_mode="Markdown", reply_markup=main_menu())
                
            except Exception as e:
                except Exception as e:
    print(f"خطأ في حلقة المراقبة: {e}"
                
        time.sleep(30) 

print("🚀 جاري تشغيل البوت التفاعلي...")
t = threading.Thread(target=monitor_inzo)
t.daemon = True
t.start()

while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"⚠️ رمشة بالإنترنت أو خطأ بسيط، جاري إعادة المحاولة... ({e})")
        time.sleep(5)

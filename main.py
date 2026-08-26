import time
import threading
import requests
import telebot

# إعدادات البوت والمنصة المكتملة
TOKEN = "8833837598:AAFlqM4XCkJsfr4Rg2EN-WSZzXkg8Mh7aAQ"
CHAT_ID = "7696437784"
BEARER_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ2NGE2QHlhaG9vLmNvbSIsImlhdCI6MTc4NzcyODE2MCwiZXhwIjoxNzg3NzcxMzYwfQ.JZhwohKpLru4WWOhMvFLJSClZ5oTgiL2fXQeitBngBn9w2dr98sZ8IlTdxodwYJn-SJrMjfTHlI_r7OSO77IBA"

bot = telebot.TeleBot(TOKEN)

# إعدادات المراقبة (طرق الدفع: Al-Rafidain QiServices & Super Qi)
TARGET_PAYMENT_METHODS = ["super qi", "al-rafidain qiservices"]
TARGET_PRICE = 1600.00  # السعر المستهدف
API_URL = "https://p2pbe.inzo.co/api/offers/BUY?pageSize=20&countryCode=IQ&sort=activeBuyer-desc,buyRate-asc"

is_monitoring = False
notified_offers = {}

def get_headers():
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    }

def monitor_inzo():
    global is_monitoring
    print("🚀 Starting INZO monitoring (Al-Rafidain & Super Qi)...")
    
    while is_monitoring:
        try:
            response = requests.get(API_URL, headers=get_headers(), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                offers = data.get("data", []) if isinstance(data, dict) else data
                
                for offer in offers:
                    if not is_monitoring:
                        break
                    
                    merchant_name = offer.get("merchantName", offer.get("user", {}).get("username", "Unknown"))
                    price = float(offer.get("price", 0))
                    available_qty = float(offer.get("availableQuantity", offer.get("surplus", 0)))
                    
                    payment_methods = offer.get("paymentMethods", offer.get("payMethods", []))
                    is_valid_method = False
                    
                    for m in payment_methods:
                        method_name = ""
                        if isinstance(m, dict):
                            method_name = str(m.get("name", m.get("title", m.get("paymentMethodName", "")))).lower()
                        elif isinstance(m, str):
                            method_name = m.lower()
                        
                        for target in TARGET_PAYMENT_METHODS:
                            if target in method_name:
                                is_valid_method = True
                                break
                        if is_valid_method:
                            break
                    
                    if is_valid_method and price > 0 and price <= TARGET_PRICE and available_qty > 0:
                        if notified_offers.get(merchant_name) != price:
                            current_time = time.strftime('%H:%M:%S')
                            alert_msg = (
                                f"🚨 USDT Offer Alert (Al-Rafidain / Super Qi) 🚨\n\n"
                                f"🛒 Merchant: {merchant_name}\n"
                                f"💵 Price: {price} IQD\n"
                                f"📦 Available: {available_qty} USDT\n"
                                f"🕒 Time: {current_time}\n"
                                f"------------------------"
                            )
                            bot.send_message(CHAT_ID, alert_msg, parse_mode="Markdown")
                            notified_offers[merchant_name] = price
                            
            elif response.status_code == 401:
                is_monitoring = False
                bot.send_message(CHAT_ID, "❌ ⚠️ Security Alert: INZO token expired! Please send the new token here.")
                break
                
        except Exception as e:
            pass
            
        time.sleep(30)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_start = telebot.types.KeyboardButton('▶️ Start Monitoring')
    btn_stop = telebot.types.KeyboardButton('⏹️ Stop Monitoring')
    btn_status = telebot.types.KeyboardButton('📊 Bot Status')
    btn_token = telebot.types.KeyboardButton('🔄 Update Token')
    markup.add(btn_start, btn_stop)
    markup.add(btn_status, btn_token)
    
    bot.send_message(message.chat.id, "Welcome to INZO P2P Monitor Bot (Al-Rafidain & Super Qi).\nChoose an option below:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    global is_monitoring, BEARER_TOKEN
    text = message.text.strip()
    
    if text == '▶️ Start Monitoring':
        if not is_monitoring:
            is_monitoring = True
            t = threading.Thread(target=monitor_inzo)
            t.daemon = True
            t.start()
            bot.send_message(message.chat.id, "✅ Monitoring for Al-Rafidain & Super Qi has started successfully.")
        else:
            bot.send_message(message.chat.id, "ℹ️ Monitoring is already running!")
            
    elif text == '⏹️ Stop Monitoring':
        is_monitoring = False
        bot.send_message(message.chat.id, "⏹️ Monitoring has been stopped.")
        
    elif text == '📊 Bot Status':
        status = "🟢 Running" if is_monitoring else "🔴 Stopped"
        bot.send_message(message.chat.id, f"📊 System Status:\n- Monitoring: {status}\n- Methods: Al-Rafidain QiServices & Super Qi\n- Target Price: {TARGET_PRICE}", parse_mode="Markdown")
        
    elif text == '🔄 Update Token' or text.startswith('eyJ') or 'Bearer ' in text:
        new_token = text.replace('Bearer ', '').strip()
        if len(new_token) > 20:
            BEARER_TOKEN = new_token
            bot.send_message(message.chat.id, "✅ INZO token updated successfully! You can now start monitoring.")
        else:
            bot.send_message(message.chat.id, "📝 Send the new token now: (Copy it from your browser and paste it here)", parse_mode="Markdown")

print("Bot is running...")
while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        time.sleep(5)

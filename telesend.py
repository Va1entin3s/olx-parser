import json
import requests
from collections import defaultdict
import os

# Загружаем данные из файла
with open('olx_ads.json', 'r') as f:
    data = json.load(f)

ads = data.get("ads", [])

TELEGRAM_BOT_TOKEN = "8079356951:AAHCpC7ZNUyLacLHBPOjxL09hRVUsYRfBRU"
TELEGRAM_CHAT_ID = "-1002590092233"
SENT_ADS_FILE = 'sent_ads.json'
MARKET_PRICES_FILE = 'market_prices.json'

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    return response

# Функция для загрузки ссылок уже отправленных объявлений
def load_sent_ads():
    if os.path.exists(SENT_ADS_FILE):
        with open(SENT_ADS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Функция для сохранения ссылок отправленных объявлений
def save_sent_ads(sent_ads):
    with open(SENT_ADS_FILE, 'w') as f:
        json.dump(sent_ads, f, indent=4)

# Загружаем информацию о рыночных ценах, если файл существует
try:
    with open(MARKET_PRICES_FILE, 'r') as f:
        market_prices = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    market_prices = {}

# Загружаем ссылки уже отправленных объявлений
sent_ads = load_sent_ads()

# Сначала собираем все цены по (model, year)
price_groups = defaultdict(list)

for ad in ads:
    details = ad.get("details", {})
    model = details.get("Model") or details.get("Model pojazdu")
    year = details.get("Rok produkcji")
    price_text = ad.get("price", "")
    try:
        price_number = int(price_text.replace("zł", "").replace(" ", "").strip())
    except (ValueError, AttributeError):
        continue

    if model and year:
        price_groups[(model, year)].append(price_number)

# Обновляем и усредняем цены
for key, prices in price_groups.items():
    model, year = key
    market_key = f"{model}-{year}"
    new_avg = int(sum(prices) / len(prices))

    if market_key in market_prices:
        old_avg = market_prices[market_key]
        market_prices[market_key] = int((old_avg + new_avg) / 2)
    else:
        market_prices[market_key] = new_avg

# Сохраняем обновленные рыночные цены в файл
with open(MARKET_PRICES_FILE, 'w') as f:
    json.dump(market_prices, f, indent=4)

# Проверяем объявления и отправляем в Telegram, если цена ниже рыночной
for ad in ads:
    details = ad.get("details", {})
    model = details.get("Model") or details.get("Model pojazdu", "N/A")
    year = details.get("Rok produkcji", "N/A")
    price_text = ad.get("price", "N/A")
    ad_link = ad.get("link")  # Ссылка объявления

    try:
        price_number = int(price_text.replace("zł", "").replace(" ", "").strip())
    except (ValueError, AttributeError):
        continue

    # Пропускаем объявление, если оно уже отправлено
    if ad_link in sent_ads:
        continue

    market_key = f"{model}-{year}"
    if market_key in market_prices and price_number:
        market_price = market_prices[market_key]
        if price_number < market_price * 0.5:  # если 0.6, то на 40% дешевле если 0.3 то на 70% дешевле
            message = f"🔥 <b>JEST!</b>\nModel: {model}\nROK: {year}\nCENA: {price_text}\n<a href='{ad_link}'>Zobać</a>"
            send_to_telegram(message)

            # Сохраняем ссылку отправленного объявления
            sent_ads[ad_link] = True

# Сохраняем обновленный список отправленных объявлений
save_sent_ads(sent_ads)

# Функция для отправки изменений на GitHub
def push_to_github():
    os.system("git config --global user.name 'github-actions'")
    os.system("git config --global user.email 'github-actions@github.com'")
    os.system("git add sent_ads.json")
    os.system("git add market_prices.json")
    os.system('git commit -m "Автоматическое обновление объявлений" || echo "No changes to commit"')
    os.system("git push")

# Пушим изменения на GitHub
push_to_github()

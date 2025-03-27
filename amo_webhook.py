import requests
import json
from datetime import datetime
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 AmoCRM данные (лучше хранить в переменных окружения)
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImM3YzI4ZmE0NWMwNmExODM5MTQyZTM1MDdlOTJjOTVkNjUxZDA5ZTAyNzdkZjc2ODRmZTkzNWFlMDg5ZjY4NWIxMjM4YWQyYmZhZjNhMzUxIn0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJjN2MyOGZhNDVjMDZhMTgzOTE0MmUzNTA3ZTkyYzk1ZDY1MWQwOWUwMjc3ZGY3Njg0ZmU5MzVhZTA4OWY2ODViMTIzOGFkMmJmYWYzYTM1MSIsImlhdCI6MTc0MzA2MjcxOCwibmJmIjoxNzQzMDYyNzE4LCJleHAiOjE5MDA4MDAwMDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiZmQzMTc5ZGQtMDhkNi00MmRkLWJlYWQtMGRmODEyY2U1NTYwIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Y3_fkHzktIMthQuKkXTbpTLcLd4BZH7962-UFozIKCC6YbjgxV_Lpm2z4gL-Qo11eegBK6AbEP3E-AWpaWuoE20lmlO3zeNZLVqvFumoHMf0gKK-abNCkIbV-rmD-kWACraJCupvCQD2_f7U1M0nVu_diXF0L8LW5fzOaH9EvPEZS7PCQ6ZcoqvIXRBkXJW4lLoH8BqP3bc5H1_hodTCejCE5a444BM0ltCGTr4kwEN6wnOcnAOHeL5VmjEIzUwfdP-i0BfWAwlRsuEGovCLOvIekHAivjAGLIOTx2nE5vVvikkGUNdMZx2c_KFmOOUSkVjVxYB5QsVRHYtANgSBCQ"  # НЕ публикуйте реальные токены!
AMOCRM_DOMAIN = "https://arbitrajy.amocrm.ru"
TOKEN_FIELD_ID = 898037  # ID поля, где хранится токен
NEW_LEAD_STAGE_ID = 75086270  # ID этапа "NEW Lead"

# 🔹 ID полей AmoCRM
FIELDS_MAPPING = {
    "age": 896769,
    "chainId": 896369,
    "name": 896479,
    "symbol": 896481,
    "marketCap": 896483,
    "liquidity": 896485,
    "volume": 896487,
    "telegram": 898051,
    "twitter": 898053
}

# 🔹 DexScreener API URL
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens/"

def get_dexscreener_data(token_address):
    """Получаем данные о токене с DexScreener API."""
    url = f"{DEXSCREENER_API_URL}{token_address}"
    headers = {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
         "Accept": "application/json",
         "Referer": "https://dexscreener.com/",
         "Origin": "https://dexscreener.com"
    }
    response = requests.get(url, headers=headers)
    # Выводим статус-код для отладки
    print("Status code:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        if "pairs" in data and data["pairs"]:
            pair = max(data["pairs"], key=lambda x: x["liquidity"].get("usd", 0))
            timestamp = pair["pairCreatedAt"] / 1000
            days_since_creation = (datetime.utcnow() - datetime.utcfromtimestamp(timestamp)).days
            social_links = pair.get("info", {}).get("socials", [])
            twitter_link = next((s["url"] for s in social_links if s["type"] == "twitter"), None)
            telegram_link = next((s["url"] for s in social_links if s["type"] == "telegram"), None)
            return {
                "age": f"{days_since_creation} d",
                "chainId": pair["chainId"],
                "name": pair["baseToken"]["name"],
                "symbol": pair["baseToken"]["symbol"],
                "marketCap": pair.get("marketCap", "N/A"),
                "liquidity": pair["liquidity"].get("usd", 0),
                "volume": pair["volume"].get("h24", 0),
                "telegram": telegram_link,
                "twitter": twitter_link
            }
    else:
        print("Ошибка при запросе к DexScreener:", response.status_code)
    return None


def get_leads_with_token_field():
    """Получаем сделки на этапе 'NEW Lead', где заполнено поле TOKEN_FIELD_ID."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    params = {"filter[statuses]": NEW_LEAD_STAGE_ID, "with": "custom_fields_values"}
    logger.info("Запрос к amoCRM: %s с параметрами %s", url, params)
    
    response = requests.get(url, headers=headers, params=params)
    
    try:
        data = response.json()
        logger.info("Полный ответ от amoCRM: %s", data)
    except Exception as e:
        logger.error("Ошибка при обработке JSON ответа от amoCRM: %s", e)
        return []
    
    if response.status_code == 200:
        leads = data.get("_embedded", {}).get("leads", [])
        logger.info("Найдено сделок: %d", len(leads))
        filtered_leads = []
        
        for lead in leads:
            if lead.get("status_id") != NEW_LEAD_STAGE_ID:
                continue
            
            token_address = None
            existing_fields = {}
            if "custom_fields_values" in lead:
                try:
                    existing_fields = {field["field_id"]: field["values"][0]["value"] for field in lead["custom_fields_values"]}
                except Exception as e:
                    logger.error("Ошибка при обработке custom_fields_values сделки %s: %s", lead.get("id"), e)
            
            if TOKEN_FIELD_ID in existing_fields:
                token_address = existing_fields[TOKEN_FIELD_ID].replace("http://", "").replace("https://", "").strip()
            
            if token_address:
                filtered_leads.append({"id": lead["id"], "token": token_address, "existing_fields": existing_fields})
        logger.info("Сделок с токеном: %d", len(filtered_leads))
        return filtered_leads
    else:
        logger.error("Ошибка запроса к amoCRM: %d", response.status_code)
    return []

def update_lead(lead_id, update_data):
    """Обновляем сделку в AmoCRM."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    logger.info("Обновление сделки %s с данными: %s", lead_id, update_data)
    response = requests.patch(url, headers=headers, data=json.dumps(update_data))
    logger.info("Ответ обновления сделки %s: %d - %s", lead_id, response.status_code, response.text)
    return response.status_code == 200

def process_leads():
    """Обрабатываем сделки с токеном на этапе 'NEW Lead'."""
    logger.info("Начало обработки сделок.")
    leads = get_leads_with_token_field()
    if not leads:
        logger.info("Сделки на этапе 'NEW Lead' с токенами не найдены.")
        return
    
    for lead in leads:
        logger.info("Обрабатываем сделку %s с токеном %s", lead['id'], lead['token'])
        token_data = get_dexscreener_data(lead['token'])
        if token_data:
            update_payload = {"custom_fields_values": []}
            for key, value in token_data.items():
                field_id = FIELDS_MAPPING.get(key)
                if field_id and field_id not in lead['existing_fields']:
                    update_payload["custom_fields_values"].append({"field_id": field_id, "values": [{"value": str(value)}]})
            
            if update_payload["custom_fields_values"]:
                if update_lead(lead['id'], update_payload):
                    logger.info("Сделка %s успешно обновлена в AmoCRM", lead['id'])
                else:
                    logger.error("Ошибка при обновлении сделки %s", lead['id'])
            else:
                logger.info("Сделка %s уже содержит все данные, обновление не требуется.", lead['id'])
        else:
            logger.error("Не удалось получить данные о токене %s", lead['token'])

@app.route('/webhook', methods=['POST'], strict_slashes=False)
def webhook():
    logger.info("Получен POST-запрос на /webhook")
    process_leads()
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def index():
    return "Сервис работает!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

import requests
import json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔹 AmoCRM данные (лучше хранить в переменных окружения)
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImM3YzI4ZmE0NWMwNmExODM5MTQyZTM1MDdlOTJjOTVkNjUxZDA5ZTAyNzdkZjc2ODRmZTkzNWFlMDg5ZjY4NWIxMjM4YWQyYmZhZjNhMzUxIn0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJjN2MyOGZhNDVjMDZhMTgzOTE0MmUzNTA3ZTkyYzk1ZDY1MWQwOWUwMjc3ZGY3Njg0ZmU5MzVhZTA4OWY2ODViMTIzOGFkMmJmYWYzYTM1MSIsImlhdCI6MTc0MzA2MjcxOCwibmJmIjoxNzQzMDYyNzE4LCJleHAiOjE5MDA4MDAwMDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiZmQzMTc5ZGQtMDhkNi00MmRkLWJlYWQtMGRmODEyY2U1NTYwIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Y3_fkHzktIMthQuKkXTbpTLcLd4BZH7962-UFozIKCC6YbjgxV_Lpm2z4gL-Qo11eegBK6AbEP3E-AWpaWuoE20lmlO3zeNZLVqvFumoHMf0gKK-abNCkIbV-rmD-kWACraJCupvCQD2_f7U1M0nVu_diXF0L8LW5fzOaH9EvPEZS7PCQ6ZcoqvIXRBkXJW4lLoH8BqP3bc5H1_hodTCejCE5a444BM0ltCGTr4kwEN6wnOcnAOHeL5VmjEIzUwfdP-i0BfWAwlRsuEGovCLOvIekHAivjAGLIOTx2nE5vVvikkGUNdMZx2c_KFmOOUSkVjVxYB5QsVRHYtANgSBCQ"
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
    print(f"Запрос к DexScreener: {url}")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Ответ от DexScreener: {data}")
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
            print("Нет данных в ключе 'pairs' или он пуст")
    else:
        print(f"Ошибка при запросе к DexScreener: {response.status_code}")
    return None

def get_leads_with_token_field():
    """Получаем сделки на этапе 'NEW Lead', где заполнено поле TOKEN_FIELD_ID."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    params = {"filter[statuses]": NEW_LEAD_STAGE_ID, "with": "custom_fields_values"}
    response = requests.get(url, headers=headers, params=params)
    
    # Вывод полного ответа для отладки
    try:
        data = response.json()
        print("Ответ от amoCRM:", data)
    except Exception as e:
        print("Ошибка при обработке JSON ответа:", e)
    
    if response.status_code == 200:
        leads = data.get("_embedded", {}).get("leads", [])
        print(f"Найдено сделок: {len(leads)}")
        filtered_leads = []
        
        for lead in leads:
            if lead.get("status_id") != NEW_LEAD_STAGE_ID:
                continue
            
            token_address = None
            existing_fields = {field["field_id"]: field["values"][0]["value"] for field in lead.get("custom_fields_values", [])}
            
            if TOKEN_FIELD_ID in existing_fields:
                token_address = existing_fields[TOKEN_FIELD_ID].replace("http://", "").replace("https://", "").strip()
            
            if token_address:
                filtered_leads.append({"id": lead["id"], "token": token_address, "existing_fields": existing_fields})
        print(f"Сделок с токеном: {len(filtered_leads)}")
        return filtered_leads
    else:
        print(f"Ошибка запроса к amoCRM: {response.status_code}")
    return []


def update_lead(lead_id, update_data):
    """Обновляем сделку в AmoCRM."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    print(f"Обновление сделки {lead_id} с данными: {update_data}")
    response = requests.patch(url, headers=headers, data=json.dumps(update_data))
    print(f"Ответ обновления сделки {lead_id}: {response.status_code} - {response.text}")
    return response.status_code == 200

def process_leads():
    """Обрабатываем сделки с токеном на этапе 'NEW Lead'."""
    leads = get_leads_with_token_field()
    if not leads:
        print("Сделки на этапе 'NEW Lead' с токенами не найдены.")
        return
    
    for lead in leads:
        print(f"Обрабатываем сделку {lead['id']} с токеном {lead['token']}")
        token_data = get_dexscreener_data(lead['token'])
        if token_data:
            update_payload = {"custom_fields_values": []}
            for key, value in token_data.items():
                field_id = FIELDS_MAPPING.get(key)
                if field_id and field_id not in lead['existing_fields']:
                    update_payload["custom_fields_values"].append({"field_id": field_id, "values": [{"value": str(value)}]})
            
            if update_payload["custom_fields_values"]:
                if update_lead(lead['id'], update_payload):
                    print(f"Сделка {lead['id']} успешно обновлена в AmoCRM")
                else:
                    print(f"Ошибка при обновлении сделки {lead['id']}")
            else:
                print(f"Сделка {lead['id']} уже содержит все данные, обновление не требуется.")
        else:
            print(f"Не удалось получить данные о токене {lead['token']}")

@app.route('/webhook', methods=['POST'], strict_slashes=False)
def webhook():
    print("Получен POST-запрос на /webhook")
    process_leads()
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def index():
    return "Сервис работает!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

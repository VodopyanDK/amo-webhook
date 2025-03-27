from flask import Flask, request
import requests
import json
from datetime import datetime
import os

# 🔹 Создаём Flask-приложение
app = Flask(__name__)

@app.route("/")
def home():
    return "Webhook сервис работает!", 200

@app.route("/run", methods=["POST"])
def run_script():
    print("Получен запрос:", request.method, request.headers, request.data)
    process_leads()
    return {"status": "success", "message": "Процесс запущен"}, 200

# 🔹 AmoCRM данные
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImYxNTYyOTVlZmYzYjI4ZjlmMjE4YTYxZmRjMjliMDMzNmZiOTJmZjJmOWNjNWQxYzI0MDNiMzRlYTI3YzVjZjRlMWUyZjBhOTgwM2VmZjM5In0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJmMTU2Mjk1ZWZmM2IyOGY5ZjIxOGE2MWZkYzI5YjAzMzZmYjkyZmYyZjljYzVkMWMyNDAzYjM0ZWEyN2M1Y2Y0ZTFlMmYwYTk4MDNlZmYzOSIsImlhdCI6MTc0MjM4NzU3NiwibmJmIjoxNzQyMzg3NTc2LCJleHAiOjE5MDAxMDg4MDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNjkxMjU4NzMtNzA4Zi00ODU5LWFkMTktNzYwZTFmMDdhOGNkIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Ff9ZBKREBg1iV-GnkoubiY_BS66jJSUFpuTVqNo620SrS6jO8dDZtXe5drm3u0EYKGp97xDhGtV-HajW1QCpT3veI7V6kWW_2I_CPA-NCsSpP59K1m0E5-9thBWxiDSUVicL9s0Os-67eEqdDHWrlkNZac-qZKUj6Un4almFfCD2jYSIZhqF4dWUVziEzTRHoK8jyJfPdjqaevp4k3nhpg3EyyEtVmD-Eb67GfSmYysQvlIos1_S_pLKEWf_6HfxNB1kO4jKXcfsLzXFcVT50zMNvTlqT7_wqCD2_2fIXXqlKbGMQq7NOC_m712HQtFdrPQr5alsHNeQ9nyRpFAdJA"  # Убери токен перед публикацией!
AMOCRM_DOMAIN = "https://arbitrajy.amocrm.ru"
TOKEN_FIELD_ID = 898037  
NEW_LEAD_STAGE_ID = 75086270  

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

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens/"

def get_dexscreener_data(token_address):
    url = f"{DEXSCREENER_API_URL}{token_address}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if "pairs" in data and data["pairs"]:
            pair = max(data["pairs"], key=lambda x: x["liquidity"].get("usd", 0))
            timestamp = pair["pairCreatedAt"] / 1000
            days_since_creation = (datetime.utcnow() - datetime.utcfromtimestamp(timestamp)).days
            return {
                "age": f"{days_since_creation} d",
                "chainId": pair["chainId"],
                "name": pair["baseToken"]["name"],
                "symbol": pair["baseToken"]["symbol"],
                "marketCap": pair.get("marketCap", "N/A"),
                "liquidity": pair["liquidity"].get("usd", 0),
                "volume": pair["volume"].get("h24", 0)
            }
    return None

def get_leads_with_token_field():
    url = f"{AMOCRM_DOMAIN}/api/v4/leads"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    params = {"filter[statuses]": NEW_LEAD_STAGE_ID, "with": "custom_fields_values"}
    response = requests.get(url, headers=headers, params=params)
    
    # Добавляем вывод для отладки
    print("Ответ AmoCRM:", response.json())
    
    if response.status_code == 200:
        leads = response.json().get("_embedded", {}).get("leads", [])
        return [
            {"id": lead["id"], "token": lead["custom_fields_values"][0]["values"][0]["value"]}
            for lead in leads if lead.get("custom_fields_values")
        ]
    return []

def update_lead(lead_id, update_data):
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}", "Content-Type": "application/json"}
    response = requests.patch(url, headers=headers, data=json.dumps(update_data))
    return response.status_code == 200

def process_leads():
    leads = get_leads_with_token_field()
    print("Найдено сделок:", leads)
    if not leads:
        print("❌ Сделки на этапе 'NEW Lead' с токенами не найдены.")
        return
    for lead in leads:
        print(f"✅ Обрабатываем сделку {lead['id']} с токеном {lead['token']}")
        token_data = get_dexscreener_data(lead["token"])
        if token_data:
            update_payload = {
                "custom_fields_values": [
                    {"field_id": FIELDS_MAPPING[key], "values": [{"value": str(value)}]}
                    for key, value in token_data.items() if key in FIELDS_MAPPING
                ]
            }
            if update_lead(lead["id"], update_payload):
                print(f"Сделка {lead['id']} обновлена успешно.")
            else:
                print(f"Ошибка обновления сделки {lead['id']}.")

# Запускаем сервер Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

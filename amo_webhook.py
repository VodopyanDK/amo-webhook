from flask import Flask, request
import requests
import json
from datetime import datetime
import os

app = Flask(__name__)

# 🔹 AmoCRM данные
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImYxNTYyOTVlZmYzYjI4ZjlmMjE4YTYxZmRjMjliMDMzNmZiOTJmZjJmOWNjNWQxYzI0MDNiMzRlYTI3YzVjZjRlMWUyZjBhOTgwM2VmZjM5In0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJmMTU2Mjk1ZWZmM2IyOGY5ZjIxOGE2MWZkYzI5YjAzMzZmYjkyZmYyZjljYzVkMWMyNDAzYjM0ZWEyN2M1Y2Y0ZTFlMmYwYTk4MDNlZmYzOSIsImlhdCI6MTc0MjM4NzU3NiwibmJmIjoxNzQyMzg3NTc2LCJleHAiOjE5MDAxMDg4MDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNjkxMjU4NzMtNzA4Zi00ODU5LWFkMTktNzYwZTFmMDdhOGNkIiwiYXBpX2RvbWFpbiI6ImFwaS1pLmFtb2NybS5ydSJ9.Ff9ZBKREBg1iV-GnkoubiY_BS66jJSUFpuTVqNo620SrS6jO8dDZtXe5drm3u0EYKGp97xDhGtV-HajW1QCpT3veI7V6kWW_2I_CPA-NCsSpP59K1m0E5-9thBWxiDSUVicL9s0Os-67eEqdDHWrlkNZac-qZKUj6Un4almFfCD2jYSIZhqF4dWUVziEzTRHoK8jyJfPdjqaevp4k3nhpg3EyyEtVmD-Eb67GfSmYysQvlIos1_S_pLKEWf_6HfxNB1kO4jKXcfsLzXFcVT50zMNvTlqT7_wqCD2_2fIXXqlKbGMQq7NOC_m712HQtFdrPQr5alsHNeQ9nyRpFAdJA"  # Убери токен перед публикацией!
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
    response = requests.get(url)
    
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
    return None

def get_leads_with_token_field():
    """Получаем сделки, находящиеся ТОЛЬКО на этапе 'NEW Lead', где заполнено поле TOKEN_FIELD_ID."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    params = {"filter[statuses]": NEW_LEAD_STAGE_ID, "with": "custom_fields_values"}  # Жесткая фильтрация по статусу
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        leads = response.json().get("_embedded", {}).get("leads", [])
        filtered_leads = []
        
        for lead in leads:
            if lead.get("status_id") != NEW_LEAD_STAGE_ID:
                continue  # Пропускаем сделки не из этапа "NEW Lead"
            
            token_address = None
            existing_fields = {field["field_id"]: field["values"][0]["value"] 
                               for field in lead.get("custom_fields_values", [])}
            
            if TOKEN_FIELD_ID in existing_fields:
                token_address = existing_fields[TOKEN_FIELD_ID].replace("http://", "").replace("https://", "").strip()
            
            if token_address:
                filtered_leads.append({
                    "id": lead["id"],
                    "token": token_address,
                    "existing_fields": existing_fields
                })
        return filtered_leads
    return []

def update_lead(lead_id, update_data):
    """Обновляем сделку в AmoCRM."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, headers=headers, data=json.dumps(update_data))
    print(f"🔹 Обновление сделки {lead_id}: {response.status_code}", response.text, flush=True)
    return response.status_code == 200

def process_leads():
    """Обрабатываем только сделки, находящиеся на этапе 'NEW Lead' и содержащие токен."""
    leads = get_leads_with_token_field()
    print("Найдено сделок:", leads, flush=True)
    if not leads:
        print("❌ Сделки на этапе 'NEW Lead' с токенами не найдены.", flush=True)
        return
    
    for lead in leads:
        print(f"✅ Обрабатываем сделку {lead['id']} с токеном {lead['token']}", flush=True)
        token_data = get_dexscreener_data(lead['token'])
        if token_data:
            print("Данные от DexScreener:", token_data, flush=True)
            update_payload = {"custom_fields_values": []}
            for key, value in token_data.items():
                field_id = FIELDS_MAPPING.get(key)
                if field_id and field_id not in lead['existing_fields']:
                    update_payload["custom_fields_values"].append({
                        "field_id": field_id,
                        "values": [{"value": str(value)}]
                    })
            
            if update_payload["custom_fields_values"]:
                if update_lead(lead['id'], update_payload):
                    print(f"✅ Сделка {lead['id']} успешно обновлена в AmoCRM", flush=True)
                else:
                    print(f"❌ Ошибка при обновлении сделки {lead['id']}", flush=True)
            else:
                print(f"ℹ️ Сделка {lead['id']} уже содержит все данные, обновление не требуется.", flush=True)
        else:
            print(f"❌ Не удалось получить данные о токене {lead['token']}", flush=True)

@app.route("/")
def home():
    return "Webhook сервис работает!", 200

@app.route("/run", methods=["POST"])
def run_script():
    print("Получен запрос:", request.method, request.headers, request.data, flush=True)
    process_leads()
    return {"status": "success", "message": "Процесс запущен"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

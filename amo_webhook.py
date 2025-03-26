#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
import json
from datetime import datetime

# 🔹 AmoCRM данные
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImYxNTYyOTVlZmYzYjI4ZjlmMjE4YTYxZmRjMjliMDMzNmZiOTJmZjJmOWNjNWQxYzI0MDNiMzRlYTI3YzVjZjRlMWUyZjBhOTgwM2VmZjM5In0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJmMTU2Mjk1ZWZmM2IyOGY5ZjIxOGE2MWZkYzI5YjAzMzZmYjkyZmYyZjljYzVkMWMyNDAzYjM0ZWEyN2M1Y2Y0ZTFlMmYwYTk4MDNlZmYzOSIsImlhdCI6MTc0MjM4NzU3NiwibmJmIjoxNzQyMzg3NTc2LCJleHAiOjE5MDAxMDg4MDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNjkxMjU4NzMtNzA4Zi00ODU5LWFkMTktNzYwZTFmMDdhOGNkIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Ff9ZBKREBg1iV-GnkoubiY_BS66jJSUFpuTVqNo620SrS6jO8dDZtXe5drm3u0EYKGp97xDhGtV-HajW1QCpT3veI7V6kWW_2I_CPA-NCsSpP59K1m0E5-9thBWxiDSUVicL9s0Os-67eEqdDHWrlkNZac-qZKUj6Un4almFfCD2jYSIZhqF4dWUVziEzTRHoK8jyJfPdjqaevp4k3nhpg3EyyEtVmD-Eb67GfSmYysQvlIos1_S_pLKEWf_6HfxNB1kO4jKXcfsLzXFcVT50zMNvTlqT7_wqCD2_2fIXXqlKbGMQq7NOC_m712HQtFdrPQr5alsHNeQ9nyRpFAdJA"  # Убери токен перед публикацией!
AMOCRM_DOMAIN = "https://arbitrajy.amocrm.ru"
TOKEN_FIELD_ID = 898037  # ID поля, где хранится токен
LEAD_ID = 33794059  # ID тестовой сделки

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
            # Выбираем торговую пару с наибольшей ликвидностью
            pair = max(data["pairs"], key=lambda x: x["liquidity"].get("usd", 0))
            
            timestamp = pair["pairCreatedAt"] / 1000  # Время в секундах
            pair_created_date = datetime.utcfromtimestamp(timestamp)
            days_since_creation = (datetime.utcnow() - pair_created_date).days
            
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

def get_lead_details(lead_id):
    """Получаем информацию о сделке из AmoCRM."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def update_lead(lead_id, update_data):
    """Обновляем сделку в AmoCRM."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, headers=headers, data=json.dumps(update_data))
    print("🔹 AmoCRM Response:", response.status_code, response.text)
    return response.status_code == 200

# 🔹 1. Получаем текущую сделку
lead_data = get_lead_details(LEAD_ID)
if not lead_data:
    print("❌ Ошибка: Не удалось получить данные сделки")
else:
    custom_fields = lead_data.get("custom_fields_values", [])
    token_address = None
    for field in custom_fields:
        if field["field_id"] == TOKEN_FIELD_ID:
            token_address = field["values"][0]["value"].replace("http://", "").replace("https://", "").strip()
            break
    
    if not token_address:
        print("❌ Ошибка: Токен не найден в пользовательском поле")
    else:
        print(f"✅ Токен найден: {token_address}")
        token_data = get_dexscreener_data(token_address)
        if token_data:
            print("✅ Данные о токене получены:", token_data)
            update_payload = {
                "custom_fields_values": [
                    {"field_id": FIELDS_MAPPING[key], "values": [{"value": str(value)}]}
                    for key, value in token_data.items() if key in FIELDS_MAPPING
                ]
            }
            if update_lead(LEAD_ID, update_payload):
                print("✅ Сделка успешно обновлена в AmoCRM")
            else:
                print("❌ Ошибка при обновлении сделки")
        else:
            print("❌ Ошибка: Не удалось получить данные о токене")


from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# 🔹 AmoCRM данные
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImYxNTYyOTVlZmYzYjI4ZjlmMjE4YTYxZmRjMjliMDMzNmZiOTJmZjJmOWNjNWQxYzI0MDNiMzRlYTI3YzVjZjRlMWUyZjBhOTgwM2VmZjM5In0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJmMTU2Mjk1ZWZmM2IyOGY5ZjIxOGE2MWZkYzI5YjAzMzZmYjkyZmYyZjljYzVkMWMyNDAzYjM0ZWEyN2M1Y2Y0ZTFlMmYwYTk4MDNlZmYzOSIsImlhdCI6MTc0MjM4NzU3NiwibmJmIjoxNzQyMzg3NTc2LCJleHAiOjE5MDAxMDg4MDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNjkxMjU4NzMtNzA4Zi00ODU5LWFkMTktNzYwZTFmMDdhOGNkIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Ff9ZBKREBg1iV-GnkoubiY_BS66jJSUFpuTVqNo620SrS6jO8dDZtXe5drm3u0EYKGp97xDhGtV-HajW1QCpT3veI7V6kWW_2I_CPA-NCsSpP59K1m0E5-9thBWxiDSUVicL9s0Os-67eEqdDHWrlkNZac-qZKUj6Un4almFfCD2jYSIZhqF4dWUVziEzTRHoK8jyJfPdjqaevp4k3nhpg3EyyEtVmD-Eb67GfSmYysQvlIos1_S_pLKEWf_6HfxNB1kO4jKXcfsLzXFcVT50zMNvTlqT7_wqCD2_2fIXXqlKbGMQq7NOC_m712HQtFdrPQr5alsHNeQ9nyRpFAdJA" AMOCRM_DOMAIN = "https://arbitrajy.amocrm.ru"
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

def get_lead_data(lead_id):
    """Получаем данные сделки (включая токен)."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        lead = response.json()
        token_address = None
        existing_fields = {field["field_id"]: field["values"][0]["value"] for field in lead.get("custom_fields_values", [])}
        
        if TOKEN_FIELD_ID in existing_fields:
            token_address = existing_fields[TOKEN_FIELD_ID].replace("http://", "").replace("https://", "").strip()
        
        return {"id": lead["id"], "token": token_address, "existing_fields": existing_fields} if token_address else None
    return None

def update_lead(lead_id, update_data):
    """Обновляем сделку в AmoCRM."""
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, headers=headers, data=json.dumps(update_data))
    return response.status_code == 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    lead_id = data.get("lead_id")

    if not lead_id:
        return jsonify({"error": "No lead_id provided"}), 400

    lead = get_lead_data(lead_id)
    if not lead:
        return jsonify({"error": "Lead not found or missing token"}), 404

    token_data = get_dexscreener_data(lead["token"])
    if not token_data:
        return jsonify({"error": "Failed to get token data"}), 500

    update_payload = {
        "custom_fields_values": [
            {"field_id": FIELDS_MAPPING[key], "values": [{"value": str(value)}]}
            for key, value in token_data.items() if key in FIELDS_MAPPING and FIELDS_MAPPING[key] not in lead["existing_fields"]
        ]
    }

    if not update_payload["custom_fields_values"]:
        return jsonify({"message": "No new data to update"}), 200

    if update_lead(lead_id, update_payload):
        return jsonify({"success": "Lead updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update lead"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

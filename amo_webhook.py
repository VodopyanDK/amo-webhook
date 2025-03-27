import os
import re
import json
import logging
import requests
from flask import Flask, request
from datetime import datetime

# Настройка логирования для вывода в консоль
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# === Твои настройки AmoCRM ===
AMOCRM_DOMAIN = "https://arbitrajy.amocrm.ru"  # URL твоего AmoCRM аккаунта
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImYxNTYyOTVlZmYzYjI4ZjlmMjE4YTYxZmRjMjliMDMzNmZiOTJmZjJmOWNjNWQxYzI0MDNiMzRlYTI3YzVjZjRlMWUyZjBhOTgwM2VmZjM5In0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJmMTU2Mjk1ZWZmM2IyOGY5ZjIxOGE2MWZkYzI5YjAzMzZmYjkyZmYyZjljYzVkMWMyNDAzYjM0ZWEyN2M1Y2Y0ZTFlMmYwYTk4MDNlZmYzOSIsImlhdCI6MTc0MjM4NzU3NiwibmJmIjoxNzQyMzg3NTc2LCJleHAiOjE5MDAxMDg4MDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiNjkxMjU4NzMtNzA4Zi00ODU5LWFkMTktNzYwZTFmMDdhOGNkIiwiYXBpX2RvbWFpbiI6ImFwaS1pLmFtb2NybS5ydSJ9.Ff9ZBKREBg1iV-GnkoubiY_BS66jJSUFpuTVqNo620SrS6jO8dDZtXe5drm3u0EYKGp97xDhGtV-HajW1QCpT3veI7V6kWW_2I_CPA-NCsSpP59K1m0E5-9thBWxiDSUVicL9s0Os-67eEqdDHWrlkNZac-qZKUj6Un4almFfCD2jYSIZhqF4dWUVziEzTRHoK8jyJfPdjqaevp4k3nhpg3EyyEtVmD-Eb67GfSmYysQvlIos1_S_pLKEWf_6HfxNB1kO4jKXcfsLzXFcVT50zMNvTlqT7_wqCD2_2fIXXqlKbGMQq7NOC_m712HQtFdrPQr5alsHNeQ9nyRpFAdJA"
NEW_LEAD_STAGE_ID = '75086270'   # ID этапа "NEW Lead" (как строка)
TOKEN_FIELD_ID = '898037'        # ID поля, где хранится токен

# === Твои настройки кастомных полей, куда будут записываться данные с DexScreener ===
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

# === Настройки DexScreener ===
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens/"

def get_token_data_from_dex(token: str) -> dict:
    """
    Получаем информацию о токене с DexScreener.
    Запрос выполняется к поисковому эндпоинту, после чего выбирается первая пара.
    """
    token = token.strip()
    if not token:
        return None
    try:
        search_url = f"{DEXSCREENER_API_URL}{token}"
        logging.info(f"Запрос к DexScreener: {search_url}")
        resp = requests.get(search_url, timeout=10)
        logging.info(f"DexScreener response: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            return None
        data = resp.json()
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
                "twitter": twitter_link,
            }
    except Exception as e:
        logging.exception(f"Ошибка получения данных DexScreener для токена {token}: {e}")
    return None

def add_note_to_lead(lead_id: str, note_text: str):
    """
    Добавляет заметку к сделке в AmoCRM с указанным текстом.
    """
    url = f"{AMOCRM_DOMAIN}/api/v4/leads/{lead_id}/notes"
    payload = [{
        "note_type": "common",
        "params": {"text": note_text}
    }]
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        logging.info(f"Добавление заметки в сделку {lead_id}: {note_text}")
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if 200 <= resp.status_code < 300:
            logging.info(f"Заметка успешно добавлена в сделку {lead_id}.")
        else:
            logging.error(f"Ошибка при добавлении заметки в сделку {lead_id}: {resp.status_code} {resp.text}")
    except Exception as e:
        logging.exception(f"Исключение при добавлении заметки в сделку {lead_id}: {e}")

def get_leads_with_token_field():
    """
    Из AmoCRM выбираем сделки, находящиеся на этапе 'NEW Lead' (75086270)
    и где заполнено кастомное поле с токеном (ID 898037).
    """
    url = f"{AMOCRM_DOMAIN}/api/v4/leads"
    headers = {"Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}"}
    params = {"filter[statuses]": NEW_LEAD_STAGE_ID, "with": "custom_fields_values"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        leads = response.json().get("_embedded", {}).get("leads", [])
        filtered_leads = []
        for lead in leads:
            if str(lead.get("status_id")) != NEW_LEAD_STAGE_ID:
                continue
            token_address = None
            # Собираем существующие кастомные поля
            existing_fields = {str(field["field_id"]): field["values"][0]["value"]
                               for field in lead.get("custom_fields_values", [])}
            if TOKEN_FIELD_ID in existing_fields:
                token_address = existing_fields[TOKEN_FIELD_ID]
                # Удаляем http:// и https://, если они есть
                token_address = token_address.replace("http://", "").replace("https://", "").strip()
            if token_address:
                filtered_leads.append({
                    "id": lead["id"],
                    "token": token_address,
                    "existing_fields": existing_fields
                })
        return filtered_leads
    return []

def process_leads():
    """
    Обрабатывает сделки: для каждой сделки с этапом 'NEW Lead' и токеном
    запрашивает данные с DexScreener и добавляет заметку в AmoCRM.
    """
    leads = get_leads_with_token_field()
    logging.info(f"Найдено сделок: {leads}")
    if not leads:
        logging.info("❌ Сделки на этапе 'NEW Lead' с токенами не найдены.")
        return
    for lead in leads:
        logging.info(f"✅ Обрабатываем сделку {lead['id']} с токеном {lead['token']}")
        token_data = get_token_data_from_dex(lead['token'])
        if token_data:
            token_name = token_data.get("name") or ""
            token_symbol = token_data.get("symbol") or ""
            price_usd = token_data.get("price_usd")
            price_text = str(price_usd) if price_usd is not None else "N/A"
            note_text = f"DexScreener info: Token {token_name} ({token_symbol}) price = {price_text} USD."
            add_note_to_lead(lead['id'], note_text)
        else:
            logging.info(f"❌ Не удалось получить данные о токене {lead['token']}")

@app.route('/run', methods=['POST'])
def amocrm_webhook():
    """
    Обработчик вебхука от amoCRM. При получении POST-запроса (form-urlencoded)
    извлекает сделки, проверяет стадию и кастомное поле, затем запускает process_leads().
    """
    if not request.form:
        logging.warning("Получен POST-запрос без form data.")
        return "Bad Request: no form data", 400
    try:
        raw_data = request.get_data(as_text=True)
        logging.info(f"Получены данные вебхука: {raw_data}")
    except Exception as e:
        logging.error(f"Ошибка чтения данных вебхука: {e}")
    form = request.form
    leads_to_process = []
    # Определяем тип события: изменение стадии (status) или добавление (add)
    event_type = None
    if any(key.startswith('leads[status]') for key in form.keys()):
        event_type = 'status'
    elif any(key.startswith('leads[add]') for key in form.keys()):
        event_type = 'add'
    else:
        logging.info("Данные вебхука не содержат leads[status] или leads[add].")
        return "No leads data", 200

    # Собираем ID сделок с этапом "NEW Lead" (75086270)
    if event_type == 'status':
        indices = set()
        for key in form.keys():
            match = re.match(r'leads\[status\]\[(\d+)\]\[id\]', key)
            if match:
                indices.add(match.group(1))
        for idx in indices:
            new_status = form.get(f"leads[status][{idx}][status_id]")
            if new_status == '75086270':
                lead_id = form.get(f"leads[status][{idx}][id]")
                if lead_id:
                    leads_to_process.append((lead_id, idx))
    elif event_type == 'add':
        indices = set()
        for key in form.keys():
            match = re.match(r'leads\[add\]\[(\d+)\]\[id\]', key)
            if match:
                indices.add(match.group(1))
        for idx in indices:
            status_id = form.get(f"leads[add][{idx}][status_id]")
            if status_id == '75086270':
                lead_id = form.get(f"leads[add][{idx}][id]")
                if lead_id:
                    leads_to_process.append((lead_id, idx))
    if not leads_to_process:
        logging.info("Нет сделок в стадии 'NEW Lead' для обработки.")
        return "No relevant leads", 200

    for lead_id, idx in leads_to_process:
        logging.info(f"Обработка сделки {lead_id}")
        token_value = None
        field_index = 0
        while True:
            field_id = form.get(f"leads[{event_type}][{idx}][custom_fields][{field_index}][id]")
            if not field_id:
                break
            if field_id == '898037':
                token_value = form.get(f"leads[{event_type}][{idx}][custom_fields][{field_index}][values][0]")
                break
            field_index += 1
        if not token_value:
            logging.info(f"Для сделки {lead_id} не найден токен (поле 898037). Пропуск.")
            continue
        logging.info(f"Найден токен для сделки {lead_id}: {token_value}")
        token_data = get_token_data_from_dex(token_value)
        if not token_data:
            logging.info(f"DexScreener не вернул данные для токена {token_value}.")
            continue
        token_name = token_data.get("name") or ""
        token_symbol = token_data.get("symbol") or ""
        price_usd = token_data.get("price_usd")
        price_text = str(price_usd) if price_usd is not None else "N/A"
        note_text = f"DexScreener info: Token {token_name} ({token_symbol}) price = {price_text} USD."
        add_note_to_lead(lead_id, note_text)
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Webhook listener is running.", 200

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

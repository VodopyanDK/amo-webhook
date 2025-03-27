import os
import json
import requests
import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# ==================== Ваши настройки ====================
AMOCRM_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImM3YzI4ZmE0NWMwNmExODM5MTQyZTM1MDdlOTJjOTVkNjUxZDA5ZTAyNzdkZjc2ODRmZTkzNWFlMDg5ZjY4NWIxMjM4YWQyYmZhZjNhMzUxIn0.eyJhdWQiOiJkMTM3YTAzYi1lMTczLTRkMWYtOTQxMi0xMjExZDE0YmI1MWQiLCJqdGkiOiJjN2MyOGZhNDVjMDZhMTgzOTE0MmUzNTA3ZTkyYzk1ZDY1MWQwOWUwMjc3ZGY3Njg0ZmU5MzVhZTA4OWY2ODViMTIzOGFkMmJmYWYzYTM1MSIsImlhdCI6MTc0MzA2MjcxOCwibmJmIjoxNzQzMDYyNzE4LCJleHAiOjE5MDA4MDAwMDAsInN1YiI6IjEyMjYwMzA2IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjMyMjk4NTEwLCJiYXNlX2RvbWFpbiI6ImFtb2NybS5ydSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJjcm0iLCJmaWxlcyIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiLCJwdXNoX25vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiZmQzMTc5ZGQtMDhkNi00MmRkLWJlYWQtMGRmODEyY2U1NTYwIiwiYXBpX2RvbWFpbiI6ImFwaS1iLmFtb2NybS5ydSJ9.Y3_fkHzktIMthQuKkXTbpTLcLd4BZH7962-UFozIKCC6YbjgxV_Lpm2z4gL-Qo11eegBK6AbEP3E-AWpaWuoE20lmlO3zeNZLVqvFumoHMf0gKK-abNCkIbV-rmD-kWACraJCupvCQD2_f7U1M0nVu_diXF0L8LW5fzOaH9EvPEZS7PCQ6ZcoqvIXRBkXJW4lLoH8BqP3bc5H1_hodTCejCE5a444BM0ltCGTr4kwEN6wnOcnAOHeL5VmjEIzUwfdP-i0BfWAwlRsuEGovCLOvIekHAivjAGLIOTx2nE5vVvikkGUNdMZx2c_KFmOOUSkVjVxYB5QsVRHYtANgSBCQ"  # Лучше вынести в переменные окружения
AMOCRM_DOMAIN = "arbitrajy.amocrm.ru"

NEW_LEAD_STAGE_ID = 75086270
PIPELINE_ID = 9370934

FIELD_CONTRACT_ADDRESS = 898037
FIELD_COMMUNITY_ID     = 898655
FIELD_FOLLOWERS_ID     = 897815

# Google Sheets
GOOGLE_SHEET_ID = "1P_WErNkDV-Rlvmx0p4EJwSwbSBxDQPc4UGy4Xt-VOSs"
SHEET_NAME = "Telegram"

# Путь к JSON-файлу ключей (можно заместо файла использовать Render Secret File)
JSON_KEYFILE = "arbitrajy-b2d72dcc490a.json"

# Авторизация в Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, scope)
client = gspread.authorize(creds)

# ----------------- Ваши функции -----------------
def get_leads_in_stage(pipeline_id, stage_id, limit=250):
    ...
    # (точно так же, как у вас в коде)

def get_values_from_sheet(contract_address):
    ...
    # (точно так же)

def get_custom_field_value(lead_data, field_id):
    ...
    # (точно так же)

def update_lead(lead_id, kols_value, callers_value):
    ...
    # (точно так же)

def run_main_logic():
    """
    Обёртка с вашей главной логикой,
    чтобы мы могли вызывать её из Flask-маршрута.
    """
    leads = get_leads_in_stage(PIPELINE_ID, NEW_LEAD_STAGE_ID)
    print(f"Всего найдено сделок в стадии {NEW_LEAD_STAGE_ID}: {len(leads)}")

    for lead in leads:
        lead_id = lead["id"]
        contract_address = get_custom_field_value(lead, FIELD_CONTRACT_ADDRESS)
        if not contract_address:
            print(f"Сделка #{lead_id} — нет Contract Address, пропускаем.")
            continue

        kols_value, callers_value = get_values_from_sheet(contract_address)
        if not (kols_value or callers_value):
            print(f"   Нет совпадений в таблице для {contract_address}")
            continue
        
        existing_kols = get_custom_field_value(lead, FIELD_COMMUNITY_ID)
        existing_callers = get_custom_field_value(lead, FIELD_FOLLOWERS_ID)
        
        if existing_kols:
            kols_value = None
        if existing_callers:
            callers_value = None
        
        if kols_value or callers_value:
            update_lead(lead_id, kols_value, callers_value)
        else:
            print(f"   Все необходимые поля уже были заполнены, пропускаем сделку #{lead_id}")


# ----------------- Flask-маршруты -----------------
@app.route("/")
def index():
    return "Hello from Render! Use /run-script to run the logic."

@app.route("/run-script", methods=["GET", "POST"])
def run_script():
    """
    При вызове GET/POST на этот маршрут будет запускаться ваш скрипт.
    """
    run_main_logic()
    return "OK, скрипт отработал."

# Запуск локально (для теста)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

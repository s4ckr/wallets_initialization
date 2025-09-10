import os 

from solana.rpc.async_api import AsyncClient

from aiogram import Bot, Dispatcher

API_URL = "https://mainnet.helius-rpc.com/?api-key=456ca87b-9004-4270-971a-5a9838c6f925"

async_client = AsyncClient(API_URL)

# ---------------- Telegram setup ----------------
API_TOKEN = ""
CHAT_ID =  

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

CEXS_LIST = ["Gate"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRE_JSON =  os.path.join(BASE_DIR, r"pre_balance.json")

MEXC_COLD_CSV = os.path.join(BASE_DIR, r"mexc_cold.csv")

GATE_COLD_CSV = os.path.join(BASE_DIR, r"gate_cold.csv")

FUNDS_JSON = os.path.join(BASE_DIR, r"fundings.json")

MEXC_WARM_CSV = os.path.join(BASE_DIR, r"mexc_warm.csv")

GATE_WARM_CSV = os.path.join(BASE_DIR, r"gate_warm.csv")

CEXS = os.path.join(BASE_DIR, r"cexs.json")

TRANSIT_JSON = os.path.join(BASE_DIR, r"transit.json")
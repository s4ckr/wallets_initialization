# ========== IMPORTS ==========
import os 
from solana.rpc.async_api import AsyncClient
from aiogram import Bot, Dispatcher

# ---------------- Telegram setup ----------------
API_TOKEN =            #Telegram bot token
CHAT_ID =                                                   #Chat id 

# ---------------- Main setup ----------------
HELIUS_API_KEY =                 #Helius API KEY
API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"     #Helius API URL
CEXS_LIST = ["Gate", "MEXC"]                                                     #list of cexs you'd like to use (now "Gate" and "MEXC")

MIN_SLEEP_SECONDS = 600
MAX_SLEEP_SECONDS = 1800

MIN_FUND_AMOUNT = 0.1
MAX_FUND_AMOUNT = 0.5

BALANCE_THRESHOLD =  0.00025

# ========== DONT TOUCH ==========
async_client = AsyncClient(API_URL)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRE_JSON =  os.path.join(BASE_DIR, r"pre_balance.json")
MEXC_COLD_CSV = os.path.join(BASE_DIR, r"mexc_cold.csv")
GATE_COLD_CSV = os.path.join(BASE_DIR, r"gate_cold.csv")
FUNDS_JSON = os.path.join(BASE_DIR, r"fundings.json")
MEXC_WARM_CSV = os.path.join(BASE_DIR, r"mexc_warm.csv")
GATE_WARM_CSV = os.path.join(BASE_DIR, r"gate_warm.csv")
CEXS = os.path.join(BASE_DIR, r"cexs.json")



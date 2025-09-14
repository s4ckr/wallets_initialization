# ========== IMPORTS ==========
import os 
from solana.rpc.async_api import AsyncClient
from aiogram import Bot, Dispatcher

# ---------------- Telegram setup ----------------
API_TOKEN =             #Telegram bot token
CHAT_ID =                                                   #Chat id 

# ---------------- Main setup ----------------
HELIUS_API_KEY =                  #Helius API KEY
API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"    #Helius API URL
CEXS_LIST = ["Gate"]                                                     #list of cexs you'd like to use (now "Gate" and "MEXC")

MIN_SLEEP_SECONDS = 60
MAX_SLEEP_SECONDS = 90

MIN_FUND_AMOUNT = 0.1
MAX_FUND_AMOUNT = 0.5

BALANCE_THRESHOLD =  0.00025

ACTIVITY_THRESHOLD = 10800

MEXC_API_KEY = ""
MEXC_API_SECRET = ""
MEXC_PK = ""

GATE_API_KEY = 
GATE_API_SECRET = 
GATE_PK = 

# ========== DONT TOUCH ==========
async_client = AsyncClient(API_URL)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRE_JSON =  os.path.join(BASE_DIR, r"pre_balance.json")
MEXC_CSV = os.path.join(BASE_DIR, r"mexc_wl.csv")
GATE_CSV = os.path.join(BASE_DIR, r"gate_wl.csv")
COLD_CSV = os.path.join(BASE_DIR, r"cold.csv")
WARM_CSV = os.path.join(BASE_DIR, r"warm.csv")
BONDED_CSV = os.path.join(BASE_DIR, r"bonded.csv")

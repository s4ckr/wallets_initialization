# ========== IMPORTS ==========
import os 
from solana.rpc.async_api import AsyncClient
from aiogram import Bot, Dispatcher

# ---------------- Telegram setup ----------------
API_TOKEN = "8220323380:AAELI7J0YuClbcilTllamshWBeyVquabvRg"                     #Telegram bot token
CHAT_ID = -4817641464                                                             #Chat id 

# ---------------- Main setup ----------------
HELIUS_API_KEY = "456ca87b-9004-4270-971a-5a9838c6f925"                          #Helius API KEY
API_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"            #Helius API URL
CEXS_LIST = ["Gate", "MEXC"]                                                     #list of cexs you'd like to use (now "Gate" and "MEXC")

MIN_SLEEP_SECONDS = 20
MAX_SLEEP_SECONDS = 40

MIN_FUND_AMOUNT = 0.1
MAX_FUND_AMOUNT = 0.5

BALANCE_THRESHOLD =  0.0005

ACTIVITY_THRESHOLD = 10800

MEXC_API_KEY = "mx0vgl7lqnoDSSTWq5"
MEXC_API_SECRET = "2099008972474768a7044afee8aee02b"
MEXC_PK = "ExyVZ6jEgBbvnSWnCYQop62J8VcQ2J2467th4HEQPN5a"

GATE_API_KEY = "c450124770b3283d67593300ef19af5c"
GATE_API_SECRET = "69f6446adacb485b5c2994953270716b0dfed2c1ba282fd988c7a015f9067097"
GATE_PK = "4bEwapT1xH6oZcbWR6CXy3NeX7FiHsdy8rAcy7v7zTUF"

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
NEW_CSV = os.path.join(BASE_DIR, r"new_wl.csv")
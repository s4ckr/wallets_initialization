import time
import hmac
import hashlib
import requests
import json
import ccxt
from config import MEXC_API_KEY, MEXC_API_SECRET, MEXC_PK, GATE_API_KEY, GATE_API_SECRET, GATE_PK

def mexc_withdraw(amount, address):
    exchange = ccxt.mexc({
        'apiKey': MEXC_API_KEY,
        'secret': MEXC_API_SECRET
    })

    currency = 'SOL' 
    amount = amount 
    address = address
    tag = None
    network = 'SOL' 

    try:
        result = exchange.withdraw(currency, amount, address, tag, params={'network': network})
        print(result)
        return result
    except ccxt.NetworkError as e:
        print(f"Network error: {e}")
        return 
    except ccxt.ExchangeError as e:
        print(f"Exchange error: {e}")
        return "Insufficient balance"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return 

def gate_withdraw(amount, address):
    exchange = ccxt.gate({
        'apiKey': GATE_API_KEY,
        'secret': GATE_API_SECRET
    })

    currency = 'SOL'  
    amount = amount  
    address = address 
    tag = None
    network = 'SOL' 

    try:
        result = exchange.withdraw(currency, amount, address, tag, params={'network': network})
        
        return result
    except ccxt.NetworkError as e:
        print(f"Network error: {e}")
    except ccxt.ExchangeError as e:
        print(f"Exchange error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

async def get_cex_balance(cex):
    if cex == "MEXC":
        balance, _ = get_mexc_balance()
        return balance, MEXC_PK
            
    elif cex == "Gate":
        balance, _ = get_gate_balance()
        return balance, GATE_PK

BASE_URL = "https://api.mexc.com"

def sign(params: dict) -> dict:
    query = "&".join([f"{k}={params[k]}" for k in sorted(params)])
    signature = hmac.new(MEXC_API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature
    return params

# ---------------- Get deposit address ----------------
def get_deposit_address(coin="SOL", network="SOL"):
    url = f"{BASE_URL}/api/v3/capital/deposit/address"
    params = {"coin": coin, "netWork": network, "timestamp": int(time.time()*1000)}
    params = sign(params)
    headers = {"X-MEXC-APIKEY": MEXC_API_KEY}
    r = requests.get(url, params=params, headers=headers)
    return r.json()[0].get("address")

# ---------------- Get balance ----------------
def get_mexc_balance(coin="SOL"):
    url = f"{BASE_URL}/api/v3/account"
    params = {"timestamp": int(time.time()*1000)}
    params = sign(params)
    headers = {"X-MEXC-APIKEY": MEXC_API_KEY}
    r = requests.get(url, params=params, headers=headers)
    data = r.json()
    for asset in data.get("balances", []):
        if asset["asset"] == coin:
            return float(asset["free"]), float(asset["locked"])
    return 0.0, 0.0

def wait_for_increase_mexc(before_balance: float, timeout: int = 600):
    deadline = time.time() + timeout
    post_balance = before_balance

    while post_balance <= before_balance and time.time() < deadline:
        post_balance, locked = get_mexc_balance()
        if locked > 0:
            print("locked: ", locked)
        if post_balance > before_balance:
            return True
        time.sleep(10)
    return post_balance > before_balance

def wait_for_increase_gate(before_balance: float, timeout: int = 600):
    deadline = time.time() + timeout
    post_balance = before_balance

    while post_balance <= before_balance and time.time() < deadline:
        post_balance, locked = get_gate_balance()
        if locked > 0:
            print("locked: ", locked)
        if post_balance > before_balance:
            return True
        time.sleep(10)
    return post_balance > before_balance

def get_gate_balance(coin="SOL"):
    exchange = ccxt.gate({
        'apiKey': GATE_API_KEY,
        'secret': GATE_API_SECRET
    })
    fetched = exchange.fetch_balance({"type":"spot","settle":"sol"})

    balances = fetched["info"][0]
    if balances["currency"] == coin:
        free = balances["available"]
        locked = balances["locked"]
        return float(free), float(locked)
        

    return 0.0, 0.0

import csv
import os
import getpass
import asyncio
from typing import Optional, Tuple
from solders.keypair import Keypair
from encoding import encrypt_secret
from solana.rpc.core import RPCException

from config import COLD_CSV, GATE_CSV, MEXC_CSV, NEW_CSV
import json
import csv
import datetime
from zoneinfo import ZoneInfo
from solders.pubkey import Pubkey
from config import async_client

def get_ts():
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]  
    return ts

def _is_history_unavailable(e: Exception) -> bool:
    s = str(e).lower()
    return "-32019" in s or ("history" in s and "available" in s)

async def get_first_funding_tx(
    pubkey: str,
    *,
    tz: datetime.tzinfo = datetime.timezone.utc,
) -> tuple[Optional[str], Optional[str]]:
    retries = 3
    retry = 0

    while retry < retries:
        try:
            pk = Pubkey.from_string(pubkey)
            try:
                sigs = await async_client.get_signatures_for_address(
                pk, limit=1000, commitment="confirmed"
            )
            except Exception as e:
                if _is_history_unavailable(e):
                    return None, pubkey
                if retries > 0:
                    retries -= 1
                    continue
                return None, pubkey
            
            if not sigs.value:
                return None, None

            first = sigs.value[-1]  
            sig = first.signature

            bt = first.block_time

            tx = await async_client.get_transaction(
                sig,
                max_supported_transaction_version=0,
                commitment="finalized",
            )
            if tx.value:
                bt = tx.value.block_time
                if bt is None:
                    # 3) если и тут нет, берём slot и спрашиваем get_block_time
                    try:
                        slot = tx.value.slot
                        bt_resp = await async_client.get_block_time(slot, commitment="finalized")
                        bt = bt_resp.value
                    except Exception:
                        bt = None

            tz = ZoneInfo("Asia/Almaty")

            fund_datetime = (
                datetime.datetime.fromtimestamp(bt, tz=datetime.timezone.utc).astimezone(tz)
                if bt is not None else None
            )

            # Плательщик (fee payer) как правило первый аккаунт в сообщении
            funder_pk: Optional[str] = None

            try:
                if tx and tx.value:
                    msg = tx.value.transaction.transaction.message
                    funder_pk = str(msg.account_keys[0])
            except Exception:
                pass

            return fund_datetime, funder_pk
        except Exception as e:
            print(f"[{get_ts()}] | Exception: ", e)
            retry+=1

def generate_wallets(password, output, n=50):
    file_exists = os.path.isfile(output) and os.path.getsize(output) > 0

    with open(output, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        if not file_exists:
            writer.writerow(["sk","pk"])
        
        for _ in range(n): 
            kp = Keypair()
            sk = str(encrypt_secret(bytes(kp), password)).strip()
            pk = str(kp.pubkey()).strip()
            
            writer.writerow([sk,pk])

def generate_funds(n = 10, password = None):
    wallets = []

    if password is not None:
        for _ in range(n):
            kp = Keypair()
            wallets.append({"sk" : str(encrypt_secret(bytes(kp), password)), "pk" : str(kp.pubkey())})

        with open(COLD_CSV, "w") as f:
            json.dump(wallets, f, ensure_ascii=False, indent=4)

        return    
    
    print(f"[{get_ts()}] | No password")
    return
def password_buffer():
    retry = 0

    while retry < 3:
        password = getpass.getpass("Enter password: ")
        password_check = getpass.getpass("Confirm password: ")
        if password_check != password:
            print(f"[{get_ts()}] | Passwords does not match!")
            retry += 1
        else:
            print(f"[{get_ts()}] | Passwords match!")
            return password
    print(f"[{get_ts()}] | Too many retries, blocking.")
    return

if __name__ == "__main__":
    password = password_buffer()
    
    csv_type = input("Enter the type of csv you'd like to extend (MEXC, Gate) or enter f to recreate fundings file of new to add new wls: ")

    amount = int(input("Enter wallets amount: "))

    if csv_type == "MEXC":
        generate_wallets(password, n=amount, output=COLD_CSV)
    elif csv_type == "Gate":
        generate_wallets(password, n=amount, output=GATE_CSV)
    elif csv_type == "new":
        generate_wallets(password, n=amount, output=NEW_CSV)
    elif csv_type == "f":
        s = input("Are you sure you want to recreate fundings file? (y/n): ")
        if s == "y":
            generate_funds(amount, password)
        else: 
            print(f"[{get_ts()}] | no")

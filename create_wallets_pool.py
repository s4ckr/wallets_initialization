import csv
import os
import getpass
from solders.keypair import Keypair
from encoding import encrypt_secret

from config import MEXC_COLD_CSV, GATE_COLD_CSV, FUNDS_JSON
import json
import csv
import datetime
from solders.pubkey import Pubkey
from config import async_client

async def get_first_funding_tx(pubkey: str):
    sigs = await async_client.get_signatures_for_address(Pubkey.from_string(pubkey), limit=1000)
    if not sigs.value:
        return None, None

    oldest_sig = sigs.value[-1].signature
    tx = await async_client.get_transaction(oldest_sig, max_supported_transaction_version=0)

    if not tx.value:
        return None, None
    block_time = tx.value.block_time
    fund_datetime = datetime.datetime.now(datetime.UTC).isoformat() if block_time else None

    try:
        funder_pk = str(tx.value.transaction.transaction.message.account_keys[0])
    except Exception:
        funder_pk = None

    return fund_datetime, funder_pk

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

    print(f"Добавлено {n} кошельков → {output}")

def generate_funds(n = 10, password = None):
    wallets = []

    if password is not None:
        for _ in range(n):
            kp = Keypair()
            wallets.append({"sk" : str(encrypt_secret(bytes(kp), password)), "pk" : str(kp.pubkey())})

        # сохраняем в JSON
        with open(FUNDS_JSON, "w") as f:
            json.dump(wallets, f, ensure_ascii=False, indent=4)

        print(f"Сгенерировано {n} кошельков → {FUNDS_JSON}")
        return    
    
    print("No password")
    return
def password_buffer():
    retry = 0

    while retry < 3:
        password = getpass.getpass("Enter password: ")
        password_check = getpass.getpass("Confirm password: ")
        if password_check != password:
            print("Passwords does not match!")
            retry += 1
        else:
            print("Passwords match!")
            return password
    print("Too many retries, blocking.")
    return

if __name__ == "__main__":
    password = password_buffer()
    
    csv_type = input("Enter the type of csv you'd like to extend (MEXC, Gate) or enter f to recreate fundings file: ")

    amount = int(input("Enter wallets amount: "))

    if csv_type == "MEXC":
        generate_wallets(password, n=amount, output=MEXC_COLD_CSV)
    elif csv_type == "Gate":
        generate_wallets(password, n=amount, output=GATE_COLD_CSV)
    elif csv_type == "f":
        s = input("Are you sure you want to recreate fundings file? (y/n): ")
        if s == "y":
            generate_funds(amount, password)
        else: 
            print("ok")